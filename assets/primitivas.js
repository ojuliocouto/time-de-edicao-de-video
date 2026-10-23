/* =============================================================================
   PRIMITIVAS DE INSERT, semente da biblioteca

   Cada funcao e um mecanismo atomico extraido de um tutorial. A cena e so uma
   sequencia de chamadas destas funcoes: e isso que faz o catalogo crescer sem
   virar uma lista de cenas soltas.

   COMO USAR
   Cole o bloco dentro do <script> da composicao, depois de criar a timeline.
   Todas as funcoes leem `tl` do escopo, entao `tl` precisa existir antes.

   Duas dependem de DOM proprio, e nao funcionam soltas:
   - aplicarCamera / aproxima / trocaCena  exigem um elemento #mundo que
     envolva todas as cenas. Sem ele, a camera nao tem o que mover.
   - rolaPagina exige a captura dentro de um contentor com overflow hidden.

   Todas sao seek-safe: fromTo com estado inicial explicito, sem Math.random,
   sem Date.now, so transform e paint.

   ORIGEM DAS PRIMITIVAS
   - palavrasSubindo, palavrasDeslizando, quique, linhaComPonto, grifo, brilho,
     cardSubindo, aproxima, trocaCena ....... BeTheCut, "Clean Motion Design in AE"
   - o voo de camera 3D ................... Vane Motion, "3D Kinetic Typography"
     (mora em cenas/voo-3d-tipografia.html, ainda nao generalizado)
   - o revelador movel .................... construido do zero
     (mora em cenas/revelador-movel.html)

   - trocaNoLugar ......................... catalogo, kinetic-type-swap
   - umViraMuitos ......................... catalogo, stagger-lattice
   - camadasSeparando ..................... catalogo, camera-rig-depth-stack
   - giroQueTransforma .................... regra card-morph-anchor

   Os onze efeitos do eixo estao cobertos. Nao ha buraco conhecido.

   INDICE POR INTENCAO
   O nome da funcao diz o mecanismo. Esta coluna diz o que ele SIGNIFICA na
   cena, que e por onde voce procura quando esta montando.

     a palavra chega e assenta ............ palavrasSubindo, palavrasDeslizando
     a palavra CARIMBA, nao desliza ....... carimba
     a frase ganha peso numa palavra ...... grifo
     a lista avanca sem ninguem sair ...... listaEnvelhece
     o objeto tem peso e pousa ............ quique, cardSubindo
     um vira muitos ....................... umViraMuitos
     as camadas se separam ................ camadasSeparando
     alguma coisa percorre um caminho ..... linhaComPonto
     uma coisa vira outra ................. giroQueTransforma, trocaNoLugar
     alguma coisa emite ................... brilho
     a camera conta a frase ............... aproxima, trocaCena
     a pagina e lida ...................... rolaPagina, trocaJanela
   ============================================================================= */

// 1. texto palavra a palavra, subindo, com desfoque resolvendo
function palavrasSubindo(sel, t, passo) {
  tl.fromTo(
    sel,
    { opacity: 0, y: 46, filter: "blur(7px)" },
    {
      opacity: 1,
      y: 0,
      filter: "blur(0px)",
      duration: 0.44,
      stagger: passo || 0.1,
      ease: "power3.out",
    },
    t
  );
}

// 2. texto palavra a palavra, deslizando pelo eixo X
function palavrasDeslizando(sel, t, passo) {
  tl.fromTo(
    sel,
    { opacity: 0, x: -70, filter: "blur(6px)" },
    {
      opacity: 1,
      x: 0,
      filter: "blur(0px)",
      duration: 0.46,
      stagger: passo || 0.1,
      ease: "power3.out",
    },
    t
  );
}

// 3. entrada com quique
function quique(sel, t, dur) {
  tl.fromTo(
    sel,
    { opacity: 0, scale: 0.45 },
    { opacity: 1, scale: 1, duration: dur || 0.44, ease: "back.out(2.8)" },
    t
  );
}

// 4 + 5. linha que se desenha com o ponto preso na ponta
function linhaComPonto(sel, t, largura, dur) {
  tl.fromTo(sel + " b", { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.18 }, t - 0.05);
  tl.fromTo(sel + " i", { scaleX: 0 }, { scaleX: 1, duration: dur, ease: "power2.inOut" }, t);
  tl.fromTo(sel + " b", { x: 0 }, { x: largura, duration: dur, ease: "power2.inOut" }, t);
}

