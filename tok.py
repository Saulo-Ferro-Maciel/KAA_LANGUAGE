from dataclasses import dataclass
from typing import Any
from tipos_token import TipoToken

@dataclass
class Token:
    tipo:   TipoToken
    lexema: str
    valor:  Any  # valor convertido para literais
    linha:  int

    def __repr__(self):
        return f"Token({self.tipo.name}, {self.lexema!r})"
