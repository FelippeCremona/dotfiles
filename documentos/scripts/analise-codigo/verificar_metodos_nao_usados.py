#!/usr/bin/env python3
"""
Lista metodos publicos de services Angular (.service()/.factory()) que nao
parecem ser chamados em nenhum outro lugar do frontend (controllers, outros
services, directives, etc.).

Uso:
    python3 verificar_metodos_nao_usados.py [pasta_frontend]

Se o diretorio nao for passado como argumento, o script pergunta
interativamente (com seletor fzf, se disponivel, ou Tab para autocompletar).

Como funciona (resumo):
  1. Encontra registros '.service("Nome", FabricaFn)' / '.factory(...)' e, em
     cada arquivo, o ultimo bloco 'return { chave: valor, ... };' da fabrica
     -- essa e a API publica do service (o que os outros arquivos podem
     chamar via injecao de dependencia).
  2. Para cada OUTRO arquivo .js, resolve o apelido local usado para injetar
     aquele service (o parametro da funcao pode ter nome diferente do nome
     registrado, ex.: 'DocumentoLancamentoService' -> 'documentoLancamentoService'),
     casando a lista do '$inject' com os parametros da funcao na mesma
     posicao.
  3. Um metodo e considerado "sem uso" se: (a) nao ha chamada 'apelido.metodo('
     em nenhum arquivo que injeta aquele service; (b) nao ha chamada solta
     'metodo(' em outro lugar do PROPRIO arquivo (reuso interno); e (c) uma
     busca ampla por '.metodo(' em QUALQUER arquivo (qualquer objeto) tambem
     nao encontra nada -- essa ultima checagem existe so para reduzir falso
     positivo quando a resolucao de apelido falha por algum padrao atipico.
"""

import os
import re
import sys

from verificar_apis import (
    FUNC_NAME_RE,
    IGNORED_DIRS,
    ask_dir,
    find_files,
    find_repo_root,
    parse_param_names,
    pick_and_open_in_editor,
    setup_path_completion,
    strip_comments,
)

SERVICE_REGISTER_RE = re.compile(r'''\.(?:service|factory)\(\s*['"](\w+)['"]\s*,\s*(\w+)\s*\)''')
INJECT_RE = re.compile(r'\b(\w+)\.\$inject\s*=\s*\[([^\]]*)\]')
RETURN_OBJ_RE = re.compile(r'\breturn\s*\{')


def parse_inject_list(raw):
    items = []
    for part in raw.split(','):
        part = part.strip()
        m = re.match(r'''^['"](.+)['"]$''', part)
        if m:
            items.append(m.group(1))
    return items


def extract_balanced_braces(content, open_pos):
    """open_pos aponta para '{'. Retorna (texto_interno, indice_apos_fechamento)."""
    depth = 0
    in_str = None
    i = open_pos
    n = len(content)
    inner_start = open_pos + 1
    while i < n:
        c = content[i]
        if in_str:
            if c == '\\':
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
        if c == '{':
            depth += 1
            i += 1
            continue
        if c == '}':
            depth -= 1
            i += 1
            if depth == 0:
                return content[inner_start:i - 1], i
            continue
        i += 1
    return content[inner_start:], n


def find_public_api(content):
    """Retorna a lista de pares (chave_exposta, nome_da_funcao) do ULTIMO
    bloco 'return {...}' do arquivo -- convencao deste projeto para expor a
    API publica de um service/factory Angular."""
    matches = list(RETURN_OBJ_RE.finditer(content))
    if not matches:
        return []
    last = matches[-1]
    open_pos = last.end() - 1
    inner_text, _ = extract_balanced_braces(content, open_pos)
    return re.findall(r'(\w+)\s*:\s*(\w+)\s*(?=[,}]|$)', inner_text)


def build_alias_map(content):
    """Para um arquivo, retorna {nome_do_dependencia: apelido_local}, casando
    'Nome.$inject = [...]' com 'function Nome(param1, param2, ...)'."""
    injects = {m.group(1): parse_inject_list(m.group(2)) for m in INJECT_RE.finditer(content)}
    func_params = {m.group(1): [p.strip() for p in m.group(2).split(',') if p.strip()]
                   for m in FUNC_NAME_RE.finditer(content)}
    alias = {}
    for name, deps in injects.items():
        params = func_params.get(name)
        if not params or len(params) != len(deps):
            continue
        for dep, param in zip(deps, params):
            alias[dep] = param
    return alias


def collect_services(files):
    """files: lista de (path, content_sem_comentarios).
    Retorna dict service_name -> {'file', 'methods': {chave: {'func','line'}}}."""
    services = {}
    for path, content in files:
        for m in SERVICE_REGISTER_RE.finditer(content):
            service_name = m.group(1)
            pairs = find_public_api(content)
            if not pairs:
                continue
            methods = {}
            for key, func_name in pairs:
                dm = re.search(r'\bfunction\s+' + re.escape(func_name) + r'\s*\(', content)
                line = content.count('\n', 0, dm.start()) + 1 if dm else None
                methods[key] = {'func': func_name, 'line': line}
            if methods:
                services[service_name] = {'file': path, 'methods': methods}
    return services


