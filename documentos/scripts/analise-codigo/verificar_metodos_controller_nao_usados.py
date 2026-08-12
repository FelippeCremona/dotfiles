#!/usr/bin/env python3
"""
Lista metodos de controllers Angular (expostos via 'vm.metodo = ...') que
nao parecem ser chamados em nenhum HTML (ng-click, etc.) nem em nenhum
outro arquivo JS do frontend.

Uso:
    python3 verificar_metodos_controller_nao_usados.py [pasta_frontend]

Se o diretorio nao for passado como argumento, o script pergunta
interativamente (seletor fzf, se disponivel, ou Tab para autocompletar).

Como funciona (resumo):
  Neste projeto 'controllerAs' e sempre 'vm', mas isso NAO significa que
  'vm.metodo(' em qualquer HTML/JS do projeto conta como uso do metodo de
  QUALQUER controller: dois controllers sem nenhuma relacao podem ter,
  cada um, seu proprio metodo 'vm.algo' com o mesmo nome, e uma busca
  puramente global confundiria as duas coisas (fazendo um metodo
  realmente orfao parecer "usado" so por coincidencia de nome). Por isso a
  busca principal e ESCOPADA por controller, usando o mapeamento
  view -> controller de 'map_html_to_controllers' (le templateUrl/
  controller nas rotas do $stateProvider e nos modais $modal.open/
  $uibModal.open, em verificar_apis.py):

  Um metodo e considerado "sem uso" se, em ordem:
    (a) nao ha chamada solta 'metodo(' em outro ponto do PROPRIO arquivo
        (reuso interno, ex.: um metodo de vm chamando outro internamente);
    (b) nao ha 'vm.metodo(' no proprio arquivo do controller, nos arquivos
        dos controllers FILHOS (heranca via $controller(...) +
        angular.extend(this, ...), transitivamente) nem nos HTMLs
        mapeados via rota/modal para o controller ou algum desses filhos;
    (c) [rede de seguranca 1] nao ha 'vm.metodo(' em nenhum HTML que nao
        foi possivel mapear a um controller (ex.: partials via ng-include,
        ou templateUrl com expressao dinamica) nem em nenhum outro .js; e
    (d) [rede de seguranca 2] uma busca ampla por '.metodo(' (qualquer
        objeto, em TUDO) tambem nao acha nada.

  As redes de seguranca (c)/(d) existem porque o mapeamento view->
  controller e heuristico (regex) e pode nao cobrir 100% dos casos; elas
  evitam que a precisao extra do escopo por controller vire falso
  positivo quando a view realmente usada nao pode ser identificada.
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
    warn,
)

CONTROLLER_REGISTER_RE = re.compile(r'''\.controller\(\s*['"](\w+)['"]\s*,\s*(\w+)\s*\)''')
PARENT_CONTROLLER_RE = re.compile(r'''\$controller\(\s*['"](\w+)['"]''')
FUNC_DEF_RE = re.compile(r'\bfunction\s+(\w+)\s*\(')
VM_EXPOSE_BARE_RE = re.compile(r'\bvm\.(\w+)\s*=\s*(\w+)\s*;')
VM_EXPOSE_FUNC_RE = re.compile(r'\bvm\.(\w+)\s*=\s*function\b')


def collect_controllers(js_files):
    """js_files: lista de (path, content_sem_comentarios).
    Retorna dict path -> {'name', 'parent', 'methods': {chave: {...}}}."""
    controllers = {}
    for path, content in js_files:
        reg = CONTROLLER_REGISTER_RE.search(content)
        if not reg:
            continue
        name = reg.group(1)

        func_def_names = set(FUNC_DEF_RE.findall(content))
        methods = {}

        for m in VM_EXPOSE_BARE_RE.finditer(content):
            key, value = m.group(1), m.group(2)
            if value not in func_def_names:
                continue  # nao referencia uma funcao -> e propriedade/dado, nao metodo
            dm = re.search(r'\bfunction\s+' + re.escape(value) + r'\s*\(', content)
            line = content.count('\n', 0, dm.start()) + 1 if dm else content.count('\n', 0, m.start()) + 1
            methods.setdefault(key, {'func': value, 'inline': False, 'line': line})

        for m in VM_EXPOSE_FUNC_RE.finditer(content):
            key = m.group(1)
            line = content.count('\n', 0, m.start()) + 1
            methods.setdefault(key, {'func': None, 'inline': True, 'line': line})

        if not methods:
            continue

        parent_match = PARENT_CONTROLLER_RE.search(content)
        controllers[path] = {
            'name': name,
            'parent': parent_match.group(1) if parent_match else None,
            'methods': methods,
        }
    return controllers


def method_used_internally(content, func_name):
    if not func_name:
        return False
    occurrences = len(re.findall(r'\b' + re.escape(func_name) + r'\s*\(', content))
    return occurrences > 1


def find_keys_matching_anywhere(contents, keys, template):
    """Varre 'contents' UMA vez com um regex combinado (alternancia de todas
    as 'keys' de uma vez) em vez de um regex por chave por arquivo -- e o
    que torna a busca viavel com milhares de metodos e centenas de arquivos."""
    if not keys:
        return set()
    pattern = re.compile(template.format(alt='|'.join(re.escape(k) for k in sorted(keys))))
    found = set()
    for content in contents:
        for m in pattern.finditer(content):
            found.add(m.group(1))
        if len(found) == len(keys):
            break
    return found


def build_children_map(controllers):
    children = {}
    for info in controllers.values():
        if info['parent']:
            children.setdefault(info['parent'], []).append(info['name'])
    return children


def descendants_of(name, children_map):
    """Fecho transitivo de 'name' + todos os controllers que o estendem
    (direta ou indiretamente) via $controller(...) + angular.extend(this,
    ...). Um metodo definido no controller base conta como usado se
    QUALQUER descendente (ou o HTML de qualquer descendente) o chamar."""
    result = set()
    stack = [name]
    while stack:
        n = stack.pop()
        if n in result:
            continue
        result.add(n)
        stack.extend(children_map.get(n, []))
    return result


def controller_scope_content(name, children_map, path_by_name, js_by_path, html_by_ctrl, html_by_path):
    """Conteudo (proprio .js + .js dos descendentes + HTMLs mapeados via
    rota/modal para o controller ou algum desses descendentes) usado como
    escopo de busca por uso de um membro do controller 'name'."""
    content = []
    for n in descendants_of(name, children_map):
        p = path_by_name.get(n)
        if p:
            content.append(js_by_path[p])
        for h in html_by_ctrl.get(n, ()):
            content.append(html_by_path[h])
    return content


def find_unused_controller_methods(controllers, all_js, all_html, view_controllers, children_map):
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
        for key, data in info['methods'].items():
            if method_used_internally(own_content, data['func']):
                continue
            pending.append((path, info, key, data))

    # 2) busca ESCOPADA: 'vm.chave(' so no proprio controller + descendentes
    #    (proprio .js + HTMLs mapeados via rota/modal para esse escopo) --
    #    evita que um metodo de mesmo nome em um controller SEM RELACAO
    #    nenhuma faca um metodo realmente orfao parecer "usado".
    scope_cache = {}
    still_pending = []
    for path, info, key, data in pending:
        name = info['name']
        if name not in scope_cache:
            scope_cache[name] = controller_scope_content(
                name, children_map, path_by_name, js_by_path, html_by_ctrl, html_by_path)
        pattern = re.compile(r'\bvm\.' + re.escape(key) + r'\s*\(')
        if any(pattern.search(c) for c in scope_cache[name]):
            continue
        still_pending.append((path, info, key, data))

    # 3) rede de seguranca 1: 'vm.chave(' em HTML que nao pode ser mapeado a
    #    um controller (partials via ng-include, templateUrl dinamico) ou em
    #    QUALQUER .js -- fallback para nao gerar falso positivo quando a
    #    view realmente usada nao pode ser identificada.
    fallback_content = all_js_content + unmapped_html_content
    pending_keys = {key for _, _, key, _ in still_pending}
    found_fallback = find_keys_matching_anywhere(fallback_content, pending_keys, r'\bvm\.({alt})\s*\(')
    remaining = [(p, i, k, d) for p, i, k, d in still_pending if k not in found_fallback]

    # 4) rede de seguranca 2: '.chave(' em qualquer objeto, em TUDO
    all_content = all_js_content + [c for _, c in all_html]
    remaining_keys = {key for _, _, key, _ in remaining}
    found_loose = find_keys_matching_anywhere(all_content, remaining_keys, r'\.\s*({alt})\s*\(')
    truly_unused_keys = remaining_keys - found_loose

    unused = []
    for path, info, key, data in remaining:
        if key not in truly_unused_keys:
            continue
        unused.append({
            'file': path,
            'controller': info['name'],
            'parent': info['parent'],
            'method': key,
            'line': data['line'],
            'inline': data['inline'],
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

    controllers = collect_controllers(all_js)
    total_methods = sum(len(c['methods']) for c in controllers.values())
    log(f"  {len(controllers)} controller(s) encontrado(s), {total_methods} metodo(s) expostos via 'vm.' no total.")

    children_map = build_children_map(controllers)

    log("\nMapeando views (templateUrl) para controllers (rotas + modais)...")
    view_controllers, unresolved, not_found = map_html_to_controllers(all_js, frontend_dir, html_paths)
    log(format_view_mapping_log(view_controllers, unresolved, not_found))

    log("\nProcurando usos (escopado por controller, com rede de seguranca global)...")
    unused = find_unused_controller_methods(controllers, all_js, all_html, view_controllers, children_map)

    return {
        'controllers': controllers,
        'total_methods': total_methods,
        'unused': unused,
        'children_map': children_map,
        'view_controllers': view_controllers,
    }


def format_unused_controller_method(u):
    tag = ' ' + warn('[inline]') if u['inline'] else ''
    return f"{u['controller']}.vm.{u['method']}(){tag}"


def print_report(result):
    unused = result['unused']
    children_map = result['children_map']
    print("\n" + "=" * 78)
    if unused:
        print(f"Metodos de controller SEM nenhum sinal de uso encontrado: {len(unused)}\n")
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
                tag = ' ' + warn('[inline]') if u['inline'] else ''
                print(f"    linha {u['line']:>5}  vm.{u['method']}(){tag}")
            print()
    else:
        print("Nenhum metodo de controller orfao encontrado: todos tem algum sinal de uso.")

    print("=" * 78)
    print(f"Resumo: {len(result['controllers'])} controller(s) | {result['total_methods']} metodo(s) expostos | "
          f"{len(unused)} sem uso encontrado")
    print("\nObs.: script heuristico (regex). So considera metodos expostos no padrao "
          "'vm.metodo = metodo;' ou 'vm.metodo = function(...) {...}' (padrao usado neste "
          "projeto; controllerAs e sempre 'vm'). Propriedades/dados (vm.algo = valor, sem "
          "referenciar uma funcao) nao entram na analise. A busca de uso e ESCOPADA por "
          "controller (proprio .js + descendentes via $controller(...)+angular.extend(this,"
          "...) + HTMLs mapeados via rota/modal para esse escopo) -- um metodo do controller "
          "base conta como usado se QUALQUER descendente (js ou html) o chamar, mas um metodo "
          "de mesmo nome num controller SEM RELACAO nao conta mais como uso. Como rede de "
          "seguranca, tambem checa HTML nao mapeado a nenhum controller (partials via "
          "ng-include, templateUrl dinamico) e, por ultimo, '.metodo(' solto em qualquer "
          "objeto -- para nao gerar falso positivo quando a view real nao pode ser "
          "identificada. Uso via bind(), apply/call dinamico pode nao ser detectado. Revise "
          "manualmente antes de remover algo.")


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
    pick_and_open_in_editor(result['unused'], format_unused_controller_method)


if __name__ == '__main__':
    main()