// 6. GRIFO que abre por tras da palavra
//
// ATENCAO: a versao ingenua (uma copia so, color: var(--fundo)) DEIXA A PALAVRA
// INVISIVEL no meio da tween, e os quatro verificadores passam limpos. Nao use.
// Detalhe em references/fabrica-armadilhas.md.
//
// Sao DUAS copias recortadas pela MESMA variavel. O pai nao pode ter texto
// proprio: o verificador de contraste le o no de texto direto do pai e ignora
// clip-path do filho.
//
// HTML:
//   <span class="grifo" id="g1"
//         data-layout-allow-overlap="true" data-layout-allow-occlusion="true">
//     <span class="g-clara">palavra</span><span class="g-escura">palavra</span>
//   </span>
//
// CSS:
//   .grifo { position: relative; display: inline-block; padding: 10px 16px; }
//   .grifo > span { display: block; white-space: nowrap; }
//   /* a metade que ainda esta FORA do acento */
//   .grifo .g-clara {
//     color: var(--tinta);
//     clip-path: inset(0 0 0 calc(var(--w, 0) * 100%));
//   }
//   /* a metade que JA esta sobre o acento. A barra e o fundo DESTA copia,
//      entao o mesmo clip-path corta texto e barra juntos: nunca existe um
//      pixel de acento sem o texto escuro certo em cima. */
//   .grifo .g-escura {
//     position: absolute; inset: 0; padding: 10px 16px;
//     color: var(--fundo); background: var(--acento);
//     clip-path: inset(0 calc(100% - var(--w, 0) * 100%) 0 0);
//   }
//
// O check VAI acusar contraste 1:1 nesta construcao mesmo estando certa, porque
// amostra o centro da caixa e ignora o clip-path. E o mesmo numero do defeito
// que ela corrige. So o print distingue. Confira com snapshot no meio da tween.
function grifo(sel, t, dur) {
  tl.fromTo(sel, { "--w": 0 }, { "--w": 1, duration: dur || 0.42, ease: "power3.out" }, t);
}

// 12. brilho de gradiente desfocado que se desenha
function brilho(sel, t, giro) {
  tl.fromTo(
    sel,
    { scaleX: 0, opacity: 0, rotation: giro || -12 },
    { scaleX: 1, opacity: 0.5, duration: 1.1, ease: "power2.out" },
    t
  );
}

// 13. card subindo de baixo com sombra direcional
function cardSubindo(sel, t) {
  tl.fromTo(
    sel,
    { opacity: 0, y: 200, scale: 0.94, filter: "blur(8px)" },
    {
      opacity: 1,
      y: 0,
      scale: 1,
      filter: "blur(0px)",
      duration: 0.75,
      ease: "power3.out",
    },
    t
  );
}

/* ---------- a camera 2D em pernas encadeadas ---------- */
const cam = { s: 1, y: 0 };
const mundo = document.getElementById("mundo");
function aplicarCamera() {
  mundo.style.transform = "translateY(" + cam.y + "px) scale(" + cam.s + ")";
}
aplicarCamera();

function aproxima(alvo, t, dur, ease) {
  tl.to(cam, { s: alvo, duration: dur, ease: ease, onUpdate: aplicarCamera }, t);
}
function trocaCena(destinoY, t) {
  tl.to(
    cam,
    { y: destinoY, s: 1, duration: 0.8, ease: "power3.inOut", onUpdate: aplicarCamera },
    t
  );
}

/* ============================ BURACOS FECHADOS ============================ */

