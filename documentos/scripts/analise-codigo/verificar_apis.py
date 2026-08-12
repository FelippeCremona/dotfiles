#!/usr/bin/env python3
"""
Verifica chamadas de API feitas no frontend (Angular/$http) contra os
endpoints JAX-RS definidos no backend (Java), reportando chamadas que
nao possuem um endpoint correspondente.

Uso:
    python3 verificar_apis.py [pasta_frontend] [pasta_backend]

Se os diretorios nao forem passados como argumento, o script pergunta
interativamente.
"""

import glob
import os
import re
import shutil
import subprocess
import sys

try:
    import readline
except ImportError:
    readline = None

IGNORED_DIRS = {'.git', 'node_modules', 'target', 'dist', 'build', '.settings', 'lib'}

# Fundo amarelo vivido (truecolor RGB, #FFCC00) com texto preto -- usa cor
# de 24 bits (38;2;R;G;B / 48;2;R;G;B) em vez dos indices 0-15/90-97 da
# paleta base, que muitos temas de terminal remapeiam (foi o que deixou o
# amarelo/preto anteriores sem contraste). RGB explicito ignora esse
# remapeamento e renderiza a cor exata em qualquer terminal com suporte a
# truecolor (a grande maioria hoje em dia).
COLOR_WARN = '\033[1;38;2;0;0;0;48;2;255;204;0m'
COLOR_RESET = '\033[0m'


def warn(text):
    """Envolve 'text' em cor de aviso (fundo amarelo vivido, texto preto), so
    se a saida for um terminal -- evita sujar a saida quando redirecionada
    para arquivo/pipe."""
    if not sys.stdout.isatty():
        return text
    return f'{COLOR_WARN}{text}{COLOR_RESET}'

# Diretorios extras a esconder apenas na listagem interativa (fzf) -- nao
# afeta a varredura de arquivos .js/.java, so a navegacao.
BROWSE_IGNORED_DIRS = IGNORED_DIRS | {
    '__pycache__', '.cache', '.npm', '.rustup', '.cargo',
    '.venv', 'venv', '.idea', '.vscode', '.m2', '.gradle',
}

VERB_RE = re.compile(r'@(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b')
PATH_RE = re.compile(r'@Path\s*\(\s*"([^"]*)"\s*\)')
CLASS_DECL_RE = re.compile(r'\bpublic\s+(?:abstract\s+)?class\s+\w+')
METHOD_DECL_RE = re.compile(r'^\s*(?:public|protected|private)\s+[\w<>\[\],\s\?\.]+\s+(\w+)\s*\(')
FUNC_NAME_RE = re.compile(r'\bfunction\s+(\w+)\s*\(([^)]*)\)')
VAR_DEF_RE = re.compile(r'\b(?:var|let|const)\s+(\w+)\s*=\s*(.+?);', re.DOTALL)
TEMPLATE_URL_KEY_RE = re.compile(r'\btemplateUrl\s*:\s*')
CONTROLLER_KEY_RE = re.compile(r'\bcontroller\s*:\s*[\'"](\w+)[\'"]')

SENTINEL = '\x01'


# --------------------------------------------------------------------------
# Remocao de comentarios (evita casar @Path/$http dentro de codigo morto)
# --------------------------------------------------------------------------

def strip_comments(content):
    """Remove comentarios estilo C (// e /* */) preservando strings/templates
    e a contagem de linhas (troca o comentario por quebras de linha)."""
    result = []
    i = 0
    n = len(content)
    in_str = None
    while i < n:
        c = content[i]
        if in_str:
            result.append(c)
            if c == '\\' and i + 1 < n:
                result.append(content[i + 1])
                i += 2
                continue
            if c == in_str:
                in_str = None
            i += 1
            continue
        if c in '\'"`':
            in_str = c
            result.append(c)
            i += 1
            continue
        if c == '/' and i + 1 < n and content[i + 1] == '/':
            j = content.find('\n', i)
            if j == -1:
                i = n
            else:
                result.append('\n')
                i = j + 1
            continue
        if c == '/' and i + 1 < n and content[i + 1] == '*':
            j = content.find('*/', i + 2)
            end = j + 2 if j != -1 else n
            result.append('\n' * content.count('\n', i, end))
            i = end
            continue
        result.append(c)
        i += 1
    return ''.join(result)


