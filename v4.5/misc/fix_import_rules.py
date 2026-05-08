import sys

with open('/home/saulo_ferro/.Kaa/vm.pyx', 'r') as f:
    content = f.read()

# We need to find _load_module and add the checks at the end before returning mod
old_block = """        mod = KaaModule(os.path.basename(caminho), caminho, exports)
        self.modules[caminho] = mod
        return mod"""

new_block = """        mod = KaaModule(os.path.basename(caminho), caminho, exports)
        
        for name, val in exports.items():
            if not isinstance(val, ObjClosure):
                raise RuntimeError(f"Kaa: Erro de importação em '{mod.name}'. Apenas funções podem ser exportadas.")
                
        for name, val in self.globals.items():
            if not isinstance(val, ObjClosure) and name not in self.builtins:
                raise RuntimeError(f"Kaa: Erro em '{mod.name}'. O uso de variáveis globais ('{name}') em bibliotecas não é permitido. Encapsule o estado dentro de funções.")
                
        self.modules[caminho] = mod
        return mod"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('/home/saulo_ferro/.Kaa/vm.pyx', 'w') as f:
        f.write(content)
    print("vm.pyx updated.")
else:
    print("Could not find the block in vm.pyx")
