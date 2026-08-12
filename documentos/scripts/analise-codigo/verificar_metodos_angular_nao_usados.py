#!/usr/bin/env python3
"""
Roda verificar_metodos_nao_usados.py (services Angular),
verificar_metodos_controller_nao_usados.py (controllers Angular) e
verificar_funcoes_locais_nao_usadas.py (funcoes locais, .js) sobre a
MESMA pasta e junta os tres resultados em um unico relatorio/seletor.

Uso:
    python3 verificar_metodos_angular_nao_usados.py [pasta_frontend]

Se o diretorio nao for passado como argumento, o script pergunta
interativamente (seletor fzf, se disponivel, ou Tab para autocompletar).

Este script e so um "agregador": toda a logica de deteccao continua nos
tres scripts originais (que tambem podem ser rodados separados se voce
quiser o relatorio de apenas um deles, com as explicacoes completas de
como cada checagem funciona).
"""

import os
import sys

import verificar_funcoes_locais_nao_usadas as func_module
import verificar_metodos_controller_nao_usados as ctrl_module
import verificar_metodos_nao_usados as svc_module
from verificar_apis import ask_dir, pick_and_open_in_editor, setup_path_completion, strip_comments, warn


def classify_local_function_files(paths):
    """Para cada caminho em 'paths' (arquivos com funcao local orfa),
    decide se e um arquivo de controller ('.controller(...)') ou de
    service/factory ('.service(...)'/'.factory(...)'), para poder rotular
    o item como '[controller]'/'[service]' no seletor em vez de generico
    '[funcao local]'. Arquivos que nao sao nenhum dos dois (directive,
    config, filter, etc.) ficam sem classificacao."""
    kind_by_file = {}
    for path in paths:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                content = strip_comments(fh.read())
        except OSError:
            continue
        if ctrl_module.CONTROLLER_REGISTER_RE.search(content):
            kind_by_file[path] = 'controller'
        elif svc_module.SERVICE_REGISTER_RE.search(content):
            kind_by_file[path] = 'service'
    return kind_by_file


def analyze(frontend_dir, log=print):
    log("=== Services Angular ===")
    svc_result = svc_module.analyze(frontend_dir, log=log)
    log("\n=== Controllers Angular ===")
    ctrl_result = ctrl_module.analyze(frontend_dir, log=log)
    log("\n=== Funcoes locais (.js) ===")
    func_result = func_module.analyze(frontend_dir, log=log)

    local_func_paths = {u['file'] for u in func_result['unused']}
    file_kind = classify_local_function_files(local_func_paths)

    unused = []
    for u in svc_result['unused']:
        item = dict(u)
        item['kind'] = 'service'
        unused.append(item)
    for u in ctrl_result['unused']:
        item = dict(u)
        item['kind'] = 'controller'
        unused.append(item)
    for u in func_result['unused']:
        item = dict(u)
        item['kind'] = 'local_function'
        item['file_kind'] = file_kind.get(u['file'])
        unused.append(item)

    unused.sort(key=lambda u: (u['file'], u['line'] if u['line'] is not None else 0))

    return {
        'svc_services': len(svc_result['services']),
        'svc_methods': svc_result['total_methods'],
        'ctrl_controllers': len(ctrl_result['controllers']),
        'ctrl_methods': ctrl_result['total_methods'],
        'func_total_js': func_result['total_js'],
        'children_map': ctrl_result['children_map'],
        'unused': unused,
    }


def format_unused_item(u):
    if u['kind'] == 'service':
        return '[service]      ' + svc_module.format_unused_method(u)
    if u['kind'] == 'controller':
        return '[controller]   ' + ctrl_module.format_unused_controller_method(u)
    # local_function: rotula como '[controller]'/'[service]' se o arquivo
    # onde a funcao mora for reconhecido como um desses tipos; senao usa o
    # rotulo generico.
    file_kind = u.get('file_kind')
    if file_kind == 'controller':
        label = '[controller]   '
    elif file_kind == 'service':
        label = '[service]      '
    else:
        label = '[funcao local] '
    return label + func_module.format_unused_function(u)


