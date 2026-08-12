#!/usr/bin/env python3
"""
Lista variaveis/atributos de controllers Angular (expostos via
'vm.atributo = <valor>', sem ser uma funcao) que nao parecem ser lidos em
nenhum HTML (interpolacao, ng-model, ng-if, etc.), no proprio controller,
nem em outro controller.

Uso:
    python3 verificar_variaveis_controller_nao_usadas.py [pasta_frontend]

Se o diretorio nao for passado como argumento, o script pergunta
interativamente (seletor fzf, se disponivel, ou Tab para autocompletar).

Como funciona (resumo):
  Complementa o 'verificar_metodos_controller_nao_usados.py': aquele script
  cobre 'vm.algo = function...' / 'vm.algo = nomeDeFuncao;' (metodos); este
  aqui cobre tudo que sobra em 'vm.algo = <expressao>;' quando <expressao>
  NAO e uma funcao inline nem uma referencia a uma funcao definida no
  arquivo -- ou seja, dado/estado exposto para a view (numeros, strings,
  booleanos, objetos, arrays, resultado de chamadas, etc.).

  Neste projeto 'controllerAs' e sempre 'vm', mas isso NAO significa que
  'vm.atributo' em qualquer .js/.html conta como leitura da variavel de
  QUALQUER controller: dois controllers sem nenhuma relacao podem ter,
  cada um, seu 'vm.atributo' com o mesmo nome, e uma busca puramente
  global confundiria as duas coisas. Por isso a busca principal e
  ESCOPADA por controller (mesmo mecanismo do script de metodos): proprio
  .js + .js dos controllers filhos (heranca via $controller(...) +
  angular.extend(this, ...), transitivamente) + HTMLs mapeados via rota/
  modal (map_html_to_controllers, em verificar_apis.py) para esse escopo.
  Como rede de seguranca, se nao achar nada no escopo, tambem procura em
  qualquer HTML que nao pode ser mapeado a um controller (partials via
  ng-include, templateUrl dinamico) e em qualquer outro .js -- para nao
  gerar falso positivo quando a view real nao pode ser identificada.

  Uma ocorrencia de 'vm.atributo' conta como "uso" (leitura) quando NAO e
  uma atribuicao simples ('vm.atributo = valor', sem ser '==', '===' etc.).
  Isso cobre leitura direta (vm.atributo), acesso a sub-propriedade
  (vm.atributo.x), comparacoes (vm.atributo === 'x'), incremento/decremento
  (vm.atributo++) e atribuicao composta (vm.atributo += 1). Uma variavel e
  considerada "sem uso" se so aparecer do lado esquerdo de atribuicoes
  simples -- ou seja, e escrita mas nunca lida.
"""

import os
import re
import sys

from verificar_apis import (
    ask_dir,
    find_files,
    find_repo_root,
    format_view_mapping_log,
    map_html_to_controllers,
    pick_and_open_in_editor,
    setup_path_completion,
    strip_comments,
)
from verificar_metodos_controller_nao_usados import (
    CONTROLLER_REGISTER_RE,
    FUNC_DEF_RE,
    PARENT_CONTROLLER_RE,
    build_children_map,
    controller_scope_content,
    find_keys_matching_anywhere,
)

VM_ASSIGN_RE = re.compile(r'\bvm\.(\w+)\s*=(?!=)\s*')
BARE_IDENT_RE = re.compile(r'^\w+$')
ARROW_FUNC_RE = re.compile(r'^\(?[\w\s,]*\)?\s*=>')

# Template para find_keys_matching_anywhere: conta como "uso" qualquer
# ocorrencia de 'vm.chave' que NAO seja uma atribuicao simples logo em
# seguida (permite '==', '===', '.subpropriedade', '++', '+=', etc.).
USAGE_TEMPLATE = r'\bvm\.({alt})\b(?!\s*=(?!=))'


def scan_assignment_value(content, pos):
    """pos aponta para logo apos 'vm.atributo = '. Retorna (texto_da_expressao,
    indice_do_';' que termina a atribuicao), respeitando strings/templates e
    aninhamento de (), [], {} -- necessario porque objetos/arrays literais
    costumam ser multi-linha."""
    depth = 0
    in_str = None
    i = pos
    n = len(content)
    start = i
    while i < n:
        c = content[i]
        if in_str:
            if c == '\\' and i + 1 < n:
                i += 2
                continue
            if c == in_str:
                in_str = None
            i += 1
            continue
        if c in '\'"`':
            in_str = c
            i += 1
            continue
        if c in '([{':
            depth += 1
            i += 1
            continue
        if c in ')]}':
            depth -= 1
            i += 1
            continue
        if c == ';' and depth == 0:
            break
        i += 1
    return content[start:i].strip(), i


