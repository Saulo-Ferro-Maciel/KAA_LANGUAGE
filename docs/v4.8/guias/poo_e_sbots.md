[⬅️ Voltar para a Enciclopédia](../index.md)
<br>

# Orientação a Objetos: A Arquitetura S-Bot

Diferente do tradicional *Class-based Inheritance* de Java ou C++, Kaa atinge a Orientação a Objetos de forma livre através de **Factory Patterns** baseados em *Closures* (conhecidos internamente como **S-Bots**). S-bots surgiram de quando o criador, Saulo Maciel, era criança e aprendeu a criar bots que imitava-o para resolver atividades escolares.

A flag associada aos S-Bots é a `-obj`.

## Estrutura de um S-Bot

Qualquer método ou dado anexado ao escopo de um dicionário dinâmico retornado por uma função (Factory) converte-se em um S-Bot completo, com comportamento e propriedades intrínsecas:

```kaa
// Fábrica de Inimigos (Ogro)
fun Ogro(nome) {
    // Escopo Base
    var -obj self = {
        "vida": 200,
        "dano": 30,
        "nome": nome
    };
    
    // Comportamento
    fun gritar() {
        print self.nome, "ESTA FURIOSO!!";
    }
    
    // Injeção de método no objeto e devolução do S-Bot
    self.gritar = gritar; 
    return self;
}

// Inicializando instâncias independentes
var -obj chefe = Ogro("Gromm");
var -obj lacaio = Ogro("Dorg");

// Mutação direta e despacho
chefe.vida = 999;     
chefe.gritar();       
```

## O Despachante Híbrido

O acesso de atributos nos S-Bots de Kaa (`var -obj`) funciona de forma incrivelmente flexível e ágil:

> [!TIP]
> O que é declarado via String como uma chave de dicionário (`"vida": 200`) é perfeitamente captado pela notação de propriedade de pontos! O motor Cython mapeia a chamada genérica de `.vida` da estrutura para as chaves internas `["vida"]`, garantindo velocidade nativa C-Bound e elegância sintática ao desenvolvedor.

Os S-Bots, atrelados com as recém implementadas regras de **Strict Scope** das funções em Kaa, garantem um encapsulamento total, evitando conflitos de memória externa e protegendo a integridade das entidades dos seus jogos ou utilitários.
