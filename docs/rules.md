# Regras de Organização do Projeto Kaa

Este documento estabelece as regras fundamentais para a manutenção e organização dos arquivos e diretórios do projeto da linguagem Kaa.

## 1. Preservação de Dados e Histórico

**NUNCA remova ou exclua arquivos de dados, códigos antigos ou literaturas desatualizadas do projeto principal.**

A linguagem Kaa está em constante evolução, e manter o histórico de como as coisas funcionavam ou foram desenhadas em versões anteriores é crucial para o desenvolvimento futuro, depuração e referência.

## 2. Versionamento de Literatura e Dados

Em vez de excluir, **mova os dados e arquivos antigos para as pastas de versão correspondentes dentro do diretório `LITERATURE`**.

- Sempre que uma nova versão da linguagem for lançada ou houver uma reestruturação significativa, crie uma pasta para a versão antiga (ex: `LITERATURE/v4.0/`, `LITERATURE/v4.5/`).
- Mova os documentos, exemplos antigos e dados que pertenciam àquela versão para dentro dessa pasta específica.
- Isso garante que a documentação atual na raiz de `LITERATURE` (como a `Enciclopedia_Kaa.md`) reflita sempre a versão mais recente, enquanto o histórico permanece intacto e organizado.

## 3. Estrutura Limpa

- **Raiz do Projeto:** Mantenha apenas os arquivos essenciais para a execução e compilação da linguagem (ex: `.py`, `.c`, `.pyx`, `.md` principal).
- **Códigos em Kaa:** Use a pasta `Códigos em Kaa` para todos os exemplos, testes práticos e programas desenvolvidos em Kaa.
- **Libs:** Mantenha a pasta `libs` organizada por módulos para facilitar as importações no sistema.

Seguindo estas regras, garantimos que o projeto Kaa cresça de forma sustentável e documentada!
