#!/usr/bin/env python3
"""
Verifica, para cada view (HTML) associada a um controller Angular via rota
($stateProvider.state) ou modal ($modal.open/$uibModal.open), se as
chamadas 'vm.algo' usadas no HTML correspondem a algo realmente definido
naquele controller -- metodo exposto via 'vm.algo = function...' /
'vm.algo = funcaoNomeada;' ou variavel exposta via 'vm.algo = <valor>;'
(incluindo o que e herdado de um controller "abstrato" via
'$controller("Base", {$scope: $scope})' + 'angular.extend(this, ...)').

Uso:
    python3 verificar_vm_indefinidos_no_html.py [pasta_frontend]

Se o diretorio nao for passado como argumento, o script pergunta
interativamente (seletor fzf, se disponivel, ou Tab para autocompletar).

Como funciona (resumo):
  1) Mapeia view -> controller lendo, em todo .js, blocos de objeto literal
     que tem 'templateUrl:' e 'controller: "Nome"' como propriedades
     diretas do mesmo '{...}' -- cobre tanto rotas do $stateProvider
     (views: {content: {templateUrl, controller, controllerAs}}) quanto
     modais abertos via $modal.open/$uibModal.open, sem precisar
     distinguir os dois formatos. O valor de templateUrl pode ser uma
     concatenacao de variaveis locais (ex.: 'urlViews + "Foo.html"'); e
     resolvido do mesmo jeito que verificar_apis.py resolve URLs de
     $http. Views cujo templateUrl nao resolve para um caminho 100%
     literal (sobra algum pedaco dinamico) sao ignoradas.
  2) Reaproveita os coletores de verificar_metodos_controller_nao_usados.py
     e verificar_variaveis_controller_nao_usadas.py para saber quais
     'vm.algo' cada controller realmente expoe (metodos + variaveis),
     incluindo heranca via $controller(...) + angular.extend(this, ...).
  3) Para cada HTML mapeado, procura toda ocorrencia de 'vm.algo' no texto
     (fora de comentarios HTML) e reporta as que NAO batem com nenhum
     membro exposto por NENHUM dos controllers associados aquela view --
     uma mesma view pode ser reaproveitada por mais de uma rota/controller;
     so e reportada se faltar em TODOS eles, para evitar falso positivo.
     'vm.algo' usado em 'name="vm.algo"' (ex.: '<form name="vm.formX">',
     '<ng-form name="vm.formX">') e ignorado -- o AngularJS publica o
     FormController automaticamente nessa propriedade, sem precisar de
     nada no controller.

  HTMLs cujo templateUrl nao foi encontrado em nenhuma rota/modal (ex.:
  partials incluidos via ng-include, como header/menu/footer) sao
  contados a parte, sem checagem, por falta de controller conhecido.
"""

import os
import re
import sys

from verificar_apis import (
    ask_dir,
    find_files,
    map_html_to_controllers,
    pick_and_open_in_editor,
    setup_path_completion,
    strip_comments,
)
from verificar_metodos_controller_nao_usados import (
    CONTROLLER_REGISTER_RE,
    collect_controllers,
)
from verificar_variaveis_controller_nao_usadas import collect_controller_vars

HTML_COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)
VM_USAGE_RE = re.compile(r'\bvm\.(\w+)')
NAME_ATTR_RE = re.compile(r'\bname\s*=\s*[\'"]vm\.(\w+)')


# --------------------------------------------------------------------------
# 1) membros ('vm.algo') expostos por cada controller, com heranca
# --------------------------------------------------------------------------

