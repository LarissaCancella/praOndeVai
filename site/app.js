import { html, render, useState, useEffect } from "https://unpkg.com/htm@3.1.1/preact/standalone.module.js";
import { cartoesPara } from "./contexto.js";
import { Mapa } from "./mapa.js";
import { Parlamentares } from "./parlamentares.js";
import { CALAMIDADE, nf1, fmt, fmtVar, pct, fmtPct, slug, mesAno, media, faixa, anosDoGoverno, unidade } from "./util.js";
// Quem mantém o site (exigência de transparência; ver regras do TSE no CLAUDE.md).
const MANTENEDOR = "[preencher: nome ou organização responsável e contato]";

// ---------- cálculo (mesma regra para os dois governos) ----------

function serie(f, op) {
  const base = f[op.recorte][op.valores];
  const inv = f.inv_fin[op.recorte][op.valores];
  const out = {};
  for (const a in base) out[a] = base[a] - (op.semInv ? inv[a] || 0 : 0);
  return out;
}

function comparar(D, f, op) {
  const s = serie(f, op);
  const [ga, gb] = D.governos;
  const a = media(anosDoGoverno(D, ga, op).map((x) => s[x]));
  const b = media(anosDoGoverno(D, gb, op).map((x) => s[x]));
  const invB = media(anosDoGoverno(D, gb, op).map((x) => f.inv_fin[op.recorte][op.valores][x] || 0));
  return { f, a, b, dRs: b - a, dPct: pct(a, b), invB };
}

function descricaoRecorte(D, op) {
  const [ga, gb] = D.governos;
  const anos = (g) => anosDoGoverno(D, g, op);
  const sem = op.semCalamidade ? " (sem 2020 e 2024)" : "";
  return op.recorte === "anual"
    ? `Média anual de despesa empenhada, ${faixa(anos(ga))} × ${faixa(anos(gb))}${sem}`
    : `Média de despesa liquidada de ${D.parcial.descricao}, ${faixa(anos(ga))} × ${faixa(anos(gb))}${sem}`;
}

// ---------- componentes ----------

function Controles({ op, set, mapa = false }) {
  const Seg = ({ campo, opcoes }) => html`<div class="seg" role="group">
    ${opcoes.map(([v, r]) => html`<button aria-pressed=${op[campo] === v} onClick=${() => set({ ...op, [campo]: v })}>${r}</button>`)}
  </div>`;
  return html`<div class="controles"><div class="wrap">
    <div class="grupo"><span>Período</span><${Seg} campo="recorte" opcoes=${[["anual", "Ano fechado"], ["parcial", "Jan–ago, todos os anos"]]} /></div>
    <div class="grupo"><span>Valores</span><${Seg} campo="valores" opcoes=${[["real", "Corrigidos (IPCA)"], ["nominal", "Nominais"]]} /></div>
    ${mapa ? null : html`<label class="grupo check"><input type="checkbox" checked=${op.semInv} onChange=${(e) => set({ ...op, semInv: e.target.checked })} />Sem inversões financeiras</label>`}
    <label class="grupo check"><input type="checkbox" checked=${op.semCalamidade} onChange=${(e) => set({ ...op, semCalamidade: e.target.checked })} />Excluir anos de calamidade (2020, 2024)</label>
  </div></div>`;
}

function Cartoes({ funcao }) {
  const cs = cartoesPara(funcao);
  if (!cs.length) return null;
  return html`<aside class="lateral">
    <h3>Contexto</h3>
    ${cs.map((c) => html`<article class="cartao" id=${c.id}>
      <h4>${c.titulo}</h4><p>${c.texto}</p>
      <div class="fontes">Fonte: ${c.fontes.map((x) => html`<a href=${x.url} target="_blank" rel="noopener">${x.nome}</a>`)}</div>
    </article>`)}
  </aside>`;
}

function Legenda({ D }) {
  const [ga, gb] = D.governos;
  return html`<div class="legenda-gov">
    <div><span class="chip a"></span><b>${ga.inicio}–${ga.fim}</b> ${ga.nome} <small>(${ga.partido})</small></div>
    <div><span class="chip b"></span><b>${gb.inicio}–${gb.fim}</b> ${gb.nome} <small>(${gb.partido})</small></div>
    <small>Mesmas métricas e mesmas regras para os dois períodos.</small>
  </div>`;
}

