import { html, useState, useEffect } from "https://unpkg.com/htm@3.1.1/preact/standalone.module.js";
import { nf0, nf1 } from "./util.js";

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const brl2 = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2 });
const pctTxt = (n, d) => (d ? `${nf1.format((n / d) * 100)}%` : "—");
const semAcento = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

// partido do deputado no fim do ano (ou na última troca até lá)
function partidoNoAno(p, ano) {
  const fim = `${ano}-12-31`;
  const ate = p.partidos.filter((x) => x.desde <= fim);
  return (ate.length ? ate[ate.length - 1] : p.partidos[0])?.partido || "—";
}

function subsidiosDoAno(subsidio, ano) {
  const ini = `${ano}-01-01`, fim = `${ano}-12-31`;
  const vigente = [...subsidio].reverse().find((s) => s.desde <= ini);
  const novos = subsidio.filter((s) => s.desde > ini && s.desde <= fim);
  return [vigente, ...novos].filter(Boolean);
}

export function Parlamentares({ Cartoes }) {
  const [P, setP] = useState(null);
  const [erro, setErro] = useState(null);
  const [casa, setCasa] = useState("camara");
  const [ano, setAno] = useState(null);
  const [busca, setBusca] = useState("");
  const [partido, setPartido] = useState("");
  const [uf, setUf] = useState("");
  const [ordem, setOrdem] = useState({ col: "nome", dir: 1 });

  useEffect(() => {
    fetch("data/parlamentares.json").then((r) => r.json())
      .then((d) => { setP(d); setAno(d.anos.includes("2025") ? "2025" : d.anos[d.anos.length - 1]); })
      .catch((e) => setErro(String(e)));
  }, []);
  if (erro) return html`<p class="carregando">Não foi possível carregar os dados (${erro}).</p>`;
  if (!P) return html`<p class="carregando">Carregando parlamentares…</p>`;

  const lista = casa === "camara" ? P.deputados : P.senadores;
  const linhas = lista.filter((p) => p.anos[ano]).map((p) => {
    const a = p.anos[ano];
    const part = casa === "camara" ? partidoNoAno(p, ano) : a.partido || "—";
    const base = casa === "camara" ? a.dias_sessao : a.dias_votacao;
    return { p, a, partido: part, base, taxa: base ? a.presencas / base : null };
  });
  const partidos = [...new Set(linhas.map((l) => l.partido))].sort();
  const ufs = [...new Set(linhas.map((l) => l.p.uf))].sort();
  const q = semAcento(busca.trim());
  // um partido ou UF escolhido pode não existir em outro ano ou Casa: nesse caso o filtro não se aplica
  const fPartido = partidos.includes(partido) ? partido : "";
  const fUf = ufs.includes(uf) ? uf : "";
  const filtradas = linhas.filter((l) => (!q || semAcento(l.p.nome).includes(q)) && (!fPartido || l.partido === fPartido) && (!fUf || l.p.uf === fUf));

  const valor = {
    nome: (l) => semAcento(l.p.nome), partido: (l) => l.partido, uf: (l) => l.p.uf,
    base: (l) => l.base, presencas: (l) => l.a.presencas, taxa: (l) => l.taxa ?? -1, cota: (l) => l.a.cota,
    just: (l) => l.a.ausencias_justificadas ?? 0, njust: (l) => l.a.ausencias_nao_justificadas ?? 0,
    comissao: (l) => l.a.reunioes_comissao ?? 0, mandato: (l) => l.a.dias_exercicio ?? 0,
  };
  const f = valor[ordem.col];
  filtradas.sort((x, y) => (f(x) < f(y) ? -1 : f(x) > f(y) ? 1 : 0) * ordem.dir);
  const Th = ({ col, children, cls }) => html`<th class=${cls}><button aria-pressed=${ordem.col === col}
    onClick=${() => setOrdem({ col, dir: ordem.col === col ? -ordem.dir : col === "nome" || col === "partido" || col === "uf" ? 1 : -1 })}>
    ${children}${ordem.col === col ? (ordem.dir > 0 ? " ↑" : " ↓") : ""}</button></th>`;

  const subs = subsidiosDoAno(P.subsidio, ano);
  const totCota = filtradas.reduce((s, l) => s + l.a.cota, 0);
  const Seg = ({ v, set, opcoes }) => html`<div class="seg" role="group">
    ${opcoes.map(([k, r]) => html`<button aria-pressed=${v === k} onClick=${() => set(k)}>${r}</button>`)}</div>`;

  return html`
    <section class="wrap">
      <div class="abertura">
        <div>
          <h1>Deputados e senadores,<br /><span class="anos">2019–2026</span></h1>
          <p>Partido, estado, subsídio do cargo, gastos da cota parlamentar e presença no plenário de quem exerceu mandato
          no Congresso nas legislaturas 2019–2023 e 2023–2027. Dados oficiais da Câmara e do Senado.</p>
        </div>
        <div class="legenda-gov">
          <div><b>Subsídio mensal em ${ano}</b></div>
          ${subs.map((s) => html`<div>${brl2.format(s.valor)} <small>desde ${s.desde.split("-").reverse().join("/")}</small></div>`)}
          <small>Igual para todos os deputados e senadores. Fonte: ${subs.map((s) => s.norma).filter((x, i, a) => a.indexOf(x) === i).map((n) => {
            const u = P.subsidio.find((s) => s.norma === n && s.url)?.url;
            return html`<a href=${u} target="_blank" rel="noopener">${n}</a> `;
          })}</small>
        </div>
      </div>
    </section>
    <div class="controles"><div class="wrap">
      <div class="grupo"><span>Casa</span><${Seg} v=${casa} set=${(c) => { setCasa(c); setPartido(""); }} opcoes=${[["camara", "Câmara"], ["senado", "Senado"]]} /></div>
      <div class="grupo"><span>Ano</span>
        <select class="sel" value=${ano} onChange=${(e) => setAno(e.target.value)}>${P.anos.map((a) => html`<option value=${a}>${a}</option>`)}</select></div>
      <div class="grupo"><span>Partido</span>
        <select class="sel" value=${fPartido} onChange=${(e) => setPartido(e.target.value)}><option value="">Todos</option>${partidos.map((x) => html`<option value=${x}>${x}</option>`)}</select></div>
      <div class="grupo"><span>UF</span>
        <select class="sel" value=${fUf} onChange=${(e) => setUf(e.target.value)}><option value="">Todas</option>${ufs.map((x) => html`<option value=${x}>${x}</option>`)}</select></div>
      <div class="grupo"><input class="busca" type="search" placeholder="Buscar por nome" value=${busca} onInput=${(e) => setBusca(e.target.value)} /></div>
    </div></div>
    <section class="wrap">
      <div class="principal">
        <div>
          <div class="secao-titulo"><h2>${casa === "camara" ? "Câmara dos Deputados" : "Senado Federal"} em ${ano}</h2>
            <span class="nota">${filtradas.length} parlamentares · cota somada: ${brl.format(totCota)}${ano === P.anos[P.anos.length - 1] ? " · ano em curso" : ""}</span></div>
          ${casa === "camara" && ano === "2020" ? html`<p class="aviso-ni">Em 2020, a partir de março, a Câmara votou em sessões remotas por causa da pandemia
            e não registrou frequência nesse período: o registro oficial cobre só os dias com sessão de fevereiro e março. Por isso os números de presença de 2020 são baixos para todos.</p>` : null}
          <div class="rolagem"><table class="tabela tabela-parl">
            <thead><tr>
              <${Th} col="nome">Nome</${Th}><${Th} col="partido" cls="col-opc">Partido</${Th}><${Th} col="uf" cls="col-opc">UF</${Th}>
              <${Th} col="base" cls="col-opc">${casa === "camara" ? "Dias com sessão" : "Dias com votação"}</${Th}>
              <${Th} col="presencas" cls="col-opc">Presente</${Th}><${Th} col="just" cls="col-opc">Ausência justificada</${Th}>
              <${Th} col="njust">Ausência não justificada</${Th}><${Th} col="taxa">% presença</${Th}>
              ${casa === "camara" ? html`<${Th} col="comissao" cls="col-opc">Reuniões de comissão</${Th}><${Th} col="mandato" cls="col-opc">Dias no mandato</${Th}>` : null}
              <${Th} col="cota">Cota parlamentar</${Th}>
            </tr></thead>
            <tbody>${filtradas.map((l) => html`<tr key=${l.p.id}>
              <td class="nome"><b>${l.p.nome}</b><span class="so-celular marcador">${l.partido} · ${l.p.uf}</span>
                <span class="marcador">${l.p.cargo}${l.p.condicao?.includes("Suplente") ? " · assumiu como suplente" : ""}</span></td>
              <td class="col-opc">${l.partido}</td><td class="col-opc">${l.p.uf}</td>
              <td class="col-opc">${nf0.format(l.base)}</td><td class="col-opc">${nf0.format(l.a.presencas)}</td>
              <td class="col-opc" title=${Object.entries(l.a.motivos || {}).map(([m, n]) => `${m}: ${n}`).join("\n")}>${nf0.format(l.a.ausencias_justificadas)}</td>
              <td>${nf0.format(l.a.ausencias_nao_justificadas)}</td>
              <td>${pctTxt(l.a.presencas, l.base)}<span class="so-celular marcador">${l.a.presencas} de ${l.base}</span></td>
              ${casa === "camara" ? html`<td class="col-opc">${nf0.format(l.a.reunioes_comissao)}</td><td class="col-opc">${nf0.format(l.a.dias_exercicio)}</td>` : null}
              <td>${brl.format(l.a.cota)}</td>
            </tr>`)}</tbody>
          </table></div>
          <p class="marcador">${casa === "camara"
            ? "Presença: frequência oficial da Câmara nos dias com sessão deliberativa no Plenário, contados só enquanto o deputado estava em exercício. É o registro usado para descontar do subsídio as faltas sem justificativa. Passe o mouse sobre a ausência justificada para ver os motivos. Reuniões de comissão: reuniões formais (deliberativas, audiências públicas, comparecimento de ministros etc.) com presença registrada; não há total possível para comparar, porque cada deputado integra comissões diferentes."
            : "Presença: dias com votação nominal no Plenário em que o senador esteve presente em ao menos uma votação. São poucos dias por ano (cerca de 35 a 40), porque a maioria das matérias é aprovada em votação simbólica, sem registro individual. Ausências justificadas incluem licenças, missões oficiais e atividade parlamentar fora do plenário."}
            Deputados e senadores não batem ponto: nada disso mede trabalho no gabinete ou no estado. A cota parlamentar reembolsa despesas do mandato (passagens, escritório, divulgação) e não é salário.</p>
        </div>
        <${Cartoes} funcao="Parlamentares" />
      </div>
    </section>`;
}
