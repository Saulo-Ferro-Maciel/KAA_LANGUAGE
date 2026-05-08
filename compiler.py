"""
Kaa Compiler v4.7 — AST → Bytecode
=====================================
Corrigido:
- Estado de compilação por função (CompilerContext) — sem slot collision
- compile_assignment trata Token e Variavel
- compile_import / compile_expon emitem opcodes reais
- compile_while com JUMP_BACK signed-int16 correto
- compile_fun_decl isola locals/scope_depth por função
"""

from vm_opcodes import Opcode, FunctionKind
from chunk import Chunk, ObjFunction, ObjClosure
from tipos_token import TipoToken


# ─── Contexto de Compilação ───────────────────────────────────────────────────

class CompilerContext:
    """
    Estado de compilação para UMA função.
    O Compiler mantém uma pilha desses contextos — um por função ativa.
    Isso garante que locals/scope_depth de funções internas não poluem as externas.
    """
    def __init__(self, name="<module>", arity=0, parent=None):
        self.chunk       = Chunk(name=name)
        self.locals      = []   # [{'name', 'slot', 'depth'}]
        self.upvalues    = []   # [{'name', 'is_local', 'index'}]
        self.scope_depth = 0
        self.name        = name
        self.arity       = arity
        self.parent      = parent

    def resolve_local(self, name):
        """Retorna slot da variável local mais recente com esse nome, ou None."""
        for local in reversed(self.locals):
            if local['name'] == name and local['depth'] <= self.scope_depth:
                return local['slot']
        return None

    def get_local_type(self, name):
        """Retorna o tipo da variável local mais recente com esse nome, ou None."""
        for local in reversed(self.locals):
            if local['name'] == name and local['depth'] <= self.scope_depth:
                return local.get('tipo')
        return None

    def begin_scope(self):
        self.scope_depth += 1

    def end_scope(self):
        self.scope_depth -= 1
        while self.locals and self.locals[-1]['depth'] > self.scope_depth:
            self.locals.pop()

    def add_local(self, name, tipo=None):
        slot = len(self.locals)
        self.locals.append({'name': name, 'slot': slot, 'depth': self.scope_depth, 'tipo': tipo})
        return slot


# ─── Compiler ────────────────────────────────────────────────────────────────

