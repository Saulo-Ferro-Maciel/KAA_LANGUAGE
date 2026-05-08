"""
Kaa VM - Bytecode Virtual Machine v3.2.2 (Restauração Completa)
===============================================================
Correções v3.2.2:
- SET_ATTR: ordem correta (val empilha antes de obj no compilador)
- _str: inteiros sem '.0', True/-T e False/-F corretos
- INPUT: aceita N partes de prompt (match com compilador)
- METHOD_CALL (op=82): busca atributo e chama closure em linha
- Lógica booleana: _truthy rejeita não-booleanos em condições
- JIT: corrigido _jit_optimize para novos layouts
"""

from vm_opcodes import Opcode
from chunk import ObjFunction, ObjClosure
import time
import os

# ─── Diretório de bibliotecas ─────────────────────────────────────────────────
# Quando instalado: KAA_LIBS=/opt/kaa/libs (definido pelo wrapper shell)
# Em desenvolvimento: usa 'libs/' ao lado do vm.pyx
_KAA_LIBS_DIR = os.environ.get(
    'KAA_LIBS',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs')
)

class VMFrame:
    __slots__ = ['closure', 'ip', 'slots']
    def __init__(self, closure, slots_count):
        self.closure = closure
        self.ip = 0
        self.slots = [None] * slots_count

class KaaModule:
    __slots__ = ['name', 'path', 'exports']
    def __init__(self, name, path, exports):
        self.name    = name
        self.path    = path
        self.exports = exports

class FValFloat(float):
    def __new__(cls, val, original=None):
        obj = super().__new__(cls, val)
        obj.original = original if original is not None else val
        return obj
    def __call__(self, casas=2):
        return FValFloat(round(self.original, int(casas)), self.original)

class CallableInt(int):
    def __call__(self, *args): return self
class CallableList(list):
    def __call__(self, *args): return self
class CallableTuple(tuple):
    def __call__(self, *args): return self
class CallableDict(dict):
    def __call__(self, *args): return self

# ─── Tipo booleano estrito Kaa ─────────────────────────────────────────────────

class KaaBool:
    """Sentinel para verificacao de tipo booleano estrito."""
    pass

_BOOL_STRICT = True  # Ativa checagem de tipo em condicoes

def _check_bool(v, context="condição"):
    """Lança erro se v não for booleano Kaa (-T / -F)."""
    if _BOOL_STRICT and not isinstance(v, bool):
        raise RuntimeError(
            f"Kaa: tipo inválido em {context}: "
            f"esperado -T ou -F, recebido {type(v).__name__!r} = {v!r}.\n"
            f"Use uma expressão de comparação (==, !=, <, >, <=, >=) ou literal -T/-F."
        )
    return v