def print_group_header(f, items, children_map):
    """Um mesmo arquivo pode ter itens de tipos diferentes ao mesmo tempo
    (ex.: um controller com metodos 'vm.algo' sem uso E funcoes locais sem
    uso) -- o cabecalho usa o primeiro item de service/controller que
    achar (se houver) para nomear o arquivo; funcoes locais nao tem nome
    de service/controller proprio."""
    header_name = None
    header_kind = None
    for it in items:
        if it['kind'] in ('service', 'controller'):
            header_kind = it['kind']
            header_name = it['service'] if it['kind'] == 'service' else it['controller']
            break

    if header_kind is None:
        print(f"- {f}")
        return

    note = ''
    if header_kind == 'controller':
        if header_name in children_map:
            note = f"  [controller base, herdado por: {', '.join(sorted(children_map[header_name]))}]"
        else:
            parent = next((it.get('parent') for it in items if it.get('parent')), None)
            if parent:
                note = f"  [estende {', '.join(parent)}]"
    label = 'service' if header_kind == 'service' else 'controller'
    print(f"- {f}  ({label} '{header_name}'){note}")


def print_item_line(u):
    if u['kind'] == 'service':
        linha = u['line'] if u['line'] is not None else '?'
        print(f"    linha {linha:>5}  {u['method']}()")
    elif u['kind'] == 'controller':
        tag = ' ' + warn('[inline]') if u['inline'] else ''
        print(f"    linha {u['line']:>5}  vm.{u['method']}(){tag}")
    else:
        print(f"    linha {u['line']:>5}  function {u['name']}()")


def print_report(result):
    unused = result['unused']
    children_map = result['children_map']
    print("\n" + "=" * 78)
    if unused:
        print(f"Metodos/funcoes Angular (services + controllers + funcoes locais) SEM nenhum "
              f"sinal de uso encontrado: {len(unused)}\n")
        by_file = {}
        for u in unused:
            by_file.setdefault(u['file'], []).append(u)
        for f in sorted(by_file):
            items = sorted(by_file[f], key=lambda u: u['line'] if u['line'] is not None else 0)
            print_group_header(f, items, children_map)
            for u in items:
                print_item_line(u)
            print()
    else:
        print("Nenhum metodo/funcao orfao encontrado (services + controllers + funcoes "
              "locais): todos tem algum sinal de uso.")

    print("=" * 78)
    print(f"Resumo: {result['svc_services']} service(s) [{result['svc_methods']} metodo(s) publico(s)] | "
          f"{result['ctrl_controllers']} controller(s) [{result['ctrl_methods']} metodo(s) expostos] | "
          f"{result['func_total_js']} arquivo(s) .js (funcoes locais) | "
          f"{len(unused)} sem uso encontrado no total")
    print("\nObs.: relatorio combinado de verificar_metodos_nao_usados.py (services Angular), "
          "verificar_metodos_controller_nao_usados.py (controllers Angular) e "
          "verificar_funcoes_locais_nao_usadas.py (funcoes locais, .js). Rode qualquer um dos "
          "tres separadamente se quiser a explicacao completa de como aquela checagem "
          "especifica funciona. Revise manualmente antes de remover algo.")


def main():
    setup_path_completion()
    args = sys.argv[1:]
    home = os.path.expanduser('~')
    frontend_dir = ask_dir(
        "Diretorio com os services/controllers Angular (frontend, ex.: .../web/src/main/angular): ",
        args[0] if len(args) > 0 else None,
        search_root=home,
        header='Selecione a pasta do FRONTEND (services/controllers Angular)',
    )

    result = analyze(frontend_dir)
    print_report(result)
    pick_and_open_in_editor(result['unused'], format_unused_item)


if __name__ == '__main__':
    main()