# --------------------------------------------------------------------------
# Utilitarios de varredura de diretorios
# --------------------------------------------------------------------------

def find_files(root, extension):
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for f in filenames:
            if f.endswith(extension):
                result.append(os.path.join(dirpath, f))
    return result


# --------------------------------------------------------------------------
# Parsing de expressoes JS (tokenizacao por '+' respeitando strings/parenteses)
# --------------------------------------------------------------------------

def split_top_level_plus(expr):
    tokens = []
    depth = 0
    current = []
    in_str = None
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if in_str:
            current.append(c)
            if c == '\\' and i + 1 < n:
                current.append(expr[i + 1])
                i += 2
                continue
            if c == in_str:
                in_str = None
            i += 1
            continue
        if c in '\'"`':
            in_str = c
            current.append(c)
            i += 1
            continue
        if c in '([{':
            depth += 1
            current.append(c)
            i += 1
            continue
        if c in ')]}':
            depth -= 1
            current.append(c)
            i += 1
            continue
        if c == '+' and depth == 0:
            tokens.append(''.join(current).strip())
            current = []
            i += 1
            continue
        current.append(c)
        i += 1
    if current:
        tokens.append(''.join(current).strip())
    return [t for t in tokens if t]


def classify_token(tok):
    tok = tok.strip()
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in '\'"`':
        return ('lit', tok[1:-1])
    return ('dyn', tok)


IDENT_RE = re.compile(r'^[A-Za-z_$][\w$]*$')


def resolve_expr(expr, var_defs, pos, local_params_fn, seen=None):
    """Resolve identificadores usando a definicao mais proxima (nearest
    preceding) antes de 'pos'. Necessario porque o mesmo nome de variavel
    local (ex.: 'exportUrl') costuma ser redefinido em varias funcoes do
    mesmo arquivo; pegar sempre a primeira definicao do arquivo misturaria
    os resultados entre funcoes diferentes.

    Identificadores que sao PARAMETROS da funcao que envolve 'pos' nunca sao
    substituidos por uma 'var' de mesmo nome de outra funcao (isso ocorre,
    por exemplo, em funcoes auxiliares genericas tipo
    'function exportarDocumentos(filtro, exportUrl, nome)' que recebem a
    url pronta via parametro) -- nesse caso o identificador fica como
    dinamico/nao resolvido em vez de herdar um valor de outro escopo."""
    if seen is None:
        seen = frozenset()
    local_params = local_params_fn(pos)
    result = []
    for tok in split_top_level_plus(expr):
        kind, val = classify_token(tok)
        if kind == 'dyn' and IDENT_RE.match(val) and val not in local_params \
                and val in var_defs and val not in seen:
            candidates = [(p, e) for (p, e) in var_defs[val] if p < pos]
            if candidates:
                def_pos, def_expr = max(candidates, key=lambda t: t[0])
                result.extend(resolve_expr(def_expr, var_defs, def_pos, local_params_fn, seen | {val}))
                continue
        result.append((kind, val))
    return result


def tokens_to_segments(tokens):
    tokens = list(tokens)
    # Remove prefixo dinamico inicial (ex.: appValue.rest), que nao tem
    # correspondente no @Path do backend (que ja e relativo ao recurso).
    while tokens and tokens[0][0] == 'dyn':
        tokens.pop(0)
    parts = []
    for kind, val in tokens:
        parts.append(val if kind == 'lit' else SENTINEL)
    joined = ''.join(parts)
    segments = []
    for seg in joined.split('/'):
        if seg == '':
            continue
        segments.append('*' if SENTINEL in seg else seg.lower())
    return segments


# --------------------------------------------------------------------------
# Extracao de chamadas $http / Upload.upload no frontend
# --------------------------------------------------------------------------

def scan_expr(text, i):
    """Varre 'text' a partir de i ate encontrar ',' ou fechamento de bloco
    no nivel 0, respeitando strings e aninhamento de (), [], {}."""
    depth = 0
    in_str = None
    start = i
    n = len(text)
    while i < n:
        c = text[i]
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
        if c in '([{':
            depth += 1
            i += 1
            continue
        if c in ')]}':
            if depth == 0:
                break
            depth -= 1
            i += 1
            continue
        if c == ',' and depth == 0:
            break
        i += 1
    return text[start:i].strip(), i


