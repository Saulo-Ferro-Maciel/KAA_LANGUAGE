import sys

with open('/home/saulo_ferro/.Kaa/vm.pyx', 'r') as f:
    content = f.read()

old_block = """        for name, val in exports.items():
            if not isinstance(val, ObjClosure):
                raise RuntimeError(f"Kaa: Erro de importação em '{mod.name}'. Apenas funções podem ser exportadas.")"""

new_block = """        for name, val in exports.items():
            if not isinstance(val, ObjClosure) and not callable(val):
                raise RuntimeError(f"Kaa: Erro de importação em '{mod.name}'. Apenas funções podem ser exportadas.")"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('/home/saulo_ferro/.Kaa/vm.pyx', 'w') as f:
        f.write(content)
    print("vm.pyx updated.")
else:
    print("Could not find the block in vm.pyx")
