#!/usr/bin/env python3
"""
Menu para escolher qual verificacao rodar (chama o main() do script
correspondente). Uso: python3 verificar.py

Cada verificacao, ao final, oferece um seletor (fzf) para escolher um item
do relatorio e abri-lo direto no nvim/vim, ja posicionado na linha certa.
"""

import shutil
import subprocess
import sys

import verificar_apis
import verificar_apis_nao_usadas
import verificar_metodos_angular_nao_usados
import verificar_metodos_java_nao_usados
import verificar_variaveis_controller_nao_usadas
import verificar_vm_indefinidos_no_html

CHOICES = [
    ("Chamadas de API sem endpoint correspondente (frontend -> backend)", verificar_apis),
    ("APIs sem nenhuma chamada correspondente (backend -> frontend)", verificar_apis_nao_usadas),
    ("Metodos/funcoes Angular sem uso (services + controllers + funcoes locais)", verificar_metodos_angular_nao_usados),
    ("Metodos Java sem uso (incluindo publicos)", verificar_metodos_java_nao_usados),
    ("Variaveis de controller Angular sem uso", verificar_variaveis_controller_nao_usadas),
    ("Chamadas 'vm.algo' no HTML sem correspondencia no controller", verificar_vm_indefinidos_no_html),
]


def pick_menu():
    if shutil.which('fzf') and sys.stdin.isatty():
        lines = [f"{i}\t{i + 1}) {label}" for i, (label, _mod) in enumerate(CHOICES)]
        try:
            proc = subprocess.run(
                ['fzf', '--delimiter=\t', '--with-nth=2..', '--height=40%', '--reverse',
                 '--header=Selecione a verificacao que deseja rodar (Esc para sair)'],
                input='\n'.join(lines), capture_output=True, text=True,
            )
        except OSError:
            proc = None
        if proc is not None and proc.returncode == 0 and proc.stdout.strip():
            idx = int(proc.stdout.split('\t', 1)[0])
            return CHOICES[idx][1]
        return None

    print("Escolha uma verificacao:")
    for i, (label, _mod) in enumerate(CHOICES):
        print(f"  {i + 1}) {label}")
    print("  0) sair")
    raw = input("Numero: ").strip()
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(CHOICES):
            return CHOICES[idx][1]
    except ValueError:
        pass
    return None


def main():
    while True:
        try:
            module = pick_menu()
        except (EOFError, KeyboardInterrupt):
            print("\nAte mais.")
            return
        if module is None:
            print("Ate mais.")
            return
        module.main()
        print()


if __name__ == '__main__':
    main()
