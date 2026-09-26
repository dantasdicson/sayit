"""Fonte única dos desafios de frases. Incremente VERSAO ao trocar a avaliação."""
from dataclasses import dataclass

VERSAO = 'frases-v1'
NOTA_MINIMA = 70


@dataclass(frozen=True)
class Desafio:
    numero: int
    frase: str
    importantes: tuple
    conteudos: tuple

    @property
    def palavras(self):
        return self.frase.rstrip('.').split()


DESAFIOS = (
    Desafio(1, 'I like cake.', ('cake',), ('Magic E',)),
    Desafio(2, 'The ship is big.', ('ship',), ('SH',)),
    Desafio(3, 'The cute cat is on the ship.', ('cute', 'cat', 'ship'), ('Magic E', 'Som do A', 'SH')),
)
