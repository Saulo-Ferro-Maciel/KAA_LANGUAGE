[⬅️ Voltar para a Enciclopédia](../index.md)
<br>

# Coleções e Métodos Nativos de Memória

Para garantir a leveza e velocidade, Kaa evitou injetar milhares de métodos atrelados aos seus tipos abstratos e coleções. Em contrapartida, expôs métodos altamente cirúrgicos que resolvem os maiores gargalos de processamento.

Apenas as rotinas mais otimizadas (e as que demandam intervenção do sistema/C-level) sobrevivem como métodos nativos:

## Propriedades e Utilidades

- **`.length`**: Retorna a contagem exata e dinâmica do tamanho da coleção (lista, tupla ou dicionário). Aplicado em tipos primitivos como números, sempre retorna `0`.
- **`.is_num`**: Retorna `-T` (True) se a variável inspecionada contiver ou for traduzível para um número (`-i` ou `-f`) e `-F` caso contrário. Ferramenta poderosa para validar inputs oriundos do usuário.
- **`.keys`**: Atributo reservado a Dicionários (`-d`). Extrai de maneira instantânea as chaves do dicionário e as devolve empilhadas em uma Lista (`-l`).
- **`.values`**: Semelhante ao `.keys`, este atributo extrai instantaneamente todos os valores do Dicionário (`-d`) e os devolve empilhados em uma Lista (`-l`), permitindo iteração direta e em alta velocidade pelos dados contidos.

## Limpeza Numérica

- **`.f_valuation(casas)`**: Operador especial para Float (`-f`). Durante cálculos de flutuação, conversões binárias podem gerar resíduos (ex: `3.140000000001`). O método `.f_valuation()` limpa a variável arredondando o erro. Se o parâmetro for omitido, o padrão é arredondar mantendo 2 casas decimais precisas.

## O Coletor `.rm_nil` e Compressão C-Bound

- **`.rm_nil`**: Uma das features mais formidáveis para Lists, Tuples e Dicts. Em Kaa, para remover itens, o programador atribui `nil` (Nulo/Vazio) às posições indesejadas. Em seguida, chamando a propriedade `.rm_nil`, o compilador delega ao motor Cython uma varredura atômica de altíssima velocidade. 
  Todos os espaços apontados como nulos são descartados, os ponteiros são realocados internamente, e a coleção retorna comprimida, contínua e sem fragmentos de memória.

> [!WARNING]
> A prática recomendada na linguagem Kaa é o uso de deleção passiva (atribuir nil) seguida da compactação nativa `.rm_nil`, pois evita o recálculo custoso de shifts de array comum em outras linguagens.

## Limpeza Global e Módulos (GC Manual)

Se você está procurando pelas funções globais de manipulação de memória de arquivos importados, como `destroy_arena("modulo")` e a função de debug `arenas_info()`, elas foram movidas para a página focada em arquitetura profunda: **[Performance, JIT e Arenas](./performance_e_jit.md)**. O arquivo atual trata apenas de métodos nativos anexados a coleções individuais.
