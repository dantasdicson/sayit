from array import array
from unittest import TestCase
from core.management.commands.popular_sayit import PARES_DIDATICOS
from core.narracao_resumos import roteiro, texto_falado, VOZ_PT, VOZ_EN
from core.resumos import RESUMOS
from docs.gerar_narracoes import preparar


class NarracaoResumosTests(TestCase):
    def test_nove_roteiros_tem_quatro_pares_e_so_duas_trocas_de_voz(self):
        for numero in RESUMOS:
            with self.subTest(modulo=numero):
                partes = roteiro(numero, PARES_DIDATICOS[numero])
                self.assertEqual(len(partes), 6)
                self.assertEqual([p['voz'] for p in partes], [VOZ_PT] + [VOZ_EN] * 4 + [VOZ_PT])
                self.assertEqual([p['texto'] for p in partes[1:5]],
                                 [f'{a}, {b}.' for a, b in PARES_DIDATICOS[numero]])
                self.assertTrue(all(len(p['texto'].split()) >= 2 for p in partes))
                self.assertIn('Você terminou a revisão', partes[-1]['texto'])

    def test_divergencia_entre_tela_e_catalogo_impede_geracao(self):
        with self.assertRaises(ValueError):
            roteiro(2, [('wrong', 'word')] * 4)
        with self.assertRaises(ValueError):
            roteiro(1, PARES_DIDATICOS[1][:3])

    def test_nomes_de_letras_sem_alterar_artigos(self):
        self.assertEqual(texto_falado('O E muda o A. A letra O. Módulo 2.'),
                         'O ê muda o á. A letra ó. Módulo dois.')
        self.assertEqual(texto_falado('S e H, TH e PH.'), 'esse e agá, tê agá e pê agá.')

    def test_segmento_silencioso_e_rejeitado(self):
        with self.assertRaises(ValueError):
            preparar(bytes(48000))

    def test_pcm_tem_bordas_suaves_sem_clipping(self):
        entrada = array('h', [0] * 24000 + [10000, -10000] * 12000 + [0] * 24000)
        saida = array('h', preparar(entrada.tobytes()))
        self.assertLess(len(saida), len(entrada))
        self.assertEqual(saida[0], 0)
        self.assertEqual(saida[-1], 0)
        self.assertLess(max(map(abs, saida)), 32767)