def extract_call_blocks(content):
    """Encontra chamadas $http(...) e Upload.upload(...), retornando o
    texto completo do argumento (respeitando parenteses aninhados)."""
    blocks = []
    for m in re.finditer(r'(?<!\w)(\$http|Upload\.upload)\s*\(', content):
        depth = 0
        in_str = None
        i = m.end() - 1  # posicao do '('
        start = i
        n = len(content)
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
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        blocks.append({'kind': m.group(1), 'pos': m.start(), 'text': content[start:i]})
    return blocks


# --------------------------------------------------------------------------
# Mapeamento view (templateUrl) -> controller, via rotas ($stateProvider) e
# modais ($modal.open/$uibModal.open) -- usado pelos scripts que precisam
# saber qual HTML pertence a qual controller (em vez de tratar controllerAs
# 'vm' como global em todo o frontend).
# --------------------------------------------------------------------------

def extract_view_controller_pairs(content):
    """Varre 'content' mantendo uma pilha de objetos '{...}' abertos; toda
    vez que acha 'templateUrl:' ou 'controller: "X"' anota no objeto
    ATUALMENTE mais interno (topo da pilha). Ao fechar um objeto que tinha
    'templateUrl', devolve (expressao_templateUrl, posicao, controller_ou_
    None). Cobre '$stateProvider.state(..., {views: {content: {templateUrl,
    controller}}})' e '$modal.open({templateUrl, controller})' da mesma
    forma, pois ambos sao apenas um objeto literal com essas duas chaves
    como propriedades diretas."""
    pairs = []
    stack = []
    i = 0
    n = len(content)
    while i < n:
        c = content[i]
        if c in '\'"`':
            quote = c
            i += 1
            while i < n and content[i] != quote:
                if content[i] == '\\':
                    i += 1
                i += 1
            i += 1
            continue
        if c == '{':
            stack.append({'expr': None, 'pos': None, 'controller': None})
            i += 1
            continue
        if c == '}':
            if stack:
                frame = stack.pop()
                if frame['expr'] is not None:
                    pairs.append((frame['expr'], frame['pos'], frame['controller']))
            i += 1
            continue
        if stack:
            m = TEMPLATE_URL_KEY_RE.match(content, i)
            if m:
                expr, end = scan_expr(content, m.end())
                stack[-1]['expr'] = expr
                stack[-1]['pos'] = m.start()
                i = end
                continue
            m2 = CONTROLLER_KEY_RE.match(content, i)
            if m2:
                stack[-1]['controller'] = m2.group(1)
                i = m2.end()
                continue
        i += 1
    return pairs


def resolve_template_path(expr, var_defs, pos):
    tokens = resolve_expr(expr, var_defs, pos, lambda _p: set())
    if any(kind == 'dyn' for kind, _ in tokens):
        return None
    literal = ''.join(val for _, val in tokens).strip()
    return literal or None


def map_html_to_controllers(all_js, frontend_dir, html_paths):
    """Retorna (view_controllers, unresolved): view_controllers e um dict
    path_html -> set(nome_controller) montado lendo templateUrl/controller
    em TODO .js (rotas + modais); unresolved e a contagem de templateUrl
    encontrados cuja expressao nao resolveu para um caminho 100% literal
    (ex.: concatenacao com algo alem de 'var' local)."""
    html_by_norm_path = {os.path.normpath(p): p for p in html_paths}
    view_controllers = {}
    unresolved = 0
    for path, content in all_js:
        if 'templateUrl' not in content:
            continue
        var_defs = {}
        for m in VAR_DEF_RE.finditer(content):
            name, vexpr = m.group(1), m.group(2)
            var_defs.setdefault(name, []).append((m.start(), vexpr))

        for expr, pos, controller in extract_view_controller_pairs(content):
            if not controller:
                continue
            literal = resolve_template_path(expr, var_defs, pos)
            if literal is None:
                unresolved += 1
                continue
            norm = os.path.normpath(os.path.join(frontend_dir, literal.strip('/')))
            html_path = html_by_norm_path.get(norm)
            if not html_path:
                continue
            view_controllers.setdefault(html_path, set()).add(controller)
    return view_controllers, unresolved


def parse_param_names(raw):
    names = set()
    for part in raw.split(','):
        part = part.strip()
        if not part:
            continue
        name = re.split(r'[=\s]', part, 1)[0].strip()
        if IDENT_RE.match(name):
            names.add(name)
    return names


