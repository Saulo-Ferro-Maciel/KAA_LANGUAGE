"""
Interpretador da linguagem Kaa.

Segue o padrão Visitor: cada nó do AST tem um método 'visitar_*' que
sabe como evaluá-lo. O ambiente (scoping) é gerido por uma cadeia de
Ambiente objects que apontam para o enclosing (pai).

Fluxo:
  Scanner (lexical) → Parser (AST) → Interpretador (execução)
"""

import os
import sys
import time
from datetime import datetime
from ambiente import Ambiente, Arena
from funcao import PyloxFuncao, RetornoException
from tipos_token import TipoToken
from ast_nos import (
    Binaria, Unaria, Literal, Agrupamento, Variavel, Atribuicao, Chamada, Logico,
    DeclVar, DeclFun, StmtExpr, StmtPrint, StmtBloco, StmtIf, StmtWhile, StmtReturn,
    StmtInput, Lista, Tuplo, Dicionario, AcessoIndice, DeclExpon, StmtImport,
    AcessoAtributo
)


class Interpretador:
    """
    Executor do AST. Mantém 'env' como o ambiente atual (Current Scope).
    Ambientes pais são acedidos via 'enclosing'.

    OTIMIZAÇÕES:
    - Tabela de dispatch para visitor (evita getattr repetido)
    - Inline cache para variáveis locais
    - Fast path para operações aritméticas
    """

    # Constantes booleanas Kaa
    KAA_TRUE = True   # -T
    KAA_FALSE = False # -F

    def __init__(self):
        self.global_env = Ambiente()   # escopo global (raiz)
        self.env        = self.global_env
        self.carregando = set()        # arquivos sendo carregados (detecção de ciclos)
        self.arenas     = {}           # {caminho_modulo: Arena} - GC por s-bot

        # OTIMIZAÇÃO 1: Tabela de dispatch pré-computada (evita getattr em cada nó)
        self._dispatch = {
            'Literal': self.visitar_Literal,
            'Agrupamento': self.visitar_Agrupamento,
            'Lista': self.visitar_Lista,
            'Tuplo': self.visitar_Tuplo,
            'Dicionario': self.visitar_Dicionario,
            'AcessoIndice': self.visitar_AcessoIndice,
            'AcessoAtributo': self.visitar_AcessoAtributo,
            'Unaria': self.visitar_Unaria,
            'Binaria': self.visitar_Binaria,
            'Logico': self.visitar_Logico,
            'Variavel': self.visitar_Variavel,
            'Atribuicao': self.visitar_Atribuicao,
            'Chamada': self.visitar_Chamada,
            'StmtExpr': self.visitar_StmtExpr,
            'StmtPrint': self.visitar_StmtPrint,
            'StmtInput': self.visitar_StmtInput,
            'StmtBloco': self.visitar_StmtBloco,
            'DeclVar': self.visitar_DeclVar,
            'DeclFun': self.visitar_DeclFun,
            'DeclExpon': self.visitar_DeclExpon,
            'StmtImport': self.visitar_StmtImport,
            'StmtIf': self.visitar_StmtIf,
            'StmtWhile': self.visitar_StmtWhile,
            'StmtReturn': self.visitar_StmtReturn,
        }

        # OTIMIZAÇÃO 2: Cache L1 para variáveis locais (hot path crítico)
        self._var_cache = {}  # {lexema: (ambiente_id, valor)}

        # OTIMIZAÇÃO 3: Cache especializado para _str (int e float separados)
        self._int_str_cache = {}    # {int: str}
        self._float_str_cache = {}  # {float: str}

    def _builtin_sleep(self, segundos):
        time.sleep(float(segundos))
        return None

    def _builtin_timestamp(self):
        return time.time()

    def _builtin_time_str(self):
        return datetime.now().strftime("%H:%M:%S")

    def _builtin_date_str(self, formato="dd/mm/aaaa"):
        agora = datetime.now()
        if formato == "dd/mm/aaaa":
            return agora.strftime("%d/%m/%Y")
        elif formato == "mm/dd/aaaa":
            return agora.strftime("%m/%d/%Y")
        elif formato == "aaaa-mm-dd":
            return agora.strftime("%Y-%m-%d")
        else:
            return agora.strftime("%d/%m/%Y")

    def _builtin_wait_until(self, hora):
        agora = datetime.now()
        try:
            partes = hora.split(":")
            h = int(partes[0])
            m = int(partes[1]) if len(partes) > 1 else 0
            alvo = agora.replace(hour=h, minute=m, second=0, microsecond=0)
            if alvo < agora:
                alvo = alvo.replace(day=alvo.day + 1)
            delta = (alvo - agora).total_seconds()
            if delta > 0:
                time.sleep(delta)
            return True
        except:
            return False

    def _builtin_destroy_arena(self, nome_modulo=None):
        if nome_modulo is None:
            count = len(self.arenas)
            for arena in self.arenas.values():
                arena.liberar()
            self.arenas.clear()
            return count
        for caminho, arena in list(self.arenas.items()):
            if arena.nome == nome_modulo or caminho.endswith(nome_modulo + '.kaa'):
                arena.liberar()
                del self.arenas[caminho]
                return 1
        return 0

    def _builtin_arenas_info(self):
        info = []
        for caminho, arena in self.arenas.items():
            info.append({
                'nome': arena.nome,
                'caminho': caminho,
                'ambientes': len(arena.ambientes)
            })
        return info

    # --- Entry point ---

    def interpretar(self, stmts):
        """
        Recebe uma lista de statements (raiz do AST) e executa em sequência.
        Captura RetornoException no escopo global para permitir 'return' como exit.

        OTIMIZAÇÃO: Inline de executar() para evitar camada extra.
        """
        try:
            for stmt in stmts:
                self._executar_inline(stmt)
        except RetornoException as e:
            pass

    def _executar_inline(self, stmt):
        """Execução direta sem wrapper - hot path crítico."""
        nome = type(stmt).__name__
        m = self._dispatch.get(nome)
        if m is None:
            raise NotImplementedError(f'Sem visitante para {nome}')
        return m(stmt)

    def executar(self, stmt):
        """Dispatch para o visitor do nó. Retorna o resultado da expressão."""
        return self._executar_inline(stmt)

    def _avaliar_inline(self, expr):
        """
        Avaliação direta com cache para casos comuns.
        OTIMIZAÇÃO: Evita dispatch para Literal e Variavel.
        """
        tipo = type(expr)
        # Fast path: Literal (sem lookup)
        if tipo is Literal:
            return expr.valor
        # Fast path: Variavel (apenas busca no ambiente)
        if tipo is Variavel:
            return self.env.obter(expr.nome)
        # Fallback: dispatch completo
        return self._dispatch.get(type(expr).__name__, lambda x: None)(expr)

    def avaliar(self, expr):
        """Avalia uma expressão e retorna o seu valor Python resultante."""
        return self._avaliar_inline(expr)

    # --- Visitor dispatch ---

    def visitar(self, no):
        """
        Padrão Visitor: usa tabela de dispatch pré-computada.
        Mais rápido que getattr() em cada chamada.
        """
        nome = type(no).__name__
        m = self._dispatch.get(nome)
        if m is None:
            raise NotImplementedError(f'Sem visitante para {nome}')
        return m(no)

    # ═══════════════════════════════════════════════════════════
    #  EXPRESSÕES
    # ═══════════════════════════════════════════════════════════

    def visitar_Literal(self, no):
        """Literais: números, strings, -T, -F, nil. Já são valores Python."""
        return no.valor

    def visitar_Agrupamento(self, no):
        """Agrupa uma expressão entre parênteses: ( expr )"""
        return self._avaliar_inline(no.expr)

    def visitar_Lista(self, no):
        """Lista literal: [elem1, elem2, ...]"""
        return [self._avaliar_inline(elem) for elem in no.elementos]

    def visitar_Tuplo(self, no):
        """Tuplo literal: (elem1, elem2, ...)"""
        return tuple(self._avaliar_inline(elem) for elem in no.elementos)

    def visitar_Dicionario(self, no):
        """Dicionário literal: {chave1: valor1, ...}"""
        resultado = {}
        for chave, valor in zip(no.chaves, no.valores):
            k = self._avaliar_inline(chave)
            v = self._avaliar_inline(valor)
            resultado[k] = v
        return resultado

    def visitar_AcessoIndice(self, no):
        """
        Acesso a índice: objeto[indice]
        Suporta listas, tuplos e dicionários.

        OTIMIZAÇÃO: Verificação de tipo via type() e comparação direta.
        OTIMIZAÇÃO: _avaliar_inline para casos comuns.
        """
        obj = self._avaliar_inline(no.objeto)
        idx = self._avaliar_inline(no.indice)
        linha = no.indice_token.linha

        # OTIMIZAÇÃO: type() é mais rápido que isinstance()
        # Converte float inteiro para int (ex: 1.0 → 1)
        if type(idx) is float and idx == int(idx):
            idx = int(idx)

        # Fast path para lista (caso mais comum)
        if type(obj) is list:
            if type(idx) is not int:
                raise RuntimeError(f'Linha {linha}: índice deve ser inteiro, obtido {type(idx).__name__}')
            if idx < 0 or idx >= len(obj):
                raise RuntimeError(f'Linha {linha}: índice {idx} fora dos limites (tamanho: {len(obj)})')
            return obj[idx]

        if type(obj) is tuple:
            if type(idx) is not int:
                raise RuntimeError(f'Linha {linha}: índice deve ser inteiro')
            if idx < 0 or idx >= len(obj):
                raise RuntimeError(f'Linha {linha}: índice {idx} fora dos limites')
            return obj[idx]

        if type(obj) is dict:
            if idx not in obj:
                raise RuntimeError(f'Linha {linha}: chave {idx!r} não existe')
            return obj[idx]

        raise RuntimeError(f'Linha {linha}: objeto não é indexável')

    def visitar_AcessoAtributo(self, no):
        """
        Acesso a atributo: objeto.atributo
        Usado para acessar métodos/atributos de módulos Python.
        Casos especiais:
          - lista.length → tamanho da lista
          - tuplo.length → tamanho do tuplo
          - dicionario.length → número de chaves
          - float.f_valuation → arredonda para 2 casas decimais
          - float.f_valuation(n) → arredonda para n casas decimais

        OTIMIZAÇÃO: Fast path para .length com type() direto.
        OTIMIZAÇÃO: _avaliar_inline para objeto.
        """
        obj = self._avaliar_inline(no.objeto)
        atributo = no.atributo.lexema

        # Fast path: .length para coleções
        if atributo == 'length':
            if type(obj) is list:
                return len(obj)
            if type(obj) is tuple:
                return len(obj)
            if type(obj) is dict:
                return len(obj)
            # Fallback para outros objetos Python
            try:
                return len(obj)
            except TypeError:
                pass

        # Fast path: .keys para dicionários (retorna lista de chaves)
        if atributo == 'keys':
            if type(obj) is dict:
                return list(obj.keys())
            # Fallback para outros objetos Python com dict_keys
            try:
                return list(obj.keys())
            except (TypeError, AttributeError):
                pass

        # NEW: f_valuation para redução de memória (floats)
        if atributo == 'f_valuation':
            if type(obj) is float:
                # Sem parênteses: retorna valor já arredondado para 2 casas
                fator = 100
                return round(obj * fator) / fator
            # Para inteiros, retorna o próprio valor (já é "otimizado")
            if type(obj) is int:
                return obj

        # NEW: rm_nil para GC manual de coleções (remove elementos nil)
        if atributo == 'rm_nil':
            # Lista: remove todos os elementos None
            if type(obj) is list:
                return [x for x in obj if x is not None]
            # Tuplo: retorna novo tuplo sem elementos None
            if type(obj) is tuple:
                return tuple(x for x in obj if x is not None)
            # Dicionário: remove apenas entradas com chave nil (ou chave e valor nil)
            # Mantém entradas onde só o valor é nil (ex: "chave": nil)
            if type(obj) is dict:
                return {k: v for k, v in obj.items() if k is not None}

        # NEW: Métodos de formatação de string
        if type(obj) is str:
            if atributo == 'capitalize': return obj.capitalize()
            if atributo == 'capitalize_phrase': return obj.title()
            if atributo == 'upper_letters': return obj.upper()
            if atributo == 'lower_letters': return obj.lower()
            if atributo == 'replace_elements': return obj.replace(" ", "")

        return getattr(obj, atributo)

    def visitar_Unaria(self, no):
        """
        Operador unário: -expr (negativo) ou !expr (not).
        Primeiro avalia a expressão filha, depois aplica o operador.
        OTIMIZAÇÃO: _avaliar_inline para expressão filha.
        """
        d = self._avaliar_inline(no.expr)
        match no.op.tipo:
            case TipoToken.MINUS:
                return -d
            case TipoToken.BANG:
                return self.KAA_TRUE if not self._verdadeiro(d) else self.KAA_FALSE

    def visitar_Binaria(self, no):
        """
        Operadores binários: + - * / > < >= <= == !=
        Avalia ambos os operandos antes de aplicar a operação.

        OTIMIZAÇÃO: Fast path para operações quentes (+, -, *, /).
        OTIMIZAÇÃO: _avaliar_inline para operandos.
        """
        e = self._avaliar_inline(no.esq)
        d = self._avaliar_inline(no.dir)
        op = no.op.tipo

        # Fast path para operações numéricas comuns
        if op == TipoToken.PLUS:
            # String concatenação ou soma numérica
            if type(e) is str or type(d) is str:
                return self._str(e) + self._str(d)
            return e + d

        if op == TipoToken.MINUS:
            return e - d

        if op == TipoToken.STAR:
            return e * d

        if op == TipoToken.SLASH:
            if d == 0:
                raise RuntimeError(f'Linha {no.op.linha}: divisão por zero')
            return e / d

        if op == TipoToken.PERCENT:
            if d == 0:
                raise RuntimeError(f'Linha {no.op.linha}: módulo por zero')
            return e % d

        # Comparações
        if op == TipoToken.GREATER:
            return self.KAA_TRUE if e > d else self.KAA_FALSE
        if op == TipoToken.GREATER_EQ:
            return self.KAA_TRUE if e >= d else self.KAA_FALSE
        if op == TipoToken.LESS:
            return self.KAA_TRUE if e < d else self.KAA_FALSE
        if op == TipoToken.LESS_EQ:
            return self.KAA_TRUE if e <= d else self.KAA_FALSE
        if op == TipoToken.EQ_EQ:
            return self.KAA_TRUE if e == d else self.KAA_FALSE
        if op == TipoToken.BANG_EQ:
            return self.KAA_TRUE if e != d else self.KAA_FALSE
        if op == TipoToken.IN:
            try:
                return self.KAA_TRUE if e in d else self.KAA_FALSE
            except TypeError:
                raise RuntimeError(f"Linha {no.op.linha}: operador 'in' requer uma coleção iterável")
        if op == TipoToken.BANG_IN:
            try:
                return self.KAA_TRUE if e not in d else self.KAA_FALSE
            except TypeError:
                raise RuntimeError(f"Linha {no.op.linha}: operador '!in' requer uma coleção iterável")

    def visitar_Logico(self, no):
        """
        Operadores lógicos: and / or
        Retorna -T ou -F sempre.
        Avaliação em curto-circuito: 'and' para se esquerda for falsa,
        'or' para se esquerda for verdadeira.
        OTIMIZAÇÃO: _avaliar_inline para operandos.
        """
        e = self._avaliar_inline(no.esq)
        if no.op.tipo == TipoToken.OR:
            if self._verdadeiro(e):
                return self.KAA_TRUE
            d = self.avaliar(no.dir)
            return self.KAA_TRUE if self._verdadeiro(d) else self.KAA_FALSE
        else:  # AND
            if not self._verdadeiro(e):
                return self.KAA_FALSE
            d = self.avaliar(no.dir)
            return self.KAA_TRUE if self._verdadeiro(d) else self.KAA_FALSE

    def visitar_Variavel(self, no):
        """
        Resolve o nome de uma variável no ambiente atual.
        OTIMIZAÇÃO: Cache L1 para variáveis locais mais acessadas.
        """
        lexema = no.nome.lexema

        # Tenta cache L1 primeiro (hit rate típico > 80% para variáveis locais)
        if lexema in self._var_cache:
            cached_env_id, valor = self._var_cache[lexema]
            # Verifica se o cache ainda é válido (mesmo ambiente)
            if cached_env_id == id(self.env):
                return valor

        # Cache miss: busca normal no ambiente
        valor = self.env.obter(no.nome)
        # Atualiza cache L1
        self._var_cache[lexema] = (id(self.env), valor)
        return valor

    def visitar_Atribuicao(self, no):
        """
        Atribuição: x = valor  ou  lista[i] = valor
        1. Avalia o valor do lado direito.
        2. Se o alvo for uma variável, faz coerce e guarda no ambiente.
        3. Se o alvo for acesso a índice, atualiza a coleção diretamente.

        OTIMIZAÇÃO: type() direto e cache de ambiente.
        OTIMIZAÇÃO: Invalida cache L1 após atribuição.
        """
        v = self._avaliar_inline(no.valor)

        # Caso 1: atribuição em índice (lista[i] = valor, dict[k] = valor)
        if type(no.nome) is AcessoIndice:
            acesso = no.nome
            obj = self._avaliar_inline(acesso.objeto)
            idx = self._avaliar_inline(acesso.indice)
            linha = acesso.indice_token.linha

            # OTIMIZAÇÃO: type() é mais rápido que isinstance()
            if type(idx) is float and idx == int(idx):
                idx = int(idx)

            # Fast path para lista
            if type(obj) is list:
                if type(idx) is not int:
                    raise RuntimeError(f'Linha {linha}: índice deve ser inteiro')
                if idx < 0:
                    raise RuntimeError(f'Linha {linha}: índice negativo não permitido')
                # Auto-grow: se índice >= tamanho, expande a lista com None
                if idx >= len(obj):
                    obj.extend([None] * (idx - len(obj) + 1))
                obj[idx] = v
            elif type(obj) is tuple:
                raise RuntimeError(f'Linha {linha}: não é possível modificar tuplo')
            elif type(obj) is dict:
                obj[idx] = v
            else:
                raise RuntimeError(f'Linha {linha}: objeto não é indexável')
            return v

        # Caso 2: atribuição em variável simples
        # OTIMIZAÇÃO: Invalida cache L1 para esta variável
        lexema = no.nome.lexema
        if lexema in self._var_cache:
            del self._var_cache[lexema]

        tipo = self.env.obter_tipo(lexema)
        if tipo:
            v = self._coerce(v, tipo, no.nome.linha)
        self.env.atribuir(no.nome, v)
        return v

    def visitar_Chamada(self, no):
        """
        Chamada de função: foo(arg1, arg2)
        OU chamada de método nativo: lista.length(), float.f_valuation(n)
        1. Avalia o callable (deve ser um PyloxFuncao ou função Python).
        2. Avalia todos os argumentos.
        3. Delega a execução para 'chamar()' da função ou chama diretamente.

        OTIMIZAÇÃO: Fast path para .length() e conversão rápida de args.
        OTIMIZAÇÃO: _avaliar_inline para callable e args.
        """
        # Fast path: métodos nativos em coleções e floats
        if type(no.chamado) is AcessoAtributo:
            obj = self._avaliar_inline(no.chamado.objeto)
            metodo = no.chamado.atributo.lexema

            # .length() em listas/tuplos/dicionários
            if metodo == 'length':
                if type(obj) is list or type(obj) is tuple or type(obj) is dict:
                    if len(no.args) > 0:
                        raise RuntimeError(f'Linha {no.paren.linha}: length() não aceita argumentos')
                    return len(obj)

            # .f_valuation() em floats
            if metodo == 'f_valuation':
                if type(obj) is float:
                    # Sem argumentos: usa 2 casas decimais
                    if len(no.args) == 0:
                        fator = 100
                        return round(obj * fator) / fator
                    # Com argumentos: usa n casas decimais
                    if len(no.args) == 1:
                        casas = self._avaliar_inline(no.args[0])
                        if type(casas) is float and casas.is_integer():
                            casas = int(casas)
                        if type(casas) is not int:
                            raise RuntimeError(f'Linha {no.paren.linha}: f_valuation() espera inteiro')
                        if casas < 0:
                            casas = 0
                        if casas > 15:
                            casas = 15
                        fator = 10 ** casas
                        return round(obj * fator) / fator
                    raise RuntimeError(f'Linha {no.paren.linha}: f_valuation() aceita no máximo 1 argumento')

            # .rm_nil() em listas, tuplos e dicionários (GC manual)
            if metodo == 'rm_nil':
                if len(no.args) > 0:
                    raise RuntimeError(f'Linha {no.paren.linha}: rm_nil() não aceita argumentos')
                # Lista: remove todos os elementos None
                if type(obj) is list:
                    return [x for x in obj if x is not None]
                # Tuplo: retorna novo tuplo sem elementos None
                if type(obj) is tuple:
                    return tuple(x for x in obj if x is not None)
                # Dicionário: remove apenas entradas com chave nil (ou chave e valor nil)
                # Mantém entradas onde só o valor é nil (ex: "chave": nil)
                if type(obj) is dict:
                    return {k: v for k, v in obj.items() if k is not None}

            # Métodos de formatação de string
            if type(obj) is str:
                if metodo in ('capitalize', 'capitalize_phrase', 'upper_letters', 'lower_letters', 'replace_elements'):
                    if metodo != 'replace_elements' and len(no.args) > 0:
                        raise RuntimeError(f'Linha {no.paren.linha}: {metodo}() não aceita argumentos')
                    if metodo == 'capitalize': return obj.capitalize()
                    if metodo == 'capitalize_phrase': return obj.title()
                    if metodo == 'upper_letters': return obj.upper()
                    if metodo == 'lower_letters': return obj.lower()
                    if metodo == 'replace_elements':
                        if len(no.args) == 2:
                            return obj.replace(self._str(self._avaliar_inline(no.args[0])), self._str(self._avaliar_inline(no.args[1])))
                        elif len(no.args) == 0:
                            return obj.replace(" ", "")
                        else:
                            raise RuntimeError(f'Linha {no.paren.linha}: replace_elements() espera 0 ou 2 argumentos')

            # Outros métodos de objetos Python
            fn = getattr(obj, metodo, None)
            if fn is not None and callable(fn):
                args = [self._avaliar_inline(a) for a in no.args]
                # OTIMIZAÇÃO: Conversão rápida de floats inteiros
                args_python = [int(a) if type(a) is float and a == int(a) else a for a in args]
                return fn(*args_python)

        fn   = self._avaliar_inline(no.chamado)
        args = [self._avaliar_inline(a) for a in no.args]

        # Se for função Python (builtin ou método de módulo)
        if callable(fn) and not hasattr(fn, 'chamar'):
            # OTIMIZAÇÃO: List comprehension é mais rápida que loop for
            args_python = [int(a) if type(a) is float and a == int(a) else a for a in args]
            return fn(*args_python)

        # Se for função Kaa (PyloxFuncao)
        if hasattr(fn, 'chamar'):
            if len(args) != fn.aridade():
                raise RuntimeError(f'Linha {no.paren.linha}: aridade incorreta')
            return fn.chamar(self, args)

        raise RuntimeError(f'Linha {no.paren.linha}: não é uma função')

    # ═══════════════════════════════════════════════════════════
    #  DECLARAÇÕES (statements)
    # ═══════════════════════════════════════════════════════════

    def visitar_StmtExpr(self, no):
        """Expressão usada como statement — avalia e descarta o resultado."""
        self.avaliar(no.expr)

    def visitar_StmtPrint(self, no):
        """
        print expr1, expr2, ...
        Avalia cada expressão e concatena como string, depois printa.
        """
        partes = [self._str(self.avaliar(e)) for e in no.exprs]
        print(''.join(partes))

    def visitar_StmtInput(self, no):
        """
        input "prompt" >> variavel;
        input "prompt" >> lista[i];
        1. Mostra o prompt via input() - pode ser múltiplas expressões concatenadas.
        2. Se alvo for variável: recupera tipo, coerce e guarda.
        3. Se alvo for acesso a índice: atualiza a coleção diretamente.

        OTIMIZAÇÃO: type() direto e auto-grow com extend.
        """
        # Avalia e concatena todas as expressões do prompt
        if hasattr(no.prompt, 'exprs'):
            msg = ''.join(self._str(self.avaliar(e)) for e in no.prompt.exprs)
        elif isinstance(no.prompt, list):
            msg = ''.join(self._str(self.avaliar(e)) for e in no.prompt)
        else:
            msg = self._str(self.avaliar(no.prompt))
        valor = input(msg)

        # Caso 1: acesso a índice (lista[i], dict[k])
        if type(no.alvo) is AcessoIndice:
            acesso = no.alvo
            obj = self.avaliar(acesso.objeto)
            idx = self.avaliar(acesso.indice)
            linha = acesso.indice_token.linha

            # OTIMIZAÇÃO: type() é mais rápido que isinstance()
            if type(idx) is float and idx == int(idx):
                idx = int(idx)

            # Fast path para lista
            if type(obj) is list:
                if type(idx) is not int:
                    raise RuntimeError(f'Linha {linha}: índice deve ser inteiro')
                if idx < 0:
                    raise RuntimeError(f'Linha {linha}: índice negativo não permitido')
                # OTIMIZAÇÃO: extend é mais rápido que append em loop
                if idx >= len(obj):
                    obj.extend([None] * (idx - len(obj) + 1))
                # Coerção para numérico
                try:
                    valor = float(valor)
                except ValueError:
                    pass
                obj[idx] = valor
            elif type(obj) is dict:
                try:
                    valor = float(valor)
                except ValueError:
                    pass
                obj[idx] = valor
            elif type(obj) is tuple:
                raise RuntimeError(f'Linha {linha}: não é possível modificar tuplo')
            else:
                raise RuntimeError(f'Linha {linha}: objeto não é indexável')

        elif type(no.alvo) is Variavel:
            # Caso 2: variável simples
            tipo = self.env.obter_tipo(no.alvo.nome.lexema)
            if tipo is None:
                raise RuntimeError(
                    f'Linha {no.alvo.nome.linha}: variável {no.alvo.nome.lexema!r} '
                    f'não declarada antes do input'
                )
            valor = self._coerce(valor, tipo, no.alvo.nome.linha)
            self.env.atribuir(no.alvo.nome, valor)
        else:
            raise RuntimeError(f'Linha {no.alvo.linha if hasattr(no.alvo, "linha") else "?"}: alvo inválido para input')

    def visitar_StmtBloco(self, no):
        """
        Bloco: { stmt1; stmt2; ... }
        OTIMIZAÇÃO: Lazy environment - só cria novo ambiente se houver DeclVar.
        """
        # Verifica se o bloco tem declarações de variáveis
        tem_variaveis = any(type(s) is DeclVar for s in no.stmts)

        if tem_variaveis:
            # Precisa de novo ambiente para scope das variáveis
            self.executar_bloco(no.stmts, Ambiente(enclosing=self.env))
        else:
            # OTIMIZAÇÃO: Reusa ambiente atual, não cria scope desnecessário
            # Mas invalida cache L1 para segurança
            self._var_cache.clear()
            for s in no.stmts:
                self.executar(s)

    def executar_bloco(self, stmts, env):
        """
        Executa uma lista de statements num ambiente específico.
        Usa try/finally para garantir que o ambiente anterior é restaurado
        mesmo que haja um return ou erro.
        """
        ant = self.env
        try:
            self.env = env
            # Invalida cache L1 ao entrar em novo ambiente
            self._var_cache.clear()
            for s in stmts:
                self.executar(s)
        finally:
            self.env = ant

    def visitar_DeclVar(self, no):
        """
        Declaração de variável: var -tipo nome [= expr];
        1. Se tem inicializador, avalia e coerce para o tipo.
        2. Se não tem e é bool/list/tuple/dict, atribui valor padrão.
        3. Guarda no ambiente com o tipo.
        """
        if no.inicializador:
            v = self._coerce(self.avaliar(no.inicializador), no.tipo, no.nome.linha)
        elif no.tipo == 'bool_t':
            v = True      # -T sem inicializador → True
        elif no.tipo == 'bool_f':
            v = False     # -F sem inicializador → False
        elif no.tipo == 'list':
            v = []        # -l sem inicializador → lista vazia
        elif no.tipo == 'tuple':
            v = ()        # -t sem inicializador → tuplo vazio
        elif no.tipo == 'dict':
            v = {}        # -d sem inicializador → dict vazio
        else:
            v = None      # outros tipos ficam com None
        self.env.definir(no.nome.lexema, v, no.tipo)

    def visitar_DeclFun(self, no):
        """
        Declaração de função: fun foo(x, y) { ... }
        Guarda a função como um objeto Chamável no ambiente.
        """
        self.env.definir(no.nome.lexema, PyloxFuncao(no, self.env))

    def visitar_DeclExpon(self, no):
        """
        expor all;  ou  expor foo, bar;
        Regista apenas funções no registry de exports.
        Variáveis fora de funções NÃO são exportadas.
        Funções Python (add -py) também são exportadas.
        """
        if no.todos:
            # Exporta apenas funções do ambiente atual (Kaa e Python)
            for nome, valor in self.env.valores.items():
                if isinstance(valor, PyloxFuncao) or (callable(valor) and not hasattr(valor, 'chamar')):
                    tipo = self.env.tipos.get(nome)
                    self.env.exportar(nome, valor, tipo)
        else:
            # Exporta apenas nomes listados que sejam funções
            for token in no.nomes:
                nome = token.lexema
                if nome not in self.env.valores:
                    raise RuntimeError(f'Linha {token.linha}: "{nome}" não foi declarado')
                valor = self.env.valores[nome]
                if not (isinstance(valor, PyloxFuncao) or (callable(valor) and not hasattr(valor, 'chamar'))):
                    raise RuntimeError(f'Linha {token.linha}: "{nome}" não é uma função')
                tipo = self.env.tipos.get(nome)
                self.env.exportar(nome, valor, tipo)

    def visitar_StmtImport(self, no):
        """
        add "./path.kaa" -> foo, bar;  ou  add "./path.kaa" all;
        add -py "import math";  ou  add -py "from random import choice";

        ARENA POR S-BOT: Cada módulo importado cria uma arena para GC de ciclo de vida.
        """
        caminho = self.avaliar(no.caminho)

        # Verifica se é import Python (caminho começa com "py:")
        if isinstance(caminho, str) and caminho.startswith("py:"):
            self._importar_python(caminho[3:], no.nomes)
            return

        # Import Kaa normal
        # Verifica se é biblioteca oficial
        if isinstance(caminho, str) and not caminho.endswith('.kaa') and '/' not in caminho and '\\' not in caminho:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            caminho = os.path.join(base_dir, 'libs', f"{caminho}.kaa")

        # Obtém caminho absoluto relativo ao working directory
        if not os.path.isabs(caminho):
            caminho = os.path.abspath(caminho)

        # 2. Detecção de ciclos
        if caminho in self.carregando:
            raise RuntimeError(f'Ciclo detectado: {caminho}')

        # 3. Carrega o arquivo
        try:
            with open(caminho, encoding='utf-8') as f:
                codigo = f.read()
        except FileNotFoundError:
            raise RuntimeError(f'Arquivo não encontrado: {caminho}')

        # 4. Parse e executa em ambiente filho do global
        from scanner import Scanner
        from parser import Parser

        tokens = Scanner(codigo).escanear()
        parser = Parser(tokens)
        stmts = parser.parse()

        # ARENA POR S-BOT: Cria arena para este módulo
        nome_modulo = os.path.basename(caminho).replace('.kaa', '')
        arena = Arena(nome=nome_modulo)

        # Cria ambiente filho do global com arena (herda closures)
        env_import = Ambiente(enclosing=self.global_env, arena=arena)
        arena.adicionar(env_import)

        # Salva ambiente atual (onde os exports serão copiados)
        env_original = self.env

        # Adiciona à pilha de carregamento
        self.carregando.add(caminho)

        # Registra arena para este módulo
        self.arenas[caminho] = arena

        # Registra funções nativas se for time.kaa
        if caminho.endswith('time.kaa'):
            env_import.definir('sleep', self._builtin_sleep, tipo='builtin')
            env_import.definir('timestamp', self._builtin_timestamp, tipo='builtin')
            env_import.definir('time_str', self._builtin_time_str, tipo='builtin')
            env_import.definir('date_str', self._builtin_date_str, tipo='builtin')
            env_import.definir('wait_until', self._builtin_wait_until, tipo='builtin')
            # Arena GC - funções para destruir arenas
            env_import.definir('destroy_arena', self._builtin_destroy_arena, tipo='builtin')
            env_import.definir('arenas_info', self._builtin_arenas_info, tipo='builtin')

        try:
            # Executa no ambiente isolado
            self.env = env_import
            for stmt in stmts:
                self.executar(stmt)

            # 5. Copia exports para o ambiente ORIGINAL (não env_import!)
            if no.nomes is None:  # importa all
                for nome, (valor, tipo) in env_import.exports.items():
                    env_original.definir(nome, valor, tipo)
            else:  # importa específicos
                for token in no.nomes:
                    nome = token.lexema
                    if nome not in env_import.exports:
                        raise RuntimeError(f'Linha {token.linha}: "{nome}" não foi exportado')
                    valor, tipo = env_import.exports[nome]
                    env_original.definir(nome, valor, tipo)
        finally:
            # Restaura ambiente e remove da pilha
            self.env = env_original
            self.carregando.discard(caminho)

    def _importar_python(self, codigo_python, nomes):
        """
        Executa import Python e disponibiliza no ambiente Kaa.
        Ex: add -py "import math as m";  →  m.sqrt(4)
        """
        # Ambiente Python isolado para o import
        py_env = {}
        exec(codigo_python, py_env)

        # Copia para o ambiente Kaa
        if nomes is None:
            # Import all - copia todos os nomes (exceto builtins)
            for nome, valor in py_env.items():
                if not nome.startswith('_'):
                    self.env.definir(nome, valor, tipo='py')
        else:
            # Import específicos
            for token in nomes:
                nome = token.lexema
                if nome in py_env:
                    valor = py_env[nome]
                    self.env.definir(nome, valor, tipo='py')
                else:
                    raise RuntimeError(f'Linha {token.linha}: "{nome}" não foi importado')

    def visitar_StmtIf(self, no):
        """
        if (cond) stmt else stmt
        Avalia a condição; se verdadeira executa o bloco 'então', senão o 'senao'.
        """
        if self._verdadeiro(self.avaliar(no.cond)):
            self.executar(no.entao)
        elif no.senao:
            self.executar(no.senao)

    def visitar_StmtWhile(self, no):
        """
        while (cond) stmt
        Avalia a condição antes de cada iteração (loop tradicional).
        """
        while self._verdadeiro(self.avaliar(no.cond)):
            self.executar(no.corpo)

    def visitar_StmtReturn(self, no):
        """
        return [expr];
        Levanta RetornoException com o valor (ou None).
        O bloco que executar 'chamar()' apanha esta exceção e devolve o valor.
        """
        raise RetornoException(
            self.avaliar(no.valor) if no.valor else None
        )

    # ═══════════════════════════════════════════════════════════
    #  HELPERS
    # ═══════════════════════════════════════════════════════════

    def _coerce(self, valor, tipo, linha):
        """
        Converte (coerção) um valor Python para o tipo declarado em Kaa.
        Cada tipo tem regras específicas de conversão.

        OTIMIZAÇÃO: type() direto e early returns para casos comuns.
        GC MANUAL: nil é permitido em qualquer tipo para permitir "x = nil" como GC.
        """
        # GC MANUAL: nil é permitido em qualquer tipo
        if valor is None:
            return None

        # Booleano não pode ser atribuído a tipo não-bool (proteção de tipo)
        if type(valor) is bool and tipo not in ('bool_t', 'bool_f'):
            raise RuntimeError(
                f'Linha {linha}: booleano não pode ser atribuído '
                f'a variável do tipo {tipo}. Use -T ou -F.'
            )

        # Fast path para tipos primitivos
        if tipo == 'int':
            f = float(valor)
            if f.is_integer():
                return float(int(f))
            raise RuntimeError(
                f'Linha {linha}: valor {valor!r} é incompatível com o '
                f'tipo declarado ({tipo}).'
            )

        if tipo == 'float':
            return float(valor)

        if tipo == 'str':
            return self._str(valor)

        if tipo in ('bool_t', 'bool_f'):
            # Aceita APENAS: bool nativo ou string "-T"/"-F"
            if type(valor) is bool:
                return valor
            if type(valor) is str:
                v = valor.upper()
                if v == '-T':
                    return True
                if v == '-F':
                    return False
            raise RuntimeError(
                f'Linha {linha}: valor {valor!r} é incompatível com o '
                f'tipo declarado ({tipo}).'
            )

        # Tipos de coleção com type() direto
        if tipo == 'list':
            if type(valor) is list:
                return valor
            raise RuntimeError(
                f'Linha {linha}: valor {valor!r} não é uma lista'
            )

        if tipo == 'tuple':
            if type(valor) is tuple:
                return valor
            raise RuntimeError(
                f'Linha {linha}: valor {valor!r} não é um tuplo'
            )

        if tipo == 'dict':
            if type(valor) is dict:
                return valor
            raise RuntimeError(
                f'Linha {linha}: valor {valor!r} não é um dicionário'
            )

        raise RuntimeError(
            f'Linha {linha}: valor {valor!r} é incompatível com o '
            f'tipo declarado ({tipo}).'
        )

    def _verdadeiro(self, v):
        """
        Converte valor Kaa para booleano (truthy/falsy).
        Em Kaa, só None e False são falsos — todo o resto é verdadeiro.
        Nota: 0 (zero numérico) é TRUE em Kaa, apenas None e False são falsos.

        OTIMIZAÇÃO: Comparação direta é mais rápida que 'not in'.
        """
        # Em Kaa: apenas None e False são falsos
        # 0, 0.0, "", [] são todos TRUE (design da linguagem)
        return v is not None and v is not False

    def _str(self, v):
        """
        Converte valor Python para string Kaa.
        Regras Kaa:
          None → "nil"
          True → "true"
          False → "false"
          float 10.0 → "10" (sem .0)

        OTIMIZAÇÃO: Cache separado para int e float (casos mais comuns).
        """
        # Casos diretos (sem cache necessário)
        if v is None:
            return 'nil'
        if v is True:
            return '-T'
        if v is False:
            return '-F'

        # Cache especializado para int (mais rápido que dict genérico)
        if type(v) is int:
            if v not in self._int_str_cache:
                self._int_str_cache[v] = str(v)
            return self._int_str_cache[v]

        # Cache especializado para float
        if type(v) is float:
            if v not in self._float_str_cache:
                s = str(v)
                self._float_str_cache[v] = s[:-2] if s.endswith('.0') else s
            return self._float_str_cache[v]

        # Fallback para outros tipos
        return str(v)
