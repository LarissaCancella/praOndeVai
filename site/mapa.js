import { html, useState, useEffect } from "https://unpkg.com/htm@3.1.1/preact/standalone.module.js";
import { CALAMIDADE, nf0, fmt, fmtPct, pct, media, faixa, anosDoGoverno, mesAno } from "./util.js";

const NOMES = {
  AC: "Acre", AL: "Alagoas", AM: "Amazonas", AP: "Amapá", BA: "Bahia", CE: "Ceará", DF: "Distrito Federal",
  ES: "Espírito Santo", GO: "Goiás", MA: "Maranhão", MG: "Minas Gerais", MS: "Mato Grosso do Sul", MT: "Mato Grosso",
  PA: "Pará", PB: "Paraíba", PE: "Pernambuco", PI: "Piauí", PR: "Paraná", RJ: "Rio de Janeiro", RN: "Rio Grande do Norte",
  RO: "Rondônia", RR: "Roraima", RS: "Rio Grande do Sul", SC: "Santa Catarina", SE: "Sergipe", SP: "São Paulo", TO: "Tocantins",
};
const CATEGORIAS = [
  ["todas", "Todas"],
  ["constitucionais", "Constitucionais (por fórmula)"],
  ["demais", "Legais e voluntárias"],
  ["investimento", "Só investimento"],
];
const fmtHab = (v) => (v == null ? "—" : `R$ ${nf0.format(v)}`);