def is_function_like(expr, func_def_names):
    if expr.startswith('function'):
        return True
    if ARROW_FUNC_RE.match(expr):
        return True
    if BARE_IDENT_RE.match(expr) and expr in func_def_names:
        return True
    return False


def collect_controller_vars(js_files):
    """js_files: lista de (path, content_sem_comentarios).
    Retorna dict path -> {'name', 'parent', 'variables': {chave: {...}}}."""
    controllers = {}
    for path, content in js_files:
        reg = CONTROLLER_REGISTER_RE.search(content)
        if not reg:
            continue
        name = reg.group(1)

        func_def_names = set(FUNC_DEF_RE.findall(content))
        variables = {}

        for m in VM_ASSIGN_RE.finditer(content):
            key = m.group(1)
            expr, _end = scan_assignment_value(content, m.end())
            if not expr or is_function_like(expr, func_def_names):
                continue  # e metodo (inline ou referencia a funcao) -> fora do escopo deste script
            line = content.count('\n', 0, m.start()) + 1
            snippet = expr if len(expr) <= 50 else expr[:47] + '...'
            variables.setdefault(key, {'line': line, 'expr': snippet})

        if not variables:
            continue

        parent_match = PARENT_CONTROLLER_RE.search(content)
        controllers[path] = {
            'name': name,
            'parent': parent_match.group(1) if parent_match else None,
            'variables': variables,
        }
    return controllers


def var_used_internally(content, key):
    pattern = re.compile(r'\bvm\.' + re.escape(key) + r'\b(?!\s*=(?!=))')
    return bool(pattern.search(content))


def find_unused_controller_vars(controllers, all_js, all_html, view_controllers, children_map):
    all_js_content = [c for _, c in all_js]
    js_by_path = dict(all_js)
    html_by_path = dict(all_html)
    path_by_name = {info['name']: path for path, info in controllers.items()}

    html_by_ctrl = {}
    for html_path, names in view_controllers.items():
        for name in names:
            html_by_ctrl.setdefault(name, set()).add(html_path)
    unmapped_html_content = [c for p, c in all_html if p not in view_controllers]

    # 1) reuso interno (rapido: so olha o proprio arquivo de cada controller)
    pending = []  # lista de (path, info, key, data)
    for path, info in controllers.items():
        own_content = js_by_path[path]
        for key, data in info['variables'].items():
            if var_used_internally(own_content, key):
                continue
            pending.append((path, info, key, data))

    # 2) busca ESCOPADA: leitura de 'vm.chave' so no proprio controller +
    #    descendentes (proprio .js + HTMLs mapeados via rota/modal para
    #    esse escopo) -- evita que uma variavel de mesmo nome num
    #    controller SEM RELACAO nenhuma faca uma variavel realmente orfa
    #    parecer "usada".
    scope_cache = {}
    still_pending = []
    for path, info, key, data in pending:
        name = info['name']
        if name not in scope_cache:
            scope_cache[name] = controller_scope_content(
                name, children_map, path_by_name, js_by_path, html_by_ctrl, html_by_path)
        pattern = re.compile(r'\bvm\.' + re.escape(key) + r'\b(?!\s*=(?!=))')
        if any(pattern.search(c) for c in scope_cache[name]):
            continue
        still_pending.append((path, info, key, data))

    # 3) rede de seguranca: leitura de 'vm.chave' em HTML que nao pode ser
    #    mapeado a um controller (partials via ng-include, templateUrl
    #    dinamico) ou em QUALQUER .js -- fallback para nao gerar falso
    #    positivo quando a view realmente usada nao pode ser identificada.
    fallback_content = all_js_content + unmapped_html_content
    pending_keys = {key for _, _, key, _ in still_pending}
    used_in_fallback = find_keys_matching_anywhere(fallback_content, pending_keys, USAGE_TEMPLATE)
    truly_unused_keys = pending_keys - used_in_fallback

    unused = []
    for path, info, key, data in still_pending:
        if key not in truly_unused_keys:
            continue
        unused.append({
            'file': path,
            'controller': info['name'],
            'parent': info['parent'],
            'var': key,
            'line': data['line'],
            'expr': data['expr'],
        })
    return unused