class Compiler:
    """
    Compila AST para bytecode Kaa.
    Mantém uma pilha de CompilerContext (um por função ativa).
    """

    def __init__(self):
        self._ctx_stack = []   # pilha de CompilerContext
        self._is_call_target = False
        self.builtins = {
            'sleep', 'timestamp', 'time_str', 'date_str', 
            'destroy_arena', 'arenas_info', 'wait_until',
            'randint', 'random', 'range', 'print', '_rs'
        }

    # ── contexto atual ──────────────────────────────────────

    @property
    def ctx(self):
        return self._ctx_stack[-1]

    @property
    def chunk(self):
        return self.ctx.chunk

    def _push_ctx(self, name, arity=0):
        parent = self.ctx if self._ctx_stack else None
        self._ctx_stack.append(CompilerContext(name=name, arity=arity, parent=parent))

    def _pop_ctx(self):
        return self._ctx_stack.pop()

    def resolve_upvalue(self, ctx_idx, name):
        if ctx_idx <= 0: return None
        enclosing = self._ctx_stack[ctx_idx - 1]
        
        for local in reversed(enclosing.locals):
            if local['name'] == name:
                return self.add_upvalue(self._ctx_stack[ctx_idx], name, True, local['slot'])
                
        upvalue_idx = self.resolve_upvalue(ctx_idx - 1, name)
        if upvalue_idx is not None:
            return self.add_upvalue(self._ctx_stack[ctx_idx], name, False, upvalue_idx)
            
        return None

    def add_upvalue(self, ctx, name, is_local, index):
        for i, up in enumerate(ctx.upvalues):
            if up['name'] == name:
                return i
        ctx.upvalues.append({'name': name, 'is_local': is_local, 'index': index})
        return len(ctx.upvalues) - 1

    # ── entrada ─────────────────────────────────────────────

    def compile(self, stmts, name="<module>"):
        """Compila lista de statements para ObjFunction (módulo raiz)."""
        self._push_ctx(name, arity=0)
        for stmt in stmts:
            self.compile_stmt(stmt)
        self.emit_op(Opcode.HALT)
        ctx = self._pop_ctx()
        return ObjFunction(arity=0, chunk=ctx.chunk, name=name)

    # ── emissão ─────────────────────────────────────────────

    def emit_op(self, op, line=1):
        self.chunk.emit_op(int(op), line)

    def emit_byte(self, b, line=1):
        self.chunk.emit_byte(b & 0xFF, line)

    def emit_int16(self, val, line=1):
        # signed: guarda como unsigned 16-bit (complemento de dois)
        uval = val & 0xFFFF
        self.chunk.emit_byte(uval & 0xFF, line)
        self.chunk.emit_byte((uval >> 8) & 0xFF, line)

    def emit_constant(self, value, line=1):
        idx = len(self.chunk.constants)
        self.chunk.constants.append(value)
        self.emit_op(Opcode.LOAD_CONST, line)
        self.emit_byte(idx, line)
        return idx

    def emit_jump(self, op, line=1):
        """Emite jump com placeholder. Retorna pos do primeiro byte do offset."""
        pos = len(self.chunk.code)
        self.emit_op(op, line)
        self.emit_int16(0, line)
        return pos + 1   # posição do low-byte do offset

    def patch_jump(self, offset_pos):
        """Corrige o offset de um forward jump."""
        target   = len(self.chunk.code)
        relative = target - (offset_pos + 2)   # IP estará em offset_pos+2 ao ler o offset
        self.chunk.code[offset_pos]     = relative & 0xFF
        self.chunk.code[offset_pos + 1] = (relative >> 8) & 0xFF

    # ── helpers ─────────────────────────────────────────────

    def _line(self, node):
        if hasattr(node, 'nome') and hasattr(node.nome, 'linha'):
            return node.nome.linha
        if hasattr(node, 'op') and hasattr(node.op, 'linha'):
            return node.op.linha
        if hasattr(node, 'linha'):
            return node.linha
        return 1

    def _add_name_const(self, name):
        """Adiciona string de nome às constantes e retorna o índice."""
        if name in self.chunk.constants:
            return self.chunk.constants.index(name)
        idx = len(self.chunk.constants)
        self.chunk.constants.append(name)
        return idx

    # ═══════════════════════════════════════════════════════
    # STATEMENTS
    # ═══════════════════════════════════════════════════════

    def compile_stmt(self, stmt):
        t = type(stmt).__name__

        if t == 'StmtExpr':
            self.compile_expr(stmt.expr)
            self.emit_op(Opcode.POP, self._line(stmt))

        elif t == 'StmtPrint':
            for expr in stmt.exprs:
                self.compile_expr(expr)
            self.emit_op(Opcode.PRINT, self._line(stmt))
            self.emit_byte(len(stmt.exprs))

        elif t == 'StmtInput':
            prompts = (stmt.prompt.exprs if hasattr(stmt.prompt, 'exprs')
                       else stmt.prompt if isinstance(stmt.prompt, list)
                       else [stmt.prompt])
            for expr in prompts:
                self.compile_expr(expr)
            # Emite lvalue como constante (lido pela VM após INPUT)
            self.compile_lvalue(stmt.alvo)
            self.emit_op(Opcode.INPUT, self._line(stmt))
            self.emit_byte(len(prompts))

        elif t == 'StmtBloco':
            self.ctx.begin_scope()
            for s in stmt.stmts:
                self.compile_stmt(s)
            self.ctx.end_scope()

        elif t == 'DeclVar':
            self.compile_var_decl(stmt)

        elif t == 'DeclFun':
            self.compile_fun_decl(stmt)

        elif t == 'StmtIf':
            self.compile_if(stmt)

        elif t == 'StmtWhile':
            self.compile_while(stmt)

        elif t == 'StmtReturn':
            if stmt.valor:
                self.compile_expr(stmt.valor)
            else:
                self.emit_op(Opcode.LOAD_NIL, self._line(stmt))
            self.emit_op(Opcode.RETURN, self._line(stmt))

        elif t == 'StmtImport':
            self.compile_import(stmt)

        elif t == 'DeclExpon':
            self.compile_expon(stmt)

    # ── if ──────────────────────────────────────────────────

    def compile_if(self, stmt):
        self.compile_expr(stmt.cond)
        j_else = self.emit_jump(Opcode.JUMP_IF_FALSE)
        self.emit_op(Opcode.POP)
        self.compile_stmt(stmt.entao)
        j_end = self.emit_jump(Opcode.JUMP)
        self.patch_jump(j_else)
        self.emit_op(Opcode.POP)
        if stmt.senao:
            self.compile_stmt(stmt.senao)
        self.patch_jump(j_end)

    # ── while ───────────────────────────────────────────────

    def compile_while(self, stmt):
        loop_start = len(self.chunk.code)
        self.compile_expr(stmt.cond)
        j_end = self.emit_jump(Opcode.JUMP_IF_FALSE)
        self.emit_op(Opcode.POP)
        self.compile_stmt(stmt.corpo)

        # JUMP_BACK com offset signed negativo
        # Instrução: opcode(1) + offset_lo(1) + offset_hi(1) = 3 bytes
        # Depois de ler o offset, ip estará em (current_pos + 3)
        # Queremos ip = loop_start  →  offset = loop_start - (current_pos + 3)
        current_pos = len(self.chunk.code)
        offset = loop_start - (current_pos + 3)   # negativo
        self.emit_op(Opcode.JUMP_BACK)
        self.emit_int16(offset)   # emit_int16 faz & 0xFFFF → complemento de dois

        self.patch_jump(j_end)
        self.emit_op(Opcode.POP)

    # ── var ─────────────────────────────────────────────────

    def compile_var_decl(self, stmt):
        line = self._line(stmt)
        tipo = getattr(stmt, 'tipo', None)

        if stmt.inicializador:
            self.compile_expr(stmt.inicializador)
        else:
            if tipo in ('list', '-l'):
                self.emit_op(Opcode.BUILD_LIST, line)
                self.emit_byte(0)
            elif tipo in ('tuple', '-t'):
                self.emit_op(Opcode.BUILD_TUPLE, line)
                self.emit_byte(0)
            elif tipo in ('dict', '-d', 'obj', '-obj'):
                self.emit_op(Opcode.BUILD_DICT, line)
                self.emit_byte(0)
            elif tipo in ('bool_t', '-T'):
                self.emit_op(Opcode.LOAD_TRUE, line)
            elif tipo in ('bool_f', '-F'):
                self.emit_op(Opcode.LOAD_FALSE, line)
            else:
                self.emit_op(Opcode.LOAD_NIL, line)

        if self.ctx.scope_depth == 0 and len(self._ctx_stack) == 1:
            idx = self._add_name_const(stmt.nome.lexema)
            self.emit_op(Opcode.STORE_GLOBAL, line)
            self.emit_byte(idx & 0xFF)
            self.emit_byte((idx >> 8) & 0xFF)
        else:
            slot = self.ctx.add_local(stmt.nome.lexema, tipo)
            self.emit_op(Opcode.STORE_LOCAL, line)
            self.emit_byte(slot)

    # ── fun ─────────────────────────────────────────────────

    def compile_fun_decl(self, stmt):
        """
        Compila declaração de função criando um CompilerContext novo.
        Isola completamente locals/scope_depth da função-pai.
        """
        name      = stmt.nome.lexema
        is_global = (self.ctx.scope_depth == 0)
        line      = self._line(stmt)
        arity     = len(stmt.params)

        # ── Contexto filho ──
        self._push_ctx(name, arity=arity)
        self.ctx.begin_scope()

        # Registra parâmetros como locals (slots 0..arity-1)
        for p in stmt.params:
            self.ctx.add_local(p.lexema)

        # Compila corpo
        for s in stmt.corpo:
            self.compile_stmt(s)

        # Return implícito nil
        self.emit_op(Opcode.LOAD_NIL)
        self.emit_op(Opcode.RETURN)

        self.ctx.end_scope()
        func_ctx = self._pop_ctx()
        # ── Volta ao contexto pai ──

        func_obj = ObjFunction(arity=arity, chunk=func_ctx.chunk, name=name)
        if not hasattr(func_obj, 'upvalue_names'):
            func_obj.upvalue_names = []
        func_obj.upvalue_names = [u['name'] for u in func_ctx.upvalues]
        func_obj.upvalue_count = len(func_ctx.upvalues)

        # Carrega como closure
        const_idx = len(self.chunk.constants)
        self.chunk.constants.append(func_obj)
        self.emit_op(Opcode.CLOSURE, line)
        self.emit_byte(const_idx)
        for up in func_ctx.upvalues:
            self.emit_byte(1 if up['is_local'] else 0)
            self.emit_byte(up['index'])

        # Armazena no escopo correto
        if is_global:
            # STORE_GLOBAL consome o topo da pilha (sem DUP) — a closure não fica solta
            name_idx = self._add_name_const(name)
            self.emit_op(Opcode.STORE_GLOBAL, line)
            self.emit_int16(name_idx)
        else:
            slot = self.ctx.add_local(name, 'function')
            self.emit_op(Opcode.STORE_LOCAL, line)
            self.emit_byte(slot)

    # ── import / export ─────────────────────────────────────

    def compile_import(self, stmt):
        """
        add "path.kaa" all;         → IMPORT_MODULE
        add "path.kaa" -> a, b;     → IMPORT_MODULE (names_list)
        add -py "import math";      → IMPORT_PYTHON
        """
        line = self._line(stmt)

        # Extrair caminho
        caminho_str = (stmt.caminho.valor
                       if hasattr(stmt.caminho, 'valor')
                       else str(stmt.caminho))

        import_all  = 1 if stmt.nomes is None else 0
        names_list  = (None if stmt.nomes is None
                       else [t.lexema for t in stmt.nomes])

        path_idx  = len(self.chunk.constants); self.chunk.constants.append(caminho_str)
        names_idx = len(self.chunk.constants); self.chunk.constants.append(names_list)

        is_py = isinstance(caminho_str, str) and caminho_str.startswith("py:")
        if is_py:
            self.chunk.constants[path_idx] = caminho_str[3:]
            self.emit_op(Opcode.IMPORT_PYTHON, line)
        else:
            self.emit_op(Opcode.IMPORT_MODULE, line)

        self.emit_int16(path_idx)
        self.emit_int16(names_idx)
        self.emit_byte(import_all)

    def compile_expon(self, stmt):
        """expor all;  ou  expor foo, bar;"""
        line = self._line(stmt)
        if stmt.todos:
            self.emit_op(Opcode.EXPORT_ALL, line)
        else:
            for token in stmt.nomes:
                name_idx = self._add_name_const(token.lexema)
                self.emit_op(Opcode.EXPORT_NAME, line)
                self.emit_byte(name_idx)

    # ═══════════════════════════════════════════════════════
    # EXPRESSIONS
    # ═══════════════════════════════════════════════════════

    def compile_expr(self, expr):
        t = type(expr).__name__

        if t == 'Literal':
            v = expr.valor
            if v is None:
                self.emit_op(Opcode.LOAD_NIL, self._line(expr))
            elif v is True:
                self.emit_op(Opcode.LOAD_TRUE, self._line(expr))
            elif v is False:
                self.emit_op(Opcode.LOAD_FALSE, self._line(expr))
            else:
                self.emit_constant(v, self._line(expr))

        elif t == 'Variavel':
            self.compile_var_load(expr)

        elif t == 'Atribuicao':
            self.compile_assignment(expr)

        elif t == 'Binaria':
            self.compile_binary(expr)

        elif t == 'Unaria':
            self.compile_unary(expr)

        elif t == 'Logico':
            self.compile_logical(expr)

        elif t == 'Chamada':
            self.compile_call(expr)

        elif t == 'AcessoIndice':
            self.compile_index_get(expr)

        elif t == 'AcessoAtributo':
            self.compile_attr(expr)

        elif t == 'Agrupamento':
            self.compile_expr(expr.expr)

        elif t == 'Lista':
            for elem in expr.elementos:
                self.compile_expr(elem)
            self.emit_op(Opcode.BUILD_LIST, self._line(expr))
            self.emit_byte(len(expr.elementos))

        elif t == 'Tuplo':
            for elem in expr.elementos:
                self.compile_expr(elem)
            self.emit_op(Opcode.BUILD_TUPLE, self._line(expr))
            self.emit_byte(len(expr.elementos))

        elif t == 'Dicionario':
            for chave, valor in zip(expr.chaves, expr.valores):
                self.compile_expr(chave)
                self.compile_expr(valor)
            self.emit_op(Opcode.BUILD_DICT, self._line(expr))
            self.emit_byte(len(expr.chaves))

    def compile_var_load(self, expr):
        name = expr.nome.lexema
        line = self._line(expr)
        slot = self.ctx.resolve_local(name)
        if slot is not None:
            self.emit_op(Opcode.LOAD_LOCAL, line)
            self.emit_byte(slot)
        else:
            upvalue_idx = self.resolve_upvalue(len(self._ctx_stack) - 1, name)
            if upvalue_idx is not None:
                self.emit_op(Opcode.LOAD_UPVALUE, line)
                self.emit_byte(upvalue_idx)
            else:
                # Restrição de Global em Funções
                if len(self._ctx_stack) > 1 and name not in self.builtins and not self._is_call_target:
                    raise RuntimeError(f"Linha {line}: [Sintaxe] Acesso à variável global '{name}' não permitido dentro de funções. Encapsule como parâmetro ou variável local.")
                
                idx = self._add_name_const(name)
                self.emit_op(Opcode.LOAD_GLOBAL, line)
                self.emit_int16(idx)

    def compile_assignment(self, expr):
        """
        Atribuição: nome pode ser Token, Variavel ou AcessoIndice.
        Deixa o valor na pilha (para uso como expressão).
        """
        name = expr.nome
        line = self._line(expr)
        t    = type(name).__name__

        if t in ('Token', 'Variavel'):
            # Extrai o lexema independente do tipo do nó
            var_name = name.lexema if t == 'Token' else name.nome.lexema
            self.compile_expr(expr.valor)
            slot = self.ctx.resolve_local(var_name)
            if slot is not None:
                self.emit_op(Opcode.DUP, line)
                self.emit_op(Opcode.STORE_LOCAL, line)
                self.emit_byte(slot)
            else:
                upvalue_idx = self.resolve_upvalue(len(self._ctx_stack) - 1, var_name)
                if upvalue_idx is not None:
                    self.emit_op(Opcode.DUP, line)
                    self.emit_op(Opcode.STORE_UPVALUE, line)
                    self.emit_byte(upvalue_idx)
                else:
                    # Restrição de Escrita Global em Funções
                    if len(self._ctx_stack) > 1 and var_name not in self.builtins:
                        raise RuntimeError(f"Linha {line}: [Sintaxe] Atribuição à variável global '{var_name}' não permitido dentro de funções. Use variáveis locais.")
                    
                    idx = self._add_name_const(var_name)
                    self.emit_op(Opcode.DUP, line)
                    self.emit_op(Opcode.STORE_GLOBAL, line)
                    self.emit_int16(idx)

        elif t == 'AcessoIndice':
            # Pilha deve ficar [obj, idx, val] → VM faz val=pop, idx=pop, obj=pop
            self.compile_expr(name.objeto)
            self.compile_expr(name.indice)
            self.compile_expr(expr.valor)
            self.emit_op(Opcode.INDEX_SET, line)

        elif t == 'AcessoAtributo':
            # Ordem para VM: val empilhado antes, obj empilhado depois
            # VM faz: obj = pop(), val = pop()
            self.compile_expr(expr.valor)   # empilha val
            self.compile_expr(name.objeto)  # empilha obj
            attr_name = name.atributo.lexema
            idx = self._add_name_const(attr_name)
            self.emit_op(Opcode.SET_ATTR, line)
            self.emit_byte(idx)

    def compile_binary(self, expr):
        line = self._line(expr)
        op   = expr.op.tipo
        self.compile_expr(expr.esq)
        self.compile_expr(expr.dir)
        
        _MAP = {
            TipoToken.PLUS:       Opcode.ADD,
            TipoToken.MINUS:      Opcode.SUB,
            TipoToken.STAR:       Opcode.MUL,
            TipoToken.SLASH:      Opcode.DIV,
            TipoToken.PERCENT:    Opcode.MOD,
            TipoToken.GREATER:    Opcode.GT,
            TipoToken.GREATER_EQ: Opcode.GTE,
            TipoToken.LESS:       Opcode.LT,
            TipoToken.LESS_EQ:    Opcode.LTE,
            TipoToken.EQ_EQ:      Opcode.EQ,
            TipoToken.BANG_EQ:    Opcode.NE,
            TipoToken.IN:         Opcode.CONTAINS,
            TipoToken.BANG_IN:    Opcode.NOT_CONTAINS,
        }
        
        # Otimização Cython: Emitir Opcodes tipados
        if type(expr.esq).__name__ == 'Variavel':
            var_tipo = self.ctx.get_local_type(expr.esq.nome.lexema)
            if var_tipo in ('int', '-i'):
                if op == TipoToken.PLUS:  self.emit_op(Opcode.ADD_INT, line); return
                if op == TipoToken.MINUS: self.emit_op(Opcode.SUB_INT, line); return
                if op == TipoToken.STAR:  self.emit_op(Opcode.MUL_INT, line); return
            elif var_tipo in ('float', '-f'):
                if op == TipoToken.PLUS:  self.emit_op(Opcode.ADD_FLOAT, line); return
                if op == TipoToken.MINUS: self.emit_op(Opcode.SUB_FLOAT, line); return
                if op == TipoToken.STAR:  self.emit_op(Opcode.MUL_FLOAT, line); return
                
        if op in _MAP:
            self.emit_op(_MAP[op], line)

    def compile_unary(self, expr):
        line = self._line(expr)
        op   = expr.op.tipo if hasattr(expr.op, 'tipo') else expr.op
        self.compile_expr(expr.expr)
        if op == TipoToken.MINUS:
            self.emit_op(Opcode.NEG, line)
        elif op == TipoToken.BANG:
            self.emit_op(Opcode.NOT, line)

    def compile_logical(self, expr):
        """&& e || com curto-circuito."""
        if expr.op.tipo == TipoToken.OR:
            self.compile_expr(expr.esq)
            j = self.emit_jump(Opcode.JUMP_IF_TRUE)
            self.emit_op(Opcode.POP)
            self.compile_expr(expr.dir)
            self.patch_jump(j)
        else:   # AND
            self.compile_expr(expr.esq)
            j = self.emit_jump(Opcode.JUMP_IF_FALSE)
            self.emit_op(Opcode.POP)
            self.compile_expr(expr.dir)
            self.patch_jump(j)

    def compile_call(self, expr):
        chamado = expr.chamado
        line    = self._line(expr)
        # Otimizacao: objeto.metodo(args) → METHOD_CALL (busca + call em 1 opcode)
        if type(chamado).__name__ == 'AcessoAtributo':
            self.compile_expr(chamado.objeto)  # empilha o objeto
            for arg in expr.args:
                self.compile_expr(arg)          # empilha args
            attr_name = chamado.atributo.lexema
            attr_idx  = self._add_name_const(attr_name)
            self.emit_op(Opcode.METHOD_CALL, line)
            self.emit_byte(attr_idx)
            self.emit_byte(len(expr.args))
        else:
            # Rastreia se estamos compilando o alvo de uma chamada (permite LOAD_GLOBAL para funções)
            old_is_call = self._is_call_target
            self._is_call_target = True
            self.compile_expr(chamado)
            self._is_call_target = old_is_call

            for arg in expr.args:
                self.compile_expr(arg)
            self.emit_op(Opcode.CALL, line)
            self.emit_byte(len(expr.args))

    def compile_index_get(self, expr):
        self.compile_expr(expr.objeto)
        self.compile_expr(expr.indice)
        
        # Otimização Cython: Acesso direto em lista se for local conhecido
        if type(expr.objeto).__name__ == 'Variavel':
            var_tipo = self.ctx.get_local_type(expr.objeto.nome.lexema)
            if var_tipo in ('list', '-l'):
                self.emit_op(Opcode.INDEX_LIST, self._line(expr))
                return
                
        self.emit_op(Opcode.INDEX_GET, self._line(expr))

    def compile_attr(self, expr):
        self.compile_expr(expr.objeto)
        attr_name = expr.atributo.lexema
        idx = self._add_name_const(attr_name)
        self.emit_op(Opcode.GET_ATTR, self._line(expr))
        self.emit_byte(idx)

    def compile_lvalue(self, alvo):
        """
        Compila lvalue para INPUT.
        Empilha descritor que _store_lvalue da VM interpreta.
        """
        t = type(alvo).__name__
        if t == 'Variavel':
            name = alvo.nome.lexema
            slot = self.ctx.resolve_local(name)
            if slot is not None:
                self.emit_constant(('local', slot), self._line(alvo))
            else:
                # Restrição de Input Global em Funções
                if len(self._ctx_stack) > 1 and name not in self.builtins:
                    raise RuntimeError(f"Linha {self._line(alvo)}: [Sintaxe] Entrada de dados direta em variável global '{name}' não permitido dentro de funções.")
                self.emit_constant(name, self._line(alvo))
        elif t == 'AcessoIndice':
            self.compile_expr(alvo.objeto)
            self.compile_expr(alvo.indice)
            self.emit_constant('__index__', self._line(alvo))