export function Mapa({ D, op, setOp, Controles, Cartoes }) {
  const [M, setM] = useState(null);
  const [G, setG] = useState(null);
  const [erro, setErro] = useState(null);
  const [cat, setCat] = useState("todas");
  const [metrica, setMetrica] = useState("hab");
  const [mostrar, setMostrar] = useState("var");
  const [sel, setSel] = useState(null);
  const [ordem, setOrdem] = useState("var");

  useEffect(() => {
    Promise.all([fetch("data/mapa.json").then((r) => r.json()), fetch("data/ufs.json").then((r) => r.json())])
      .then(([m, g]) => { setM(m); setG(g); })
      .catch((e) => setErro(String(e)));
  }, []);
  if (erro) return html`<p class="carregando">Não foi possível carregar o mapa (${erro}).</p>`;
  if (!M || !G) return html`<p class="carregando">Carregando mapa…</p>`;

  const [ga, gb] = D.governos;
  const anosA = anosDoGoverno(M, ga, op), anosB = anosDoGoverno(M, gb, op);
  const serieUF = (uf) => M.series[cat][uf][op.recorte][op.valores];
  const conv = (uf, bi) => (bi == null ? null : metrica === "hab" ? (bi * 1e9) / M.populacao.uf[uf] : bi);
  const linhas = Object.keys(NOMES).map((uf) => {
    const s = serieUF(uf);
    const a = conv(uf, media(anosA.map((x) => s[x] ?? 0)));
    const b = conv(uf, media(anosB.map((x) => s[x] ?? 0)));
    return { uf, a, b, d: b - a, p: pct(a, b) };
  });
  const porUF = Object.fromEntries(linhas.map((l) => [l.uf, l]));
  const maxAbs = Math.max(...linhas.map((l) => Math.max(l.a, l.b)), 1e-9);
  const maxPct = Math.max(...linhas.map((l) => Math.abs(l.p ?? 0)), 1);

  const cor = (l) => {
    if (mostrar === "var") {
      if (l.p == null) return "var(--papel-2)";
      const t = Math.min(Math.abs(l.p) / maxPct, 1) * 85 + 5;
      return `color-mix(in srgb, var(--gov-${l.p >= 0 ? "b" : "a"}) ${t}%, var(--papel-2))`;
    }
    const v = mostrar === "a" ? l.a : l.b;
    return `color-mix(in srgb, var(--gov-${mostrar}) ${Math.max(v, 0) / maxAbs * 90 + 5}%, var(--papel-2))`;
  };
  const fmtV = (v) => (metrica === "hab" ? fmtHab(v) : `${fmt(v)} bi`);

  // transferências sem UF no Portal (repasses extraordinários via Tesouro): mostradas para os dois períodos
  const sNI = M.series[cat].NI[op.recorte][op.valores];
  const semUF = (anos) => {
    const ni = media(anos.map((x) => sNI[x] ?? 0));
    const tot = media(anos.map((x) => Object.keys(NOMES).reduce((s, uf) => s + (serieUF(uf)[x] ?? 0), 0) + (sNI[x] ?? 0)));
    return { ni, p: tot ? (ni / tot) * 100 : null };
  };
  const niA = semUF(anosA), niB = semUF(anosB);
  const sFora = M.series[cat].FORA?.[op.recorte][op.valores] || {};
  const foraA = media(anosA.map((x) => sFora[x] ?? 0)), foraB = media(anosB.map((x) => sFora[x] ?? 0));

  const ordenadas = [...linhas].sort(ordem === "var" ? (x, y) => (y.p ?? -1e9) - (x.p ?? -1e9)
    : ordem === "b" ? (x, y) => y.b - x.b : (x, y) => NOMES[x.uf].localeCompare(NOMES[y.uf]));

  const Seg = ({ v, set, opcoes }) => html`<div class="seg" role="group">
    ${opcoes.map(([k, r]) => html`<button aria-pressed=${v === k} onClick=${() => set(k)}>${r}</button>`)}</div>`;

  const legenda = mostrar === "var"
    ? html`<div class="escala"><span>${fmtPct(-maxPct)}</span><i style="background:linear-gradient(90deg,var(--gov-a),var(--papel-2),var(--gov-b))"></i><span>${fmtPct(maxPct)}</span></div>
           <p class="marcador">Azul: ${faixa(anosA)} transferiu mais por ano. Vermelho: ${faixa(anosB)} transferiu mais.</p>`
    : html`<div class="escala"><span>0</span><i style=${`background:linear-gradient(90deg,var(--papel-2),var(--gov-${mostrar}))`}></i><span>${fmtV(maxAbs)}</span></div>
           <p class="marcador">Mesma escala para os dois períodos.</p>`;

  return html`
    <section class="wrap">
      <div class="abertura">
        <div>
          <h1>Quanto a União repassou para cada estado</h1>
          <p>Transferências federais ao governo estadual e às prefeituras de cada estado, por habitante.
          Mostra repasses, não o gasto direto da União no estado (como obras federais e salários de servidores).</p>
        </div>
        <div class="legenda-gov">
          <div><span class="chip a"></span><b>${ga.inicio}–${ga.fim}</b> ${ga.nome}</div>
          <div><span class="chip b"></span><b>${gb.inicio}–${gb.fim}</b> ${gb.nome}</div>
          <small>Dados até ${mesAno(M.ultimo_mes)}. População: ${M.populacao.fonte}, para todos os anos.</small>
        </div>
      </div>
    </section>
    <${Controles} op=${op} set=${setOp} mapa=${true} />
    <div class="controles controles-2"><div class="wrap">
      <div class="grupo"><span>Tipo</span><${Seg} v=${cat} set=${setCat} opcoes=${CATEGORIAS} /></div>
      <div class="grupo"><span>Medida</span><${Seg} v=${metrica} set=${setMetrica} opcoes=${[["hab", "Por habitante"], ["total", "Total"]]} /></div>
      <div class="grupo"><span>Mostrar</span><${Seg} v=${mostrar} set=${setMostrar} opcoes=${[["var", "Diferença"], ["a", faixa(anosA)], ["b", faixa(anosB)]]} /></div>
    </div></div>
    <section class="wrap">
      <div class="principal">
        <div>
          <div class="secao-titulo"><h2>Média por ano</h2><span class="nota">${op.recorte === "anual" ? "anos fechados" : `${M.parcial.descricao} de cada ano`} ·
            ${op.valores === "real" ? `R$ de ${mesAno(M.preco_base)}` : "R$ correntes"}${op.semCalamidade ? " · sem 2020 e 2024" : ""}</span></div>
          <div class="mapa-grade">
            <svg class="mapa" viewBox=${G.viewBox} role="img" aria-label="Mapa do Brasil por estado">
              ${Object.entries(G.ufs).map(([uf, g]) => html`<path d=${g.path} style=${{ fill: cor(porUF[uf]) }}
                class=${sel === uf ? "uf sel" : "uf"} onClick=${() => setSel(sel === uf ? null : uf)}>
                <title>${NOMES[uf]}: ${fmtV(porUF[uf].a)} → ${fmtV(porUF[uf].b)} (${fmtPct(porUF[uf].p)})</title></path>`)}
              ${Object.entries(G.ufs).map(([uf, g]) => html`<text x=${g.cx} y=${g.cy} class="uf-rotulo">${uf}</text>`)}
            </svg>
            <div>${legenda}
              <p class="aviso-ni">Fora do mapa, sem estado identificado no Portal:${" "}<span class="val-a">${fmt(niA.ni)} bi/ano</span>${" "}em ${faixa(anosA)} (${fmtPct(niA.p).replace("+", "")} do total) e${" "}<span class="val-b">${fmt(niB.ni)} bi/ano</span>${" "}em ${faixa(anosB)} (${fmtPct(niB.p).replace("+", "")}).${" "}<a href="#repasses-sem-uf">Por quê?</a>${" "}Também fora: repasses a entidades privadas, empresas e organismos internacionais (<span class="val-a">${fmt(foraA)}</span> e${" "}<span class="val-b">${fmt(foraB)}</span> bi/ano).</p>
              ${sel ? html`<${DetalheUF} uf=${sel} l=${porUF[sel]} M=${M} op=${op} ga=${ga} gb=${gb} anosA=${anosA} anosB=${anosB} fmtV=${fmtV} cat=${cat} metrica=${metrica} />`
                : html`<p class="marcador">Clique num estado para ver o detalhe.</p>`}
            </div>
          </div>

          <div class="secao-titulo" style=${{ marginTop: "28px" }}><h2>Todos os estados</h2><span class="nota">${metrica === "hab" ? "R$ por habitante por ano" : "R$ bilhões por ano"}</span></div>
          <div class="rolagem"><table class="tabela">
            <thead><tr>
              <th><button aria-pressed=${ordem === "nome"} onClick=${() => setOrdem("nome")}>Estado</button></th>
              <th class="val-a">${faixa(anosA)}</th>
              <th class="val-b"><button aria-pressed=${ordem === "b"} onClick=${() => setOrdem("b")}>${faixa(anosB)}</button></th>
              <th><button aria-pressed=${ordem === "var"} onClick=${() => setOrdem("var")}>Var. %</button></th>
            </tr></thead>
            <tbody>${ordenadas.map((l, i) => html`<tr key=${l.uf + ordem} style=${{ animationDelay: `${i * 15}ms` }} onClick=${() => setSel(l.uf)} class=${sel === l.uf ? "sel" : ""}>
              <td class="nome"><b>${NOMES[l.uf]}</b> <span class="marcador" style="display:inline">${l.uf}</span></td>
              <td class="val-a">${fmtV(l.a)}</td><td class="val-b">${fmtV(l.b)}</td><td class="var">${fmtPct(l.p)}</td>
            </tr>`)}</tbody>
          </table></div>

          <div class="texto" id="metodo-mapa">
            <h2>Método do mapa</h2>
            <ul>
              <li><b>Fonte:</b> arquivos mensais de transferências do Portal da Transparência (CGU), com a UF do favorecido. Dados de jan/2019 a ${mesAno(M.ultimo_mes)}.</li>
              <li><b>Ano fechado</b> soma janeiro a dezembro; <b>jan–ago</b> soma os mesmos meses de todos os anos, como no comparador.</li>
              <li><b>Inflação:</b> cada mês é corrigido pelo IPCA até ${mesAno(M.preco_base)}.</li>
              <li><b>Por habitante:</b> população do Censo 2022 (IBGE) em todos os anos.</li>
              <li><b>Quem recebe:</b> só governos estaduais e municipais e demais órgãos e fundos públicos (tipo de favorecido “Administração Pública”). Entidades privadas, empresas, agentes intermediários e organismos internacionais ficam fora do mapa.</li>
              <li><b>Tipos:</b> “constitucionais” é a categoria “Constitucionais e Royalties” do Portal; “legais e voluntárias” é “Legais, Voluntárias e Específicas”; “investimento” são as linhas com grupo de despesa 4.</li>
            </ul>
            <p>Conferência: o FPE por estado no Portal da Transparência é comparado com o arquivo do Tesouro Nacional.</p>
            <table><thead><tr><th>Mês</th><th>FPE Portal (R$ bi)</th><th>FPE Tesouro (R$ bi)</th><th>Maior diferença num estado (R$)</th></tr></thead>
              <tbody>${(M.conferencia_fpe || []).map((c) => html`<tr><td>${mesAno(c.mes)}</td><td>${fmt(c.fpe_portal)}</td><td>${fmt(c.fpe_tesouro)}</td><td>${nf0.format(c.maior_dif_uf_reais)}</td></tr>`)}</tbody></table>
            <p>Fontes: ${M.fontes.map((x) => html`<a href=${x.url} target="_blank" rel="noopener">${x.nome}</a>; `)}</p>
          </div>
        </div>
        <${Cartoes} funcao="Mapa" />
      </div>
    </section>`;
}

