[⬅️ Início](index.md)
<br>

# Download e Instalação

A linguagem Kaa é distribuída como um pacote auto-contido para Linux (x86_64), garantindo que você tenha todas as dependências, incluindo um ambiente Python portátil otimizado para a nossa VM Cython.

## 📦 Versão Atual: v5.0.1 (Stable)

| Componente | Link de Download | Plataforma |
| :--- | :--- | :--- |
| **Kaa Installer** | [kaa-installer-linux-x86_64.tar.gz](downloads/kaa-installer-linux-x86_64.tar.gz) | Linux x86_64 |

---

## 🛠️ Como Instalar

Siga os passos abaixo para instalar a Kaa no seu sistema Linux:

1. **Extraia o pacote**:
   ```bash
   tar -xzf kaa-installer-linux-x86_64.tar.gz
   cd kaa-release
   ```

2. **Execute o script de instalação**:
   ```bash
   chmod +x build_release.sh
   ./build_release.sh --install
   ```
   > [!IMPORTANT]
   > O instalador solicitará permissão de `sudo` para configurar o link simbólico em `/usr/local/bin/kaa` e configurar a biblioteca em `/opt/kaa`.

3. **Verifique a instalação**:
   ```bash
   kaa --version
   ```

---

## 🧩 Extensão para VS Code

Para uma melhor experiência de desenvolvimento, recomendamos instalar a nossa extensão oficial que oferece realce de sintaxe e auto-complete inteligente.

* **Baixar VSIX:** [Kaa VS Code Extension](downloads/kaa-extension.vsix)
* **Como instalar:** No VS Code, vá em `Extensions` > `...` > `Install from VSIX`.

---

## 🚀 Próximos Passos
Agora que você tem a Kaa instalada, que tal começar pelo [Guia de Tipagem e Variáveis](guias/tipos_e_variaveis.md)?
