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
  resolucao de apelido de service via $inject, etc.) e, para o metodo
  escolhido, procura:

    - Controller (metodo exposto via 'vm.metodo = ...'): toda ocorrencia
      de 'vm.metodo(' em QUALQUER .js/.html do projeto (aqui o objetivo e
      listar TODOS os lugares, nao decidir se e "orfao" -- por isso NAO e
      escopado por controller como no script original), mais chamada
      solta 'metodo(' dentro do proprio arquivo (reuso interno). Toda
      ocorrencia fora do escopo do proprio controller (arquivo/
      descendentes via $controller()+angular.extend/HTML mapeado via
      rota) e marcada como "fora do escopo", ja que dois controllers sem
      relacao podem ter, cada um, seu 'vm.metodo' com o mesmo nome.

    - Service (metodo exposto via 'return { chave: funcao }'): toda
      ocorrencia de 'apelido.metodo(' em arquivos que injetam aquele
      service (apelido resolvido casando '$inject' com os parametros da
      funcao), mais chamada solta dentro do proprio arquivo. Se nada for
      encontrado por apelido, cai para uma busca ampla por '.metodo(' em
      qualquer objeto, como ultimo recurso (marcada como incerta).

  Script heuristico (regex) -- uso via bind(), apply/call dinamico pode
  nao ser detectado. Revise manualmente os resultados.
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

def is_declaration_occurrence(content, match_start):
    """True se o match 'nome(' em match_start e a propria declaracao
    'function nome(' (nao uma chamada)."""
    return content[:match_start].rstrip().endswith('function')


def find_bare_call_usages(content, func_name):
    """Posicoes de 'func_name(' que NAO sao a declaracao 'function
    func_name(' -- reuso interno dentro do proprio arquivo."""
    if not func_name:
        return []
    pattern = re.compile(r'\b' + re.escape(func_name) + r'\s*\(')
    return [m.start() for m in pattern.finditer(content) if not is_declaration_occurrence(content, m.start())]


def matches_with_lines(content, pattern):
    return [content.count('\n', 0, m.start()) + 1 for m in pattern.finditer(content)]


def find_controller_usages(item, controllers, all_js, all_html, view_controllers, children_map):
    js_by_path = dict(all_js)
    path_by_name = {info['name']: path for path, info in controllers.items()}

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
                'file': own_path, 'line': line,
                'note': 'reuso interno (chamada direta no mesmo arquivo)',
            })

    pattern = re.compile(r'\bvm\.' + re.escape(key) + r'\s*\(')
    for path, content in all_js:
        for line in matches_with_lines(content, pattern):
            note = f"vm.{key}()"
            if path not in scope_files:
                note += warn(' [fora do escopo deste controller -- confira se e o mesmo metodo]')
            usages.append({'file': path, 'line': line, 'note': note})
    for path, content in all_html:
        for line in matches_with_lines(content, pattern):
            note = f"vm.{key}() no HTML"
            if path not in scope_html:
                note += warn(' [view nao mapeada a este controller -- confira se e o mesmo metodo]')
            usages.append({'file': path, 'line': line, 'note': note})

    usages.sort(key=lambda u: (u['file'], u['line']))
    return usages


def find_service_usages(item, all_js, all_html):
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
            'file': own_path, 'line': line,
            'note': 'reuso interno (chamada direta no mesmo arquivo)',
        })

    for path, content in all_js:
        if path == own_path:
            continue
        alias = alias_maps.get(path, {}).get(name)
        if not alias:
            continue
        pattern = re.compile(r'\b' + re.escape(alias) + r'\.' + re.escape(key) + r'\s*\(')
        for line in matches_with_lines(content, pattern):
            usages.append({'file': path, 'line': line, 'note': f"{alias}.{key}()  (injeta '{name}')"})

    if not usages:
        loose_pattern = re.compile(r'\.\s*' + re.escape(key) + r'\s*\(')
        for path, content in all_js:
            if path == own_path:
                continue
            for line in matches_with_lines(content, loose_pattern):
                usages.append({
                    'file': path, 'line': line,
                    'note': warn("possivel uso (correspondencia generica '.metodo()', apelido nao resolvido -- confira manualmente)"),
                })
        for path, content in all_html:
            for line in matches_with_lines(content, loose_pattern):
                usages.append({
                    'file': path, 'line': line,
                    'note': warn("possivel uso em HTML (correspondencia generica '.metodo()' -- confira manualmente)"),
                })

    usages.sort(key=lambda u: (u['file'], u['line']))
    return usages


def print_usage_report(item, usages):
    label = format_selectable_item(item)
    print("\n" + "=" * 78)
    if not usages:
        print(f"Nenhum uso encontrado para {label}.")
        print("(Pode ser um metodo realmente orfao -- ou usado de um jeito que este "
              "script nao reconhece: bind(), apply/call dinamico, etc.)")
    else:
        print(f"{len(usages)} lugar(es) onde {label} parece ser usado:\n")
        by_file = {}
        for u in usages:
            by_file.setdefault(u['file'], []).append(u)
        for f in sorted(by_file):
            print(f"- {f}")
            for u in sorted(by_file[f], key=lambda u: u['line']):
                print(f"    linha {u['line']:>5}  {u['note']}")
            print()
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
            usages = find_service_usages(item, all_js, all_html)
        print_usage_report(item, usages)
        pick_and_open_in_editor(usages, lambda u: u['note'])


if __name__ == '__main__':
    main()
