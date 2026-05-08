from tok import Token
from tipos_token import TipoToken
from ast_nos import (
    Binaria, Unaria, Literal, Agrupamento, Variavel, Atribuicao, Chamada, Logico,
    DeclVar, DeclFun, StmtExpr, StmtPrint, StmtBloco, StmtIf, StmtWhile, StmtReturn,
    StmtInput, Lista, Tuplo, Dicionario, AcessoIndice, DeclExpon, StmtImport,
    AcessoAtributo
)

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.atual  = 0

    def peek(self):
        return self.tokens[self.atual]

    def anterior(self):
        return self.tokens[self.atual - 1]

    def fim(self):
        return self.peek().tipo == TipoToken.EOF

    def avanca(self):
        if not self.fim():
            self.atual += 1
        return self.anterior()

    def verifica(self, tipo):
        return not self.fim() and self.peek().tipo == tipo

    def combina(self, *tipos):
        for t in tipos:
            if self.verifica(t):
                self.avanca()
                return True
        return False

    def consome(self, tipo, msg):
        if self.verifica(tipo):
            return self.avanca()
        raise SyntaxError(f'Linha {self.peek().linha}: {msg}')

    # ── Expressões ──────────────────────────────────────────

    def expressao(self):
        return self.atribuicao()
    
    def atribuicao(self):
        expr = self.ou()
        if self.combina(TipoToken.EQ):
            igual = self.anterior()
            valor = self.atribuicao()
            if isinstance(expr, Variavel):
                return Atribuicao(expr.nome, valor)
            if isinstance(expr, AcessoIndice):
                return Atribuicao(expr, valor)
            if isinstance(expr, AcessoAtributo):
                return Atribuicao(expr, valor)
            raise SyntaxError(f'Linha {igual.linha}: alvo inválido')
        return expr

    def expr_stmt(self):
        """
        Statement de expressão: expr;
        Detecta uso incorreto de == quando provavelmente era para ser =
        """
        # Guarda posição atual para verificar se é comparação
        pos = self.atual
        expr = self.expressao()
        self.consome(TipoToken.SEMICOLON, "Esperado ';'")

        # Verifica se a expressão é uma comparação == usada como statement
        # Isso é quase sempre erro (ex: x == 5; em vez de x = 5;)
        if isinstance(expr, Binaria) and expr.op.tipo == TipoToken.EQ_EQ:
            raise SyntaxError(
                f'Linha {expr.op.linha}: uso incorreto de "==" (comparação) como statement. '
                f'Para atribuição, use "=".'
            )
        return StmtExpr(expr)

    def ou(self):
        expr = self.e()
        while self.combina(TipoToken.OR):
            expr = Logico(expr, self.anterior(), self.e())
        return expr

    def e(self):
        expr = self.igualdade()
        while self.combina(TipoToken.AND):
            expr = Logico(expr, self.anterior(), self.igualdade())
        return expr

    def igualdade(self):
        expr = self.comparacao()
        while self.combina(TipoToken.BANG_EQ, TipoToken.EQ_EQ):
            expr = Binaria(expr, self.anterior(), self.comparacao())
        return expr

    def comparacao(self):
        expr = self.termo()
        while True:
            if self.combina(TipoToken.GREATER, TipoToken.GREATER_EQ,
                            TipoToken.LESS, TipoToken.LESS_EQ, TipoToken.IN):
                expr = Binaria(expr, self.anterior(), self.termo())
            elif self.verifica(TipoToken.BANG) and self.atual + 1 < len(self.tokens) and self.tokens[self.atual + 1].tipo == TipoToken.IN:
                op_bang = self.avanca() # consome !
                self.avanca()           # consome IN
                op = Token(TipoToken.BANG_IN, "!in", None, op_bang.linha)
                expr = Binaria(expr, op, self.termo())
            else:
                break
        return expr

    def termo(self):
        expr = self.fator()
        while self.combina(TipoToken.PLUS, TipoToken.MINUS):
            expr = Binaria(expr, self.anterior(), self.fator())
        return expr

    def fator(self):
        expr = self.unario()
        while self.combina(TipoToken.STAR, TipoToken.SLASH, TipoToken.PERCENT):
            expr = Binaria(expr, self.anterior(), self.unario())
        return expr

    def unario(self):
        if self.combina(TipoToken.BANG, TipoToken.MINUS):
            return Unaria(self.anterior(), self.unario())
        return self.chamada()

    def chamada(self):
        expr = self.primaria()
        while True:
            if self.combina(TipoToken.LPAREN):
                args = []
                if not self.verifica(TipoToken.RPAREN):
                    while True:
                        args.append(self.expressao())
                        if not self.combina(TipoToken.COMMA):
                            break
                paren = self.consome(TipoToken.RPAREN, "Esperado ')'")
                expr = Chamada(expr, paren, args)
            elif self.combina(TipoToken.LBRACKET):
                # Acesso a índice: expr[indice]
                idx_expr = self.expressao()
                idx_token = self.anterior()  # token para obter linha
                self.consome(TipoToken.RBRACKET, "Esperado ']'")
                expr = AcessoIndice(expr, idx_expr, idx_token)
            elif self.combina(TipoToken.DOT):
                # Acesso a atributo: expr.atributo
                atributo = self.consome(TipoToken.IDENT, "Esperado nome do atributo")
                expr = AcessoAtributo(expr, atributo)
            else:
                break
        return expr

    def primaria(self):
        if self.combina(TipoToken.FALSE):   return Literal(False)
        if self.combina(TipoToken.TRUE):    return Literal(True)

        if self.combina(TipoToken.NIL):     return Literal(None)
        if self.combina(TipoToken.TIPO_BOOL_T): return Literal(True)
        if self.combina(TipoToken.TIPO_BOOL_F): return Literal(False)
        if self.combina(TipoToken.NUMBER, TipoToken.STRING):
            return Literal(self.anterior().valor)
        if self.combina(TipoToken.IDENT):
            return Variavel(self.anterior())
        if self.combina(TipoToken.LPAREN):
            # Pode ser agrupamento OU tuplo
            if self.verifica(TipoToken.RPAREN):
                # Tuplo vazio ()
                self.avanca()
                return Tuplo([])
            # Verifica se é tuplo (tem vírgula) ou agrupamento
            expr = self.expressao()
            if self.combina(TipoToken.COMMA):
                # É um tuplo
                elementos = [expr]
                while True:
                    elementos.append(self.expressao())
                    if not self.combina(TipoToken.COMMA):
                        break
                self.consome(TipoToken.RPAREN, "Esperado ')'")
                return Tuplo(elementos)
            else:
                # É agrupamento
                self.consome(TipoToken.RPAREN, "Esperado ')'")
                return Agrupamento(expr)
        # Lista [ ... ]
        if self.combina(TipoToken.LBRACKET):
            elementos = []
            if not self.verifica(TipoToken.RBRACKET):
                while True:
                    elementos.append(self.expressao())
                    if not self.combina(TipoToken.COMMA):
                        break
            self.consome(TipoToken.RBRACKET, "Esperado ']'")
            return Lista(elementos)
        # Dicionário { chave: valor }
        # Aceita valores vazios (nil implícito): {"nome":, "vida": , "dano": 30}
        if self.combina(TipoToken.LBRACE):
            chaves = []
            valores = []
            if not self.verifica(TipoToken.RBRACE):
                while True:
                    chaves.append(self.expressao())
                    self.consome(TipoToken.COLON, "Esperado ':'")
                    # Valor vazio (nil implicito) se vier ',' ou '}' diretamente
                    if self.verifica(TipoToken.COMMA) or self.verifica(TipoToken.RBRACE):
                        valores.append(Literal(None))
                    else:
                        valores.append(self.expressao())
                    if not self.combina(TipoToken.COMMA):
                        break
                    # Trailing comma antes de '}'
                    if self.verifica(TipoToken.RBRACE):
                        break
            self.consome(TipoToken.RBRACE, "Esperado '}'")
            return Dicionario(chaves, valores)
        raise SyntaxError(f'Linha {self.peek().linha}: expressão esperada')

    # ── Declarações ─────────────────────────────────────────

    def parse(self) -> list:
        stmts = []
        while not self.fim():
            stmts.append(self.declaracao())
        return stmts

    def declaracao(self):
        if self.combina(TipoToken.VAR):
            return self.var_decl()
        if self.combina(TipoToken.FUN):
            return self.fun_decl()
        if self.combina(TipoToken.EXPOR):
            return self.expon_decl()
        return self.stmt_simples()

    def stmt_simples(self):
        if self.combina(TipoToken.IF):     return self.if_stmt()
        if self.combina(TipoToken.ELIF):
            raise SyntaxError(f"Linha {self.anterior().linha}: 'elif' não é permitido na linguagem Kaa. Use blocos 'if' e 'else' aninhados verticalmente.")
        if self.combina(TipoToken.WHILE):  return self.while_stmt()
        if self.combina(TipoToken.FOR):    return self.for_stmt()
        if self.combina(TipoToken.PRINT):  return self.print_stmt()
        if self.combina(TipoToken.INPUT):  return self.input_stmt()
        if self.combina(TipoToken.RETURN): return self.return_stmt()
        if self.combina(TipoToken.LBRACE): return StmtBloco(self.bloco())
        if self.combina(TipoToken.ADD):    return self.import_stmt()
        return self.expr_stmt()

    def bloco(self) -> list:
        stmts = []
        while not self.verifica(TipoToken.RBRACE) and not self.fim():
            stmts.append(self.declaracao())
        self.consome(TipoToken.RBRACE, "Esperado '}'")
        return stmts

    def if_stmt(self):
        self.consome(TipoToken.LPAREN, "Esperado '('")
        cond = self.expressao()
        self.consome(TipoToken.RPAREN, "Esperado ')'")
        entao = self.stmt_simples()
        
        senao = None
        if self.combina(TipoToken.ELSE):
            if self.verifica(TipoToken.IF):
                raise SyntaxError(f"Linha {self.peek().linha}: 'else if' não é permitido na linguagem Kaa. Use 'if' e 'else' aninhados verticalmente.")
            senao = self.stmt_simples()
            
        return StmtIf(cond, entao, senao)

    def while_stmt(self):
        self.consome(TipoToken.LPAREN, "Esperado '('")
        cond = self.expressao()
        self.consome(TipoToken.RPAREN, "Esperado ')'")
        return StmtWhile(cond, self.stmt_simples())

    def for_stmt(self):
        self.consome(TipoToken.LPAREN, "Esperado '('")

        # === INICIALIZADOR ===
        if self.combina(TipoToken.VAR):
            init = self._var_decl(consome_semicolon=False)
        elif self.verifica(TipoToken.SEMICOLON):
            init = None
        else:
            init_expr = self.expressao()
            init = StmtExpr(init_expr)

        self.consome(TipoToken.SEMICOLON, "Esperado ';' após inicializador")

        # === CONDIÇÃO ===
        cond = None if self.verifica(TipoToken.SEMICOLON) else self.expressao()
        self.consome(TipoToken.SEMICOLON, "Esperado ';' após condição")

        # === INCREMENTO ===
        # Permite ';' opcional antes de ')' para sintaxe mais flexível
        inc = None
        if not self.verifica(TipoToken.RPAREN):
            inc = self.expressao()
            # Consome ';' opcional antes de ')'
            self.combina(TipoToken.SEMICOLON)
        self.consome(TipoToken.RPAREN, "Esperado ')'")

        corpo = self.stmt_simples()

        if inc:
            corpo = StmtBloco([corpo, StmtExpr(inc)])
        if cond is None:
            cond = Literal(True)
        corpo = StmtWhile(cond, corpo)
        if init:
            corpo = StmtBloco([init, corpo])

        return corpo

    def var_decl(self, consome_semicolon=True):
        return self._var_decl(consome_semicolon)

    def _var_decl(self, consome_semicolon=True):
        if self.combina(TipoToken.TIPO_INT):
            tipo = 'int'
        elif self.combina(TipoToken.TIPO_FLOAT):
            tipo = 'float'
        elif self.combina(TipoToken.TIPO_STR):
            tipo = 'str'
        elif self.combina(TipoToken.TIPO_BOOL_T):
            tipo = 'bool_t'
        elif self.combina(TipoToken.TIPO_BOOL_F):
            tipo = 'bool_f'
        elif self.combina(TipoToken.TIPO_LIST):
            tipo = 'list'
        elif self.combina(TipoToken.TIPO_TUPLE):
            tipo = 'tuple'
        elif self.combina(TipoToken.TIPO_DICT):
            tipo = 'dict'
        elif self.combina(TipoToken.TIPO_OBJ):
            tipo = 'obj'
        else:
            raise SyntaxError(
                f'Linha {self.peek().linha}: tipo obrigatório após "var". '
                f'Use -i (inteiro), -f (float) ou -s (string).'
            )
        nome = self.consome(TipoToken.IDENT, 'Esperado nome da variável')
        init = self.expressao() if self.combina(TipoToken.EQ) else None

        if consome_semicolon:
            self.consome(TipoToken.SEMICOLON, "Esperado ';'")

        return DeclVar(nome, tipo, init)

    def fun_decl(self):
        """
        Declaração de função: fun foo(x, y) { ... }
        Kaa NÃO usa type hints do Python (: tipo, -> retorno).
        A tipagem em Kaa é explícita apenas em variáveis (-i, -f, -s).
        """
        nome = self.consome(TipoToken.IDENT, 'Esperado nome da função')
        self.consome(TipoToken.LPAREN, "Esperado '('")
        params = []
        if not self.verifica(TipoToken.RPAREN):
            while True:
                params.append(self.consome(TipoToken.IDENT, 'Esperado parâmetro'))
                # BLOQUEIA type hint de parâmetro: fun foo(x: int)
                if self.verifica(TipoToken.COLON):
                    raise SyntaxError(
                        f'Linha {self.peek().linha}: Kaa não usa type hints do Python. '
                        f'Remova ": tipo" dos parâmetros. Em Kaa, a tipagem é apenas em variáveis (var -i x).'
                    )
                if not self.combina(TipoToken.COMMA):
                    break
        self.consome(TipoToken.RPAREN, "Esperado ')'")

        # BLOQUEIA type hint de retorno: fun foo() -> int
        if self.verifica(TipoToken.ARROW):
            raise SyntaxError(
                f'Linha {self.peek().linha}: Kaa não usa type hints do Python. '
                f'Remova "-> tipo" da função. Em Kaa, funções não declaram tipo de retorno.'
            )

        self.consome(TipoToken.LBRACE, "Esperado '{'")
        return DeclFun(nome, params, self.bloco())

    def expon_decl(self):
        """expor all;  ou  expor foo, bar;"""
        if self.combina(TipoToken.ALL):
            self.consome(TipoToken.SEMICOLON, "Esperado ';'")
            return DeclExpon(nomes=[], todos=True)

        nomes = [self.consome(TipoToken.IDENT, "Esperado nome da função")]
        while self.combina(TipoToken.COMMA):
            nomes.append(self.consome(TipoToken.IDENT, "Esperado nome da função"))
        self.consome(TipoToken.SEMICOLON, "Esperado ';'")
        return DeclExpon(nomes=nomes, todos=False)

    def import_stmt(self):
        """
        add "./path.kaa" -> foo, bar;
        add "./path.kaa" all;
        add -py "import math";
        """
        # Verifica se é import Python: add -py "..."
        python_import = False
        if self.combina(TipoToken.TIPO_PY):
            python_import = True

        caminho = self.consome(TipoToken.STRING, "Esperado caminho ou módulo Python")

        nomes = None  # None = importa all
        if self.combina(TipoToken.ARROW):
            nomes = [self.consome(TipoToken.IDENT, "Esperado nome")]
            while self.combina(TipoToken.COMMA):
                nomes.append(self.consome(TipoToken.IDENT, "Esperado nome"))
        elif self.combina(TipoToken.ALL):
            pass  # já está definido como all pelo combinas acima

        self.consome(TipoToken.SEMICOLON, "Esperado ';'")

        if python_import:
            # Para import Python, guarda o código Python
            return StmtImport(caminho=Literal(f"py:{caminho.valor}"), nomes=nomes)
        else:
            # Verifica se tem '.kaa' para imports normais ou é biblioteca oficial (ex: "math")
            is_lib = '/' not in caminho.valor and '\\' not in caminho.valor and not caminho.valor.endswith('.kaa')
            if not is_lib and not caminho.valor.endswith('.kaa'):
                raise SyntaxError(f'Linha {caminho.linha}: caminho deve terminar com .kaa ou ser o nome de uma biblioteca oficial')
            return StmtImport(caminho=Literal(caminho.valor), nomes=nomes)

    def print_stmt(self):
        # Enforce procedural print without parenthesis
        if self.verifica(TipoToken.LPAREN):
            raise SyntaxError(
                f'Linha {self.peek().linha}: O comando "print" no Kaa não deve usar parênteses como uma função. '
                f'Use a sintaxe procedural: print expr1, expr2;'
            )
            
        exprs = [self.expressao()]
        while self.combina(TipoToken.COMMA):
            exprs.append(self.expressao())
        self.consome(TipoToken.SEMICOLON, "Esperado ';'")
        return StmtPrint(exprs)

    def input_stmt(self):
        # Enforce procedural input without parenthesis
        if self.verifica(TipoToken.LPAREN):
            raise SyntaxError(
                f'Linha {self.peek().linha}: O comando "input" no Kaa não usa parênteses como uma função. '
                f'Use a sintaxe procedural: input "mensagem" >> variavel;'
            )
            
        # Aceita múltiplas expressões concatenadas como prompt (igual print)
        exprs = [self.expressao()]
        while self.combina(TipoToken.COMMA):
            exprs.append(self.expressao())
        prompt = StmtPrint(exprs)  # Reusa StmtPrint para representar concatenação
        self.consome(TipoToken.GREATER_GREATER, "Esperado '>>' após a mensagem")
        # Aceita expressão: variável simples ou acesso a índice (lista[i], dict[k])
        alvo = self.chamada()  # Permite lista[i], dict[k], obj.attr, etc.
        self.consome(TipoToken.SEMICOLON, "Esperado ';'")
        return StmtInput(prompt, alvo)

    def return_stmt(self):
        kw = self.anterior()
        valor = None if self.verifica(TipoToken.SEMICOLON) else self.expressao()
        self.consome(TipoToken.SEMICOLON, "Esperado ';'")
        return StmtReturn(kw, valor)

    def expr_stmt(self):
        """
        Statement de expressão: expr;
        Detecta uso incorreto de == quando provavelmente era para ser =
        """
        expr = self.expressao()
        self.consome(TipoToken.SEMICOLON, "Esperado ';'")

        # Verifica se a expressão é uma comparação == usada como statement
        # Isso é quase sempre erro (ex: x == 5; em vez de x = 5;)
        if isinstance(expr, Binaria) and expr.op.tipo == TipoToken.EQ_EQ:
            raise SyntaxError(
                f'Linha {expr.op.linha}: uso incorreto de "==" (comparação) como statement. '
                f'Para atribuição, use "=".'
            )
        return StmtExpr(expr)