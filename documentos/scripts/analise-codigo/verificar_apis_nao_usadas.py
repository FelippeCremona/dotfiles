#!/usr/bin/env python3
"""
Verifica quais APIs (endpoints JAX-RS) do backend NAO possuem nenhuma
chamada correspondente no frontend (Angular/$http). E o inverso do
verificar_apis.py: aqui o objetivo e encontrar APIs "orfas" (sem uso),
nao chamadas sem API.

Uso:
    python3 verificar_apis_nao_usadas.py [pasta_backend] [pasta_frontend]

Se os diretorios nao forem passados como argumento, o script pergunta
interativamente (com autocompletar de caminho via Tab).
"""

import os
import sys

from verificar_apis import (
    ask_dir,
    find_files,
    find_repo_root,
    parse_backend_file,
    parse_frontend_file,
    pick_and_open_in_editor,
    segments_match,
    setup_path_completion,
    strip_comments,
)


def find_matching_call(endpoint, calls):
    for call in calls:
        if call['verb'].upper() == endpoint['verb'].upper() and segments_match(endpoint['segments'], call['segments']):
            return call
    return None


def analyze(backend_dir, frontend_dir, log=print):
    log("\nLendo arquivos .java do backend...")
    java_files = find_files(backend_dir, '.java')
    all_endpoints = []
    for f in java_files:
        try:
            with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                content = fh.read()
        except OSError:
            continue
        all_endpoints.extend(parse_backend_file(f, strip_comments(content)))
    log(f"  {len(java_files)} arquivo(s) .java analisado(s), {len(all_endpoints)} endpoint(s) JAX-RS encontrado(s).")

    log("\nLendo arquivos .js do frontend...")
    js_files = find_files(frontend_dir, '.js')
    all_calls = []
    for f in js_files:
        try:
            with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                content = fh.read()
        except OSError:
            continue
        all_calls.extend(parse_frontend_file(f, strip_comments(content)))
    log(f"  {len(js_files)} arquivo(s) .js analisado(s), {len(all_calls)} chamada(s) de API encontrada(s).")

    unused = []
    used_count = 0
    for ep in all_endpoints:
        call = find_matching_call(ep, all_calls)
        if call:
            used_count += 1
        else:
            unused.append(ep)

    return {
        'endpoints': all_endpoints,
        'calls': all_calls,
        'unused': unused,
        'used_count': used_count,
    }


def format_unused_endpoint(ep):
    return f"[{ep['verb']:6}] {ep['raw_path']}  ({ep['method_name']}())"


def print_report(result):
    unused = result['unused']
    print("\n" + "=" * 78)
    if unused:
        print(f"Endpoints SEM nenhuma chamada correspondente no frontend: {len(unused)}\n")
        by_file = {}
        for ep in unused:
            by_file.setdefault(ep['file'], []).append(ep)
        for f in sorted(by_file):
            print(f"- {f}")
            for ep in sorted(by_file[f], key=lambda e: e['line']):
                print(f"    linha {ep['line']:>5}  [{ep['verb']:6}]  {ep['method_name']}()  "
                      f"path: {ep['raw_path']}")
            print()
    else:
        print("Nenhum endpoint orfao encontrado: todos possuem pelo menos uma chamada no frontend.")

    print("=" * 78)
    print(f"Resumo: {len(result['endpoints'])} endpoint(s) no backend | {result['used_count']} com chamada correspondente | "
          f"{len(unused)} sem chamada | {len(result['calls'])} chamada(s) encontrada(s) no frontend")
    print("\nObs.: script heuristico (regex), cobre padroes $http({...}) e "
          "Upload.upload({...}) no frontend e anotacoes JAX-RS (@Path/@GET/@POST/...) "
          "no backend. Um endpoint listado aqui pode estar sendo chamado por outro "
          "cliente (outro frontend, integracao, job, etc.) que nao esta na pasta "
          "informada -- revise manualmente antes de remover algo.")


def main():
    setup_path_completion()
    args = sys.argv[1:]
    home = os.path.expanduser('~')
    backend_dir = ask_dir(
        "Diretorio com as APIs (backend, ex.: .../web/src/main/java): ",
        args[0] if len(args) > 0 else None,
        search_root=home,
        header='Selecione a pasta do BACKEND (APIs)',
    )
    frontend_dir = ask_dir(
        "Diretorio com as chamadas de API (frontend, ex.: .../web/src/main/angular): ",
        args[1] if len(args) > 1 else None,
        search_root=find_repo_root(backend_dir, home),
        header='Selecione a pasta do FRONTEND (chamadas de API)',
    )

    result = analyze(backend_dir, frontend_dir)
    print_report(result)
    pick_and_open_in_editor(result['unused'], format_unused_endpoint)


if __name__ == '__main__':
    main()
