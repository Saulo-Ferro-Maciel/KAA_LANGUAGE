import sys
from tok import Token
from tipos_token import TipoToken

class Scanner:
    PALAVRAS_CHAVE = {
        'and':    TipoToken.AND,
        'class':  TipoToken.CLASS,
        'else':   TipoToken.ELSE,
        'false':  TipoToken.FALSE,
        'fun':    TipoToken.FUN,
        'for':    TipoToken.FOR,
        'if':     TipoToken.IF,
        'elif':   TipoToken.ELIF,
        'nil':    TipoToken.NIL,
        'or':     TipoToken.OR,
        'print':  TipoToken.PRINT,
        'return': TipoToken.RETURN,
        'true':   TipoToken.TRUE,
        'var':    TipoToken.VAR,
        'while':  TipoToken.WHILE,
        'input':  TipoToken.INPUT,
        'in':     TipoToken.IN,
        'expor':  TipoToken.EXPOR,
        'add':    TipoToken.ADD,
        'all':    TipoToken.ALL,
    }

    def __init__(self, fonte):
        self.fonte   = fonte
        self.tokens  = []
        self.inicio  = 0
        self.atual   = 0
        self.linha   = 1

    def fim(self):
        return self.atual >= len(self.fonte)

    def avanca(self):
        c = self.fonte[self.atual]
        self.atual += 1
        return c

    def espiar(self):
        return '\0' if self.fim() else self.fonte[self.atual]

    def espiar_prox(self):
        if self.atual + 1 >= len(self.fonte):
            return '\0'
        return self.fonte[self.atual + 1]

    def combina(self, esperado):
        if self.fim() or self.fonte[self.atual] != esperado:
            return False
        self.atual += 1
        return True

    def adiciona(self, tipo, valor=None):
        texto = self.fonte[self.inicio:self.atual]
        self.tokens.append(Token(tipo, texto, valor, self.linha))

    def escanear(self):
        while not self.fim():
            self.inicio = self.atual
            self._proximo_token()
        self.tokens.append(Token(TipoToken.EOF, '', None, self.linha))
        return self.tokens

    def _proximo_token(self):
        c = self.avanca()
        match c:
            case '(':
                self.adiciona(TipoToken.LPAREN)
            case ')':
                self.adiciona(TipoToken.RPAREN)
            case '{':
                self.adiciona(TipoToken.LBRACE)
            case '}':
                self.adiciona(TipoToken.RBRACE)
            case ',':
                self.adiciona(TipoToken.COMMA)
            case ';':
                self.adiciona(TipoToken.SEMICOLON)
            case '+':
                self.adiciona(TipoToken.PLUS)
            case '-':
                # Verifica se é seta: ->
                if self.espiar() == '>':
                    self.avanca()
                    self.adiciona(TipoToken.ARROW)
                # -T e -F são SEMPRE valores booleanos (não são menos + variável)
                elif self.espiar() == 'T':
                    self.avanca()
                    self.adiciona(TipoToken.TIPO_BOOL_T)
                elif self.espiar() == 'F':
                    self.avanca()
                    self.adiciona(TipoToken.TIPO_BOOL_F)
                # Verifica se é modificador de tipo: -i, -f, -s, -l, -t, -d
                elif self.espiar() in ('i', 'f', 's', 'l', 't', 'd'):
                    letra = self.espiar()
                    prox = self.fonte[self.atual + 1] if self.atual + 1 < len(self.fonte) else ''
                    # É modificador se seguido de espaço + identificador ou direto identificador
                    if prox in (' ', '\t', '\r'):
                        j = self.atual + 2
                        while j < len(self.fonte) and self.fonte[j] in (' ', '\t', '\r'):
                            j += 1
                        if j < len(self.fonte) and (self.fonte[j].isalpha() or self.fonte[j] == '_'):
                            self.avanca()
                            if letra == 'i': self.adiciona(TipoToken.TIPO_INT)
                            elif letra == 'f': self.adiciona(TipoToken.TIPO_FLOAT)
                            elif letra == 's': self.adiciona(TipoToken.TIPO_STR)
                            elif letra == 'l': self.adiciona(TipoToken.TIPO_LIST)
                            elif letra == 't': self.adiciona(TipoToken.TIPO_TUPLE)
                            elif letra == 'd': self.adiciona(TipoToken.TIPO_DICT)
                        else:
                            self.adiciona(TipoToken.MINUS)
                    elif prox.isalpha() or prox == '_':
                        self.avanca()
                        if letra == 'i': self.adiciona(TipoToken.TIPO_INT)
                        elif letra == 'f': self.adiciona(TipoToken.TIPO_FLOAT)
                        elif letra == 's': self.adiciona(TipoToken.TIPO_STR)
                        elif letra == 'l': self.adiciona(TipoToken.TIPO_LIST)
                        elif letra == 't': self.adiciona(TipoToken.TIPO_TUPLE)
                        elif letra == 'd': self.adiciona(TipoToken.TIPO_DICT)
                    else:
                        self.adiciona(TipoToken.MINUS)
                elif self.espiar() == 'p':
                    # Verifica se é -py (seguido exatamente de 'y' e não-alfanum)
                    if self.atual + 1 < len(self.fonte) and self.fonte[self.atual + 1] == 'y':
                        if self.atual + 2 >= len(self.fonte) or not (self.fonte[self.atual + 2].isalnum() or self.fonte[self.atual + 2] == '_'):
                            self.avanca()
                            self.avanca()
                            self.adiciona(TipoToken.TIPO_PY)
                        else:
                            self.adiciona(TipoToken.MINUS)
                    else:
                        self.adiciona(TipoToken.MINUS)
                elif self.espiar() == 'o':
                    # Verifica se é -obj
                    if self.atual + 2 < len(self.fonte) and self.fonte[self.atual + 1:self.atual + 3] == 'bj':
                        if self.atual + 3 >= len(self.fonte) or not (self.fonte[self.atual + 3].isalnum() or self.fonte[self.atual + 3] == '_'):
                            self.avanca()
                            self.avanca()
                            self.avanca()
                            self.adiciona(TipoToken.TIPO_OBJ)
                        else:
                            self.adiciona(TipoToken.MINUS)
                    else:
                        self.adiciona(TipoToken.MINUS)
                else:
                    self.adiciona(TipoToken.MINUS)
            case '*':
                self.adiciona(TipoToken.STAR)
            case '&':
                if self.combina('&'):
                    raise SyntaxError(f"Linha {self.linha}: uso de '&&' não é permitido no Kaa. Use 'and'.")
                else:
                    raise SyntaxError(f"Linha {self.linha}: caractere inesperado '&'")
            case '%':
                self.adiciona(TipoToken.PERCENT)
            case '!':
                t = TipoToken.BANG_EQ if self.combina('=') else TipoToken.BANG
                self.adiciona(t)
            case '=':
                t = TipoToken.EQ_EQ if self.combina('=') else TipoToken.EQ
                self.adiciona(t)
            case '<':
                t = TipoToken.LESS_EQ if self.combina('=') else TipoToken.LESS
                self.adiciona(t)
            case '>':
                if self.combina('>'):
                    self.adiciona(TipoToken.GREATER_GREATER)
                elif self.combina('='):
                    self.adiciona(TipoToken.GREATER_EQ)
                else:
                    self.adiciona(TipoToken.GREATER)
            case '/':
                if self.combina('/'):
                    while self.espiar() != '\n' and not self.fim():
                        self.avanca()
                else:
                    self.adiciona(TipoToken.SLASH)
            case '[':
                self.adiciona(TipoToken.LBRACKET)
            case ']':
                self.adiciona(TipoToken.RBRACKET)
            case '?':
                self.adiciona(TipoToken.QUESTION)
            case ':':
                self.adiciona(TipoToken.COLON)
            case '.':
                self.adiciona(TipoToken.DOT)
            case '|':
                if self.combina('|'):
                    self.adiciona(TipoToken.OR)
                else:
                    self.adiciona(TipoToken.PIPE)
            case ' ' | '\r' | '\t':
                pass
            case '\n':
                self.linha += 1
            case '"':
                self._string()
            case _:
                if c.isdigit():
                    self._numero()
                elif c.isalpha() or c == '_':
                    self._identificador()
                else:
                    raise SyntaxError(f'Linha {self.linha}: caractere inesperado {c!r}')

    def _proximo_alfanum(self, offset):
        """Verifica se o caractere após o offset atual é alfanumérico (evita -i em nomes como -if)."""
        pos = self.atual + offset
        if pos >= len(self.fonte):
            return False
        return self.fonte[pos].isalnum() or self.fonte[pos] == '_'

    def _string(self):
        """Lê string entre aspas duplas, permitindo aspas simples e caracteres especiais dentro.

        OTIMIZAÇÃO: String interning para reduzir alocações repetidas.
        """
        while self.espiar() != '"' and not self.fim():
            if self.espiar() == '\n':
                self.linha += 1
            self.avanca()
        if self.fim():
            raise SyntaxError(f'Linha {self.linha}: string não fechada')
        self.avanca()
        texto = self.fonte[self.inicio + 1:self.atual - 1]
        # OTIMIZAÇÃO: sys.intern() compartilha strings idênticas na memória
        self.adiciona(TipoToken.STRING, sys.intern(texto))

    def _numero(self):
        eh_float = False
        while self.espiar().isdigit():
            self.avanca()
        if self.espiar() == '.' and self.espiar_prox().isdigit():
            eh_float = True
            self.avanca()
            while self.espiar().isdigit():
                self.avanca()
        texto = self.fonte[self.inicio:self.atual]
        if eh_float:
            self.adiciona(TipoToken.NUMBER, float(texto))
        else:
            self.adiciona(TipoToken.NUMBER, int(texto))

    def _identificador(self):
        while self.espiar().isalnum() or self.espiar() == '_':
            self.avanca()
        texto = self.fonte[self.inicio:self.atual]

        # Verifica se há ':' seguido de tipo após o identificador (type hint do Python)
        # Isso é tratado no parser, mas guardamos o identificador corretamente aqui
        self.adiciona(self.PALAVRAS_CHAVE.get(texto, TipoToken.IDENT))