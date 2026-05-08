[⬅️ Voltar para a Enciclopédia](../index.md)
<br>

# Performance, JIT e Gerenciamento de Arenas

A linguagem Kaa evoluiu suas entranhas consideravelmente, deixando para trás seu antigo modelo como um interpretador simples em árvore (*Tree-Walk Interpreter*) e abraçando um modelo robusto de Máquina Virtual pré-compilada.

## Cython VM e C-Bound

Hoje, o ciclo principal da VM é compilado em binários nativos de C (`vm.c` > `vm.so`) usando **Cython**. 

A Kaa processa instruções num `Dispatch Loop` estritamente tipado (C-Bound). Na prática, as restrições (`var -i`, `var -l`) permitem que opcodes da linguagem (`ADD_INT`, `MUL_FLOAT`) contornem as sobrecargas generalistas (os famosos `__dunder__` methods) do Python por baixo dos panos, aplicando as lógicas em C puro muito mais rapidamente, assumindo a corretude dos tipos mapeados.

## Peephole JIT

A compilação de Bytecode na Kaa usa uma otimização **Peephole JIT**. Padrões repetitivos e de alto desgaste são identificados em tempo de compilação e fundidos:
* **Incrementos:** Um `x = x + 1` dentro de loops é compactado em *super-instruções* singulares na memória.
* Essa fusão reduz em até 5x o tempo gasto iterando *opcodes* (saltos e procuras no dicionário da VM) resultando numa execução contínua com zero latência em saltos.

## Interoperabilidade e Arenas

Apesar de ser uma VM própria, Kaa possui a habilidade de acessar diretamente o ecossistema CPython subjacente.
```kaa
add -py "import math";
print math.sqrt(16);
```

### O Sistema de Arenas
Para projetos grandes, os módulos nativos Kaa usam "Arenas" invisíveis. Se um módulo `foo` é importado, todo o ambiente e referências dele entram numa nova Arena contígua de memória.
Se ele deixar de ser útil, o programador tem acesso livre para executar um **Coletor de Lixo Cirúrgico (GC Manual)**, poupando RAM brutalmente:
```kaa
add "./biblioteca.kaa" all;
// Processamento pesado...
var -i limpos = destroy_arena("biblioteca");
```
> [!TIP]
> **Destruição Global:** O parâmetro é opcional. Se você chamar apenas `destroy_arena();` (sem argumentos), o Kaa varrerá a memória e destruirá **todas as Arenas importadas** de uma vez, retornando o total de arenas destruídas. Útil para resetar completamente o C-RAM do ambiente.
> [!NOTE]
> Você pode debugar seu ecossistema usando `arenas_info();`, que despeja as trilhas e blocos de memórias ativos no terminal.

## Benchmark Oficial (Kaa v4.7 vs CPython 3)

Como Kaa preserva conexões vitais com a estrutura Py-Models (`add -py`), ela não pode ignorar toda a arquitetura base para atingir a velocidade pura do C. Há um custo na travessia (*Trade-off planejado*). No entanto, o motor C-Bound a mantém extremamente competitiva para uma VM Customizada.

| Algoritmo | Kaa v4.7 (Cython VM) | CPython 3 | Razão de Diferença |
| :--- | :--- | :--- | :--- |
| Loop Aritmético (50k) | ~92.1 ms | ~7.1 ms | 12.9x mais lento |
| Fatorial Recursivo Simulado (2k) | ~42.6 ms | ~1.7 ms | 25.1x mais lento |
| Fibonacci (fib25 iterativo - 1k) | ~56.6 ms | ~1.2 ms | 47.1x mais lento |
| MDC (1k) | ~12.2 ms | ~0.25 ms | 48.8x mais lento |
| Acesso e Mutação em Lista (10k)| ~24.6 ms | ~1.9 ms | 12.9x mais lento |
| Teste Num. Primos Isolados (500)| ~46.9 ms | ~2.3 ms | 20.4x mais lento |

*Conclusão:* Em testes contínuos, Kaa atinge um marco de **~27x a proporção do CPython**. Um projeto de enorme calibre dado a complexidade C++ / multithreading colossal da base CPython. Kaa é uma ponte interpretativa elegante e funcional.
