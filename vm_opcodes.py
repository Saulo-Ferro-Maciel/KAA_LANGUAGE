from enum import IntEnum

class Opcode(IntEnum):
    """Instruções da máquina virtual Kaa v2.0"""

    # Constantes e Literais
    LOAD_CONST = 0
    LOAD_NIL   = 1
    LOAD_TRUE  = 2
    LOAD_FALSE = 3

    # Variáveis
    LOAD_GLOBAL   = 4
    STORE_GLOBAL  = 5
    LOAD_LOCAL    = 6
    STORE_LOCAL   = 7
    LOAD_UPVALUE  = 8
    STORE_UPVALUE = 9

    # Pilha
    POP = 10
    DUP = 11

    # Aritmética
    ADD = 20
    SUB = 21
    MUL = 22
    DIV = 23
    MOD = 24
    NEG = 25
    INC = 26
    DEC = 27

    # Comparação
    EQ  = 30
    NE  = 31
    GT  = 32
    LT  = 33
    GTE = 34
    LTE = 35
    CONTAINS = 36
    NOT_CONTAINS = 37

    # Lógicos
    NOT = 40
    AND = 41
    OR  = 42

    # Controle de Fluxo
    JUMP          = 50
    JUMP_IF_FALSE = 51
    JUMP_IF_TRUE  = 52
    JUMP_BACK     = 53

    # Funções
    CALL          = 60
    RETURN        = 61
    CLOSURE       = 62
    MAKE_FUNCTION = 63

    # Coleções
    BUILD_LIST  = 70
    BUILD_TUPLE = 71
    BUILD_DICT  = 72
    INDEX_GET   = 73
    INDEX_SET   = 74
    GET_LENGTH  = 75
    GET_KEYS    = 76
    SLICE_GET   = 77

    # Atributos
    GET_ATTR    = 80
    SET_ATTR    = 81
    METHOD_CALL = 82

    # E/S
    PRINT = 90
    INPUT = 91

    # Sistema de Módulos (NOVO v2.0)
    IMPORT_MODULE = 92   # IMPORT_MODULE <path_idx:int16> <names_idx:int16> <all:byte>
    IMPORT_PYTHON = 93   # IMPORT_PYTHON <code_idx:int16> <names_idx:int16> <all:byte>
    EXPORT_NAME   = 94   # EXPORT_NAME <name_idx:byte>
    EXPORT_ALL    = 95   # EXPORT_ALL

    # Controle
    HALT = 99
    NOP  = 100

    # ==========================
    # C-BOUND TYPES (Cython)
    # ==========================
    ADD_INT    = 110
    ADD_FLOAT  = 111
    SUB_INT    = 112
    SUB_FLOAT  = 113
    MUL_INT    = 114
    MUL_FLOAT  = 115
    INDEX_LIST = 116

    # ==========================
    # SUPERINSTRUÇÕES JIT
    # ==========================
    JIT_ADD_CONST_STORE = 150
    JIT_ADD_LOCAL_STORE = 151
    JIT_LTE_JUMP        = 152
    JIT_GLOB_ADD_CONST   = 153
    JIT_GLOB_ADD_LOCAL   = 154
    JIT_GLOB_LTE_JUMP    = 155
    JIT_ATTR_ADD_CONST   = 156
    JIT_ATTR_ADD_LOCAL   = 157
    JIT_LT_JUMP         = 158
    JIT_GLOB_LT_JUMP    = 159


class FunctionKind(IntEnum):
    KAA_FUNCTION    = 0
    PYTHON_FUNCTION = 1
    BUILTIN         = 2
    NATIVE          = 3
