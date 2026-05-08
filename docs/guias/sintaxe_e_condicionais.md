[⬅️ Voltar para a Enciclopédia](../index.md)
<br>

# Sintaxe Essencial e Condicionais

A linguagem adota um paradigma de formatação estruturado (com escopos delimitados e término de declarações, bem semelhante a linguagens como C, Java e C#), mas com uma simplicidade focada. O uso de ponto-e-vírgula (`;`) como delimitador permite escrever múltiplas instruções na mesma linha sem ambiguidade.

## Condicionais e Laços Clássicos

As condicionais e laços comportam-se de forma tradicional e muito otimizada:
```kaa
// Condicionais
if (x > 10) { print "Maior"; } else { print "Menor"; }

// Laço FOR
for (var -i x = 0; x < 10; x = x + 1) { print x; }

// Laço WHILE
while (x != 0) { x = x - 1; }
```

## Operadores de Contenção (`in` e `!in`)

Para checar existência dentro de coleções (listas, dicionários, tuplas), Kaa possui os operadores atômicos `in` e `!in`, altamente otimizados diretamente no nível do Cython.

```kaa
var -l operacao = ["+", "-", "*", "/"];

// Verifica contenção
if ("+" in operacao) { print "É uma operação válida!"; }

// Oposto da contenção (Exclusivo Kaa)
if ("x" !in operacao) { print "Operador desconhecido!"; }
```
Estes operadores substituem cadeias longas e verbosas de `and`/`or` com verificações extremamente rápidas no C-Bound.

## Entradas e Saídas Direcionais

Em Kaa, o `input` possui um mecanismo atômico nativo usando o direcional `>>`, que injeta a entrada lida diretamente em uma variável existente:
```kaa
print "Bem-vindo ao sistema", usuario, id;
input "Digite um número: " >> meu_numero;
```
> [!NOTE]
> Essa notação direcional dispensa a redundância de `var = input(...)`, conectando organicamente o terminal ao espaço de memória.

## Funções e Strict Scope (Regra de Ouro)

A partir da versão v4.7, Kaa implementa o **Strict Scope** (Escopo Estrito) para máxima segurança e integridade das rotinas. Funções **não** podem acessar, ler ou modificar variáveis do escopo global diretamente. O código deve ser puro e focado na passagem de parâmetros.

```kaa
var -s global_x = "teste";

fun somar(a, b) {
    print global_x; // ERRO FATAL: Acesso a global não permitido pelo compilador!
    var -f resultado = a + b;
    return resultado;
}
```
> [!IMPORTANT]
> Isso evita inconsistências de estado oculto e Memory Leaks e mantém funções / S-Bots perfeitamente encapsulados, forçando o programador a desenhar um código limpo.
