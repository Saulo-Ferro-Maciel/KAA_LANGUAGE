"""
Ambiente (Scope / Symbol Table).

Gerencia os namespaces da linguagem. Cada Ambiente representa um scope
(léxico) e aponta para o seu enclosing (scope pai).

Busca de variável: começa no scope atual e sobe pela cadeia de enclosing
até encontrar (ou lançar erro se não existir).

Este é o mecanismo que permite closures: quando uma função é definida,
ela captura o Ambiente no momento da definição como seu 'closure'.

OTIMIZAÇÃO: Inline Cache para resolução rápida de variáveis.
ARENA POR S-BOT: Cada ambiente pode pertencer a uma arena, que agrupa
memória de um módulo/s-bot para liberação em massa.
"""


class Arena:
    """
    Arena de memória para GC por s-bot.
    Agrupa ambientes de um módulo para liberação em massa.
    """

    def __init__(self, nome=None):
        self.nome = nome
        self.ambientes = []  # Lista de ambientes nesta arena

    def adicionar(self, ambiente):
        """Adiciona um ambiente à arena."""
        self.ambientes.append(ambiente)
        ambiente.arena = self

    def liberar(self):
        """Libera todos os ambientes da arena (GC em massa)."""
        for amb in self.ambientes:
            amb.valores.clear()
            amb.tipos.clear()
            amb.exports.clear()
            amb._cache_var.clear()
        self.ambientes.clear()

    def __len__(self):
        """Retorna número de ambientes na arena."""
        return len(self.ambientes)


class Ambiente:
    """
    Tabela de símbolos por scope.
    'valores'   → dicionário {nome: valor_Python}
    'tipos'     → dicionário {nome: tipo_Kaa_string}
    'enclosing' → referência ao Ambiente pai (None no global)
    'exports'   → dicionário {nome: (valor, tipo)} para export/import
    'arena'     → referência à Arena do s-bot (GC de ciclo de vida)

    OTIMIZAÇÃO: _cache_var guarda (ambiente_onde_encontrou, valor) para
    acesso rápido em leituras subsequentes da mesma variável.
    """

    def __init__(self, enclosing=None, arena=None):
        self.valores   = {}   # nome → valor Python atual
        self.tipos     = {}   # nome → tipo Kaa ('int', 'float', etc.)
        self.enclosing = enclosing   # scope pai (para closures)
        self.exports   = {}   # nome → (valor, tipo) para export
        self.arena     = arena       # arena do s-bot (GC)
        self._cache_var = {}  # Inline cache: {lexema: (ambiente, valor)}

    def definir(self, nome, valor, tipo=None):
        """
        Regista uma nova variável neste scope.
        Usado por: declaração de variável, parâmetros de função.
        """
        self.valores[nome] = valor
        self.tipos[nome]   = tipo

    def obter(self, token):
        """
        Resolve o valor de uma variável pela cadeia de enclosing.
        Primeiro verifica o scope atual; se não encontrar, sobe.
        Lança erro se nenhum scope tiver a variável.

        OTIMIZAÇÃO: Inline cache para evitar busca repetida na cadeia.
        """
        lexema = token.lexema

        # Tenta cache primeiro (hit rate típico > 80%)
        if lexema in self._cache_var:
            cached_env, valor = self._cache_var[lexema]
            # Verifica se o cache ainda é válido
            if cached_env is self:
                return valor

        # Cache miss: faz busca normal
        if lexema in self.valores:
            valor = self.valores[lexema]
            # Atualiza cache
            self._cache_var[lexema] = (self, valor)
            return valor

        if self.enclosing:
            valor = self.enclosing.obter(token)
            # Atualiza cache com o ambiente onde foi encontrado
            self._cache_var[lexema] = (self.enclosing, valor)
            return valor

        # Verifica se está em exports de alguma biblioteca carregada
        if self.enclosing:
            for nome, (valor, tipo) in self.enclosing.exports.items():
                if nome == lexema:
                    raise RuntimeError(
                        f'Linha {token.linha}: função "{lexema}" não foi importada. '
                        f'Use: add "./biblioteca.kaa" -> {lexema};'
                    )

        raise RuntimeError(
            f'Linha {token.linha}: variável indefinida {lexema!r}'
        )

    def obter_tipo(self, nome):
        """
        Devolve o tipo Kaa declarado de uma variável.
        Usado pelo interpretador para fazer coerce no input e atribuição.
        """
        if nome in self.tipos:
            return self.tipos[nome]
        if self.enclosing:
            return self.enclosing.obter_tipo(nome)
        return None

    def atribuir(self, token, valor):
        """
        Atribui um valor a uma variável já existente neste scope.
        Se não existir aqui, sobe para o enclosing.
        Erra se a variável não existir em nenhum scope (não cria novas).

        OTIMIZAÇÃO: Atualiza cache inline para próximo acesso rápido.
        """
        lexema = token.lexema

        if lexema in self.valores:
            self.valores[lexema] = valor
            # Atualiza cache para acesso futuro
            self._cache_var[lexema] = (self, valor)
            return
        if self.enclosing:
            self.enclosing.atribuir(token, valor)
            return
        raise RuntimeError(
            f'Linha {token.linha}: variável indefinida {lexema!r}'
        )

    def exportar(self, nome, valor, tipo=None):
        """
        Regista uma função (ou variável) como exportável.
        Guarda o valor e o tipo para cópia no import.
        """
        self.exports[nome] = (valor, tipo)

    def obter_export(self, nome):
        """
        Recupera um export pelo nome.
        Lança erro se não existir.
        """
        if nome in self.exports:
            return self.exports[nome]
        raise KeyError(f"Export '{nome}' não encontrado")
