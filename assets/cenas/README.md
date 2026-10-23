# Cenas guardadas

Cada cena é uma combinação que funcionou: quais primitivas, em que ordem, com
que tempo. A primitiva se reusa; a cena se lembra.

## O que a cena guarda, e o que ela NÃO guarda

A cena guarda **estrutura de tempo**. Nunca a copy de um projeto.

Os textos aqui são marcadores óbvios: `lado a`, `etiqueta 1`, `frase de quatro
palavras`, `primeira-url.exemplo`. É de propósito. Se a copy de um cliente
entrar numa cena guardada, ela vaza para todo projeto futuro, e pior: quem for
montar um insert vai achar que já existe resposta pronta e copiar o trabalho do
outro em vez de resolver o próprio.

**Ao promover uma cena nova, troque o texto por marcador antes de guardar.**

Elas também **não rodam como estão**: apontam para fontes e mídia que moram no
projeto, não na skill. São referência de leitura, não arquivo executável.

| Cena | Onde está | Primitivas que combina | De onde veio |
| --- | --- | --- | --- |
| **Voo 3D por tipografia**: palavras encaixadas em ângulos retos no espaço, câmera pousando de uma em uma | `cenas/voo-3d-tipografia.html` | voo de câmera 3D, foco entrando e saindo, empurrão final | Vane Motion, "3D Kinetic Typography" |
| **Revelador móvel**: lupa percorrendo um campo de palavras e acendendo o que passa por baixo | `cenas/revelador-movel.html` | máscara suave móvel, palavra achada, frase que se monta | construída do zero |
| **Motion limpo de SaaS, 4 cenas**: dor, órbita de apps, medidor caindo, solução | `cenas/motion-limpo-saas.html` | palavrasSubindo, grifo, linhaComPonto, brilho, quique, aproxima, trocaCena, aneis contra-girando, arco com contador | BeTheCut, "Clean Motion Design in AE" |
| **Quatro efeitos**: troca no mesmo lugar, um vira muitos, camadas separando, giro que transforma, uma cena por efeito | `cenas/quatro-efeitos.html` | trocaNoLugar, umViraMuitos, camadasSeparando, giroQueTransforma | catálogo do HyperFrames |
| **Comparação idêntica**: dois lados preenchendo em sincronia até levarem o mesmo selo, e o veredito no vão | `cenas/comparacao-identica.html` | entrada espelhada dos dois lados, barras em sincronia, quique nos selos, grifo no fecho | neutralizada |
| **Janela que rola**: página real rolando dentro de um navegador inclinado, troca de conteúdo no mesmo lugar, e vídeo na mesma fresta | `cenas/janela-que-rola.html` | rolaPagina, trocaJanela, quique, grifo | neutralizada |

## Como ler uma cena

Abra o HTML e olhe **o bloco da linha do tempo**, não o CSS. É lá que mora a
decisão que interessa: quais primitivas, em que ordem, com que intervalo.

O CSS é só o estilo daquele projeto e vai ser trocado de qualquer jeito.
