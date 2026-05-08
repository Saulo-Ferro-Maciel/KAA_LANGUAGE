import debugpy
import sys
import kaa

# Start debugging
print("Waiting for debugger...")
debugpy.listen(('127.0.0.1', 5679))
debugpy.wait_for_client()

print("Debugger connected! Running script...")
k = kaa.Kaa()
k.run_file("Códigos em Kaa/Exemplos/calculador.kaa")
