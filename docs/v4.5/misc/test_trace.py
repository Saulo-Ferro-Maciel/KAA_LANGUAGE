import kaa
from pprint import pprint

with open("Códigos em Kaa/Exemplos/test_math.kaa", "r", encoding="utf-8") as f:
    code = f.read()

vm = kaa.Kaa()
try:
    vm.run(code)
except Exception:
    pass

for k, v in vm.vm.globals.items():
    if getattr(v, "function", None):
        if v.function.name == "factorial":
            print("Factorial Bytecode:")
            for b in v.function.chunk.code:
                print(b, end=" ")
            print()
