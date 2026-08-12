#!/usr/bin/env python3
"""
Lista metodos Java (public/protected/private, incluindo publicos) que nao
parecem ser chamados em nenhum outro lugar do codigo-fonte informado.

Uso:
    python3 verificar_metodos_java_nao_usados.py [pasta_java]

Se o diretorio nao for passado como argumento, o script pergunta
interativamente (seletor fzf, se disponivel, ou Tab para autocompletar).

Como funciona (resumo):
  1. Encontra declaracoes de metodo (linhas com 'public/protected/private
     TipoRetorno nomeMetodo(' -- construtores nao entram, pois nao tem tipo
     de retorno separado do nome).
  2. Ignora automaticamente categorias que quase sempre sao "usadas" por
     contrato/framework e por isso dariam falso positivo com busca textual:
       - equals/hashCode/toString/main/clone/finalize/readObject/writeObject/
         setUp/tearDown
       - getters/setters (get*/set*/is*), pois costumam ser usados via
         serializacao JSON (Jackson) ou reflection, o que busca textual nao
         enxerga -- removidos da lista para nao gerar ruido
       - endpoints REST (anotados @GET/@POST/@PUT/@DELETE/@PATCH/@Path --
         sao chamados via HTTP pelo frontend, nao por outro metodo Java; use
         o verificar_apis_nao_usadas.py para checar o uso desses)
       - metodos de teste (@Test/@Before/@After/@BeforeEach/@AfterEach/
         @BeforeAll/@AfterAll/@ParameterizedTest/etc. do JUnit4/5/TestNG --
         chamados via reflection pelo test runner, nao por outro metodo Java)
       - callbacks de container/framework (@PostConstruct/@PreDestroy/
         @Produces do CDI, @Pre*/@Post* de ciclo de vida JPA, @OnOpen/
         @OnClose/@OnMessage/@OnError de WebSocket, @Schedule/@Timeout de
         EJB timer) -- idem, invocados pelo container, nao por chamada Java
  3. Para os metodos restantes, conta quantas vezes 'nomeMetodo(' aparece.
     Metodo declarado em codigo de PRODUCAO (fora de src/test/) so conta como
     usado se houver chamada em OUTRO arquivo de producao -- uma chamada
     vinda somente de um arquivo em src/test/ NAO salva o metodo da lista de
     "sem uso", pois ele continua inalcancavel por qualquer fluxo real da
     aplicacao (nesse caso o item aparece marcado como "so usado em teste").
     Ja um metodo declarado DENTRO de um arquivo de teste (ex.: um helper
     compartilhado entre varios @Test) conta como usado se outro arquivo de
     teste o chamar, normalmente.
  4. Metodos anotados com @Override (implementacao de interface ou de
     metodo abstrato de superclasse) SAO analisados, mas aparecem marcados
     como '[override]' quando sem uso -- a busca por nome nao distingue qual
     implementacao especifica e chamada atraves de uma referencia da
     interface/superclasse, entao, se OUTRA classe tiver um metodo de mesmo
     nome realmente usado em algum lugar, este item pode ser falso positivo.
     Revise com atencao antes de remover.

Limitacoes importantes: a busca e por NOME do metodo em todo o texto (nao
resolve tipos/overload), entao dois metodos de classes diferentes com o
mesmo nome contam como "uso" um do outro (raro dar falso positivo de "sem
uso", mas pode mascarar um metodo realmente morto -- risco maior em
metodos @Override, ver item 4). Para melhor precisao,
aponte para uma pasta que cubra TODOS os modulos que podem chamar o codigo
(ex.: a raiz do projeto, nao so 'web/src/main/java'), caso outros modulos
(ejb, batch, etc.) tambem chamem essas classes.
"""

import os
import re
import sys
from collections import Counter

from verificar_apis import (
    ask_dir,
    find_files,
    pick_and_open_in_editor,
    setup_path_completion,
    strip_comments,
    warn,
)


JAVA_METHOD_DECL_RE = re.compile(
    r'^\s*(public|protected|private)\s+[\w<>\[\],\s\?\.]+?\s+(\w+)\s*\('
)
ANNOTATION_RE = re.compile(r'@(\w+)')
CLASS_DECL_RE = re.compile(r'\b(?:class|interface|enum)\s+(\w+)')

