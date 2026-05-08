# Bibliotecas Padrões (Standard Libs)

A linguagem Kaa vem acompanhada de algumas bibliotecas oficiais, prontas para serem utilizadas por meio do operador `add`. Esta documentação apresenta um resumo das funcionalidades disponíveis em cada módulo.

Para acessar o auto-completar dinâmico em sua IDE, experimente utilizar a sintaxe `add "modulo" -> `, e a extensão listará exatamente as funções que você pode importar.

---

## Módulo: `time`
**Importação comum:** `add "time" all;` ou `add "time" -> sleep, timestamp;`

A biblioteca `time` gerencia funções relacionadas ao tempo, pausas, e também algumas utilidades essenciais de Garbage Collection.

* `sleep(segundos)` : Pausa a execução do programa pela quantidade de segundos informada.
* `timestamp()` : Retorna o timestamp atual (segundos desde a "epoch").
* `time_str()` : Retorna a hora atual formatada em `"HH:MM:SS"`.
* `date_str()` : Retorna a data atual. Caso não receba argumentos, será formato `"dd/mm/yyyy"`. Aceita padrões (ex: `date_str("yyyy-mm-dd")`).
* `wait_until("HH:MM")` : Pausa a execução até que o relógio atinja a hora específica.
* `count(n)` : Realiza uma contagem do número 1 até `n`, printando o valor a cada 1 segundo (útil para cronômetros).
* `destroy_arena()` e `arenas_info()` : Funções utilitárias atreladas à gestão de Memória via S-Bots para verificação ou limpeza das Arenas importadas.

---

## Módulo: `random`
**Importação comum:** `add "random" all;`

A biblioteca de utilidades pseudo-aleatórias possui um gerador congruencial linear embutido.

* `seed(s)` : Define a semente matemática de inicialização para os próximos cálculos aleatórios.
* `rand()` : Retorna um valor flutuante pseudo-aleatório entre 0 e 1.
* `randint(min, max)` : Retorna um número inteiro aleatório contido no intervalo de `min` a `max`.
* `choice(l)` : Recebe uma lista ou dicionário e escolhe um elemento ao acaso. Se for dicionário, extrai os valores usando as chaves sorteadas.

---

## Módulo: `math`
**Importação comum:** `add "math" all;`

Fornece funções matemáticas de uso geral, dispensando a necessidade de construções complexas ou integrações excessivas via `-py`.

* `calc_mdc(a, b)` : Retorna o Máximo Divisor Comum entre `a` e `b`.
* `calc_mmc(a, b)` : Retorna o Mínimo Múltiplo Comum.
* `factorial(n)` : Retorna o fatorial do número inteiro `n`.
* `percent(v, d)` : Calcula a porcentagem, multiplicando o valor por `d` e dividindo por 100.
* `is_even(n)` / `is_odd(n)` : Retornam `-T` ou `-F` se o número for par ou ímpar, respectivamente.
* `fibon(n)` : Retorna o enésimo número da sequência de Fibonacci.
* `power(b, e)` : Calcula a potência da base `b` elevada ao expoente `e`.
* `square_root(n)` : Aproximação de raiz quadrada.
* `abs_val(n)` : Retorna o valor absoluto de `n`.
* `is_prime(n)` : Avalia se o número `n` é primo.
* `sum_upto(n)` : Soma todos os inteiros de 1 até `n`.
* `list_avg(l)` / `list_max(l)` / `list_min(l)` : Funções para obter, respectivamente, a média, o maior elemento, ou o menor elemento de uma lista numérica.
* `round_val(x)` : Arredonda o valor decimal `x` para o inteiro mais próximo.
* `sine(x)` / `cosine(x)` / `tangent(x)` : Funções trigonométricas (seno, cosseno e tangente) calculadas com até 5000 iterações em série.
* `log(x)` / `log10(x)` : Retorna o logaritmo natural e o logaritmo na base 10.
