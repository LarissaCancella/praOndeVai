// Formatação e regras de cálculo compartilhadas pelo comparador e pelo mapa.
// As mesmas regras valem para os dois governos.

// Anos com calamidade pública reconhecida pelo Congresso (DL 6/2020 e DL 36/2024).
export const CALAMIDADE = ["2020", "2024"];

export const nf1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
export const nf0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
export const fmt = (v) => (v == null ? "—" : Math.abs(v) >= 100 ? nf0.format(v) : nf1.format(v));
export const fmtVar = (v) => (v == null ? "—" : Math.abs(v) < 0.05 ? "0,0" : `${v > 0 ? "▲ +" : "▼ −"}${fmt(Math.abs(v))}`);
export const pct = (a, b) => (a == null || b == null || Math.abs(a) < 0.05 ? null : (b / a - 1) * 100);
export const fmtPct = (p) => (p == null ? "n/d" : `${p > 0 ? "+" : p < 0 ? "−" : ""}${nf1.format(Math.abs(p))}%`);
export const slug = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
const MESES = ["", "jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
export const mesAno = (s) => { const [a, m] = s.split("-"); return `${MESES[+m]}/${a}`; };
export const media = (xs) => (xs.length ? xs.reduce((s, x) => s + x, 0) / xs.length : null);
export const faixa = (xs) => (xs.length ? `${xs[0]}–${xs[xs.length - 1].slice(2)}` : "—");

// `D` precisa de anos_anual e anos_parcial; `g` é um governo {inicio, fim}.
export function anosDoGoverno(D, g, op) {
  const anos = op.recorte === "anual" ? D.anos_anual : D.anos_parcial;
  return anos.filter((a) => +a >= g.inicio && +a <= g.fim && !(op.semCalamidade && CALAMIDADE.includes(a)));
}

export const unidade = (D, op) => (op.valores === "real" ? `R$ bilhões de ${mesAno(D.preco_base)}` : "R$ bilhões correntes");