function Comparador({ D, op }) {
  const [ordem, setOrdem] = useState("tamanho");
  const linhas = D.funcoes.filter((f) => !f.encargos).map((f) => comparar(D, f, op));
  const chave = { tamanho: (l) => -Math.max(l.a, l.b), varPct: (l) => -(l.dPct ?? -1e9), varRs: (l) => -l.dRs }[ordem];
  linhas.sort((x, y) => chave(x) - chave(y));
  const totA = linhas.reduce((s, l) => s + l.a, 0);
  const totB = linhas.reduce((s, l) => s + l.b, 0);
  const enc = comparar(D, D.funcoes.find((f) => f.encargos), op);
  const [ga, gb] = D.governos;
  const Th = ({ id, cls, children }) => html`<th class=${cls}><button aria-pressed=${ordem === id} onClick=${() => setOrdem(id)}>${children}</button></th>`;

  const Linha = ({ l, i }) => {
    const max = Math.max(l.a, l.b, 1e-9);
    return html`<tr style=${{ animationDelay: `${i * 25}ms` }}>
      <td class="nome"><a href=${`#/funcao/${slug(l.f.nome)}`}>${l.f.nome}</a>
        ${!op.semInv && l.invB > 0.05 * l.b ? html`<span class="inv" title="Parte relevante é inversão financeira (empréstimos)">● inclui empréstimos</span>` : null}</td>
      <td class="barras"><div class="barra a" style=${{ width: `${(Math.max(l.a, 0) / max) * 100}%` }}></div><div class="barra b" style=${{ width: `${(Math.max(l.b, 0) / max) * 100}%` }}></div></td>
      <td class="val-a">${fmt(l.a)}</td>
      <td class="val-b">${fmt(l.b)}</td>
      <td class="var col-rs">${fmtVar(l.dRs)}</td>
      <td class="var">${fmtPct(l.dPct)}</td>
    </tr>`;
  };

  return html`
    <section class="wrap">
      <div class="abertura">
        <div>
          <h1>Para onde foi o dinheiro federal,<br /><span class="anos">2019–2026</span></h1>
          <p>Despesa da União por área de política pública, com dados oficiais do Tesouro Nacional, nos dois últimos governos.
          Clique numa área para ver ano a ano, as subdivisões e o contexto. Todos os números têm fonte e método em <a href="#/metodo">Método e fontes</a>.</p>
        </div>
        <${Legenda} D=${D} />
      </div>
    </section>
    <${Controles} op=${op} set=${D.setOp} />
    <section class="wrap">
      <div class="totais">
        <div><div class="rotulo">${faixa(anosDoGoverno(D, ga, op))} · média por ano</div><div class="numero val-a">${fmt(totA)} <small>bi</small></div></div>
        <div><div class="rotulo">${faixa(anosDoGoverno(D, gb, op))} · média por ano</div><div class="numero val-b">${fmt(totB)} <small>bi</small></div></div>
        <div><div class="rotulo">Diferença</div><div class="numero">${fmtVar(totB - totA)} <small>bi · ${fmtPct(pct(totA, totB))}</small></div></div>
      </div>
      <div class="principal">
        <div>
          <div class="secao-titulo"><h2>Por área (função orçamentária)</h2><span class="nota">${descricaoRecorte(D, op)} · ${unidade(D, op)} · sem Encargos Especiais</span></div>
          <div class="rolagem"><table class="tabela">
            <thead><tr>
              <${Th} id="tamanho">Área</${Th}><th class="barras"></th>
              <th class="val-a">${faixa(anosDoGoverno(D, ga, op))}</th><th class="val-b">${faixa(anosDoGoverno(D, gb, op))}</th>
              <${Th} id="varRs" cls="col-rs">Var. R$ bi</${Th}><${Th} id="varPct">Var. %</${Th}>
            </tr></thead>
            <tbody>${linhas.map((l, i) => html`<${Linha} key=${l.f.nome + ordem} l=${l} i=${i} />`)}</tbody>
          </table></div>
          <p class="marcador">Ordenar: clique em “Área” (por tamanho), “Var. R$ bi” ou “Var. %”. Variações em % sobre bases menores que R$ 50 milhões aparecem como “n/d”.</p>

          <div class="secao-titulo" style=${{ marginTop: "40px" }}><h2>Fora do total: Encargos Especiais</h2><span class="nota">dívida e transferências constitucionais</span></div>
          <div class="rolagem"><table class="tabela"><tbody><${Linha} l=${enc} i=${0} /></tbody></table></div>
        </div>
        <${Cartoes} />
      </div>
    </section>`;
}

function GraficoAnual({ D, f, op }) {
  const s = serie(f, op);
  const inv = f.inv_fin[op.recorte][op.valores];
  const anos = op.recorte === "anual" ? D.anos_anual : D.anos_parcial;
  const W = 760, H = 300, m = { t: 24, r: 8, b: 40, l: 8 };
  const max = Math.max(...anos.map((a) => f[op.recorte][op.valores][a]), 1e-9);
  const bw = (W - m.l - m.r) / anos.length;
  const y = (v) => m.t + (H - m.t - m.b) * (1 - Math.max(v, 0) / max);
  const govDe = (a) => (+a <= D.governos[0].fim ? "a" : "b");
  const medias = D.governos.map((g, i) => {
    const xs = anosDoGoverno(D, g, op);
    const idx = anos.filter((a) => +a >= g.inicio && +a <= g.fim).map((a) => anos.indexOf(a));
    return { cls: i ? "b" : "a", v: media(xs.map((a) => s[a])), x0: m.l + Math.min(...idx) * bw, x1: m.l + (Math.max(...idx) + 1) * bw };
  });
  return html`<svg class="grafico" viewBox="0 0 ${W} ${H}" role="img" aria-label=${`Despesa anual em ${f.nome}`}>
    <defs><pattern id="hach" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="2" height="5" fill="var(--papel)" opacity=".75" /></pattern></defs>
    <line x1=${m.l} x2=${W - m.r} y1=${H - m.b} y2=${H - m.b} stroke="var(--tinta)" />
    ${anos.map((a, i) => {
      const x = m.l + i * bw + bw * 0.18, w = bw * 0.64;
      const total = f[op.recorte][op.valores][a];
      const parteInv = inv[a] || 0;
      const fora = op.semCalamidade && CALAMIDADE.includes(a);
      const cor = `var(--gov-${govDe(a)})`;
      return html`<g opacity=${fora ? 0.35 : 1}>
        <rect x=${x} y=${y(op.semInv ? total - parteInv : total)} width=${w} height=${H - m.b - y(op.semInv ? total - parteInv : total)} fill=${cor} />
        ${!op.semInv && parteInv > 0.005 ? html`<rect x=${x} y=${y(total)} width=${w} height=${H - m.b - y(parteInv)} fill="url(#hach)" />` : null}
        ${op.semInv && parteInv > 0.005 ? html`<rect x=${x} y=${y(total)} width=${w} height=${H - m.b - y(parteInv)} fill="none" stroke=${cor} stroke-dasharray="3 2" />` : null}
        <text class="valor" x=${x + w / 2} y=${y(op.semInv ? total : total) - 6} text-anchor="middle">${fmt(op.semInv ? total - parteInv : total)}</text>
        <text x=${x + w / 2} y=${H - m.b + 16} text-anchor="middle">${a}</text>
        ${CALAMIDADE.includes(a) ? html`<text x=${x + w / 2} y=${H - m.b + 30} text-anchor="middle" style="font-size:10px">calamidade</text>` : null}
      </g>`;
    })}
    ${medias.map((md) => md.v == null ? null : html`<g>
      <line class="media" x1=${md.x0} x2=${md.x1} y1=${y(md.v)} y2=${y(md.v)} stroke=${`var(--gov-${md.cls})`} />
    </g>`)}
  </svg>`;
}

function Detalhe({ D, op, nomeSlug }) {
  const f = D.funcoes.find((x) => slug(x.nome) === nomeSlug);
  if (!f) return html`<section class="wrap texto"><p>Área não encontrada. <a href="#/">Voltar</a></p></section>`;
  const c = comparar(D, f, op);
  const [ga, gb] = D.governos;
  const subs = f.subfuncoes.map((s) => {
    const vals = s[op.recorte][op.valores];
    const a = media(anosDoGoverno(D, ga, op).map((x) => vals[x] ?? 0));
    const b = media(anosDoGoverno(D, gb, op).map((x) => vals[x] ?? 0));
    return { s, a, b, dRs: b - a, dPct: pct(a, b) };
  }).filter((x) => Math.max(Math.abs(x.a), Math.abs(x.b)) >= 0.01);
  const anos = op.recorte === "anual" ? D.anos_anual : D.anos_parcial;

  return html`
    <section class="wrap"><a class="voltar" href="#/">← Todas as áreas</a>
      <div class="detalhe-cab"><div class="rotulo">Função orçamentária</div><h1>${f.nome}</h1></div>
    </section>
    <${Controles} op=${op} set=${D.setOp} />
    <section class="wrap">
      <div class="totais">
        <div><div class="rotulo">${faixa(anosDoGoverno(D, ga, op))} · média</div><div class="numero val-a">${fmt(c.a)} <small>bi</small></div></div>
        <div><div class="rotulo">${faixa(anosDoGoverno(D, gb, op))} · média</div><div class="numero val-b">${fmt(c.b)} <small>bi</small></div></div>
        <div><div class="rotulo">Diferença</div><div class="numero">${fmtVar(c.dRs)} <small>bi · ${fmtPct(c.dPct)}</small></div></div>
      </div>
      <div class="principal">
        <div>
          <div class="secao-titulo"><h2>Ano a ano</h2><span class="nota">${op.recorte === "anual" ? "despesa empenhada" : `despesa liquidada de ${D.parcial.descricao}`} · ${unidade(D, op)}</span></div>
          <${GraficoAnual} D=${D} f=${f} op=${op} />
          <div class="legenda-grafico">
            <span><span class="chip a"></span>${ga.inicio}–${ga.fim}</span><span><span class="chip b"></span>${gb.inicio}–${gb.fim}</span>
            <span>- - - média do período</span>
            <span><span class="hachura"></span>${op.semInv ? "contorno: inversões financeiras retiradas" : "hachurado: inversões financeiras (empréstimos)"}</span>
          </div>

          <div class="secao-titulo"><h2>Subdivisões (subfunções)</h2><span class="nota">${unidade(D, op)} · médias por período${op.semInv ? " · subfunções incluem inversões financeiras" : ""}</span></div>
          <div class="rolagem"><table class="tabela">
            <thead><tr><th>Subfunção</th><th class="val-a">${faixa(anosDoGoverno(D, ga, op))}</th><th class="val-b">${faixa(anosDoGoverno(D, gb, op))}</th><th class="col-rs">Var. R$ bi</th><th>Var. %</th>
              ${anos.map((a) => html`<th class="col-nominal">${a}</th>`)}</tr></thead>
            <tbody>${subs.map((x, i) => html`<tr style=${{ animationDelay: `${i * 25}ms` }}>
              <td class="nome">${x.s.cod ? html`<span class="marcador">${x.s.cod}</span>` : null}${x.s.nome}</td>
              <td class="val-a">${fmt(x.a)}</td><td class="val-b">${fmt(x.b)}</td><td class="var col-rs">${fmtVar(x.dRs)}</td><td class="var">${fmtPct(x.dPct)}</td>
              ${anos.map((a) => html`<td class="col-nominal">${fmt(x.s[op.recorte][op.valores][a])}</td>`)}
            </tr>`)}</tbody>
          </table></div>
          <p class="marcador">${f.encargos ? "Fonte das subfunções: RREO Anexo 02." : "Fonte das subfunções: Matriz de Saldos Contábeis (SICONFI), que confere com o RREO no total da função."}</p>
        </div>
        <${Cartoes} funcao=${f.nome} />
      </div>
    </section>`;
}

function Metodo({ D }) {
  return html`<section class="wrap texto">
    <h1>Método e fontes</h1>
    <p>Dados gerados em ${new Date(D.gerado_em).toLocaleDateString("pt-BR")}. Arquivo completo: <a href="data/painel.json">data/painel.json</a>.</p>

    <h2>De onde vêm os números</h2>
    <ul>${D.fontes.map((x) => html`<li><a href=${x.url} target="_blank" rel="noopener">${x.nome}</a></li>`)}</ul>

    <h2>Como a conta é feita</h2>
    <ul>
      <li><b>Ano fechado:</b> despesa empenhada até o 6º bimestre do Relatório Resumido de Execução Orçamentária (RREO), linha “Total das Despesas Exceto Intra-Orçamentárias”. Equivale à despesa liquidada mais os restos a pagar não processados inscritos no fim do ano.</li>
      <li><b>Jan–ago, todos os anos:</b> despesa liquidada até o ${D.parcial.bimestre}º bimestre (${D.parcial.descricao}), para comparar o ano em curso com o mesmo período dos anteriores. No meio do ano o empenho já reserva o valor anual das despesas obrigatórias, então o liquidado compara melhor.</li>
      <li><b>Inflação:</b> valores corrigidos pelo IPCA (Banco Central, série 433) até ${mesAno(D.preco_base)}. O ano fechado usa o índice médio do ano; o recorte jan–ago usa o índice médio desses meses.</li>
      <li><b>Médias por governo:</b> média simples dos anos de cada período. Ano fechado: 2019–2022 e 2023–2025 (2026 ainda não terminou). Jan–ago: 2019–2022 e 2023–2026. Cada ano é atribuído a quem governou durante a execução.</li>
      <li><b>Encargos Especiais</b> (dívida e transferências constitucionais) fica fora dos totais e aparece separado.</li>
      <li><b>Sem inversões financeiras:</b> retira o grupo de natureza da despesa 5 (empréstimos e aplicações que retornam ao Tesouro), obtido da Matriz de Saldos Contábeis (MSC) do SICONFI.</li>
      <li><b>Excluir anos de calamidade:</b> retira das médias os anos com calamidade pública reconhecida pelo Congresso (2020 e 2024), nos dois períodos.</li>
    </ul>

    <h2>Conferência entre fontes</h2>
    <p>Para cada função e ano, a soma da MSC é comparada com o RREO. Diferenças acima de R$ 10 milhões:</p>
    ${D.conferencia.length ? html`<div class="rolagem"><table><thead><tr><th>Função</th><th>Ano</th><th>Recorte</th><th>RREO</th><th>MSC</th><th>Dif. (R$ bi)</th></tr></thead>
      <tbody>${D.conferencia.map((c) => html`<tr><td>${c.funcao}</td><td>${c.ano}</td><td>${c.recorte}</td><td>${fmt(c.rreo)}</td><td>${fmt(c.msc)}</td><td>${nf1.format(c.dif)}</td></tr>`)}</tbody></table></div>`
      : html`<p>Nenhuma.</p>`}

    <h2>Mapa de transferências</h2>
    <p>O mapa usa outra fonte (Portal da Transparência) e tem método próprio, descrito na <a href="#/mapa">página do mapa</a>, ao final.</p>

    <h2>Limitações conhecidas</h2>
    <ul>
      <li>Programas que atravessam várias funções (como o Minha Casa, Minha Vida) não são acompanhados individualmente.</li>
      <li>As subfunções da Assistência Social mudaram de classificação em 2025.</li>
      <li>Valores do ano em curso podem ser revistos pelo Tesouro nas publicações seguintes.</li>
    </ul>

    <h2>Sobre este site</h2>
    <p>Mostra dados e contexto. Não recomenda voto nem faz pedido de voto. Mantido por ${MANTENEDOR}.</p>
  </section>`;
}

// ---------- app ----------

function App() {
  const [D, setD] = useState(null);
  const [erro, setErro] = useState(null);
  const [rota, setRota] = useState(location.hash || "#/");
  const [op, setOp] = useState({ recorte: "anual", valores: "real", semInv: false, semCalamidade: false });

  useEffect(() => {
    fetch("data/painel.json").then((r) => r.json()).then(setD).catch((e) => setErro(String(e)));
    const h = () => { setRota(location.hash || "#/"); window.scrollTo(0, 0); };
    addEventListener("hashchange", h);
    return () => removeEventListener("hashchange", h);
  }, []);

  if (erro) return html`<p class="carregando">Não foi possível carregar os dados (${erro}).</p>`;
  if (!D) return html`<p class="carregando">Carregando dados…</p>`;
  D.setOp = setOp;

  const m = rota.match(/^#\/funcao\/(.+)$/);
  const pagina = rota === "#/metodo" ? html`<${Metodo} D=${D} />`
    : rota === "#/parlamentares" ? html`<${Parlamentares} Cartoes=${Cartoes} />`
    : rota === "#/mapa" ? html`<${Mapa} D=${D} op=${op} setOp=${setOp} Controles=${Controles} Cartoes=${Cartoes} />`
    : m ? html`<${Detalhe} D=${D} op=${op} nomeSlug=${m[1]} />`
    : html`<${Comparador} D=${D} op=${op} />`;

  return html`
    <header class="topo"><div class="wrap">
      <a class="marca" href="#/">Pra onde vai<small>gastos federais 2019–2026</small></a>
      <nav class="nav"><a href="#/" aria-current=${rota === "#/" || !!m ? "page" : null}>Comparador</a><a href="#/mapa" aria-current=${rota === "#/mapa" ? "page" : null}>Mapa</a><a href="#/parlamentares" aria-current=${rota === "#/parlamentares" ? "page" : null}>Parlamentares</a><a href="#/metodo" aria-current=${rota === "#/metodo" ? "page" : null}>Método e fontes</a></nav>
    </div></header>
    <main>${pagina}</main>
    <footer class="rodape"><div class="wrap">
      <p>Fontes: Tesouro Nacional (SICONFI: RREO e MSC) e Banco Central (IPCA). Valores em ${unidade(D, op)}.</p>
      <p>Este site mostra dados e contexto; não recomenda voto. Mantido por ${MANTENEDOR}.</p>
    </div></footer>`;
}

render(html`<${App} />`, document.getElementById("app"));
