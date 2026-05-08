[⬅️ Voltar para a Enciclopédia](../index.md)
<br>

# Enciclopédia Kaa (v4.6)

> **Simples. Tipada. Poderosa. C-Bound JIT.**
>
> Um compêndio completo da linguagem Kaa, do funcionamento interno do seu compilador JIT em C-Bound Cython até a sua elegante sintaxe.

---

## 1. Visão Geral

Kaa evoluiu de um interpretador Python em árvore (Tree-Walk) para uma poderosa **Máquina Virtual (VM) Compilada**. Hoje, o ciclo principal da VM é compilado em binários nativos de C (`vm.so`) usando Cython. A versão 4.7 introduz o **Strict Scope**, impedindo inconsistências de memória ao isolar variáveis globais de dentro das funções, e o método nativo de validação **is_num**.

## 2. Tipagem e Variáveis

Kaa possui um controle estrito de **Tipagem Explícita**. Nenhuma variável existe sem sua flag de tipo correspondente:

| Tipo | Flag | Exemplo de Declaração | Descrição |
|------|------|-----------------------|-----------|
| Inteiro | `-i` | `var -i x = 10;` | Matemática exata. |
| Flutuante | `-f` | `var -f y = 3.14;` | Alta precisão (suporta `.f_valuation`). |
| String | `-s` | `var -s desc = "Olá";`| Cadeias de texto. |
| Booleano | `-T` / `-F` | `var -T atv = -T;` | Verdadeiro (`-T`) ou Falso (`-F`). Não existe `true`/`false` puro, nem negação com `not` (usamos `!`). |
| Lista | `-l` | `var -l lst = [1, 2];` | Arrays auto-redimensionáveis. |
| Tupla | `-t` | `var -t tup = (1, 2);` | Listas imutáveis. |
| Dicionário| `-d` | `var -d dic = {"x": 1};`| Mapeamento de chave-valor. |
| S-Bot | `-obj`| `var -obj bot = {};` | Entidade orientada a objetos livre. |

> **Coerção Dinâmica:** Quando a linguagem Kaa capta um Input do terminal para uma variável tipada, ela tenta realizar um *Casting* instintivo. Ou seja, se o usuário digitar "5" para uma variável `-i`, ela vira o inteiro `5` internamente sem causar crashs matemáticos.

## 3. Sintaxe Essencial

### Condicionais e Laços

A linguagem adota o paradigma tradicional (semelhante ao C/Java/JS):
```kaa
if (x > 10) { print "Maior"; } else { print "Menor"; }

for (var -i x = 0; x < 10; x = x + 1) { print x; }

while (x != 0) { x = x - 1; }
```

### Operadores de Contenção (`in` e `!in`)

Para checar existência dentro de coleções (listas, dicionários, tuplas), Kaa possui operadores nativos altamente otimizados:
```kaa
var -l operacao = ["+", "-", "*", "/"];

// Verifica contenção
if ("+" in operacao) { print "É uma operação válida!"; }

// Oposto da contenção
if ("x" !in operacao) { print "Operador desconhecido!"; }
```
Estes substituem cadeias longas de `and`/`or` com verificações atômicas diretas no C-Bound.

### Funções e Restrição de Escopo (Strict Scope)

Na v4.7, Kaa implementa o **Strict Scope**. Funções não podem acessar ou modificar variáveis globais diretamente. Isso evita inconsistências em loops e mantém S-Bots isolados.

```kaa
var -s global_x = "teste";

fun somar(a, b) {
    // print global_x; // ERRO: Acesso a global não permitido!
    var -f resultado = a + b;
    return resultado;
}
```
**Dica:** Sempre passe variáveis externas como parâmetros para a função.

### Entradas e Saídas
```kaa
print "Meu texto", var1, var2;
input "Digite um número: " >> var1;
```
> O input suporta direcionamento atômico nativo direto `>>` que acopla a variável sem necessidade de `var = input(...)`.

## 4. Coleções e Métodos Nativos de Memória

A linguagem evitou injetar milhares de métodos atrelados para manter a leveza. Apenas os de alta necessidade sobrevivem:

- **`.length`**: Retorna a contagem exata e dinâmica do tamanho da coleção. Em números, retorna 0.
- **`.is_num`**: Retorna `-T` se a variável for um número (`-i` ou `-f`) e `-F` caso contrário. Útil para validar inputs.
- **`.keys()`**: Extrai e empilha as chaves de um dicionário (`-d`) como uma Lista (`-l`).
- **`.f_valuation(casas)`**: Limpa flutuantes, arredondando matemática binária truncada (`3.140000000001` -> `3.14`). Pode receber um parâmetro indicando o número de casas, e sem parâmetros o padrão é 2.
- **`.rm_nil()`**: Varre listas, dicionários e tuplas em velocidade Cython removendo *espaços vazios* (`nil`), comprimindo a lista e liberando fragmentos de memória.

## 5. Orientação a Objetos (S-Bots)

A Kaa atinge a Orientação a Objetos de modo livre através de *Factory Patterns* assíncronas. Qualquer método anexado a um escopo vira comportamento nativo do Objeto:

```kaa
fun Ogro(nome) {
    var -obj self = {
        "vida": 200,
        "dano": 30,
        "nome": nome
    };
    
    fun gritar() {
        print self.nome, "ESTA FURIOSO!!";
    }
    
    self.gritar = gritar; 
    return self;
}

var -obj chefe = Ogro("Gromm");
chefe.vida = 999;     // Mutação Direta de Propriedade
chefe.gritar();       // Chamada do Método Atrelado ao Closure
```
> O acesso de atributos funciona de forma mista: O que é declarado via "String" é perfeitamente captado pelo despachante de propriedades (`chefe.vida` mapeia para `chefe["vida"]` internamente em velocidade C).

## 6. S-Bots, Importações e Destruição de Arenas (GC Manual)

### Interoperabilidade (Módulos)
Kaa permite que você "roube" módulos Python e bibliotecas Kaa livremente:
```kaa
add -py "import math";
print math.sqrt(16);

add "./biblioteca.kaa" -> foo, bar;
add "./biblioteca.kaa" all;
```
Para exportar funções num módulo nativo Kaa para que outro leia:
```kaa
expor foo, bar; // ou: expor all;
```

### Arenas (O Gerenciador Opcional de Memória)
Importar arquivos não enche a memória permanentemente. O compilador injeta "Arenas" invisíveis em cada módulo Kaa (`add`).
Caso termine as execuções de determinado módulo, pode destruí-lo sumariamente liberando C-RAM e Ponteiros, uma exclusão manual cirúrgica:
```kaa
var -i limpos = destroy_arena("biblioteca");
```
Pode-se checar o estado da memória imprimindo a rotina global: `arenas_info();`.

## 7. Performance: O Salto do Cython e Peephole JIT

Kaa v4.7 processa instruções num `Dispatch Loop` estritamente tipado (C-Bound). Os *Opcodes* (`ADD_INT`, `MUL_FLOAT`, etc) ignoram sobrecargas de Python (`__add__`) quando as variáveis têm os tipos mapeados. 

O motor de **Peephole JIT** colapsa em memória as instruções de incremento em for-loops (`x = x + 1`) e em `while`, transformando em super-instruções que cortam em 5x o tempo de saltos na matriz de execução.

### Benchmark Oficial (v4.7 vs Python 3)

| Algoritmo | Kaa v4.7 (Cython VM) | CPython 3 | Razão |
| :--- | :--- | :--- | :--- |
| Loop Aritmético (50k) | ~92.1 ms | ~7.1 ms | 12.9x mais lento |
| Fatorial Recursivo Simulado (2k) | ~42.6 ms | ~1.7 ms | 25.1x mais lento |
| Fibonacci (fib25 iterativo - 1k) | ~56.6 ms | ~1.2 ms | 47.1x mais lento |
| MDC (1k) | ~12.2 ms | ~0.25 ms | 48.8x mais lento |
| Acesso e Mutação em Lista (10k)| ~24.6 ms | ~1.9 ms | 12.9x mais lento |
| Teste Num. Primos Isolados (500)| ~46.9 ms | ~2.3 ms | 20.4x mais lento |

*O tempo médio consolidado demonstra que Kaa opera numa janela geral **~27x mais lenta** que o interpretador ultracomplexo e multiparalelizado do CPython. Este é um trade-off planejado: Em troca de velocidade C 100% pura, Kaa preserva total acoplagem de memória aos objetos Python (via `add -py`), sendo uma ponte interpretativa ágil onde C-Bound coexiste com Py-Models.*