CONTRACT_METHOD_NAMES = {
    'equals', 'hashCode', 'toString', 'main', 'clone', 'finalize',
    'readObject', 'writeObject', 'readResolve', 'writeReplace',
    # ciclo de vida JUnit 3 (extends TestCase), sem anotacao -- convencao por nome
    'setUp', 'tearDown',
}
HTTP_VERB_ANNOTATIONS = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'}
# Anotacoes que indicam que o metodo e invocado pelo CONTAINER/FRAMEWORK via
# reflection (JUnit/TestNG, ciclo de vida CDI/EJB, callbacks JPA, WebSocket,
# timer EJB, producer CDI) -- nao por outro metodo Java, entao busca textual
# por chamada nao teria como encontrar nada mesmo que o metodo esteja ativo.
FRAMEWORK_MANAGED_ANNOTATIONS = {
    # JUnit 4/5, TestNG
    'Test', 'Before', 'After', 'BeforeClass', 'AfterClass',
    'BeforeEach', 'AfterEach', 'BeforeAll', 'AfterAll',
    'ParameterizedTest', 'RepeatedTest', 'TestFactory', 'TestTemplate',
    # CDI / EJB
    'PostConstruct', 'PreDestroy', 'Produces', 'Schedule', 'Schedules', 'Timeout',
    # callbacks de ciclo de vida JPA
    'PrePersist', 'PostPersist', 'PreUpdate', 'PostUpdate',
    'PreRemove', 'PostRemove', 'PostLoad',
    # WebSocket
    'OnOpen', 'OnClose', 'OnMessage', 'OnError',
}
ACCESSOR_RE = re.compile(r'^(get|set|is)[A-Z0-9]')

BATCH_SIZE = 400


def is_test_file(path):
    """Convencao padrao Maven/Gradle: codigo de teste fica em .../src/test/...
    (o codigo de producao correspondente fica em .../src/main/...)."""
    normalized = path.replace(os.sep, '/')
    return '/src/test/' in normalized


def current_class_name(lines, idx):
    for j in range(idx, -1, -1):
        m = CLASS_DECL_RE.search(lines[j])
        if m:
            return m.group(1)
    return None


def collect_java_methods(path, content):
    """Retorna lista de dicts: name, file, line, modifier, class, is_accessor,
    is_test_file, para metodos que NAO sao contrato/@Override/endpoint REST."""
    lines = content.splitlines()
    methods = []
    pending_annotations = set()
    in_test_file = is_test_file(path)

    for idx, line in enumerate(lines):
        pending_annotations.update(ANNOTATION_RE.findall(line))

        m = JAVA_METHOD_DECL_RE.match(line)
        if m:
            modifier, name = m.group(1), m.group(2)

            is_contract = name in CONTRACT_METHOD_NAMES
            is_override = 'Override' in pending_annotations
            is_endpoint = bool(HTTP_VERB_ANNOTATIONS & pending_annotations) or 'Path' in pending_annotations
            is_framework_managed = bool(FRAMEWORK_MANAGED_ANNOTATIONS & pending_annotations)
            is_accessor = bool(ACCESSOR_RE.match(name))

            if not (is_contract or is_endpoint or is_framework_managed or is_accessor):
                methods.append({
                    'name': name,
                    'file': path,
                    'line': idx + 1,
                    'modifier': modifier,
                    'class': current_class_name(lines, idx),
                    'is_test_file': in_test_file,
                    'is_override': is_override,
                })
            pending_annotations = set()
            continue

        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('@'):
            continue
        if '(' not in line and ')' not in line:
            # linha "solta" que nao e continuacao de assinatura -> descarta
            # anotacoes pendentes que nao acabaram grudadas em um metodo
            pending_annotations = set()

    return methods


def count_occurrences(contents, names):
    """Conta, para cada nome em 'names', quantas vezes 'nome(' aparece
    somando TODOS os arquivos em 'contents'. Faz em lotes para nao gerar um
    regex gigante demais de uma vez so."""
    counts = Counter()
    names_list = sorted(names)
    for i in range(0, len(names_list), BATCH_SIZE):
        batch = names_list[i:i + BATCH_SIZE]
        pattern = re.compile(r'\b(' + '|'.join(re.escape(n) for n in batch) + r')\s*\(')
        for content in contents:
            for m in pattern.finditer(content):
                counts[m.group(1)] += 1
    return counts


def analyze(java_dir, log=print):
    log("\nLendo arquivos .java...")
    java_files = find_files(java_dir, '.java')
    files = []
    for f in java_files:
        try:
            with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                raw = fh.read()
        except OSError:
            continue
        files.append((f, strip_comments(raw)))
    log(f"  {len(files)} arquivo(s) .java analisado(s).")

    all_methods = []
    for path, content in files:
        all_methods.extend(collect_java_methods(path, content))
    log(f"  {len(all_methods)} metodo(s) elegivel(is) para analise "
        "(exclui construtores, equals/hashCode/toString/main, getters/setters "
        "e endpoints REST; metodos @Override entram marcados).")

    log("\nProcurando usos em todo o codigo-fonte (pode levar um tempo)...")

    all_contents = [c for _, c in files]
    prod_contents = [c for p, c in files if not is_test_file(p)]

    prod_methods = [m for m in all_methods if not m['is_test_file']]
    test_methods = [m for m in all_methods if m['is_test_file']]

    # Metodos de PRODUCAO: so contam como usados se houver chamada em codigo
    # de PRODUCAO -- uma chamada vinda so de src/test/ nao "salva" o metodo,
    # pois ele continua inalcancavel por qualquer fluxo real da aplicacao.
    decl_counts_prod = Counter(m['name'] for m in prod_methods)
    occ_counts_prod = count_occurrences(prod_contents, decl_counts_prod.keys())
    occ_counts_prod_full = count_occurrences(all_contents, decl_counts_prod.keys())

    unused = []
    for m in prod_methods:
        name = m['name']
        if occ_counts_prod.get(name, 0) <= decl_counts_prod[name]:
            m = dict(m)
            only_in_tests = occ_counts_prod_full.get(name, 0) > decl_counts_prod[name]
            m['only_used_in_tests'] = only_in_tests
            unused.append(m)

    # Metodos declarados DENTRO de arquivo de teste (ex.: helper de teste):
    # aqui uma chamada vinda de outro arquivo de teste continua sendo uso
    # legitimo, entao a busca permanece sobre TODO o codigo-fonte.
    decl_counts_test = Counter(m['name'] for m in test_methods)
    occ_counts_test = count_occurrences(all_contents, decl_counts_test.keys())
    for m in test_methods:
        if occ_counts_test.get(m['name'], 0) <= decl_counts_test[m['name']]:
            m = dict(m)
            m['only_used_in_tests'] = False
            unused.append(m)

    return {'files_analyzed': len(files), 'methods': all_methods, 'unused': unused}


