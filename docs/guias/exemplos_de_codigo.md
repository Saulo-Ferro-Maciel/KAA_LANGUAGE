# Exemplos de Código

A melhor maneira de aprender uma linguagem é analisando códigos reais. Separamos aqui os 3 melhores exemplos presentes no repositório do projeto, demonstrando desde integrações com as bibliotecas padrões até manipulações de Orientação a Objetos (S-Bots).

---

## 1. Jogo de RPG (POO, Loops e Imports)
Este código demonstra o poder da modularidade da Kaa. Ele importa diferentes scripts como componentes do jogo, cria um "S-Bot" (Factory Pattern) para representar o Player, usa a biblioteca `random` e gerencia o estado da partida manipulando elementos dentro de listas.

```kaa
add "./RPG/levels.kaa" all;
add "./RPG/statusRPG.kaa" all;
add "./RPG/sai.kaa" all;
add "./RPG/player.kaa" all;
add "random" all;
add "time" all;

var -T control;
var -i level = 1;
var -l inimigos = levels(level);
var -obj player = player("Saulo", 100, 50, "Humano");

while(control == -T){
 status_inimigos(inimigos); 
 player.ataque(inimigos);
 inimigos = inimigos.rm_nil();

 if(inimigos.length > 0){
   var -i inimigo_ataque = randint(0,inimigos.length);
   player.perde_vida(inimigos[inimigo_ataque].ataque, inimigos[inimigo_ataque].nome);
 }
 sleep(2);
 status_player(player);

 if(inimigos.length == 0){
   print "";
   print "Parabens, voce passou de fase!!";
   level = level + 1;
   inimigos = levels(level);
   if(inimigos == nil){
     print "Você venceu o jogo!";
     control = -F;
   }
 }

 control = sai();
}
```

---

## 2. Cara ou Coroa e Probabilidade (Dicionários e Math Lib)
Um teste prático de aleatoriedade usando a `random` e cálculos com a `math`. Destaca a criação de Dicionários para contagem, a iteração usando `.keys` e o uso de funções matemáticas complexas como fatorial direto no código.

```kaa
// Teste de aleatoriedade e probabilidade
add "math" all;
add "random" all;

var -i moeda;
var -T controle;
var -d resultado;
var -i arremeco;

fun exibe(resultado, arremeco){
    var -l chaves = resultado.keys;
    var -s texto = "";
    var -f porc;
    for(var -i i=0; i<chaves.length; i=i+1){
        porc = (resultado[chaves[i]] * 100) / arremeco;
        texto = texto + chaves[i] + ": " + resultado[chaves[i]] + " (" + porc + "%) | ";
    }
    print texto;
    if(arremeco <= 15){
        print "--- Probabilidades Teoricas (Eventos Futuros) ---";
        var -i total_eventos = power(2, arremeco);
        var -i comb;
        var -f prob;
        for(var -i k=0; k<=arremeco; k=k+1){
            comb = factorial(arremeco) / (factorial(k) * factorial(arremeco - k));
            prob = (comb * 100.0) / total_eventos;
            print k, " impar (e ", arremeco - k, " par): ", prob.f_valuation, "%";
        }
    }
}

while(controle != -F){
    resultado = {"impar":0, "par":0};
    while(arremeco.is_num != -T or arremeco < 1){ input "Digite quantos arremessos: " >> arremeco; }
    
    var -i local_par = 0;
    var -i local_impar = 0;
    for(var -i i=0; i<arremeco; i=i+1){
        moeda = randint(0,1);
        if(moeda == 0){ local_par = local_par + 1; }
        else{ local_impar = local_impar + 1; }
    }
    resultado["par"] = local_par;
    resultado["impar"] = local_impar;
    exibe(resultado, arremeco);
}
```

---

## 3. Cronômetro Interativo (Input e Strings)
Um código simples que exibe como obter dados do usuário via prompt de `input`, fazer checagem flexível via `.is_num`, modificar a resposta usando o novo método `.lower_letters()`, e cronometrar um contador na tela com a biblioteca `time`.

```kaa
// Cronometer for push up
add "time" -> count;

var -f minutes;
var -T control;

fun exit(){
    var -s sair;
    print "";
    while(sair!="s" and sair!="n"){ 
        input "Deseja sair? [s/n] " >> sair; 
        sair = sair.lower_letters(); 
    }
    if(sair == "s"){ return -F; } else { return -T; }
}

while(control != -F){
    while (minutes.is_num != -T) { input "Quantos minutos devo cronometrar? " >> minutes; }
    if (0 <= minutes <= 60) { minutes = minutes * 60; }
    
    count(minutes.f_valuation); 
    minutes = nil;
    control = exit();
}
```
