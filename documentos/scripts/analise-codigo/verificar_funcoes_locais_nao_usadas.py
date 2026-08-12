#!/usr/bin/env python3
"""
Lista funcoes locais declaradas via 'function nome() {...}' em qualquer
.js do frontend que NAO sao referenciadas em lugar nenhum do proprio
arquivo -- nem chamadas ('nome('), nem atribuidas a vm/scope/return, nem
passadas como callback.

Complementa verificar_metodos_controller_nao_usados.py (metodos expostos
via 'vm.algo') e verificar_metodos_nao_usados.py (metodos publicos de
service via 'return {...}'): aqueles cobrem funcoes EXPOSTAS para fora do
arquivo (HTML/outros arquivos), por isso precisam de uma busca ampla no
projeto inteiro. Este aqui cobre o caso mais simples e mais seguro de
detectar: uma funcao declarada dentro do IIFE de um arquivo Angular
('(function () { ... })();') so e visivel DENTRO daquele mesmo arquivo
(fechamento JS) -- entao, se o nome dela nao aparece em NENHUM outro
lugar do proprio arquivo, ela e morta com certeza, sem precisar olhar o
resto do projeto.

Uso:
    python3 verificar_funcoes_locais_nao_usadas.py [pasta_frontend]

Se o diretorio nao for passado como argumento, o script pergunta
interativamente (seletor fzf, se disponivel, ou Tab para autocompletar).

Como funciona (resumo):
  1. Encontra toda declaracao 'function nome(...) {' que NAO seja uma
     EXPRESSAO de funcao (atribuida a algo -- 'vm.foo = function nome()
     {...}' --, passada direto como argumento/callback -- 'promise.then
     (function nome() {...})' --, dentro de array/objeto, retornada, em
     ternario, etc.). Nesses casos o uso ja e garantido pela propria
     posicao sintatica, entao ficam fora do escopo deste script (o padrao
     'vm.foo = function...' especificamente e coberto pelos scripts de
     metodos vm./service).
  2. Conta quantas vezes o identificador 'nome' aparece no arquivo TODO,
     ignorando ocorrencias precedidas por '.' (acesso a propriedade, ex.:
     'arquivo.name', que nao tem relacao nenhuma com uma funcao 'name').
     Se a UNICA ocorrencia for a propria declaracao, a funcao nunca e
     referenciada de forma alguma dentro do arquivo -> reportada como
     morta.
  3. Nomes declarados mais de uma vez no MESMO arquivo (function nome()
     repetido em escopos/closures diferentes) sao pulados -- a contagem
     de ocorrencias e feita no arquivo todo, entao nao da para saber com
     seguranca a qual das declaracoes uma referencia pertence.
"""

import os
import re
import sys
from collections import Counter

from verificar_apis import (
    ask_dir,
    find_files,
    find_repo_root,
    pick_and_open_in_editor,
    setup_path_completion,
    strip_comments,
)

FUNC_DECL_RE = re.compile(r'\bfunction\s+(\w+)\s*\(')
IDENT_RE = re.compile(r'(?<!\.)\b[A-Za-z_$][\w$]*\b')
FUNC_EXPR_CONTEXT_RE = re.compile(r'(?:[=(\[,:?]|\breturn)\s*$')


def is_function_expression(content, match_start):
    """Verifica se a palavra 'function' em match_start faz parte de uma
    EXPRESSAO (atribuida a algo, passada como argumento/callback, dentro
    de um array/objeto, retornada, em um operador ternario, etc.) em vez
    de uma DECLARACAO solta. Numa expressao o uso ja e garantido pela
    propria posicao sintatica -- ex.: 'promise.then(function sucesso()
    {...})' e chamada pelo .then(), nao precisa que 'sucesso' apareca de
    novo em lugar nenhum -- entao fica fora do escopo deste script (que so
    cobre declaracoes soltas nunca referenciadas)."""
    prefix = content[max(0, match_start - 30):match_start]
    return bool(FUNC_EXPR_CONTEXT_RE.search(prefix))