function DetalheUF({ uf, l, M, op, ga, gb, anosA, anosB, fmtV, cat, metrica }) {
  const s = M.series[cat][uf][op.recorte][op.valores];
  const anos = op.recorte === "anual" ? M.anos_anual : M.anos_parcial;
  const conv = (bi) => (metrica === "hab" ? (bi * 1e9) / M.populacao.uf[uf] : bi);
  const rotulo = (v) => (metrica === "hab" ? nf0.format(v) : fmt(v));
  const maxConv = Math.max(...anos.map((a) => conv(s[a] ?? 0)), 1e-9);
  // as ações são sempre comparadas em ano fechado, qualquer que seja o recorte escolhido
  const fechadoA = anosDoGoverno(M, ga, { ...op, recorte: "anual" });
  const fechadoB = anosDoGoverno(M, gb, { ...op, recorte: "anual" });
  const acoes = (M.principais_acoes[uf] || []).map((x) => ({
    ...x, a: media(fechadoA.map((y) => x.anual_real[y] ?? 0)), b: media(fechadoB.map((y) => x.anual_real[y] ?? 0)),
  }));
  return html`<div class="detalhe-uf">
    <h3>${NOMES[uf]}</h3>
    <div class="par"><span class="val-a">${fmtV(l.a)}</span> → <span class="val-b">${fmtV(l.b)}</span> <b>${fmtPct(l.p)}</b></div>
    <div class="mini">${anos.map((a) => {
      const v = conv(s[a] ?? 0);
      return html`<div title=${`${a}: ${rotulo(v)}`}>
        <b>${rotulo(v)}</b>
        <i style=${{ height: `${Math.max((v / maxConv) * 72, 1)}px`, background: `var(--gov-${+a <= ga.fim ? "a" : "b"})`, opacity: op.semCalamidade && CALAMIDADE.includes(a) ? 0.35 : 1 }}></i>
        <span>${a}</span></div>`;
    })}</div>
    <p class="marcador">${metrica === "hab" ? "R$ por habitante" : "R$ bilhões"} por ano (${op.recorte === "anual" ? "anos fechados" : M.parcial.descricao}).</p>
    <h4>Maiores repasses (todas as categorias, média por ano fechado, R$ bi de ${mesAno(M.preco_base)})</h4>
    <table class="tabela compacta"><thead><tr><th>Ação</th><th class="val-a">${faixa(fechadoA)}</th><th class="val-b">${faixa(fechadoB)}</th></tr></thead><tbody>${acoes.map((x) => html`<tr>
      <td class="nome">${x.nome.toLowerCase()}</td><td class="val-a">${fmt(x.a)}</td><td class="val-b">${fmt(x.b)}</td></tr>`)}</tbody></table>
  </div>`;
}
