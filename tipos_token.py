from enum import Enum, auto

class TipoToken(Enum):
    # Símbolos de um caractere
    LPAREN      = auto()  # (
    RPAREN      = auto()  # )
    LBRACE      = auto()  # {
    RBRACE      = auto()  # }
    COMMA       = auto()  # ,
    SEMICOLON   = auto()  # ;
    PLUS        = auto()  # +
    MINUS       = auto()  # -
    STAR        = auto()  # *
    SLASH       = auto()  # /
    PERCENT     = auto()  # %

    # Símbolos de um ou dois caracteres
    BANG        = auto()  # !
    BANG_EQ     = auto()  # !=
    EQ          = auto()  # =
    EQ_EQ       = auto()  # ==
    GREATER         = auto()  # >
    GREATER_EQ      = auto()  # >=
    GREATER_GREATER = auto()  # >>
    LESS        = auto()  # <
    LESS_EQ     = auto()  # <=
    LBRACKET     = auto()  # [
    RBRACKET     = auto()  # ]
    QUESTION     = auto()  # ?
    COLON        = auto()  # :
    DOT          = auto()  # . (acesso a atributo)
    PIPE         = auto()  # | (bitwise or)

    # Literais
    IDENT       = auto()  # nome de variável ou função
    STRING      = auto()  # "texto"
    NUMBER      = auto()  # 42, 3.14

    # Modificadores de tipo
    TIPO_INT    = auto()  # -i
    TIPO_FLOAT  = auto()  # -f
    TIPO_STR    = auto()  # -s
    TIPO_PY     = auto()  # -py (import Python)
    TIPO_OBJ    = auto()  # -obj (Orientação à Objetos)

    # Booleanos
    TIPO_BOOL_T  = auto()  # -T
    TIPO_BOOL_F  = auto()  # -F

    # Coleção de itens
    TIPO_LIST   = auto()  # [1, 2, 3]
    TIPO_TUPLE  = auto()  # (1, "dois", 3.0)
    TIPO_DICT   = auto()  # {"chave": "valor"}

    # Export/Import
    EXPOR       = auto()  # expor
    ADD         = auto()  # add
    ARROW       = auto()  # ->
    ALL         = auto()  # all

    # Palavras-chave
    AND         = auto()
    CLASS       = auto()
    ELSE        = auto()
    FALSE       = auto()
    FUN         = auto()
    FOR         = auto()
    IF          = auto()
    IN          = auto()
    BANG_IN     = auto() # !in
    ELIF        = auto()
    NIL         = auto()
    OR          = auto()
    PRINT       = auto()
    INPUT       = auto()
    RETURN      = auto()
    TRUE        = auto()
    VAR         = auto()
    WHILE       = auto()
    EOF         = auto()