def parse_frontend_file(path, content):
    var_defs = {}
    for m in VAR_DEF_RE.finditer(content):
        name, expr = m.group(1), m.group(2)
        var_defs.setdefault(name, []).append((m.start(), expr))

    func_markers = [(m.start(), m.group(1), parse_param_names(m.group(2)))
                     for m in FUNC_NAME_RE.finditer(content)]

    def enclosing_function(pos):
        name = '(desconhecida)'
        for start, fname, _params in func_markers:
            if start <= pos:
                name = fname
            else:
                break
        return name

    def local_params_at(pos):
        params = set()
        for start, _fname, fparams in func_markers:
            if start <= pos:
                params = fparams
            else:
                break
        return params

    calls = []
    for block in extract_call_blocks(content):
        text = block['text']

        m_method = re.search(r'\bmethod\s*:\s*[\'"](\w+)[\'"]', text)
        if m_method:
            verb = m_method.group(1).upper()
        else:
            verb = 'POST' if block['kind'] == 'Upload.upload' else 'GET'

        m_url = re.search(r'\burl\s*:\s*', text)
        if not m_url:
            continue
        url_expr, _ = scan_expr(text, m_url.end())
        if not url_expr:
            continue

        tokens = resolve_expr(url_expr, var_defs, block['pos'], local_params_at)
        segments = tokens_to_segments(tokens)
        line_no = content.count('\n', 0, block['pos']) + 1

        calls.append({
            'file': path,
            'line': line_no,
            'function': enclosing_function(block['pos']),
            'verb': verb,
            'url_expr': url_expr,
            'segments': segments,
        })
    return calls


# --------------------------------------------------------------------------
# Extracao de endpoints JAX-RS no backend
# --------------------------------------------------------------------------

def normalize_path_to_segments(path_str):
    if not path_str:
        return []
    segments = []
    for seg in path_str.split('/'):
        if seg == '':
            continue
        if re.fullmatch(r'\{[^}]+\}', seg):
            segments.append('*')
        else:
            segments.append(seg.lower())
    return segments


def parse_backend_file(path, content):
    if '@Path' not in content:
        return []

    lines = content.splitlines()
    class_path = ''
    class_line_idx = None
    for idx, line in enumerate(lines):
        if CLASS_DECL_RE.search(line):
            class_line_idx = idx
            break
    if class_line_idx is not None:
        for j in range(class_line_idx, max(-1, class_line_idx - 15), -1):
            m = PATH_RE.search(lines[j])
            if m:
                class_path = m.group(1)
                break

    endpoints = []
    pending_verb = None
    pending_path = None
    for idx, line in enumerate(lines):
        vm = VERB_RE.search(line)
        if vm:
            pending_verb = vm.group(1)

        pm = PATH_RE.search(line)
        if pm and (class_line_idx is None or idx > class_line_idx):
            pending_path = pm.group(1)

        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('@') or stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*'):
            continue

        mdm = METHOD_DECL_RE.match(line)
        if mdm and (pending_verb or pending_path is not None):
            if pending_verb:
                endpoints.append({
                    'file': path,
                    'line': idx + 1,
                    'method_name': mdm.group(1),
                    'verb': pending_verb,
                    'raw_path': combine_raw(class_path, pending_path),
                    'segments': normalize_path_to_segments(class_path) + normalize_path_to_segments(pending_path),
                })
            pending_verb = None
            pending_path = None
        elif '(' not in line and ')' not in line:
            # Linha de codigo "solta" (nao e declaracao de metodo nem
            # continuacao de assinatura) -> descarta anotacoes pendentes
            pending_verb = None
            pending_path = None

    return endpoints


def combine_raw(class_path, method_path):
    a = (class_path or '').strip('/')
    b = (method_path or '').strip('/')
    if a and b:
        return '/' + a + '/' + b
    return '/' + (a or b)


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------

def segments_match(seg_a, seg_b):
    if len(seg_a) != len(seg_b):
        return False
    for a, b in zip(seg_a, seg_b):
        if a == '*' or b == '*':
            continue
        if a != b:
            return False
    return True