def format_unused_method(m):
    tag = ' ' + warn('[override]') if m.get('is_override') else ''
    tag += ' ' + warn('[so usado em teste]') if m.get('only_used_in_tests') else ''
    cls = f"{m['class']}." if m['class'] else ''
    return f"{m['modifier']} {cls}{m['name']}(){tag}"


def print_report(result):
    unused = result['unused']
    print("\n" + "=" * 78)
    if unused:
        print(f"Metodos Java SEM nenhum sinal de uso encontrado: {len(unused)}\n")
        by_file = {}
        for m in unused:
            by_file.setdefault(m['file'], []).append(m)
        for f in sorted(by_file):
            items = sorted(by_file[f], key=lambda m: m['line'])
            print(f"- {f}")
            for m in items:
                tag = '  ' + warn('[override -- pode ser usado via outra implementacao com mesmo nome; revisar com cuidado]') \
                    if m.get('is_override') else ''
                if m.get('only_used_in_tests'):
                    tag += '  ' + warn('[chamado somente por teste JUnit -- inalcancavel na aplicacao real]')
                cls = f"{m['class']}." if m['class'] else ''
                print(f"    linha {m['line']:>5}  {m['modifier']:9} {cls}{m['name']}(){tag}")
            print()
    else:
        print("Nenhum metodo orfao encontrado: todos tem algum sinal de uso.")

    print("=" * 78)
    print(f"Resumo: {result['files_analyzed']} arquivo(s) .java | {len(result['methods'])} metodo(s) analisado(s) | "
          f"{len(unused)} sem uso encontrado")
    print("\nObs.: script heuristico (regex, busca por nome em todo o texto -- nao resolve "
          "tipos/overload). Ignora construtores, equals/hashCode/toString/main/clone/"
          "finalize/readObject/writeObject/setUp/tearDown, getters/setters (get*/set*/is*, "
          "que costumam ser usados via serializacao JSON/reflection, algo que busca textual "
          "nao enxerga), endpoints REST (@GET/@POST/@Path etc., que sao "
          "chamados via HTTP -- use o verificar_apis_nao_usadas.py para esses), metodos de "
          "teste (@Test/@Before/@After/@BeforeEach/etc. do JUnit/TestNG) e callbacks de "
          "container/framework (@PostConstruct/@PreDestroy/@Produces do CDI, ciclo de vida "
          "JPA, @OnOpen/@OnClose do WebSocket, @Schedule/@Timeout de EJB timer) -- todos "
          "invocados via reflection pelo container, nao por chamada Java direta. Metodos "
          "@Override aparecem marcados: a busca por nome nao distingue qual implementacao e "
          "chamada atraves de uma referencia de interface/superclasse, entao um item pode ser "
          "falso positivo se outra classe tiver um metodo de mesmo nome realmente em uso. "
          "Metodos de "
          "producao chamados apenas por arquivos em src/test/ aparecem marcados como 'so "
          "usado em teste' -- contam como sem uso, pois nao sao alcancados por nenhum fluxo "
          "real da aplicacao. Se outros modulos "
          "(ejb, batch, etc.) tambem chamam este codigo, aponte para uma pasta que cubra "
          "todos eles. Se a pasta incluir SDKs/bibliotecas de terceiros vendorizadas (codigo "
          "fonte de outro pacote, ex.: nao comecando com o pacote da propria aplicacao), "
          "metodos delas podem aparecer como 'sem uso' so porque quem os chama fica fora do "
          "escopo varrido -- nesse caso considere apontar para uma subpasta mais especifica. "
          "Revise manualmente antes de remover algo.")


def main():
    setup_path_completion()
    args = sys.argv[1:]
    home = os.path.expanduser('~')
    java_dir = ask_dir(
        "Diretorio com o codigo Java (ex.: raiz do projeto ou .../web/src/main/java): ",
        args[0] if len(args) > 0 else None,
        search_root=home,
        header='Selecione a pasta com o codigo Java a analisar',
    )

    result = analyze(java_dir)
    print_report(result)
    pick_and_open_in_editor(result['unused'], format_unused_method)


if __name__ == '__main__':
    main()