class VM:
    def __init__(self):
        self.stack   = []
        self.frames  = []
        self.globals = {}
        self.builtins = {}
        self.modules  = {}       # cache de módulos
        self.loading  = set()    # ciclo detection
        self._mod_exports = None
        self._register_builtins()

    def _register_builtins(self):
        from datetime import datetime
        self.builtins.update({
            'sleep':         lambda *a: (time.sleep(float(a[0])) if a else None),
            'timestamp':     lambda *a: time.time(),
            'time_str':      lambda *a: datetime.now().strftime("%H:%M:%S"),
            'date_str':      lambda *a: datetime.now().strftime("%d/%m/%Y"),
            'destroy_arena': self._builtin_destroy_arena,
            'arenas_info':   self._builtin_arenas_info,
        })

    def _builtin_arenas_info(self, *a):
        info = CallableList()
        for mod in self.modules.values():
            info.append(CallableDict({"name": mod.name, "path": mod.path, "environments": 1}))
        return info

    def _builtin_destroy_arena(self, name=None):
        if not name:
            count = len(self.modules); self.modules.clear(); return count
        to_del = []
        name_clean = name.replace(".kaa", "")
        for path, mod in self.modules.items():
            mod_name_clean = mod.name.replace(".kaa", "")
            if mod_name_clean == name_clean:
                for e in mod.exports: self.globals.pop(e, None)
                to_del.append(path)
        for p in to_del: del self.modules[p]
        return len(to_del)

    def run(self, function: ObjFunction):
        closure = ObjClosure(function=function, module_globals=self.globals)
        frame   = VMFrame(closure, function.arity + 256)
        if not hasattr(self, 'frames') or self.frames is None:
            self.frames = []
        target_depth = len(self.frames)
        self.frames.append(frame)
        return self._run_frame(target_depth)

    def _run_frame(self, int target_depth=0):
        """LOOP MESTRE NÃO-RECURSIVO COM SUPORTE TOTAL v3.2.3 (Otimizado)"""
        frame    = self.frames[len(self.frames)-1]
        closure  = frame.closure
        chunk    = closure.function.chunk
        
        # Aplicar JIT uma única vez fora do loop quente
        if not getattr(chunk, '_jitted', False):
            self._jit_optimize(chunk)

        code = chunk.code
        cdef int ip = frame.ip
        cdef list slots = frame.slots
        cdef list constants = chunk.constants
        globals_ = getattr(closure, 'module_globals', self.globals) or self.globals
        builtins_= self.builtins
        cdef list stack = self.stack
        
        # Tipagem local para loop quente
        cdef int op
        cdef int argc
        cdef int n

        while ip < len(code):
            # Fast-path JIT: garante que funções chamadas também sejam otimizadas
            if not chunk._jitted:
                self._jit_optimize(chunk)
                code = chunk.code # Refresh local reference
            
            op = code[ip]
            ip += 1

            # ─── JIT FAST PATHS (Otimizado) ────────────────────
            if op >= 150:
                if op == 150:   # JIT_ADD_CONST_STORE (local += const)
                    idx_slot = code[ip]; val = constants[code[ip+2]]; ip += 8
                    try: slots[idx_slot] += val
                    except: slots[idx_slot] = self._str(slots[idx_slot]) + self._str(val)
                    continue
                elif op == 151: # JIT_ADD_LOCAL_STORE (local += local)
                    dst = code[ip]; src = code[ip+2]; ip += 5
                    try: slots[dst] += slots[src]
                    except: slots[dst] = self._str(slots[dst]) + self._str(slots[src])
                    continue
                elif op == 152: # JIT_LTE_JUMP (local <= const → jump_if_false)
                    slot = code[ip]; val = constants[code[ip+2]]; off = code[ip+4] | (code[ip+5] << 8)
                    ip += 8
                    if not (slots[slot] <= val): ip += off
                    continue
                elif op == 153: # JIT_GLOB_ADD_CONST
                    name_idx = code[ip] | (code[ip+1] << 8)
                    val_idx  = code[ip+3] # 1 byte index
                    ip += 10
                    name = constants[name_idx]; val = constants[val_idx]
                    try: globals_[name] += val
                    except: globals_[name] = self._str(globals_[name]) + self._str(val)
                    continue
                elif op == 154: # JIT_GLOB_ADD_LOCAL
                    name_idx = code[ip] | (code[ip+1] << 8)
                    slot_idx = code[ip+3]; ip += 10
                    name = constants[name_idx]
                    try: globals_[name] += slots[slot_idx]
                    except: globals_[name] = self._str(globals_.get(name,'')) + self._str(slots[slot_idx])
                    continue
                elif op == 155: # JIT_GLOB_LTE_JUMP
                    name_idx = code[ip] | (code[ip+1] << 8)
                    val_idx  = code[ip+3] # 1 byte
                    off      = code[ip+6] | (code[ip+7] << 8)
                    ip += 9
                    if not (globals_.get(constants[name_idx], 0) <= constants[val_idx]): ip += off
                    continue
                elif op == 158: # JIT_LT_JUMP (local < const)
                    slot = code[ip]; val = constants[code[ip+2]]; off = code[ip+4] | (code[ip+5] << 8)
                    ip += 8
                    if not (slots[slot] < val): ip += off
                    continue
                elif op == 159: # JIT_GLOB_LT_JUMP (global < const)
                    name_idx = code[ip] | (code[ip+1] << 8)
                    val_idx  = code[ip+3] # 1 byte
                    off      = code[ip+6] | (code[ip+7] << 8)
                    ip += 9
                    if not (globals_.get(constants[name_idx], 0) < constants[val_idx]): ip += off
                    continue
                elif op == 156: # JIT_ATTR_ADD_CONST
                    obj_slot = code[ip]; at_idx = code[ip+2]; v_idx = code[ip+4]; ip += 11
                    obj = slots[obj_slot]; attr = constants[at_idx]; val = constants[v_idx]
                    if isinstance(obj, dict):
                        obj[attr] = (obj.get(attr) or 0) + val
                    else:
                        setattr(obj, attr, getattr(obj, attr, 0) + val)
                    continue
                elif op == 157: # JIT_ATTR_ADD_LOCAL
                    obj_slot = code[ip]; at_idx = code[ip+2]; src_slot = code[ip+4]; ip += 11
                    obj = slots[obj_slot]; attr = constants[at_idx]; val = slots[src_slot]
                    if isinstance(obj, dict):
                        obj[attr] = (obj.get(attr) or 0) + val
                    else:
                        setattr(obj, attr, getattr(obj, attr, 0) + val)
                    continue


            # ─── DESPACHO TRADICIONAL ──────────────────────────

            # Constantes e Literais
            if op == 0:   stack.append(constants[code[ip]]); ip += 1  # LOAD_CONST
            elif op == 1: stack.append(None)                            # LOAD_NIL
            elif op == 2: stack.append(True)                            # LOAD_TRUE
            elif op == 3: stack.append(False)                           # LOAD_FALSE

            # Variáveis
            elif op == 4: # LOAD_GLOBAL
                idx = code[ip] | (code[ip+1] << 8); ip += 2
                name = constants[idx]
                if name in globals_: stack.append(globals_[name])
                elif name in builtins_: stack.append(builtins_[name])
                else: raise RuntimeError(f"Kaa: variável indefinida '{name}'")
            elif op == 5: # STORE_GLOBAL
                idx = code[ip] | (code[ip+1] << 8); ip += 2
                globals_[constants[idx]] = stack.pop()
            elif op == 6:  stack.append(slots[code[ip]]); ip += 1      # LOAD_LOCAL
            elif op == 7:  slots[code[ip]] = stack.pop(); ip += 1      # STORE_LOCAL
            elif op == 8:  stack.append(closure.upvalues[code[ip]]); ip += 1  # LOAD_UPVALUE
            elif op == 9:  closure.upvalues[code[ip]] = stack[len(stack)-1]; ip += 1    # STORE_UPVALUE

            # Pilha
            elif op == 10: # POP
                if stack: stack.pop()
            elif op == 11: stack.append(stack[len(stack)-1])                      # DUP

            # Aritmética
            elif op == 20: # ADD
                b = stack.pop(); a = stack.pop()
                if isinstance(a, str) or isinstance(b, str):
                    stack.append(self._str(a) + self._str(b))
                else:
                    stack.append(a + b)
            elif op == 21: b = stack.pop(); a = stack.pop(); stack.append(a - b)   # SUB
            elif op == 22: b = stack.pop(); a = stack.pop(); stack.append(a * b)   # MUL
            elif op == 23: # DIV
                b = stack.pop(); a = stack.pop()
                if b == 0: raise RuntimeError("Kaa: divisão por zero")
                stack.append(a / b)
            elif op == 24: b = stack.pop(); a = stack.pop(); stack.append(a % b)   # MOD
            elif op == 25: stack.append(-stack.pop())                              # NEG
            elif op == 26: slots[code[ip]] += 1; ip += 1                           # INC
            elif op == 27: slots[code[ip]] -= 1; ip += 1                           # DEC

            # Comparação — produzem -T/-F sempre
            elif op == 30: b = stack.pop(); a = stack.pop(); stack.append(a == b)  # EQ
            elif op == 31: b = stack.pop(); a = stack.pop(); stack.append(a != b)  # NE
            elif op == 32: b = stack.pop(); a = stack.pop(); stack.append(a > b)   # GT
            elif op == 33: b = stack.pop(); a = stack.pop(); stack.append(a < b)   # LT
            elif op == 34: b = stack.pop(); a = stack.pop(); stack.append(a >= b)  # GTE
            elif op == 35: b = stack.pop(); a = stack.pop(); stack.append(a <= b)  # LTE
            elif op == 36:
                b = stack.pop(); a = stack.pop()
                try: stack.append(a in b)
                except TypeError: raise RuntimeError("Kaa: operador 'in' requer uma coleção iterável")
            elif op == 37:
                b = stack.pop(); a = stack.pop()
                try: stack.append(a not in b)
                except TypeError: raise RuntimeError("Kaa: operador '!in' requer uma coleção iterável")

            # Lógicos — operam sobre booleanos Kaa
            elif op == 40: stack.append(not stack.pop())                 # NOT
            elif op == 41: b = stack.pop(); a = stack.pop(); stack.append(a and b) # AND
            elif op == 42: b = stack.pop(); a = stack.pop(); stack.append(a or b)  # OR

            # Controle de Fluxo
            elif op == 50: # JUMP
                ip += (code[ip] | (code[ip+1] << 8)) + 2
            elif op == 51: # JUMP_IF_FALSE
                off = code[ip] | (code[ip+1] << 8); ip += 2
                v = stack[len(stack)-1]
                # Otimizado: se v for bool, skip check
                if not isinstance(v, bool): _check_bool(v, "condição if/while")
                if not v: ip += off
            elif op == 52: # JUMP_IF_TRUE
                off = code[ip] | (code[ip+1] << 8); ip += 2
                v = stack[len(stack)-1]
                _check_bool(v, "condição or/and")
                if v: ip += off
            elif op == 53: # JUMP_BACK
                raw = code[ip] | (code[ip+1] << 8); ip += 2
                ip += (raw - 0x10000) if raw >= 0x8000 else raw

            # Funções
            elif op == 60: # CALL
                argc = code[ip]; ip += 1
                args = [stack.pop() for _ in range(argc)]; args.reverse()
                func = stack.pop()
                if isinstance(func, ObjClosure):
                    frame.ip = ip
                    frame = VMFrame(func, max(func.function.arity + 32, len(args) + 32))
                    for i, arg in enumerate(args): frame.slots[i] = arg
                    self.frames.append(frame)
                    closure = func; chunk = closure.function.chunk
                    code = chunk.code; ip = 0; slots = frame.slots
                    constants = chunk.constants
                    globals_ = getattr(closure, 'module_globals', self.globals) or self.globals
                    continue
                elif hasattr(func, 'chamar'):
                    stack.append(func.chamar(self, args))
                elif callable(func):
                    stack.append(func(*args))
                else:
                    raise RuntimeError(f"Kaa: não é chamável: {type(func).__name__}")
                stack = self.stack
            elif op == 61: # RETURN
                res = stack.pop() if stack else None
                self.frames.pop()
                if len(self.frames) <= target_depth: return res
                frame = self.frames[-1]; closure = frame.closure
                chunk = closure.function.chunk
                code = chunk.code; ip = frame.ip; slots = frame.slots
                constants = chunk.constants
                globals_ = getattr(closure, 'module_globals', self.globals) or self.globals
                stack.append(res)
                continue
            elif op == 62 or op == 63: # CLOSURE ou MAKE_FUNCTION
                func_obj = constants[code[ip]]; ip += 1
                new_closure = ObjClosure(func_obj, module_globals=globals_)
                n_upvalues = getattr(func_obj, 'upvalue_count', 0)
                new_upvalues = [None] * n_upvalues
                for i in range(n_upvalues):
                    is_local = code[ip]; ip += 1
                    index    = code[ip]; ip += 1
                    if is_local:
                        new_upvalues[i] = slots[index]
                    else:
                        new_upvalues[i] = closure.upvalues[index] if closure.upvalues else None
                new_closure.upvalues = new_upvalues
                stack.append(new_closure)

            # Coleções
            elif op == 70: # BUILD_LIST
                n = code[ip]; ip += 1
                items = [stack.pop() for _ in range(n)]; items.reverse()
                stack.append(CallableList(items))
            elif op == 71: # BUILD_TUPLE
                n = code[ip]; ip += 1
                items = [stack.pop() for _ in range(n)]; items.reverse()
                stack.append(CallableTuple(items))
            elif op == 72: # BUILD_DICT
                n = code[ip]; ip += 1
                d = CallableDict()
                pairs = [(stack.pop(), stack.pop()) for _ in range(n)]
                for v, k in pairs: d[k] = v
                stack.append(d)
            elif op == 73: # INDEX_GET
                idx = stack.pop(); obj = stack.pop()
                if isinstance(idx, float) and idx.is_integer(): idx = int(idx)
                if isinstance(idx, int): idx = int(idx)
                try: stack.append(obj[idx])
                except: stack.append(None)
            elif op == 74: # INDEX_SET
                val = stack.pop(); idx = stack.pop(); obj = stack.pop()
                if isinstance(idx, float) and idx.is_integer(): idx = int(idx)
                if isinstance(idx, int): idx = int(idx)
                if isinstance(obj, list) and isinstance(idx, int) and idx >= len(obj):
                    obj.extend([None] * (idx - len(obj) + 1))
                try: obj[idx] = val; stack.append(val)
                except: stack.append(None)
            elif op == 75: # GET_LENGTH
                obj = stack.pop()
                stack.append(len(obj) if hasattr(obj, '__len__') else 0)
            elif op == 76: # GET_KEYS
                obj = stack.pop()
                stack.append(CallableList(obj.keys()) if isinstance(obj, dict) else CallableList())
            elif op == 77: # SLICE_GET
                end = stack.pop(); start = stack.pop(); obj = stack.pop()
                if isinstance(start, int): start = int(start)
                if isinstance(end, int): end = int(end)
                try: stack.append(type(obj)(obj[start:end]))
                except: stack.append(None)

            # Atributos (OOP)
            elif op == 80: # GET_ATTR
                attr = constants[code[ip]]; ip += 1
                obj  = stack.pop()
                
                # Check nativos comuns antes do dispatch OOP
                if attr == 'length':
                    stack.append(len(obj) if hasattr(obj, '__len__') else 0)
                elif attr == 'f_valuation':
                    stack.append(FValFloat(round(obj, 2), obj) if isinstance(obj, (int, float)) else obj)
                elif attr == 'is_num':
                    stack.append(isinstance(obj, (int, float)))
                elif attr == 'rm_nil':
                    stack.append(self._op_rm_nil(obj))
                elif isinstance(obj, str):
                    if attr == 'capitalize': stack.append(obj.capitalize())
                    elif attr == 'capitalize_phrase': stack.append(obj.title())
                    elif attr == 'upper_letters': stack.append(obj.upper())
                    elif attr == 'lower_letters': stack.append(obj.lower())
                    elif attr == 'replace_elements': stack.append(obj.replace(" ", ""))
                    else: stack.append(getattr(obj, attr, None))
                elif isinstance(obj, dict):
                    method = obj.get(attr)
                    if method is None:
                        if attr == 'keys': stack.append(CallableList(obj.keys()))
                        elif attr == 'values': stack.append(CallableList(obj.values()))
                        else: stack.append(None)
                    else:
                        stack.append(method)
                else:
                    if hasattr(obj, attr):
                        stack.append(getattr(obj, attr))
                    else:
                        stack.append(None)
            elif op == 81: # SET_ATTR
                attr = constants[code[ip]]; ip += 1
                obj  = stack.pop()
                val  = stack.pop()
                if isinstance(obj, dict):
                    obj[attr] = val
                else:
                    setattr(obj, attr, val)
                stack.append(val)
            elif op == 82: # METHOD_CALL
                attr = constants[code[ip]]; argc = code[ip+1]; ip += 2
                if argc == 0: args = []
                elif argc == 1: args = [stack.pop()]
                elif argc == 2: b = stack.pop(); args = [stack.pop(), b]
                else: args = [stack.pop() for _ in range(argc)]; args.reverse()
                obj  = stack.pop()
                method = None
                
                if attr == 'length':
                    method = lambda *a: len(obj) if hasattr(obj, '__len__') else 0
                elif attr == 'f_valuation':
                    method = lambda *a: self._op_f_valuation(obj, a[0] if a else 2)
                elif attr == 'is_num':
                    method = lambda *a: isinstance(obj, (int, float))
                elif attr == 'rm_nil':
                    method = lambda *a: self._op_rm_nil(obj)
                elif isinstance(obj, str):
                    if attr == 'capitalize': method = lambda *a: obj.capitalize()
                    elif attr == 'capitalize_phrase': method = lambda *a: obj.title()
                    elif attr == 'upper_letters': method = lambda *a: obj.upper()
                    elif attr == 'lower_letters': method = lambda *a: obj.lower()
                    elif attr == 'replace_elements':
                        method = lambda *a: obj.replace(self._str(a[0]), self._str(a[1])) if len(a) >= 2 else obj.replace(" ", "")
                    else: method = getattr(obj, attr, None)
                elif isinstance(obj, dict):
                    method = obj.get(attr)
                    if method is None:
                        if attr == 'keys': method = lambda *a: CallableList(obj.keys())
                        elif attr == 'values': method = lambda *a: CallableList(obj.values())
                else:
                    method = getattr(obj, attr, None)
                if method is None:
                    raise RuntimeError(f"Kaa: método '{attr}' não encontrado em objeto")
                if isinstance(method, ObjClosure):
                    frame.ip = ip
                    frame = VMFrame(method, max(method.function.arity + 32, len(args) + 32))
                    for i, arg in enumerate(args): frame.slots[i] = arg
                    self.frames.append(frame)
                    closure = method; chunk = closure.function.chunk
                    code = chunk.code; ip = 0; slots = frame.slots
                    constants = chunk.constants
                    globals_ = getattr(closure, 'module_globals', self.globals) or self.globals
                    continue
                elif callable(method):
                    stack.append(method(*args))
                else:
                    raise RuntimeError(f"Kaa: '{attr}' não é chamável")
                stack = self.stack
            # E/S
            elif op == 90: # PRINT
                n = code[ip]; ip += 1
                parts = [stack.pop() for _ in range(n)]; parts.reverse()
                print(''.join(self._str(p) for p in parts))
            elif op == 91: # INPUT
                n_parts  = code[ip]; ip += 1
                lvalue   = stack.pop()                              # pode ser nome ou '__index__'
                idx_val, obj = None, None
                if lvalue == '__index__':
                    idx_val = stack.pop()
                    obj = stack.pop()
                
                parts    = [stack.pop() for _ in range(n_parts)]    # pega N partes
                parts.reverse()
                msg = ''.join(self._str(p) for p in parts)
                val = input(msg)
                
                # Re-coloca obj e idx pra _store_lvalue funcionar como antes
                if lvalue == '__index__':
                    stack.append(obj)
                    stack.append(idx_val)
                    
                self._store_lvalue(frame, lvalue, val)
                slots = frame.slots

            # Sistema de Módulos
            elif op == 92: # IMPORT_MODULE
                frame.ip = ip; self._op_import_module(frame, code, constants); ip = frame.ip
                globals_ = self.globals
            elif op == 93: # IMPORT_PYTHON
                frame.ip = ip; self._op_import_python(frame, code, constants); ip = frame.ip
                globals_ = self.globals
            elif op == 94: # EXPORT_NAME
                name = constants[code[ip]]; ip += 1
                if self._mod_exports is not None:
                    self._mod_exports[name] = globals_.get(name)
            elif op == 95: # EXPORT_ALL
                if self._mod_exports is not None:
                    self._mod_exports.update(globals_)

            # Controle
            elif op == 99: # HALT
                res = stack.pop() if stack else None
                if self.frames:
                    self.frames.pop()
                if len(self.frames) <= target_depth: return res
                frame = self.frames[len(self.frames)-1]; closure = frame.closure
                chunk = closure.function.chunk
                code = chunk.code; ip = frame.ip; slots = frame.slots
                constants = chunk.constants
                globals_ = getattr(closure, 'module_globals', self.globals) or self.globals
                stack.append(res)
                continue
            elif op == 100: pass                                    # NOP

            # C-BOUND TYPES (Cython Optmizations)
            elif op == 110: # ADD_INT
                b = stack.pop(); a = stack.pop()
                stack.append(<int>a + <int>b)
            elif op == 111: # ADD_FLOAT
                b = stack.pop(); a = stack.pop()
                stack.append(<float>a + <float>b)
            elif op == 112: # SUB_INT
                b = stack.pop(); a = stack.pop()
                stack.append(<int>a - <int>b)
            elif op == 113: # SUB_FLOAT
                b = stack.pop(); a = stack.pop()
                stack.append(<float>a - <float>b)
            elif op == 114: # MUL_INT
                b = stack.pop(); a = stack.pop()
                stack.append(<int>a * <int>b)
            elif op == 115: # MUL_FLOAT
                b = stack.pop(); a = stack.pop()
                stack.append(<float>a * <float>b)
            elif op == 116: # INDEX_LIST
                idx = stack.pop(); obj = stack.pop()
                try: stack.append(obj[<int>idx])
                except: stack.append(None)

    # ─── JIT Peephole Optimizer ────────────────────────────────────────────────

    def _jit_optimize(self, chunk):
        """
        Substitui sequências de bytecodes por superinstruções mais rápidas.
        Padrões reconhecidos:
          LOCAL += CONST   → JIT_ADD_CONST_STORE (150)
          GLOBAL += CONST  → JIT_GLOB_ADD_CONST  (153)
          OBJ.attr += CONST→ JIT_ATTR_ADD_CONST  (156)
        """
        code = chunk.code
        n    = len(code)
        i    = 0
        while i < n - 4:
            # Padrão LOCAL += CONST:
            # LOAD_LOCAL(1) slot | LOAD_CONST(1) idx | ADD(1) | DUP(1) | STORE_LOCAL(1) slot | POP(1)
            # codes: [6, slot, 0, idx, 20, 11, 7, slot, 10]  → 9 bytes
            if (i + 8 < n and
                code[i]   == 6 and   # LOAD_LOCAL
                code[i+2] == 0 and   # LOAD_CONST
                code[i+4] == 20 and  # ADD
                code[i+5] == 11 and  # DUP
                code[i+6] == 7 and   # STORE_LOCAL
                code[i+8] == 10 and  # POP
                code[i+1] == code[i+7]):  # mesmo slot
                code[i] = 150  # JIT_ADD_CONST_STORE
                # restante dos bytes já está nos slots corretos (ip += 8 na VM)
                i += 9
                continue

            # Padrão GLOBAL += CONST:
            # LOAD_GLOBAL(3) | LOAD_CONST(2) | ADD | DUP | STORE_GLOBAL(3) | POP  → 12 bytes
            if (i + 10 < n and
                code[i]    == 4 and  # LOAD_GLOBAL
                code[i+3]  == 0 and  # LOAD_CONST
                code[i+5]  == 20 and # ADD
                code[i+6]  == 11 and # DUP
                code[i+7]  == 5 and  # STORE_GLOBAL
                code[i+10] == 10 and # POP
                chunk.constants[code[i+1] | (code[i+2] << 8)] ==
                chunk.constants[code[i+8] | (code[i+9] << 8)]):  # mesmo nome
                code[i] = 153  # JIT_GLOB_ADD_CONST
                i += 11
                continue

            # Padrão OBJ.attr += CONST:
            # LOAD_LOCAL(2) | GET_ATTR(2) | LOAD_CONST(2) | ADD | LOAD_LOCAL(2) | SET_ATTR(2) | POP  → 12 bytes
            if (i + 11 < n and
                code[i]    == 6 and  # LOAD_LOCAL
                code[i+2]  == 80 and # GET_ATTR
                code[i+4]  == 0 and  # LOAD_CONST
                code[i+6]  == 20 and # ADD
                code[i+7]  == 6 and  # LOAD_LOCAL (objeto novamente)
                code[i+9]  == 81 and # SET_ATTR
                code[i+11] == 10 and # POP
                code[i+1]  == code[i+8] and  # mesmo slot de objeto
                code[i+3]  == code[i+10]):    # mesmo attr_idx
                code[i] = 156  # JIT_ATTR_ADD_CONST
                i += 12
                continue
                
            # Padrão OBJ.attr += LOCAL:
            # LOAD_LOCAL(2) | GET_ATTR(2) | LOAD_LOCAL(2) | ADD | LOAD_LOCAL(2) | SET_ATTR(2) | POP  → 12 bytes
            if (i + 11 < n and
                code[i]    == 6 and  # LOAD_LOCAL
                code[i+2]  == 80 and # GET_ATTR
                code[i+4]  == 6 and  # LOAD_LOCAL
                code[i+6]  == 20 and # ADD
                code[i+7]  == 6 and  # LOAD_LOCAL (objeto novamente)
                code[i+9]  == 81 and # SET_ATTR
                code[i+11] == 10 and # POP
                code[i+1]  == code[i+8] and  # mesmo slot de objeto
                code[i+3]  == code[i+10]):    # mesmo attr_idx
                code[i] = 157  # JIT_ATTR_ADD_LOCAL
                i += 12
                continue

            # Padrão LOCAL LTE_JUMP: [6, slot, 0, idx, 35, 51, lo, hi, 10] (9 bytes)
            # if (i + 8 < n and code[i] == 6 and code[i+2] == 0 and code[i+4] == 35 and 
            #    code[i+5] == 51 and code[i+8] == 10):
            #    code[i] = 152; code[i+5] = code[i+6]; code[i+6] = code[i+7]
            #    i += 9; continue

            # Padrão LOCAL LT_JUMP: [6, slot, 0, idx, 33, 51, lo, hi, 10] (9 bytes)
            # if (i + 8 < n and code[i] == 6 and code[i+2] == 0 and code[i+4] == 33 and 
            #    code[i+5] == 51 and code[i+8] == 10):
            #    code[i] = 158; code[i+5] = code[i+6]; code[i+6] = code[i+7]
            #    i += 9; continue

            # Padrão GLOB LTE_JUMP: [4, n_lo, n_hi, 0, v_idx, 35, 51, o_lo, o_hi, 10] (10 bytes)
            # if (i + 9 < n and code[i] == 4 and code[i+3] == 0 and code[i+5] == 35 and 
            #    code[i+6] == 51 and code[i+9] == 10):
                # pattern 155: name_idx at i+1, val_idx at i+4(lo) i+5(hi), offset at i+7(lo) i+8(hi)
            #    code[i] = 155; code[i+5] = 0; i += 10; continue

            # Padrão GLOB LT_JUMP: [4, n_lo, n_hi, 0, v_idx, 33, 51, o_lo, o_hi, 10] (10 bytes)
            # if (i + 9 < n and code[i] == 4 and code[i+3] == 0 and code[i+5] == 33 and 
            #    code[i+6] == 51 and code[i+9] == 10):
                # pattern 159: same as 155
            #    code[i] = 159; code[i+5] = 0; i += 10; continue

            i += 1
        chunk._jitted = True

    # ─── Helpers ───────────────────────────────────────────────────────────────

    def _op_rm_nil(self, obj):
        if isinstance(obj, list):  return CallableList([x for x in obj if x is not None])
        if isinstance(obj, tuple): return CallableTuple([x for x in obj if x is not None])
        if isinstance(obj, dict):  return CallableDict({k: v for k, v in obj.items() if k is not None})
        return obj

    def _op_f_valuation(self, obj, precision=2):
        if not isinstance(obj, (int, float)): return obj
        return FValFloat(round(obj, int(precision)), obj)

    def _store_lvalue(self, frame, lvalue, value):
        """Armazena valor convertido no lvalue correto (global, local ou índice)."""
        val = self._coerce_num(value)
        if lvalue == '__index__':
            idx = self.stack.pop(); obj = self.stack.pop()
            if isinstance(idx, float) and idx.is_integer(): idx = int(idx)
            
            # Autocriação de chaves ou expansão de lista
            if isinstance(obj, list) and isinstance(idx, int):
                # Expande lista com nil se acessar um índice além do tamanho atual
                if idx >= len(obj):
                    obj.extend([None] * (idx - len(obj) + 1))
            
            obj[idx] = val
        elif isinstance(lvalue, tuple) and lvalue[0] == 'local':
            frame.slots[lvalue[1]] = val
        else:
            self.globals[lvalue] = val

    def _coerce_num(self, valor):
        """Tenta converter string para número (int preferido, float se necessário)."""
        try:
            f = float(valor)
            return int(f) if f.is_integer() else f
        except:
            return valor

    def _truthy(self, v):
        """Verifica truthiness sem checagem de tipo estrita (uso interno seguro)."""
        return v is not None and v is not False

    def _str(self, v):
        """Serializa um valor Kaa para string impressão."""
        if v is None:   return 'nil'
        if v is True:   return '-T'
        if v is False:  return '-F'
        if isinstance(v, float):
            # Se for inteiro exato, mostra sem decimais
            if v.is_integer():
                return str(int(v))
            return str(v)
        if isinstance(v, list):
            return '[' + ', '.join(self._str(x) for x in v) + ']'
        if isinstance(v, tuple):
            if len(v) == 1:
                return '(' + self._str(v[0]) + ',)'
            return '(' + ', '.join(self._str(x) for x in v) + ')'
        if isinstance(v, dict):
            pairs = ', '.join(f'{self._str(k)}: {self._str(val)}' for k, val in v.items())
            return '{' + pairs + '}'
        if isinstance(v, ObjClosure):
            return f'<fun {v.function.name}>'
        return str(v)

    def set_builtin(self, n, v): self.builtins[n] = v
    def get_builtin(self, n): return self.builtins.get(n)

    # ─── Módulos ───────────────────────────────────────────────────────────────

    def _op_import_module(self, f, c, k):
        path_idx   = c[f.ip] | (c[f.ip+1] << 8); f.ip += 2
        names_idx  = c[f.ip] | (c[f.ip+1] << 8); f.ip += 2
        import_all = c[f.ip]; f.ip += 1
        caminho = k[path_idx]
        if not os.path.isabs(caminho):
            # Biblioteca oficial: sem extensão e sem barras → busca em KAA_LIBS
            if not caminho.endswith('.kaa') and '/' not in caminho and '\\' not in caminho:
                caminho = os.path.join(_KAA_LIBS_DIR, f"{caminho}.kaa")
            else:
                caminho = os.path.abspath(caminho)
        mod = self.modules.get(caminho) or self._load_module(caminho)
        if import_all:
            self.globals.update(mod.exports)
        else:
            for n in (k[names_idx] or []):
                self.globals[n] = mod.exports[n]

    def _load_module(self, caminho):
        if caminho in self.loading:
            raise RuntimeError(f"Kaa: importação cíclica detectada: {caminho}")
        with open(caminho, encoding='utf-8') as fh:
            codigo = fh.read()
        from scanner import Scanner
        from parser import Parser
        from compiler import Compiler
        func = Compiler().compile(Parser(Scanner(codigo).escanear()).parse(), caminho)
        globals_salvos = self.globals
        exports_salvos = self._mod_exports
        self.globals   = dict(self.builtins)
        exports        = {}
        self._mod_exports = exports
        self.loading.add(caminho)
        old_dir = os.getcwd()
        os.chdir(os.path.dirname(caminho) or '.')
        try:
            self.run(func)
        finally:
            self.loading.discard(caminho)
            self._mod_exports = exports_salvos
            self.globals      = globals_salvos
            os.chdir(old_dir)
        mod = KaaModule(os.path.basename(caminho), caminho, exports)
        
        for name, val in exports.items():
            if not isinstance(val, ObjClosure) and not callable(val):
                raise RuntimeError(f"Kaa: Erro de importação em '{mod.name}'. Apenas funções podem ser exportadas.")
                
        for name, val in self.globals.items():
            if not isinstance(val, ObjClosure) and name not in self.builtins:
                raise RuntimeError(f"Kaa: Erro em '{mod.name}'. O uso de variáveis globais ('{name}') em bibliotecas não é permitido. Encapsule o estado dentro de funções.")
                
        self.modules[caminho] = mod
        return mod

    def _op_import_python(self, f, c, k):
        code_idx  = k[c[f.ip] | (c[f.ip+1] << 8)]; f.ip += 2
        names_idx = k[c[f.ip] | (c[f.ip+1] << 8)]; f.ip += 2
        import_all = c[f.ip]; f.ip += 1
        env = {}
        exec(code_idx, env)
        if import_all:
            for n, v in env.items():
                if not n.startswith('_'):
                    self.globals[n] = self.builtins[n] = v
        else:
            for n in (names_idx or []):
                self.globals[n] = self.builtins[n] = env[n]
