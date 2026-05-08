"""
Kaa - Linguagem de Programação v5.0
=====================================
Entry point da linguagem Kaa.

v5.0:
- VM com dispatch table (mais rápido)
- Sistema de módulos completo na VM (import/export)
- Import Python via VM (add -py)
- Suporte a .kaac: compilar para bytecode e carregar bytecode pré-compilado
- Instalador self-contained com Python portátil (KAA_HOME / KAA_LIBS)

Uso:
  kaa arquivo.kaa         → executa direto
  kaa arquivo.kaa -c      → compila para arquivo.kaac
  kaa arquivo.kaac        → executa bytecode pré-compilado
  kaa --version           → exibe versão instalada
"""

import sys
import os

# ─── Caminhos de instalação ───────────────────────────────────────────────────
# Quando instalado via installer: KAA_HOME=/opt/kaa, KAA_LIBS=/opt/kaa/libs
# Em desenvolvimento: usa o diretório deste arquivo como base
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_KAA_HOME = os.environ.get('KAA_HOME', _THIS_DIR)
_KAA_LIBS = os.environ.get('KAA_LIBS', os.path.join(_THIS_DIR, 'libs'))

# Garante que o core está no sys.path (necessário quando instalado)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from scanner import Scanner
from parser import Parser
from interpretador import Interpretador
from compiler import Compiler
from vm import VM

VERSAO       = '5.0'
EXTENSAO     = '.kaa'
EXT_BYTECODE = '.kaac'


class Kaa:
    """Executor principal da linguagem Kaa."""

    def __init__(self):
        self.interp = Interpretador()
        self.vm     = VM()
        self.erro   = False
        
        # Otimização para IDEs: Se um debugger estiver ativado (como debugpy no VS Code),
        # a execução da VM compilada (Cython C-extension) pode sofrer com problemas de ABI
        # em contêineres Flatpak ou impossibilitar o trace passo a passo do interpretador.
        # Nesses casos, fazemos o fallback automático para o Interpretador Python.
        import sys
        if sys.gettrace() is not None:
            print("[Kaa Debugger] Ambiente de depuração detectado. Usando Interpretador AST (VM desativada).")
            self._use_vm = False
        else:
            self._use_vm = True

    def run(self, codigo, caminho=None):
        """Compila e executa código-fonte Kaa na VM."""
        try:
            tokens = Scanner(codigo).escanear()
            stmts  = Parser(tokens).parse()

            if self._use_vm:
                func = Compiler().compile(stmts, caminho or '<main>')
                self._setup_vm_builtins()
                self.vm.run(func)
            else:
                self.interp.interpretar(stmts)

        except SyntaxError as e:
            print(f'[Sintaxe] {e}', file=sys.stderr)
            self.erro = True
        except RuntimeError as e:
            print(f'[Execução] {e}', file=sys.stderr)
            self.erro = True
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.erro = True

    def run_bytecode(self, caminho_kaac):
        """Executa bytecode pré-compilado (.kaac)."""
        try:
            from bytecode_io import carregar
            func = carregar(caminho_kaac)
            self._setup_vm_builtins()
            self.vm.run(func)
        except Exception as e:
            print(f'[Erro] {e}', file=sys.stderr)
            self.erro = True

    def compile_to_file(self, caminho_kaa, caminho_saida=None):
        """Compila .kaa → .kaac e salva em disco."""
        try:
            with open(caminho_kaa, encoding='utf-8') as f:
                codigo = f.read()

            tokens = Scanner(codigo).escanear()
            stmts  = Parser(tokens).parse()
            func   = Compiler().compile(stmts, caminho_kaa)

            if caminho_saida is None:
                caminho_saida = os.path.splitext(caminho_kaa)[0] + EXT_BYTECODE

            from bytecode_io import salvar
            salvar(func, caminho_saida)
            size = os.path.getsize(caminho_saida)
            print(f'Compilado: {caminho_saida} ({size} bytes)')
        except Exception as e:
            print(f'[Erro ao compilar] {e}', file=sys.stderr)
            self.erro = True

    def _setup_vm_builtins(self):
        """Transfere builtins do interpretador para a VM."""
        for name in ['sleep', 'timestamp', 'time_str', 'date_str', 'wait_until']:
            builtin_fn = getattr(self.interp, f'_builtin_{name}', None)
            if builtin_fn:
                self.vm.set_builtin(name, builtin_fn)

    def run_file(self, caminho):
        """Executa um arquivo .kaa ou .kaac."""
        _, ext = os.path.splitext(caminho)
        ext = ext.lower()

        if ext == EXT_BYTECODE:
            # Executa bytecode pré-compilado
            caminho_abs = os.path.abspath(caminho)
            old_dir = os.getcwd()
            os.chdir(os.path.dirname(caminho_abs) or '.')
            try:
                self.run_bytecode(caminho_abs)
            finally:
                os.chdir(old_dir)

        elif ext == EXTENSAO:
            try:
                with open(caminho, encoding='utf-8') as f:
                    codigo = f.read()
            except FileNotFoundError:
                print(f'[Erro] Arquivo não encontrado: {caminho}', file=sys.stderr)
                sys.exit(66)

            caminho_abs = os.path.abspath(caminho)
            old_dir = os.getcwd()
            os.chdir(os.path.dirname(caminho_abs) or '.')
            try:
                self.run(codigo, caminho_abs)
            finally:
                os.chdir(old_dir)
        else:
            print(f'[Erro] Extensão não suportada: {ext}. Use {EXTENSAO} ou {EXT_BYTECODE}.')
            sys.exit(64)

        if self.erro:
            sys.exit(65)

    def repl(self):
        """Modo interativo (REPL)."""
        print('Kaa v4.5 - REPL interativo (digite "sair" para encerrar)')
        print('Modo: VM Bytecode com dispatch table | .kaac suportado')
        while True:
            try:
                linha = input('>>> ')
            except EOFError:
                break
            if linha.strip() in ('sair', 'exit', 'quit'):
                break
            self.run(linha)
            self.erro = False


if __name__ == '__main__':
    kaa = Kaa()

    if len(sys.argv) == 1:
        print('[Erro] O modo REPL (interativo) não está disponível.')
        print('Tente rodar: kaa arquivo.kaa')
        sys.exit(64)
    elif len(sys.argv) == 2 and sys.argv[1] in ('--version', '-v'):
        print(f'Kaa {VERSAO}')
        print(f'  Home  : {_KAA_HOME}')
        print(f'  Libs  : {_KAA_LIBS}')
        print(f'  Python: {sys.version.split()[0]}')
        sys.exit(0)
    elif len(sys.argv) == 2:
        kaa.run_file(sys.argv[1])
    elif len(sys.argv) == 3 and sys.argv[2] == '-c':
        # Compilar para bytecode
        kaa.compile_to_file(sys.argv[1])
    else:
        print(f'Uso:')
        print(f'  kaa arquivo.kaa         → executar código-fonte')
        print(f'  kaa arquivo.kaa -c      → compilar para .kaac')
        print(f'  kaa arquivo.kaac        → executar bytecode pré-compilado')
        print(f'  kaa --version           → exibir versão')
        sys.exit(64)

