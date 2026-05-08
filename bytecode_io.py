"""
Kaa Bytecode Serialization (bytecode_io.py)
============================================
Serializa/deserializa ObjFunction para/de arquivos .kaac (Kaa Compiled).

Formato binário:
  Header:  b"KAAC" + version(1) + reserved(3)
  Função:  serializa_funcao(func)

serializa_funcao(func):
  name_len(2) + name(utf-8)
  arity(1)
  n_constants(2) + constantes...
  code_len(4) + code(bytes)
  n_upvalue_names(1) + nomes...

Constantes (tagged):
  TAG_NIL    = 0x00
  TAG_BOOL_T = 0x01
  TAG_BOOL_F = 0x02
  TAG_INT    = 0x03 + int64
  TAG_FLOAT  = 0x04 + double(8)
  TAG_STR    = 0x05 + len(2) + utf-8
  TAG_FUN    = 0x06 + serializa_funcao (recursivo)
  TAG_LIST   = 0x07 + count(2) + itens
  TAG_TUPLE  = 0x08 + count(2) + itens
  TAG_PY_TUPLE = 0x09 + count(2) + itens  (para lvalues como ('local',0))
"""

import struct
from chunk import Chunk, ObjFunction

MAGIC   = b"KAAC"
VERSION = 1

TAG_NIL      = 0x00
TAG_BOOL_T   = 0x01
TAG_BOOL_F   = 0x02
TAG_INT      = 0x03
TAG_FLOAT    = 0x04
TAG_STR      = 0x05
TAG_FUN      = 0x06
TAG_LIST     = 0x07
TAG_TUPLE    = 0x08
TAG_PY_TUPLE = 0x09   # tuples Python como ('local', slot)
TAG_NONE_L   = 0x0A   # lista Python None (para names_list no import)


def salvar(func: ObjFunction, caminho: str):
    """Serializa uma ObjFunction para um arquivo .kaac."""
    data = bytearray()
    data += MAGIC
    data += bytes([VERSION, 0, 0, 0])  # version + 3 reserved
    data += _ser_func(func)
    with open(caminho, 'wb') as f:
        f.write(data)


def carregar(caminho: str) -> ObjFunction:
    """Deserializa um arquivo .kaac para ObjFunction."""
    with open(caminho, 'rb') as f:
        data = f.read()
    if data[:4] != MAGIC:
        raise ValueError(f"Não é um arquivo .kaac válido: {caminho}")
    if data[4] != VERSION:
        raise ValueError(f"Versão de bytecode incompatível: {data[4]} (esperado {VERSION})")
    func, _ = _des_func(data, 8)
    return func


# ─── Serialização ─────────────────────────────────────────

def _ser_func(func: ObjFunction) -> bytes:
    out = bytearray()
    # name
    name_b = func.name.encode('utf-8')
    out += struct.pack('<H', len(name_b)) + name_b
    # arity
    out += bytes([func.arity])
    # constants
    out += struct.pack('<H', len(func.chunk.constants))
    for c in func.chunk.constants:
        out += _ser_const(c)
    # code
    code_bytes = bytes(func.chunk.code)
    out += struct.pack('<I', len(code_bytes)) + code_bytes
    # upvalue_names
    out += bytes([len(func.upvalue_names)])
    for n in func.upvalue_names:
        nb = n.encode('utf-8')
        out += struct.pack('<H', len(nb)) + nb
    return bytes(out)


def _ser_const(v) -> bytes:
    if v is None:
        return bytes([TAG_NIL])
    if v is True:
        return bytes([TAG_BOOL_T])
    if v is False:
        return bytes([TAG_BOOL_F])
    if isinstance(v, int):
        return bytes([TAG_INT]) + struct.pack('<q', v)
    if isinstance(v, float):
        return bytes([TAG_FLOAT]) + struct.pack('<d', v)
    if isinstance(v, str):
        b = v.encode('utf-8')
        return bytes([TAG_STR]) + struct.pack('<H', len(b)) + b
    if isinstance(v, ObjFunction):
        return bytes([TAG_FUN]) + _ser_func(v)
    if isinstance(v, list):
        if v is None:
            return bytes([TAG_NONE_L])
        out = bytearray([TAG_LIST]) + struct.pack('<H', len(v))
        for item in v:
            out += _ser_const(item)
        return bytes(out)
    if isinstance(v, tuple):
        # Distingue tuples Python (lvalues) de tuples Kaa
        out = bytearray([TAG_PY_TUPLE]) + struct.pack('<H', len(v))
        for item in v:
            out += _ser_const(item)
        return bytes(out)
    # fallback: serializa como string
    s = str(v).encode('utf-8')
    return bytes([TAG_STR]) + struct.pack('<H', len(s)) + s


# ─── Deserialização ───────────────────────────────────────

def _des_func(data: bytes, pos: int):
    # name
    name_len = struct.unpack_from('<H', data, pos)[0]; pos += 2
    name = data[pos:pos+name_len].decode('utf-8'); pos += name_len
    # arity
    arity = data[pos]; pos += 1
    # constants
    n_const = struct.unpack_from('<H', data, pos)[0]; pos += 2
    constants = []
    for _ in range(n_const):
        val, pos = _des_const(data, pos)
        constants.append(val)
    # code
    code_len = struct.unpack_from('<I', data, pos)[0]; pos += 4
    code = bytearray(data[pos:pos+code_len]); pos += code_len
    # upvalue_names
    n_upv = data[pos]; pos += 1
    upvalue_names = []
    for _ in range(n_upv):
        nl = struct.unpack_from('<H', data, pos)[0]; pos += 2
        upvalue_names.append(data[pos:pos+nl].decode('utf-8')); pos += nl
    # Reconstrói
    chunk = Chunk(name=name)
    chunk.code = code
    chunk.constants = constants
    func = ObjFunction(arity=arity, chunk=chunk, name=name)
    func.upvalue_names = upvalue_names
    return func, pos


def _des_const(data: bytes, pos: int):
    tag = data[pos]; pos += 1
    if tag == TAG_NIL:    return None, pos
    if tag == TAG_BOOL_T: return True, pos
    if tag == TAG_BOOL_F: return False, pos
    if tag == TAG_INT:
        v = struct.unpack_from('<q', data, pos)[0]; pos += 8
        return v, pos
    if tag == TAG_FLOAT:
        v = struct.unpack_from('<d', data, pos)[0]; pos += 8
        return v, pos
    if tag == TAG_STR:
        n = struct.unpack_from('<H', data, pos)[0]; pos += 2
        v = data[pos:pos+n].decode('utf-8'); pos += n
        return v, pos
    if tag == TAG_FUN:
        func, pos = _des_func(data, pos)
        return func, pos
    if tag == TAG_LIST:
        n = struct.unpack_from('<H', data, pos)[0]; pos += 2
        items = []
        for _ in range(n):
            item, pos = _des_const(data, pos)
            items.append(item)
        return items, pos
    if tag == TAG_TUPLE:
        n = struct.unpack_from('<H', data, pos)[0]; pos += 2
        items = []
        for _ in range(n):
            item, pos = _des_const(data, pos)
            items.append(item)
        return tuple(items), pos
    if tag == TAG_PY_TUPLE:
        n = struct.unpack_from('<H', data, pos)[0]; pos += 2
        items = []
        for _ in range(n):
            item, pos = _des_const(data, pos)
            items.append(item)
        return tuple(items), pos
    if tag == TAG_NONE_L:
        return None, pos
    raise ValueError(f"Tag de constante desconhecida: {tag:#x} @ pos={pos-1}")
