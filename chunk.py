class LineInfo:
    def __init__(self):
        self.offsets = []
        self.lines = []

    def add(self, offset, line):
        self.offsets.append(offset)
        self.lines.append(line)

    def get_line(self, offset):
        if not self.offsets:
            return 0
        result = self.lines[0]
        for i, off in enumerate(self.offsets):
            if off <= offset:
                result = self.lines[i]
        return result


class Chunk:
    def __init__(self, name="<module>"):
        self.code = bytearray()
        self.constants = []
        self.lines = LineInfo()
        self.name = name
        self._jitted = False

    def emit_byte(self, byte, line):
        self.code.append(byte)
        self.lines.add(len(self.code) - 1, line)

    def emit_op(self, op, line):
        self.emit_byte(op, line)

    def emit_int16(self, val, line):
        self.emit_byte(val & 0xFF, line)
        self.emit_byte((val >> 8) & 0xFF, line)

    def emit_int32(self, val, line):
        self.emit_byte(val & 0xFF, line)
        self.emit_byte((val >> 8) & 0xFF, line)
        self.emit_byte((val >> 16) & 0xFF, line)
        self.emit_byte((val >> 24) & 0xFF, line)

    def emit_constant(self, value, line):
        idx = len(self.constants)
        self.constants.append(value)
        self.emit_op(0, line)
        self.emit_byte(idx, line)
        return idx

    def patch_jump(self, offset, target):
        relative = target - (offset + 3)
        self.code[offset] = relative & 0xFF
        self.code[offset + 1] = (relative >> 8) & 0xFF

    def __len__(self):
        return len(self.code)


class ObjFunction:
    def __init__(self, arity=0, chunk=None, name=""):
        self.arity = arity
        self.chunk = chunk
        self.name = name
        self.upvalue_names = []
        self.upvalue_count = 0

    def __len__(self):
        return len(self.chunk) if self.chunk else 0


class ObjClosure:
    def __init__(self, function=None, upvalues=None, module_globals=None):
        self.function = function
        self.upvalues = upvalues or []
        self.module_globals = module_globals

    def __repr__(self):
        return f"<closure {self.function.name}>"

    def chamar(self, vm, args):
        return vm._call_obj_closure(self, args)
