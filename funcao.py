"""
Objetos que representam funções Kaa no interpretador.

PyloxFuncao  → função definida pelo utilizador em Kaa.
                Captura o ambiente de definição (closure) no __init__.
                Quando chamada, cria um novo ambiente filho do closure
                e executa o corpo lá dentro.

RetornoException → exceção especial usada para implementar 'return'.
                Não é um erro — é o mecanismo para "desenrolar" a pilha
                de calls até ao Chamada que apanha e devolve o valor.
"""

from ambiente import Ambiente


class PyloxFuncao:
    """
    Função definida pelo utilizador em Kaa.
    Closure: o Ambiente no momento em que a função foi definida.
             Permite que funções capturem variáveis do scope externo.
    """

    def __init__(self, declaracao, closure):
        self.declaracao = declaracao   # nó DeclFun do AST
        self.closure    = closure       # Ambiente capturado ( enclosing do def )

    def chamar(self, interpretador, args):
        """
        Executa o corpo da função.
        1. Cria ambiente filho do closure (não do ambiente atual!).
           Isso é o que torna closures corretas: o closure é a raiz, não o caller.
        2. Regista os parâmetros com os argumentos passados.
        3. Executa o bloco da função.
        4. Se houver 'return', RetornoException é apanhado e o valor devolvido.
        5. Se não houver return, devolve None.
        """
        env = Ambiente(enclosing=self.closure)
        for param, arg in zip(self.declaracao.params, args):
            env.definir(param.lexema, arg)
        try:
            interpretador.executar_bloco(self.declaracao.corpo, env)
        except RetornoException as ret:
            return ret.valor
        return None

    def aridade(self):
        """Número de parâmetros que a função espera."""
        return len(self.declaracao.params)

    def __repr__(self):
        return f'<fun {self.declaracao.nome.lexema}>'


class RetornoException(Exception):
    """
    Exceção de controlo: não indica erro, apenas o valor de return.
    É levantada em visitar_StmtReturn e apanhada em PyloxFuncao.chamar.
    """
    def __init__(self, valor):
        self.valor = valor
