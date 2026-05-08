class PyloxError(Exception):
    def __init__(self, linha, msg, dica=''):
        self.linha = linha
        self.msg   = msg
        self.dica  = dica

    def __str__(self):
        s = f'\n[Linha {self.linha}] Erro: {self.msg}'
        if self.dica:
            s += f'\n  Dica: {self.dica}'
        return s