def find_matching_endpoint(call, endpoints):
    for ep in endpoints:
        if ep['verb'].upper() == call['verb'].upper() and segments_match(ep['segments'], call['segments']):
            return ep
    return None


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def setup_path_completion():
    """Habilita autocompletar de diretorios com Tab (estilo 'cd' do bash)."""
    if readline is None:
        return

    def complete_path(text, state):
        expanded = os.path.expanduser(text)
        try:
            candidates = glob.glob(glob.escape(expanded) + '*')
        except re.error:
            candidates = []
        matches = sorted(c + os.sep for c in candidates if os.path.isdir(c))
        try:
            return matches[state]
        except IndexError:
            return None

    readline.set_completer_delims(' \t\n')
    readline.parse_and_bind('tab: complete')
    readline.set_completer(complete_path)


MANUAL_ENTRY_LABEL = '✎ digitar caminho manualmente...'


def list_all_dirs(root):
    """Lista (recursivamente) todos os subdiretorios de 'root', pulando
    pastas pesadas/irrelevantes para navegacao (node_modules, .git, etc.)."""
    dirs = []
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in BROWSE_IGNORED_DIRS and not d.startswith('.')]
        dirs.append(dirpath)
    return dirs


def find_repo_root(path, fallback):
    """Sobe a arvore de diretorios a partir de 'path' procurando uma pasta
    com '.git' (raiz do repositorio). Se nao achar, retorna 'fallback'."""
    cur = os.path.abspath(path)
    while True:
        if os.path.isdir(os.path.join(cur, '.git')):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return fallback
        cur = parent


def dir_preview_cmd():
    """Comando de preview colorido do conteudo da pasta sob o cursor no fzf.
    Usa 'eza' se disponivel (mesma ferramenta ja usada no fzf-tab do zsh do
    usuario para o 'cd'); cai para 'ls --color' se nao houver eza; None se
    nem isso existir (preview fica desligado nesse caso)."""
    if shutil.which('eza'):
        return 'eza -1 --color=always --group-directories-first {} 2>/dev/null'
    if shutil.which('ls'):
        return 'ls -la --color=always {} 2>/dev/null'
    return None


def pick_dir_with_fzf(root, header):
    """Abre o fzf com todas as subpastas de 'root' para selecao interativa
    (digite para filtrar, Enter para confirmar, Esc para cancelar), com
    preview colorido do conteudo da pasta sob o cursor. Retorna o caminho
    escolhido, ou None se o fzf nao estiver disponivel, nao houver terminal
    interativo, ou o usuario cancelar/preferir digitar manualmente."""
    if shutil.which('fzf') is None or not sys.stdin.isatty():
        return None
    dirs = list_all_dirs(root)
    lines = [MANUAL_ENTRY_LABEL] + sorted(dirs)
    cmd = ['fzf', '--ansi', '--prompt=pasta> ', '--height=90%', '--reverse', '--header=' + header]
    preview = dir_preview_cmd()
    if preview:
        cmd += ['--preview', preview, '--preview-window=up:50%']
    try:
        proc = subprocess.run(cmd, input='\n'.join(lines), capture_output=True, text=True)
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    selected = proc.stdout.strip()
    if not selected or selected == MANUAL_ENTRY_LABEL:
        return None
    return selected


def ask_dir(prompt, arg_value, search_root=None, header=None):
    if arg_value:
        value = os.path.expanduser(arg_value)
        if not os.path.isdir(value):
            print(f"ERRO: '{value}' nao e um diretorio valido.")
            sys.exit(1)
        return value

    root = search_root or os.path.expanduser('~')
    picked = pick_dir_with_fzf(root, header or prompt)
    if picked:
        return picked

    while True:
        value = input(prompt).strip()
        value = os.path.expanduser(value)
        if os.path.isdir(value):
            return value
        print(f"'{value}' nao e um diretorio valido. Tente novamente (use Tab para autocompletar).")


# --------------------------------------------------------------------------
# Seletor interativo de resultados -> abre o item escolhido no editor
# --------------------------------------------------------------------------

# Preview colorido: cabecalho ciano com 'arquivo:linha' + janela de 12 linhas
# de contexto para cada lado. {3}/{4} sao os campos ocultos (arquivo, linha)
# de cada entrada -- ver pick_and_open_in_editor e code_preview_cmd().

