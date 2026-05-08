import kaa
from scanner import Scanner
from parser import Parser

with open("Códigos em Kaa/Exemplos/test_math.kaa", "r", encoding="utf-8") as f:
    code = f.read()

tokens = Scanner(code).escanear()
ast = Parser(tokens).parse()
comp = kaa.Compiler()
func = comp.compile(ast, "test_math.kaa")

print("Main Bytecode:")
for b in func.chunk.code:
    print(b, end=" ")
print()
