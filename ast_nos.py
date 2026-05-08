from dataclasses import dataclass
from typing import Any

# ========== Expressions ==========

@dataclass
class Binaria:
    esq: Any
    op: Any
    dir: Any

@dataclass
class Unaria:
    op: Any
    expr: Any

@dataclass
class Literal:
    valor: Any

@dataclass
class Agrupamento:
    expr: Any

@dataclass
class Variavel:
    nome: Any

@dataclass
class Atribuicao:
    nome: Any
    valor: Any

@dataclass
class Chamada:
    chamado: Any
    paren: Any
    args: Any

@dataclass
class Logico:
    esq: Any
    op: Any
    dir: Any

@dataclass
class Lista:
    elementos: Any

@dataclass
class Tuplo:
    elementos: Any

@dataclass
class Dicionario:
    chaves: Any
    valores: Any

@dataclass
class AcessoIndice:
    objeto: Any
    indice: Any
    indice_token: Any

@dataclass
class AcessoAtributo:
    objeto: Any
    atributo: Any

# ========== Statements ==========

@dataclass
class DeclVar:
    nome: Any
    tipo: str
    inicializador: Any

@dataclass
class DeclFun:
    nome: Any
    params: Any
    corpo: Any

@dataclass
class StmtExpr:
    expr: Any

@dataclass
class StmtPrint:
    exprs: Any

@dataclass
class StmtInput:
    prompt: Any
    alvo: Any

@dataclass
class StmtBloco:
    stmts: Any

@dataclass
class StmtIf:
    cond: Any
    entao: Any
    senao: Any

@dataclass
class StmtWhile:
    cond: Any
    corpo: Any

@dataclass
class StmtReturn:
    keyword: Any
    valor: Any

# ========== Export/Import ==========

@dataclass
class DeclExpon:
    nomes: Any
    todos: bool

@dataclass
class StmtImport:
    caminho: Any
    nomes: Any
