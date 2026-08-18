#!/usr/bin/env python3
"""
Lista os metodos de controllers e services Angular (mesma deteccao usada em
verificar_metodos_angular_nao_usados.py -- opcao 3 do menu de
verificar.py: verificar_metodos_controller_nao_usados.py +
verificar_metodos_nao_usados.py) para voce selecionar UM metodo (fzf,
digite para filtrar) e ver TODOS os lugares onde ele parece ser usado --
em outros .js E em HTML (ng-click, etc.). Ao contrario dos scripts
'verificar_metodos_*_nao_usados.py', que so reportam os que NAO tem
nenhum uso, este lista os lugares de uso de um metodo especifico
escolhido por voce.

Uso:
    python3 verificar_usos_metodo.py [pasta_frontend]

Se o diretorio nao for passado como argumento, o script pergunta
interativamente (seletor fzf, se disponivel, ou Tab para autocompletar).

Como funciona (resumo):
  Reaproveita a deteccao de controllers/services dos dois scripts originais
  (collect_controllers/collect_services, mapeamento view->controller,
  resolucao de apelido de service via $inject, etc.). 'vm.metodo(' e
  '.metodo(' sozinhos nao provam nada -- dois controllers/services sem
  relacao podem ter, cada um, um metodo de mesmo nome -- entao cada
  ocorrencia encontrada e classificada em tres niveis:

    - CONFIRMADO: identidade verificada (dentro do escopo do controller --
      proprio arquivo + descendentes via $controller()+angular.extend +
      HTML mapeado via rota/modal para esse escopo -- ou 'alias.metodo('
      com alias resolvido via $inject ate ESTE service).

    - DE OUTRO CONTROLLER/SERVICE: identidade TAMBEM verificada, mas para
      um controller/service diferente (o .js registra outro controller; a
      view esta mapeada por rota/modal a outro controller; ou o apelido
      resolve, naquele arquivo, para outro service conhecido) -- ou seja,
      comprovadamente NAO e o metodo selecionado, so uma coincidencia de
      nome. Essas ocorrencias sao DESCARTADAS da listagem (so a contagem
      aparece, para deixar claro que nao e "nada encontrado").

    - INCERTO: nao foi possivel identificar a quem aquele 'vm'/apelido
      pertence (arquivo .js sem registro de controller conhecido; view via
      ng-include/templateUrl dinamico/nao mapeada; apelido que nao bate
      com nenhum service conhecido) -- unico caso que realmente precisa de
      revisao manual.

  Chamada solta ao nome da funcao dentro do proprio arquivo (reuso
  interno) tambem e verificada, contando so ocorrencias DESQUALIFICADAS
  (nao precedidas de '.', que seria chamada a um metodo de mesmo nome em
  OUTRO objeto) e que nao sejam a propria declaracao 'function nome('.

  Script heuristico (regex) -- uso via bind(), apply/call dinamico pode
  nao ser detectado. Revise manualmente os resultados incertos.
"""

import os
import re
import shutil
import subprocess
import sys

import verificar_metodos_controller_nao_usados as ctrl_module
import verificar_metodos_nao_usados as svc_module
from verificar_apis import (
    ask_dir,
    build_aligned_line,
    code_preview_cmd,
    find_files,
    format_view_mapping_log,
    map_html_to_controllers,
    pick_and_open_in_editor,
    setup_path_completion,
    strip_comments,
    warn,
)


# --------------------------------------------------------------------------
# Lista de metodos selecionaveis (controllers + services)
# --------------------------------------------------------------------------

def build_selectable_items(controllers, services):
    items = []
    for path, info in controllers.items():
        for key, data in info['methods'].items():
            items.append({
                'kind': 'controller',
                'entity': info['name'],
                'key': key,
                'func': data['func'],
                'inline': data['inline'],
                'file': path,
                'line': data['line'],
            })
    for name, info in services.items():
        for key, data in info['methods'].items():
            items.append({
                'kind': 'service',
                'entity': name,
                'key': key,
                'func': data['func'],
                'inline': False,
                'file': info['file'],
                'line': data['line'],
            })
    items.sort(key=lambda it: (it['kind'], it['entity'].lower(), it['key'].lower()))
    return items