// BURACO 3, troca no mesmo lugar   (lido de: kinetic-type-swap)
// O que sai chicoteia pra fora da fresta com power4.in ANTES do que entra
// cruzar o centro. As duas fases se cruzam so por ~10% do rolo, entao
// nenhum quadro mostra duas palavras legiveis ao mesmo tempo.
function trocaNoLugar(sel, tempos, dur) {
  const itens = gsap.utils.toArray(sel + " span");
  gsap.set(itens, { yPercent: 100, opacity: 0 });
  gsap.set(itens[0], { yPercent: 0, opacity: 1 });
  tempos.forEach((quando, k) => {
    const sai = itens[k],
      entra = itens[k + 1];
    if (!entra) return;
    const dSai = dur * 0.55,
      entrada = quando + dur * 0.45;
    tl.to(sai, { yPercent: -112, duration: dSai, ease: "power4.in" }, quando);
    tl.set(sai, { opacity: 0 }, quando + dSai);
    tl.set(entra, { opacity: 1 }, entrada);
    tl.fromTo(
      entra,
      { yPercent: 100 },
      { yPercent: 0, duration: dur * 0.55, ease: "power3.out" },
      entrada
    );
  });
}

// BURACO 5, um vira muitos   (lido de: stagger-lattice)
// O segredo e o stagger com consciencia de grade: from "center" mais
// grid [linhas, colunas] faz o espalhamento irradiar do meio pra fora,
// em vez de varrer em fila.
//
// O passo era 0.03 e estava QUEBRADO: a 30 fps isso da 0,9 frame, ou seja,
// menos de um quadro, e a grade inteira entrava no mesmo quadro renderizado.
// Piso do que e visivel: 3 frames = 0,10 s. Ver references/fabrica-numeros.md.
function umViraMuitos(sel, t, grade, passo) {
  tl.fromTo(
    sel + " .celula",
    { "--c-y": "26px", "--c-s": 0.7, "--c-op": 0 },
    {
      "--c-y": "0px",
      "--c-s": 1,
      "--c-op": 1,
      duration: 0.32,
      stagger: { each: passo || 0.1, from: "center", grid: grade },
      ease: "power2.out",
    },
    t
  );
}

// BURACO 6, camadas separando   (lido de: camera-rig-depth-stack)
// Cada painel viaja em Z, rotateY e rotateX ao mesmo tempo, escalonado,
// debaixo de UMA perspectiva so. A pilha vira leque em profundidade.
function camadasSeparando(sel, t, dur) {
  const paineis = gsap.utils.toArray(sel + " .painel");
  const n = paineis.length;
  paineis.forEach((el, i) => {
    const k = i - (n - 1) / 2; // centraliza o leque
    tl.fromTo(
      el,
      { "--px": "0px", "--py": "0px", "--pz": "-80px", "--pry": "-22deg", "--prx": "14deg", opacity: 0 },
      {
        "--px": k * 62 + "px",
        "--py": k * 132 + "px",
        "--pz": k * 130 + "px",
        "--pry": "-14deg",
        "--prx": "10deg",
        opacity: 1,
        duration: dur || 1.2,
        ease: "power3.out",
      },
      t + i * 0.09
    );
  });
}

// BURACO 8, giro que transforma   (lido da regra card-morph-anchor)
// Largura e altura sao proibidas de animar, entao o tamanho aparente vem
// de scale. Forma, canto, cor e sombra viajam numa tween SO, com uma
// curva so. O conteudo velho sai nos primeiros 40% e o novo entra nos
// ultimos 40%: o vao no meio e a piscada natural da troca.
function giroQueTransforma(alvo, antes, depois, t, dur, pose) {
  tl.to(
    alvo,
    {
      scaleX: pose.sx,
      scaleY: pose.sy,
      rotationY: pose.ry,
      borderRadius: pose.raio,
      backgroundColor: pose.cor,
      duration: dur,
      ease: "power3.inOut",
    },
    t
  );
  tl.to(antes, { opacity: 0, duration: dur * 0.4, ease: "power2.in" }, t);
  tl.to(depois, { opacity: 1, duration: dur * 0.4, ease: "power2.out" }, t + dur * 0.6);
}

/* ===================== SAIDAS DE PROJETO REAL ===================== */

// PAGINA QUE ROLA DENTRO DE UMA JANELA        (origem: insert de um projeto real)
// A imagem e a captura da pagina INTEIRA, alta; o contentor com overflow
// hidden e a fresta. Deslocar em Y e o scroll.
// Mais confiavel que gravar tela: e deterministico, reversivel sob seek, e
// nao depende de refazer a gravacao quando o texto muda.
// Capture com scripts/capturar_pagina.py --altura 3400.
function rolaPagina(sel, t, de, ate, dur, ease) {
  tl.fromTo(sel, { y: de }, { y: ate, duration: dur, ease: ease || "power1.inOut" }, t);
}