def build_controller_members(all_js):
    """Retorna dict nome_controller -> {'members': set(...), 'parent':
    str|None}, juntando o que verificar_metodos_controller_nao_usados.py e
    verificar_variaveis_controller_nao_usadas.py conseguem enxergar."""
    method_ctrls = collect_controllers(all_js)
    var_ctrls = collect_controller_vars(all_js)

    info = {}
    for data in method_ctrls.values():
        entry = info.setdefault(data['name'], {'members': set(), 'parent': None})
        entry['members'].update(data['methods'].keys())
        if data['parent']:
            entry['parent'] = data['parent']
    for data in var_ctrls.values():
        entry = info.setdefault(data['name'], {'members': set(), 'parent': None})
        entry['members'].update(data['variables'].keys())
        if data['parent']:
            entry['parent'] = data['parent']

    # Nomes de TODOS os controllers registrados (mesmo sem metodo/variavel
    # capturado pelos coletores acima), para diferenciar "controller nao
    # encontrado" de "controller encontrado mas sem esse membro".
    for _path, content in all_js:
        reg = CONTROLLER_REGISTER_RE.search(content)
        if reg:
            info.setdefault(reg.group(1), {'members': set(), 'parent': None})

    return info


def effective_members(name, info, cache, seen=None):
    if name in cache:
        return cache[name]
    if seen is None:
        seen = frozenset()
    if name in seen or name not in info:
        return set()
    entry = info[name]
    members = set(entry['members'])
    if entry['parent']:
        members |= effective_members(entry['parent'], info, cache, seen | {name})
    cache[name] = members
    return members


# --------------------------------------------------------------------------
# 2) 'vm.algo' usado no HTML sem correspondencia no(s) controller(s)
# --------------------------------------------------------------------------

def strip_html_comments(content):
    return HTML_COMMENT_RE.sub('', content)


def looks_like_call(content, end_pos):
    j = end_pos
    n = min(len(content), end_pos + 8)
    while j < n and content[j] in ' \t\r\n':
        j += 1
    return j < len(content) and content[j] == '('


def find_undefined_vm_usages(view_controllers, controller_info):
    cache = {}
    findings = []
    unknown_controllers = set()
    for html_path, controllers in view_controllers.items():
        try:
            with open(html_path, 'r', encoding='utf-8', errors='replace') as fh:
                raw = fh.read()
        except OSError:
            continue
        content = strip_html_comments(raw)

        allowed = set()
        any_known = False
        for cname in controllers:
            if cname in controller_info:
                any_known = True
                allowed |= effective_members(cname, controller_info, cache)
            else:
                unknown_controllers.add((html_path, cname))
        if not any_known:
            continue

        auto_published = set(NAME_ATTR_RE.findall(content))

        reported = set()
        for m in VM_USAGE_RE.finditer(content):
            ident = m.group(1)
            if ident in allowed or ident in auto_published or ident in reported:
                continue
            reported.add(ident)
            line = content.count('\n', 0, m.start()) + 1
            findings.append({
                'file': html_path,
                'line': line,
                'ident': ident,
                'is_call': looks_like_call(content, m.end()),
                'controllers': sorted(controllers),
            })
    return findings, unknown_controllers


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

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

    log(f"  {len(all_js)} arquivo(s) .js e {len(html_paths)} arquivo(s) .html encontrados.")

    log("\nMapeando views (templateUrl) para controllers (rotas + modais)...")
    view_controllers, unresolved = map_html_to_controllers(all_js, frontend_dir, html_paths)
    log(f"  {len(view_controllers)} view(s) HTML mapeada(s) para controller; "
        f"{unresolved} templateUrl(s) com expressao nao totalmente resolvida (ignorados).")

    log("\nColetando metodos/variaveis expostos por cada controller...")
    controller_info = build_controller_members(all_js)
    log(f"  {len(controller_info)} controller(s) conhecido(s) no total.")

    log("\nProcurando 'vm.algo' nos HTMLs mapeados sem correspondencia no(s) controller(s)...")
    findings, unknown_controllers = find_undefined_vm_usages(view_controllers, controller_info)

    unmapped_html = sorted(set(html_paths) - set(view_controllers.keys()))

    return {
        'total_js': len(all_js),
        'total_html': len(html_paths),
        'view_controllers': view_controllers,
        'unresolved': unresolved,
        'controller_info': controller_info,
        'findings': findings,
        'unknown_controllers': unknown_controllers,
        'unmapped_html': unmapped_html,
    }