def format_selectable_item(it):
    if it['kind'] == 'controller':
        tag = ' ' + warn('[inline]') if it['inline'] else ''
        return f"[controller] {it['entity']}.vm.{it['key']}(){tag}"
    return f"[service]    {it['entity']}.{it['key']}()"


def pick_item_plain(items, format_item):
    print("\nMetodos disponiveis:")
    for i, item in enumerate(items):
        print(f"  {i + 1}) {format_item(item)}")
    raw = input("\nNumero (ou parte do nome, para filtrar) -- vazio para sair: ").strip()
    if not raw:
        return None
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(items):
            return items[idx]
        return None
    except ValueError:
        pass
    matches = [it for it in items if raw.lower() in format_item(it).lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print(f"{len(matches)} correspondencia(s) -- refine mais a busca.")
    else:
        print("Nenhuma correspondencia.")
    return None


def pick_item(items, format_item, header):
    """Seletor fzf de UM item (com preview do trecho de codigo da
    definicao), devolvendo o item escolhido (ou None se cancelar). Sem
    fzf/tty, cai para pick_item_plain."""
    if not items:
        return None
    if shutil.which('fzf') is None or not sys.stdin.isatty():
        return pick_item_plain(items, format_item)

    line_width = max((len(str(item.get('line') or 1)) for item in items), default=1)
    lines = []
    for i, item in enumerate(items):
        file_path = item.get('file') or ''
        line_no = item.get('line') or 1
        label = format_item(item)
        display = build_aligned_line(label, file_path, f"{line_no:>{line_width}}")
        lines.append(f"{i}\t{display}\t{file_path}\t{line_no}")

    preview_cmd = code_preview_cmd()
    try:
        proc = subprocess.run(
            ['fzf', '--ansi', '--delimiter=\t', '--with-nth=2',
             '--preview', preview_cmd, '--preview-window=up:55%:wrap',
             '--height=90%', '--reverse', '--header=' + header],
            input='\n'.join(lines), capture_output=True, text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    idx_str = proc.stdout.split('\t', 1)[0]
    try:
        return items[int(idx_str)]
    except (ValueError, IndexError):
        return None


# --------------------------------------------------------------------------
# Busca de usos
# --------------------------------------------------------------------------

def find_bare_call_usages(content, func_name):
    """Posicoes de 'func_name(' que sao uma chamada DIRETA e desqualificada
    a funcao local -- exclui tanto a propria declaracao ('function
    func_name(') quanto acesso de membro em outro objeto ('obj.func_name(',
    que e uma chamada a um metodo de mesmo nome em OUTRO objeto, ex.: um
    service com metodo homonimo -- e nao a funcao local; um '.' antes do
    nome ja satisfaz '\\b' sozinho, entao o regex sem esse filtro conta
    'unidadeService.recuperarUnidadeMovimento(' como se fosse uma chamada a
    'function recuperarUnidadeMovimento()' local de mesmo nome)."""
    if not func_name:
        return []
    pattern = re.compile(r'\b' + re.escape(func_name) + r'\s*\(')
    usages = []
    for m in pattern.finditer(content):
        prefix = content[:m.start()].rstrip()
        if prefix.endswith('function') or prefix.endswith('.'):
            continue
        usages.append(m.start())
    return usages


def matches_with_lines(content, pattern):
    return [content.count('\n', 0, m.start()) + 1 for m in pattern.finditer(content)]


STATUS_ORDER = {'confirmed': 0, 'different': 1, 'uncertain': 2}


def find_controller_usages(item, controllers, all_js, all_html, view_controllers, children_map):
    js_by_path = dict(all_js)
    path_by_name = {info['name']: path for path, info in controllers.items()}

    # dono definitivo de cada .js: o controller que ESSE arquivo registra
    # (independente de ter ou nao metodos expostos detectados) -- 'vm'
    # dentro desse arquivo e, sem ambiguidade, o 'this' DAQUELE controller
    # (convencao do projeto: um controller por arquivo, controllerAs 'vm').
    js_owner = {}
    for path, content in all_js:
        m = ctrl_module.CONTROLLER_REGISTER_RE.search(content)
        if m:
            js_owner[path] = m.group(1)

    html_by_ctrl = {}
    for html_path, names in view_controllers.items():
        for name in names:
            html_by_ctrl.setdefault(name, set()).add(html_path)

    name = item['entity']
    key = item['key']
    func = item['func']
    own_path = item['file']

    scope_names = ctrl_module.descendants_of(name, children_map)
    scope_files = {path_by_name[n] for n in scope_names if n in path_by_name}
    scope_html = set()
    for n in scope_names:
        scope_html |= html_by_ctrl.get(n, set())

    usages = []

    if func:
        own_content = js_by_path[own_path]
        for pos in find_bare_call_usages(own_content, func):
            line = own_content.count('\n', 0, pos) + 1
            usages.append({
                'file': own_path, 'line': line, 'status': 'confirmed',
                'note': 'reuso interno (chamada direta no mesmo arquivo)',
            })

    # 'vm' e sempre o controllerAs deste projeto, entao 'vm.key(' por si so
    # nao prova nada -- so conta como uso CONFIRMADO deste controller
    # quando o arquivo/HTML esta dentro do escopo dele (proprio .js +
    # descendentes via $controller()+angular.extend + HTMLs mapeados via
    # rota/modal para esse escopo). Quando o arquivo/view pertence,
    # comprovadamente, a OUTRO controller conhecido (o .js registra outro
    # controller; ou a view esta mapeada via rota/modal para outro
    # controller), 'vm' la e literalmente uma instancia diferente -- e
    # DEFINITIVAMENTE nao e este metodo, nao so "incerto". So fica
    # realmente incerto quando nao ha como saber a quem aquele 'vm'
    # pertence (arquivo sem registro de controller -- directive/filter/
    # config; ou view sem mapeamento -- ng-include, templateUrl dinamico).
    pattern = re.compile(r'\bvm\.' + re.escape(key) + r'\s*\(')
    for path, content in all_js:
        for line in matches_with_lines(content, pattern):
            if path in scope_files:
                status, note = 'confirmed', f"vm.{key}()"
            else:
                owner = js_owner.get(path)
                if owner:
                    status = 'different'
                    note = f"vm.{key}()  [pertence ao controller '{owner}' -- NAO e este metodo]"
                else:
                    status = 'uncertain'
                    note = f"vm.{key}()  [arquivo nao registra nenhum controller conhecido -- confira manualmente]"
            usages.append({'file': path, 'line': line, 'status': status, 'note': note})
    for path, content in all_html:
        for line in matches_with_lines(content, pattern):
            if path in scope_html:
                status, note = 'confirmed', f"vm.{key}() no HTML"
            else:
                owners = view_controllers.get(path)
                if owners:
                    status = 'different'
                    note = f"vm.{key}() no HTML  [view pertence ao controller '{', '.join(sorted(owners))}' -- NAO e este metodo]"
                else:
                    status = 'uncertain'
                    note = f"vm.{key}() no HTML  [view nao mapeada a nenhum controller conhecido (ng-include? templateUrl dinamico?) -- confira manualmente]"
            usages.append({'file': path, 'line': line, 'status': status, 'note': note})

    usages.sort(key=lambda u: (STATUS_ORDER[u['status']], u['file'], u['line']))
    return usages


def find_service_usages(item, services, all_js, all_html):
    js_by_path = dict(all_js)
    alias_maps = {path: svc_module.build_alias_map(content) for path, content in all_js}

    name = item['entity']
    key = item['key']
    func = item['func']
    own_path = item['file']

    usages = []

    own_content = js_by_path[own_path]
    for pos in find_bare_call_usages(own_content, func):
        line = own_content.count('\n', 0, pos) + 1
        usages.append({
            'file': own_path, 'line': line, 'status': 'confirmed',
            'note': 'reuso interno (chamada direta no mesmo arquivo)',
        })

    # 'alias.key(' so conta como uso CONFIRMADO deste service quando o
    # alias foi resolvido casando '$inject' com os parametros da funcao
    # do arquivo -- ou seja, o arquivo realmente injeta ESTE service (nao
    # so tem uma variavel de mesmo nome por acaso).
    for path, content in all_js:
        if path == own_path:
            continue
        alias = alias_maps.get(path, {}).get(name)
        if not alias:
            continue
        pattern = re.compile(r'\b' + re.escape(alias) + r'\.' + re.escape(key) + r'\s*\(')
        for line in matches_with_lines(content, pattern):
            usages.append({
                'file': path, 'line': line, 'status': 'confirmed',
                'note': f"{alias}.{key}()  (injeta '{name}')",
            })

    if not usages:
        # rede de seguranca: alias nao resolveu para ESTE service em
        # lugar nenhum -- busca ampla por '.key(' em qualquer objeto. Se o
        # identificador antes do ponto e, PARA AQUELE ARQUIVO, o apelido
        # de OUTRO service conhecido (via $inject daquele mesmo arquivo),
        # a chamada pertence definitivamente a esse outro service, nao ao
        # selecionado -- so fica realmente incerto quando o identificador
        # nao bate com apelido de nenhum service conhecido (variavel local,
        # $scope, elemento DOM, etc.).
        loose_pattern = re.compile(r'\b(\w+)\.\s*' + re.escape(key) + r'\s*\(')
        for path, content in all_js:
            if path == own_path:
                continue
            alias_to_service = {v: k for k, v in alias_maps.get(path, {}).items()}
            for m in loose_pattern.finditer(content):
                line = content.count('\n', 0, m.start()) + 1
                obj = m.group(1)
                other_service = alias_to_service.get(obj)
                if other_service and other_service != name and other_service in services:
                    usages.append({
                        'file': path, 'line': line, 'status': 'different',
                        'note': f"{obj}.{key}()  [pertence ao service '{other_service}' -- NAO e este metodo]",
                    })
                else:
                    usages.append({
                        'file': path, 'line': line, 'status': 'uncertain',
                        'note': f"{obj}.{key}()  [correspondencia generica -- apelido nao identificado como nenhum service conhecido, confira manualmente]",
                    })
        for path, content in all_html:
            for line in matches_with_lines(content, re.compile(r'\.\s*' + re.escape(key) + r'\s*\(')):
                usages.append({
                    'file': path, 'line': line, 'status': 'uncertain',
                    'note': "correspondencia generica '." + key + "()' no HTML -- confira manualmente se e o mesmo metodo",
                })

    usages.sort(key=lambda u: (STATUS_ORDER[u['status']], u['file'], u['line']))
    return usages


def print_usage_group(title, group):
    if not group:
        return
    print(f"{title} ({len(group)}):\n")
    by_file = {}
    for u in group:
        by_file.setdefault(u['file'], []).append(u)
    for f in sorted(by_file):
        print(f"- {f}")
        for u in sorted(by_file[f], key=lambda u: u['line']):
            print(f"    linha {u['line']:>5}  {u['note']}")
        print()


def print_usage_report(item, usages, dismissed=0):
    """'usages' ja vem SEM os itens 'different' (descartados por pertencerem,
    comprovadamente, a outro controller/service -- ver main()); 'dismissed'
    e so a contagem deles, para deixar claro que existiam e foram
    ocultados de proposito (nao que a busca falhou em achar nada)."""
    label = format_selectable_item(item)
    print("\n" + "=" * 78)
    if not usages:
        print(f"Nenhum uso encontrado para {label}.")
        print("(Pode ser um metodo realmente orfao -- ou usado de um jeito que este "
              "script nao reconhece: bind(), apply/call dinamico, etc.)")
    else:
        confirmed = [u for u in usages if u['status'] == 'confirmed']
        uncertain = [u for u in usages if u['status'] == 'uncertain']
        print(f"{len(usages)} lugar(es) encontrado(s) para {label}:\n")
        print_usage_group("USOS CONFIRMADOS (identidade verificada -- e este metodo mesmo)", confirmed)
        print_usage_group(
            warn("REALMENTE INCERTO (nao foi possivel identificar a quem pertence -- "
                 "ng-include, templateUrl dinamico, apelido nao resolvido, etc. -- confira manualmente)"),
            uncertain)
    if dismissed:
        print(f"({dismissed} ocorrencia(s) com o mesmo nome, mas comprovadamente de outro "
              f"controller/service, foram descartadas da listagem.)")
    print("=" * 78)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    setup_path_completion()
    args = sys.argv[1:]
    home = os.path.expanduser('~')
    frontend_dir = ask_dir(
        "Diretorio com os controllers/services Angular (frontend, ex.: .../web/src/main/angular): ",
        args[0] if len(args) > 0 else None,
        search_root=home,
        header='Selecione a pasta do FRONTEND (controllers/services Angular)',
    )

    print("\nLendo arquivos .js e .html...")
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

    print(f"  {len(all_js)} arquivo(s) .js e {len(all_html)} arquivo(s) .html analisado(s).")

    controllers = ctrl_module.collect_controllers(all_js)
    services = svc_module.collect_services(all_js)
    children_map = ctrl_module.build_children_map(controllers)

    print("\nMapeando views (templateUrl) para controllers (rotas + modais)...")
    view_controllers, unresolved, not_found = map_html_to_controllers(all_js, frontend_dir, html_paths)
    print(format_view_mapping_log(view_controllers, unresolved, not_found))

    items = build_selectable_items(controllers, services)
    total_ctrl_methods = sum(len(c['methods']) for c in controllers.values())
    total_svc_methods = sum(len(s['methods']) for s in services.values())
    print(f"\n{len(controllers)} controller(s) [{total_ctrl_methods} metodo(s)] | "
          f"{len(services)} service(s) [{total_svc_methods} metodo(s)] | "
          f"{len(items)} metodo(s) selecionavel(is) no total.")

    if not items:
        print("Nenhum controller/service com metodos detectados nessa pasta.")
        return

    while True:
        item = pick_item(items, format_selectable_item,
                          header='Selecione um metodo para ver onde e usado (Esc para sair)')
        if item is None:
            print("Ate mais.")
            return
        if item['kind'] == 'controller':
            usages = find_controller_usages(item, controllers, all_js, all_html, view_controllers, children_map)
        else:
            usages = find_service_usages(item, services, all_js, all_html)
        dismissed = sum(1 for u in usages if u['status'] == 'different')
        usages = [u for u in usages if u['status'] != 'different']
        print_usage_report(item, usages, dismissed)
        if usages:
            # ha resultado -> segue direto pro fzf de pick_and_open_in_editor,
            # que ja mostra os mesmos itens (com preview) sem precisar de
            # tecla extra.
            pick_and_open_in_editor(usages, lambda u: u['note'])
        elif sys.stdin.isatty():
            # sem nenhum resultado, nao ha fzf nenhum a seguir -- sem essa
            # pausa, o fzf do PROXIMO pick_item (mais abaixo, no topo do
            # loop) assume a tela cheia em seguida e a mensagem que acabou
            # de ser impressa some antes de dar tempo de ler.
            try:
                input("\nPressione Enter para continuar...")
            except (EOFError, KeyboardInterrupt):
                print("\nAte mais.")
                return


if __name__ == '__main__':
    main()