# Fallback sem syntax highlight (usado quando 'bat'/'batcat' nao esta
# instalado): linha alvo em VIDEO REVERSO (\033[7m). Reverso inverte as
# cores ATUAIS do terminal (nao usa indices fixos tipo "preto"/"amarelo"),
# entao continua legivel em qualquer esquema de cores, ao contrario de uma
# cor de fundo fixa que pode ficar sem contraste dependendo do tema. Nao
# depende de nenhuma ferramenta externa, so awk/printf.
PREVIEW_CMD_PLAIN = r"""printf '\033[1;36m%s:%s\033[0m\n\n' {3} {4}; awk -v t={4} 'NR>=t-12 && NR<=t+12 {if (NR==t) printf "\033[1;7m %4d > %s\033[0m\n", NR, $0; else printf " %4d   %s\n", NR, $0}' {3}"""


def code_preview_cmd():
    """Preview do trecho de codigo para o fzf de pick_and_open_in_editor. Usa
    'bat' (pacote 'bat' no Ubuntu/Debian pode instalar o binario como
    'batcat') para syntax highlight por linguagem quando disponivel --
    '--highlight-line' ja destaca a linha alvo com um fundo diferenciado, sem
    precisar de video reverso manual. Sem 'bat'/'batcat' instalado, cai para
    PREVIEW_CMD_PLAIN (sem highlight de sintaxe, so awk/printf)."""
    bat_bin = shutil.which('bat') or shutil.which('batcat')
    if not bat_bin:
        return PREVIEW_CMD_PLAIN
    # 'line={4}' primeiro: o fzf substitui {n} ja entre aspas simples (ex.:
    # '42'), e essas aspas literais quebram "$(( {4} - 12 ))" (illegal
    # character: '). Numa atribuicao normal as aspas sao removidas pelo
    # shell, entao usamos a variavel $line dentro da aritmetica em vez do
    # placeholder direto.
    return (
        r"line={4}; start=$(( line - 12 )); [ $start -lt 1 ] && start=1; "
        r"printf '\033[1;36m%s:%s\033[0m\n\n' {3} {4}; "
        + bat_bin +
        r" --color=always --style=numbers --paging=never "
        r"--highlight-line=$line --line-range=$start:$(( line + 12 )) {3}"
    )


ANSI_RE = re.compile(r'\033\[[0-9;]*m')

FZF_CHROME_MARGIN = 6  # marcador/scrollbar do fzf, para a linha nao "quebrar"


def visible_len(text):
    """Tamanho da string como aparece no terminal, ignorando codigos ANSI de
    cor (necessario para alinhar corretamente rotulos que usam warn())."""
    return len(ANSI_RE.sub('', text))


def get_terminal_columns():
    """Largura real do terminal. Ao contrario de shutil.get_terminal_size(),
    NAO confia nas variaveis de ambiente COLUMNS/LINES -- em zsh/tmux elas
    costumam ficar desatualizadas apos redimensionar o painel, o que fazia o
    fzf truncar a linha (a largura calculada ficava maior que a real)."""
    try:
        return os.get_terminal_size(sys.stdout.fileno()).columns
    except OSError:
        return shutil.get_terminal_size(fallback=(100, 24)).columns


def build_aligned_line(label, file_path, line_no):
    """Monta 'label' + espacos + 'arquivo:linha', empurrando o 'arquivo:linha'
    ate a borda direita do terminal (aproximado, com uma margem de seguranca
    para os marcadores do fzf)."""
    loc = f"{os.path.basename(file_path)}:{line_no}" if file_path else ''
    if not loc:
        return label
    term_width = get_terminal_columns()
    usable_width = max(term_width - FZF_CHROME_MARGIN, 20)
    gap = usable_width - visible_len(label) - len(loc)
    return f"{label}{' ' * max(gap, 2)}{loc}"