def format_finding(f):
    tag = '()' if f['is_call'] else ''
    ctrls = ', '.join(f['controllers'])
    return f"vm.{f['ident']}{tag}  [{ctrls}]"


def print_report(result):
    findings = result['findings']
    print("\n" + "=" * 78)
    if findings:
        print(f"Usos de 'vm.algo' no HTML SEM correspondencia no controller associado: {len(findings)}\n")
        by_file = {}
        for f in findings:
            by_file.setdefault(f['file'], []).append(f)
        for fpath in sorted(by_file):
            items = sorted(by_file[fpath], key=lambda x: x['line'])
            ctrls = ', '.join(items[0]['controllers'])
            print(f"- {fpath}  (controller(es): {ctrls})")
            for it in items:
                tag = '()' if it['is_call'] else ''
                print(f"    linha {it['line']:>5}  vm.{it['ident']}{tag}")
            print()
    else:
        print("Nenhum uso orfao de 'vm.algo' encontrado nos HTMLs mapeados.")

    if result['unknown_controllers']:
        print("=" * 78)
        print("Controllers referenciados em rota/modal mas NAO encontrados no codigo "
              f"(views abaixo nao puderam ser checadas): {len(result['unknown_controllers'])}")
        for html_path, cname in sorted(result['unknown_controllers']):
            print(f"  - {html_path}  ->  controller '{cname}'")

    print("\n" + "=" * 78)
    print(f"Resumo: {result['total_js']} arquivo(s) .js | {result['total_html']} arquivo(s) .html | "
          f"{len(result['view_controllers'])} view(s) mapeada(s) para controller | "
          f"{len(result['unmapped_html'])} HTML(s) sem controller conhecido (ignorados, ex.: "
          f"partials incluidos via ng-include) | {len(result['controller_info'])} controller(s) | "
          f"{len(findings)} uso(s) orfao(s) de vm.algo")
    print("\nObs.: script heuristico (regex). Mapeia view -> controller lendo blocos "
          "'{templateUrl: ..., controller: \"Nome\"}' em .js (rotas $stateProvider e modais "
          "$modal.open/$uibModal.open); templateUrl cuja expressao nao resolve para um "
          "caminho 100% literal (concatenacao com algo alem de 'var' local) e ignorado. HTMLs "
          "sem controller mapeado (partials via ng-include, headers/menus/footers) nao sao "
          "checados. Uma view reaproveitada por mais de um controller so acusa 'vm.algo' como "
          "orfao se faltar em TODOS os controllers associados. 'vm.algo' usado apenas em "
          "'name=\"vm.algo\"' (form/ng-form) e ignorado, pois o AngularJS publica o "
          "FormController ali automaticamente. Heranca via "
          "$controller('Base', {$scope:$scope}) + angular.extend(this, ...) e considerada. "
          "Nao cobre membros criados dinamicamente (vm[chave], Object.defineProperty, "
          "diretivas que injetam propriedades de fora) nem valida a assinatura de parametros "
          "de metodos chamados. Revise manualmente antes de concluir que e um bug real.")


def main():
    setup_path_completion()
    args = sys.argv[1:]
    home = os.path.expanduser('~')
    frontend_dir = ask_dir(
        "Diretorio com os controllers/views Angular (frontend, ex.: .../web/src/main/angular): ",
        args[0] if len(args) > 0 else None,
        search_root=home,
        header='Selecione a pasta do FRONTEND (controllers/views Angular)',
    )

    result = analyze(frontend_dir)
    print_report(result)
    pick_and_open_in_editor(result['findings'], format_finding)


if __name__ == '__main__':
    main()