def method_used_internally(content, func_name):
    """True se 'func_name(' aparece no proprio arquivo fora da propria
    declaracao ('function func_name(') E fora de um acesso de membro em
    outro objeto ('obj.func_name(') -- esse ultimo caso NAO e uma chamada
    a funcao local: e uma chamada a um metodo de mesmo nome em outro
    objeto, e o '\\b' do regex sozinho nao distingue os dois (um '.' antes
    do nome ja satisfaz '\\b')."""
    pattern = re.compile(r'\b' + re.escape(func_name) + r'\s*\(')
    for m in pattern.finditer(content):
        prefix = content[:m.start()].rstrip()
        if prefix.endswith('function') or prefix.endswith('.'):
            continue
        return True
    return False


def find_unused_methods(services, files):
    """files: lista de (path, content). Retorna lista de dicts com metodos
    sem nenhum sinal de uso encontrado."""
    contents_by_path = dict(files)
    alias_maps = {path: build_alias_map(content) for path, content in files}

    unused = []
    for service_name, info in services.items():
        service_file = info['file']
        methods = info['methods']
        pending = dict(methods)  # chave -> {func, line}

        # 1) reuso interno (chamada "solta" em outro ponto do proprio arquivo)
        own_content = contents_by_path[service_file]
        for key in list(pending):
            func_name = pending[key]['func']
            if method_used_internally(own_content, func_name):
                del pending[key]

        if not pending:
            continue

        # 2) uso via apelido em outros arquivos que injetam este service
        key_list = list(pending.keys())
        alt = '|'.join(re.escape(k) for k in key_list)
        for path, content in files:
            if path == service_file:
                continue
            alias = alias_maps.get(path, {}).get(service_name)
            if not alias:
                continue
            pattern = re.compile(r'\b' + re.escape(alias) + r'\.(' + alt + r')\s*\(')
            for match in pattern.finditer(content):
                pending.pop(match.group(1), None)
            if not pending:
                break

        if not pending:
            continue

        # 3) rede de seguranca: busca ampla por ".chave(" em qualquer objeto,
        # em qualquer arquivo -- evita falso positivo quando a resolucao de
        # apelido falhou por algum padrao fora do comum.
        for key in list(pending):
            loose_pattern = re.compile(r'\.\s*' + re.escape(key) + r'\s*\(')
            found = False
            for path, content in files:
                if loose_pattern.search(content):
                    found = True
                    break
            if found:
                del pending[key]

        for key, data in pending.items():
            unused.append({
                'service': service_name,
                'file': service_file,
                'method': key,
                'func': data['func'],
                'line': data['line'],
            })

    return unused


def analyze(frontend_dir, log=print):
    log("\nLendo arquivos .js...")
    js_files = find_files(frontend_dir, '.js')
    files = []
    for f in js_files:
        try:
            with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                raw = fh.read()
        except OSError:
            continue
        files.append((f, strip_comments(raw)))
    log(f"  {len(files)} arquivo(s) .js analisado(s).")

    services = collect_services(files)
    total_methods = sum(len(s['methods']) for s in services.values())
    log(f"  {len(services)} service(s)/factory(ies) encontrado(s), {total_methods} metodo(s) publico(s) no total.")

    log("\nProcurando usos em todo o frontend (pode levar alguns segundos)...")
    unused = find_unused_methods(services, files)

    return {'services': services, 'total_methods': total_methods, 'unused': unused}


def format_unused_method(u):
    return f"{u['service']}.{u['method']}()"


def print_report(result):
    unused = result['unused']
    print("\n" + "=" * 78)
    if unused:
        print(f"Metodos SEM nenhum sinal de uso encontrado: {len(unused)}\n")
        by_file = {}
        for u in unused:
            by_file.setdefault(u['file'], []).append(u)
        for f in sorted(by_file):
            items = sorted(by_file[f], key=lambda u: (u['line'] is None, u['line']))
            print(f"- {f}  (service '{items[0]['service']}')")
            for u in items:
                linha = u['line'] if u['line'] is not None else '?'
                print(f"    linha {linha:>5}  {u['method']}()")
            print()
    else:
        print("Nenhum metodo orfao encontrado: todos tem algum sinal de uso.")

    print("=" * 78)
    print(f"Resumo: {len(result['services'])} service(s) | {result['total_methods']} metodo(s) publico(s) | "
          f"{len(unused)} sem uso encontrado")
    print("\nObs.: script heuristico (regex). Cobre services registrados com "
          "'.service(...)' / '.factory(...)' que expoem a API publica via "
          "'return { chave: funcao, ... }' no final da fabrica (padrao usado "
          "neste projeto). Metodos usados apenas por HTML/templates (ng-click, "
          "etc. via controller), por codigo fora da pasta informada, ou "
          "chamados so por OUTRO metodo igualmente sem uso no mesmo arquivo "
          "podem nao ser detectados. Revise manualmente antes de remover algo.")


def main():
    setup_path_completion()
    args = sys.argv[1:]
    home = os.path.expanduser('~')
    frontend_dir = ask_dir(
        "Diretorio com os services Angular (frontend, ex.: .../web/src/main/angular): ",
        args[0] if len(args) > 0 else None,
        search_root=home,
        header='Selecione a pasta do FRONTEND (services/controllers Angular)',
    )

    result = analyze(frontend_dir)
    print_report(result)
    pick_and_open_in_editor(result['unused'], format_unused_method)


if __name__ == '__main__':
    main()