def find_unused_local_functions(all_js):
    unused = []
    for path, content in all_js:
        decl_positions = {}
        for m in FUNC_DECL_RE.finditer(content):
            if is_function_expression(content, m.start()):
                continue
            decl_positions.setdefault(m.group(1), []).append(m.start())

        if not decl_positions:
            continue

        # Uma unica varredura do arquivo conta TODOS os identificadores de
        # uma vez (em vez de um regex por funcao), o que evita um custo
        # quadratico (funcoes x tamanho do arquivo) em arquivos grandes.
        counts = Counter(IDENT_RE.findall(content))

        for name, positions in decl_positions.items():
            if len(positions) != 1:
                continue  # nome declarado mais de uma vez no arquivo -> ambiguo, pula
            if counts.get(name, 0) > 1:
                continue
            line = content.count('\n', 0, positions[0]) + 1
            unused.append({'file': path, 'line': line, 'name': name})
    return unused


def analyze(frontend_dir, log=print):
    log("\nLendo arquivos .js...")
    js_paths = find_files(frontend_dir, '.js')
    all_js = []
    for f in js_paths:
        try:
            with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                raw = fh.read()
        except OSError:
            continue
        all_js.append((f, strip_comments(raw)))
    log(f"  {len(all_js)} arquivo(s) .js analisado(s).")

    log("\nProcurando funcoes locais sem nenhuma referencia no proprio arquivo...")
    unused = find_unused_local_functions(all_js)

    return {'total_js': len(all_js), 'unused': unused}


def format_unused_function(u):
    return f"function {u['name']}()"


def print_report(result):
    unused = result['unused']
    print("\n" + "=" * 78)
    if unused:
        print(f"Funcoes locais SEM nenhuma referencia no proprio arquivo: {len(unused)}\n")
        by_file = {}
        for u in unused:
            by_file.setdefault(u['file'], []).append(u)
        for f in sorted(by_file):
            items = sorted(by_file[f], key=lambda u: u['line'])
            print(f"- {f}")
            for u in items:
                print(f"    linha {u['line']:>5}  function {u['name']}()")
            print()
    else:
        print("Nenhuma funcao local orfa encontrada.")

    print("=" * 78)
    print(f"Resumo: {result['total_js']} arquivo(s) .js | {len(unused)} funcao(oes) sem referencia encontrada(s)")
    print("\nObs.: script heuristico (regex). So considera 'function nome() {...}' como "
          "DECLARACAO (nao expressao atribuida, ex.: 'vm.foo = function nome() {...}' fica "
          "fora do escopo -- esse padrao e coberto por verificar_metodos_controller_nao_"
          "usados.py / verificar_metodos_nao_usados.py). Como a funcao so e visivel dentro do "
          "proprio arquivo (fechamento JS do IIFE Angular), a checagem e feita so no arquivo, "
          "sem precisar buscar no resto do projeto -- por isso nao ha rede de seguranca "
          "adicional aqui. Ocorrencias precedidas por '.' (acesso a propriedade, ex.: "
          "'arquivo.name') nao contam como uso. Nomes declarados mais de uma vez no mesmo "
          "arquivo (mesmo nome em closures/escopos diferentes) sao pulados por ambiguidade. "
          "Revise manualmente antes de remover algo.")


def main():
    setup_path_completion()
    args = sys.argv[1:]
    home = os.path.expanduser('~')
    frontend_dir = ask_dir(
        "Diretorio com os arquivos .js Angular (frontend, ex.: .../web/src/main/angular): ",
        args[0] if len(args) > 0 else None,
        search_root=home,
        header='Selecione a pasta do FRONTEND (.js Angular)',
    )

    result = analyze(frontend_dir)
    print_report(result)
    pick_and_open_in_editor(result['unused'], format_unused_function)


if __name__ == '__main__':
    main()