def pick_and_open_in_editor(items, format_item):
    """Mostra 'items' (rotulados via format_item(item) -> str, seguido de
    'arquivo:linha' alinhado a direita) em um fzf para o usuario escolher um,
    com preview colorido do trecho de codigo ao lado; ao confirmar, abre
    item['file'] no nvim/vim ja posicionado em item['line'] (linha 1 se
    ausente). Repete ate o usuario cancelar (Esc/Ctrl-C). Nao faz nada se a
    lista estiver vazia, nao houver terminal interativo, ou fzf/nvim/vim nao
    estiverem instalados."""
    if not items:
        return
    if shutil.which('fzf') is None or not sys.stdin.isatty():
        return
    editor = shutil.which('nvim') or shutil.which('vim')
    if editor is None:
        print("\n(nvim/vim nao encontrado no PATH -- pulando o seletor interativo.)")
        return

    line_width = max((len(str(item.get('line') or 1)) for item in items), default=1)
    lines = []
    for i, item in enumerate(items):
        file_path = item.get('file') or ''
        line_no = item.get('line') or 1
        label = format_item(item)
        display = build_aligned_line(label, file_path, f"{line_no:>{line_width}}")
        lines.append(f"{i}\t{display}\t{file_path}\t{line_no}")

    preview_cmd = code_preview_cmd()

    print(f"\nDigite para filtrar e Enter para abrir no editor ({os.path.basename(editor)}); Esc para sair.")
    while True:
        try:
            proc = subprocess.run(
                ['fzf', '--ansi', '--delimiter=\t', '--with-nth=2',
                 '--preview', preview_cmd, '--preview-window=up:55%:wrap',
                 '--height=90%', '--reverse',
                 '--header=Selecione um item para abrir no editor (Esc para sair)'],
                input='\n'.join(lines), capture_output=True, text=True,
            )
        except OSError:
            return
        if proc.returncode != 0 or not proc.stdout.strip():
            return
        idx_str = proc.stdout.split('\t', 1)[0]
        try:
            item = items[int(idx_str)]
        except (ValueError, IndexError):
            continue
        file_path = item.get('file')
        if not file_path:
            continue
        line_no = item.get('line') or 1
        subprocess.run([editor, f'+{line_no}', file_path])


def analyze(frontend_dir, backend_dir, log=print):
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

    unmatched = []
    matched_count = 0
    for call in all_calls:
        ep = find_matching_endpoint(call, all_endpoints)
        if ep:
            matched_count += 1
        else:
            unmatched.append(call)

    return {
        'calls': all_calls,
        'endpoints': all_endpoints,
        'unmatched': unmatched,
        'matched_count': matched_count,
    }


def format_unmatched_call(call):
    return f"[{call['verb']:6}] {call['url_expr']}"


def print_report(result):
    unmatched = result['unmatched']
    print("\n" + "=" * 78)
    if unmatched:
        print(f"Chamadas SEM endpoint correspondente encontrado: {len(unmatched)}\n")
        by_file = {}
        for call in unmatched:
            by_file.setdefault(call['file'], []).append(call)
        for f in sorted(by_file):
            print(f"- {f}")
            for call in sorted(by_file[f], key=lambda c: c['line']):
                print(f"    linha {call['line']:>5}  [{call['verb']:6}]  {call['function']}()  "
                      f"url: {call['url_expr']}")
                print(f"                   caminho normalizado: /{'/'.join(call['segments'])}")
            print()
    else:
        print("Nenhuma chamada orfa encontrada: todas possuem endpoint correspondente.")

    print("=" * 78)
    print(f"Resumo: {len(result['calls'])} chamada(s) | {result['matched_count']} com correspondencia | "
          f"{len(unmatched)} sem correspondencia | {len(result['endpoints'])} endpoint(s) no backend")
    print("\nObs.: script heuristico (regex), cobre padroes $http({...}) e "
          "Upload.upload({...}) no frontend e anotacoes JAX-RS (@Path/@GET/@POST/...) "
          "no backend. Revise manualmente os itens listados antes de concluir que "
          "a API realmente nao existe.")


def main():
    setup_path_completion()
    args = sys.argv[1:]
    home = os.path.expanduser('~')
    frontend_dir = ask_dir(
        "Diretorio com as chamadas de API (frontend, ex.: .../web/src/main/angular): ",
        args[0] if len(args) > 0 else None,
        search_root=home,
        header='Selecione a pasta do FRONTEND (chamadas de API)',
    )
    backend_dir = ask_dir(
        "Diretorio com as APIs (backend, ex.: .../web/src/main/java): ",
        args[1] if len(args) > 1 else None,
        search_root=find_repo_root(frontend_dir, home),
        header='Selecione a pasta do BACKEND (APIs)',
    )

    result = analyze(frontend_dir, backend_dir)
    print_report(result)
    pick_and_open_in_editor(result['unmatched'], format_unmatched_call)


if __name__ == '__main__':
    main()