// TROCA DE CONTEUDO NA MESMA JANELA           (origem: insert de um projeto real)
// A fresta nao se mexe: so o que esta dentro dela muda, em corte duro. E a
// versao "tela de produto" do efeito troca-no-mesmo-lugar.
// selUrl e selUrlNova sao duas copias empilhadas da barra de endereco; nunca
// use tl.call para trocar o texto, porque call nao e confiavel em seek pra tras.
function trocaJanela(selSai, selEntra, selUrl, selUrlNova, t) {
  tl.to(selSai, { opacity: 0, duration: 0.01, ease: "power1.out" }, t);
  tl.fromTo(selEntra, { opacity: 0 }, { opacity: 1, duration: 0.01, ease: "power1.out" }, t);
  tl.to(selUrl, { opacity: 0, duration: 0.12, ease: "power2.in" }, t - 0.1);
  tl.fromTo(selUrlNova, { opacity: 0 }, { opacity: 1, duration: 0.18, ease: "power2.out" }, t + 0.04);
}


// =============================================================================
// 17. A PALAVRA CARIMBA   (lido de: guia MOTION VOX STYLE, secao 04)
//
// Chega com rotacao leve e escala maior, assenta em poucos frames, e a tinta
// resolve em duas fases. Nunca desliza e nunca faz fade: e um carimbo batendo.
//
// A diferenca pratica pro palavrasSubindo: aquele ENTRA no quadro vindo de
// baixo, este JA ESTA na posicao e so pousa em cima dela. Serve pra palavra
// que precisa pesar sozinha, sem a leitura de "chegando".
//
// HTML:  <span class="p" id="p1">PALAVRA</span>
// CSS:   .p { display: inline-block; transform-origin: 50% 50%; }
function carimba(sel, t, dur) {
  const d = dur || 0.34;
  tl.fromTo(
    sel,
    { opacity: 0, scale: 1.34, rotation: -3.2 },
    { opacity: 1, scale: 1, rotation: 0, duration: d, ease: "power4.out" },
    t
  );
  // segunda fase: a tinta assenta depois da forma parar
  tl.fromTo(sel, { filter: "blur(4px)" }, { filter: "blur(0px)", duration: d * 0.5, ease: "power2.out" }, t);
}

// =============================================================================
// 18. A LISTA ENVELHECE   (lido de: guia MOTION VOX STYLE, secao 04)
//
// Quando o item novo entra, o anterior NAO sai de cena: ele e rebaixado. Perde
// cor em poucos frames e continua ali. A hierarquia e do agora, nao do primeiro.
//
// Resolve de graca a armadilha do quadro vazio: nunca existe um instante em que
// a coisa antiga ja saiu e a nova ainda nao chegou, porque nada sai.
//
// Rebaixa por OPACIDADE, nao por cor. Tween de cor com var() do CSS nao e
// confiavel: o GSAP nao resolve a variavel, entao o valor de partida vira
// string e a interpolacao morre. Opacidade funciona em qualquer paleta.
//
// itens: array de seletores, na ordem de entrada
// t:     tempo do primeiro
// passo: intervalo entre itens (piso de 0,10 s, ver numeros.md)
// opts:  { forcaVelha: 0.4 }  opacidade do item ja rebaixado
function listaEnvelhece(itens, t, passo, opts) {
  const p = Math.max(passo || 0.42, 0.1);
  const o = opts || {};
  const forcaVelha = o.forcaVelha == null ? 0.4 : o.forcaVelha;
  itens.forEach((sel, i) => {
    const quando = t + i * p;
    tl.set(sel, { visibility: "visible" }, 0);
    tl.fromTo(
      sel,
      { opacity: 0, y: 22 },
      { opacity: 1, y: 0, duration: 0.4, ease: "power3.out" },
      quando
    );
    // rebaixa todos os anteriores no instante em que este entra
    for (let j = 0; j < i; j++) {
      tl.to(itens[j], { opacity: forcaVelha, duration: 0.18, ease: "power2.out" }, quando);
    }
  });
}
