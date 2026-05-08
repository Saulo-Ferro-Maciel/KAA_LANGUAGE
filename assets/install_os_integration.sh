#!/bin/bash
# install_os_integration.sh
# Script para instalar a integração do Kaa com o Sistema Operacional e IDEs

set -e

echo "======================================"
echo " Instalando Integração OS para Kaa"
echo "======================================"

# Obter o diretório atual do script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

MIME_DIR="$HOME/.local/share/mime/packages"
ICON_DIR="$HOME/.local/share/icons/hicolor"

echo "[1/4] Criando diretórios necessários..."
mkdir -p "$MIME_DIR"
# Criar diretórios para os tamanhos de ícone mais comuns
mkdir -p "$ICON_DIR/128x128/mimetypes"
mkdir -p "$ICON_DIR/256x256/mimetypes"
mkdir -p "$ICON_DIR/512x512/mimetypes"

echo "[2/4] Copiando definições MIME..."
cp "$DIR/kaa.xml" "$MIME_DIR/kaa.xml"

echo "[3/4] Copiando ícone oficial do Kaa..."
# Distribuir o ícone original nas pastas (o SO escala automaticamente quando necessário,
# mas fornecer os arquivos previne bugs em alguns File Managers)
cp "$DIR/icons/kaa_1024x1024.png" "$ICON_DIR/128x128/mimetypes/text-x-kaa.png"
cp "$DIR/icons/kaa_1024x1024.png" "$ICON_DIR/256x256/mimetypes/text-x-kaa.png"
cp "$DIR/icons/kaa_1024x1024.png" "$ICON_DIR/512x512/mimetypes/text-x-kaa.png"

echo "[4/4] Atualizando caches do sistema..."
update-mime-database "$HOME/.local/share/mime"
gtk-update-icon-cache -f -t "$ICON_DIR"

echo "======================================"
echo " Instalação concluída com sucesso!"
echo " - Talvez seja necessário fechar/abrir sua IDE (VSCode) ou reiniciar o gerenciador de arquivos (ex: nautilus -q)."
echo "======================================"