def analyze(frontend_dir, log=print):
    log("\nLendo arquivos .js e .html...")
    js_paths = find_files(frontend_dir, '.js')
    html_paths = find_files(frontend_dir, '.html')

    all_js = []
    for f in js_paths:
        try:
            with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                raw = fh.read()
        except OSError:
            continue
        all_js.append((f, strip_comments(raw)))

    all_html = []
    for f in html_paths:
        try:
            with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                all_html.append((f, fh.read()))
        except OSError:
            continue

    log(f"  {len(all_js)} arquivo(s) .js e {len(all_html)} arquivo(s) .html analisado(s).")

    controllers = collect_controller_vars(all_js)
    total_vars = sum(len(c['variables']) for c in controllers.values())
    log(f"  {len(controllers)} controller(s) encontrado(s), {total_vars} variavel(is) expostas via 'vm.' no total.")

    children_map = build_children_map(controllers)

    log("\nMapeando views (templateUrl) para controllers (rotas + modais)...")
    view_controllers, unresolved, not_found = map_html_to_controllers(all_js, frontend_dir, html_paths)
    log(format_view_mapping_log(view_controllers, unresolved, not_found))

    log("\nProcurando usos (escopado por controller, com rede de seguranca global)...")
    unused = find_unused_controller_vars(controllers, all_js, all_html, view_controllers, children_map)

    return {
        'controllers': controllers,
        'total_vars': total_vars,
        'unused': unused,
        'children_map': children_map,
        'view_controllers': view_controllers,
    }


def format_unused_var(u):
    return f"{u['controller']}.vm.{u['var']}"


def print_report(result):
    unused = result['unused']
    children_map = result['children_map']
    print("\n" + "=" * 78)
    if unused:
        print(f"Variaveis de controller SEM nenhum sinal de leitura encontrado: {len(unused)}\n")
        by_file = {}
        for u in unused:
            by_file.setdefault(u['file'], []).append(u)
        for f in sorted(by_file):
            items = sorted(by_file[f], key=lambda u: u['line'])
            ctrl_name = items[0]['controller']
            note = ''
            if ctrl_name in children_map:
                note = f"  [controller base, herdado por: {', '.join(sorted(children_map[ctrl_name]))}]"
            elif items[0]['parent']:
                note = f"  [estende {items[0]['parent']}]"
            print(f"- {f}  (controller '{ctrl_name}'){note}")
            for u in items:
                print(f"    linha {u['line']:>5}  vm.{u['var']} = {u['expr']}")
            print()
    else:
        print("Nenhuma variavel de controller orfa encontrada: todas tem algum sinal de leitura.")

    print("=" * 78)
    print(f"Resumo: {len(result['controllers'])} controller(s) | {result['total_vars']} variavel(is) expostas | "
          f"{len(unused)} sem uso encontrado")
    print("\nObs.: script heuristico (regex). Complementa "
          "'verificar_metodos_controller_nao_usados.py' -- cobre 'vm.atributo = <valor>' "
          "quando <valor> nao e uma funcao inline nem referencia a uma funcao definida no "
          "arquivo (controllerAs e sempre 'vm' neste projeto). Uma variavel conta como usada "
          "se aparecer em QUALQUER lugar que nao seja o lado esquerdo de uma atribuicao "
          "simples (leitura direta, sub-propriedade, comparacao, atribuicao composta, "
          "'++'/'--'). A busca de uso e ESCOPADA por controller (proprio .js + descendentes "
          "via $controller(...)+angular.extend(this,...) + HTMLs mapeados via rota/modal para "
          "esse escopo) -- uma variavel do controller base conta como usada se QUALQUER "
          "descendente (js ou html) a ler, mas uma variavel de mesmo nome num controller SEM "
          "RELACAO nao conta mais como uso. Como rede de seguranca, tambem checa HTML nao "
          "mapeado a nenhum controller (partials via ng-include, templateUrl dinamico) e "
          "qualquer outro .js -- para nao gerar falso positivo quando a view real nao pode "
          "ser identificada. Uso via bind(), apply/call dinamico, nomes de propriedade "
          "montados dinamicamente (vm[chave]) pode nao ser detectado. Revise manualmente "
          "antes de remover algo.")


def main():
    setup_path_completion()
    args = sys.argv[1:]
    home = os.path.expanduser('~')
    frontend_dir = ask_dir(
        "Diretorio com os controllers Angular (frontend, ex.: .../web/src/main/angular): ",
        args[0] if len(args) > 0 else None,
        search_root=home,
        header='Selecione a pasta do FRONTEND (controllers/views Angular)',
    )

    result = analyze(frontend_dir)
    print_report(result)
    pick_and_open_in_editor(result['unused'], format_unused_var)


if __name__ == '__main__':
    main()
