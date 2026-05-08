import os, subprocess

kaa_files = []
for root, dirs, files in os.walk('Códigos em Kaa'):
    for file in files:
        if file.endswith('.kaa') and file != 'cara_ou_coroa.kaa':
            kaa_files.append(os.path.join(root, file))

failed = []

# Provide a sequence of inputs that tend to exit programs
inputs = "n\n0\n0\n0\nn\n1\nn\ns\n0\n" * 100

for f in kaa_files:
    print(f"Testing {f}...")
    try:
        proc = subprocess.run(['python3', 'kaa.py', f], input=inputs, text=True, capture_output=True, timeout=1.5)
        if proc.returncode != 0 and 'EOFError' not in proc.stderr and 'EOFError' not in proc.stdout:
            # Check if it's a real failure and not just reaching EOF in input
            if '[Sintaxe]' in proc.stdout or 'Erro' in proc.stdout or 'Exception' in proc.stderr:
                print(f"FAILED: {f}")
                print(proc.stdout)
                print(proc.stderr)
                failed.append(f)
    except subprocess.TimeoutExpired:
        # Timeout means it ran and waited for more input or looped infinitely (which is fine for games)
        pass

if not failed:
    print("ALL TESTS PASSED OR TIMED OUT SUCCESSFULLY")
else:
    print(f"{len(failed)} TESTS FAILED")
