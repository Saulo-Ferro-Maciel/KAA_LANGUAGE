[⬅️ Voltar para a Enciclopédia](../index.md)
<br>

# Tipagem e Variáveis

Kaa possui um controle estrito de **Tipagem Explícita**. Nenhuma variável existe sem sua flag de tipo correspondente. Este sistema garante alta performance, eliminando grande parte das validações dinâmicas necessárias em tempo de execução no nível do Cython.

## Tabela de Tipos

| Tipo | Flag | Exemplo de Declaração | Descrição |
|------|------|-----------------------|-----------|
| Inteiro | `-i` | `var -i x = 10;` | Matemática exata. Alta velocidade. |
| Flutuante | `-f` | `var -f y = 3.14;` | Alta precisão (suporta nativamente limpeza binária via `.f_valuation`). |
| String | `-s` | `var -s desc = "Olá";`| Cadeias de texto com semântica UTF. |
| Booleano | `-T` / `-F` | `var -T atv = -T;` `var -F atv = -F;` | Verdadeiro (`-T`) ou Falso (`-F`). Não existe `true`/`false` puro, nem negação com `not` (usamos `!`). |
| Lista | `-l` | `var -l lst = [1, 2];` | Arrays auto-redimensionáveis e dinâmicos. |
| Tupla | `-t` | `var -t tup = (1, 2);` | Coleções/Listas imutáveis de tamanho fixo. |
| Dicionário| `-d` | `var -d dic = {"x": 1};`| Mapeamento estruturado de chave-valor. |
| S-Bot | `-obj`| `var -obj bot = {};` | Entidade orientada a objetos livre. |

> [!TIP]
> **Coerção Dinâmica Intuitiva:** Quando a linguagem Kaa capta um Input do terminal para uma variável tipada, ela tenta realizar um *Casting* instintivo. Ou seja, se o usuário digitar `"5"` no prompt, e a variável de destino for `-i`, o Kaa a converte de string para o inteiro `5` internamente sem causar crashs matemáticos, permitindo inputs seguros e simplificados.
