"""
Despesa da União por função × subfunção × grupo de natureza da despesa (GND), a partir da
Matriz de Saldos Contábeis (MSC) orçamentária publicada no SICONFI. Gera data/gnd.json.

Serve para separar o gasto direto das operações financeiras (GND 5, inversões financeiras:
empréstimos de fundos como FNDCT e Fundo Clima, integralização de cotas etc.), que o
RREO Anexo 02 não distingue.

Fonte
  - Tesouro Nacional / SICONFI, MSC orçamentária, classe 6, saldo final do mês, ente 1 = União
    https://apidatalake.tesouro.gov.br/ords/siconfi/tt/msc_orcamentaria

Contas de execução da despesa (PCASP, classe 6)
  6.2.2.1.3.01  crédito empenhado a liquidar
  6.2.2.1.3.02  crédito empenhado em liquidação
  6.2.2.1.3.03  crédito empenhado liquidado a pagar
  6.2.2.1.3.04  crédito empenhado liquidado pago
  6.2.2.1.3.05  empenhado a liquidar inscrito em restos a pagar não processados (fim do ano)
  6.2.2.1.3.06  empenhado em liquidação inscrito em restos a pagar não processados (fim do ano)
  6.2.2.1.3.07  empenhado liquidado inscrito em restos a pagar processados (fim do ano)
  empenhado = 01 a 07 (confere com a conta de controle 6.2.2.9.2.09);  liquidado = 03 + 04 + 07
Natureza da despesa "CGMMEE00": C = categoria econômica, G = GND, MM = modalidade, EE = elemento.
Modalidade 91 (aplicação direta entre órgãos do orçamento) é intra-orçamentária e fica de fora,
para bater com a linha "Exceto Intra-Orçamentárias" do RREO.

Uso:  python etl/gnd.py
Requer apenas a biblioteca padrão do Python. Respostas brutas ficam em data/raw/ (cache).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from funcoes import FUNCOES, get_json

MSC = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/msc_orcamentaria"
RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"

EMPENHADO = {f"62213{i:02d}00" for i in range(1, 8)}
LIQUIDADO = {"622130300", "622130400", "622130700"}

GND = {
    "1": "Pessoal e encargos", "2": "Juros e encargos da dívida", "3": "Outras despesas correntes",
    "4": "Investimentos", "5": "Inversões financeiras", "6": "Amortização da dívida",
}
# código da função no PCASP (01..28) na mesma ordem da lista do RREO
COD_FUNCAO = {f"{i + 1:02d}": nome for i, nome in enumerate(FUNCOES)}


def msc_execucao(ano: int, mes: int) -> list[dict]:
    """Linhas da MSC (classe 6, saldo final) que são contas de execução da despesa. Usa cache."""
    cache = RAW / f"msc_{ano}_{mes:02d}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    linhas, offset = [], 0
    while True:
        j = get_json(MSC, {"id_ente": 1, "an_referencia": ano, "me_referencia": mes,
                           "co_tipo_matriz": "MSCC", "classe_conta": 6,
                           "id_tv": "ending_balance", "offset": offset})
        itens = j.get("items", [])
        linhas += [{k: i[k] for k in ("conta_contabil", "funcao", "subfuncao", "natureza_despesa", "valor")}
                   for i in itens if i["conta_contabil"] in EMPENHADO]
        if not j.get("hasMore") or not itens:
            break
        offset += len(itens)
    RAW.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(linhas, ensure_ascii=False), encoding="utf-8")
    return linhas


def agrega(linhas: list[dict]) -> dict:
    """{funcao: {subfuncao: {gnd: {"empenhado": R$, "liquidado": R$}}}}, sem intra-orçamentárias."""
    out: dict = {}
    for l in linhas:
        nd = l["natureza_despesa"] or ""
        if len(nd) < 4 or nd[2:4] == "91" or not l["funcao"]:
            continue
        nome = COD_FUNCAO.get(l["funcao"])
        if nome is None:
            continue
        d = out.setdefault(nome, {}).setdefault(l["subfuncao"], {}).setdefault(nd[1], {"empenhado": 0.0, "liquidado": 0.0})
        d["empenhado"] += l["valor"]
        if l["conta_contabil"] in LIQUIDADO:
            d["liquidado"] += l["valor"]
    return out


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", default="2019-2025", help="anos fechados (mês 12), ex.: 2019-2025")
    ap.add_argument("--parcial", default="2019-2026:8", help="anos e mês do recorte parcial, ex.: 2019-2026:8")
    args = ap.parse_args()

    a0, a1 = map(int, args.anos.split("-"))
    faixa, mes_p = args.parcial.split(":")
    p0, p1 = map(int, faixa.split("-"))
    mes_p = int(mes_p)

    anual, parcial = {}, {}
    for ano in range(a0, a1 + 1):
        anual[str(ano)] = agrega(msc_execucao(ano, 12))
        print(f"{ano}-12: ok", flush=True)
    for ano in range(p0, p1 + 1):
        parcial[str(ano)] = agrega(msc_execucao(ano, mes_p))
        print(f"{ano}-{mes_p:02d}: ok", flush=True)

    saida = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "unidade": "R$ correntes (nominal)",
        "gnd": GND,
        "parcial_ate_mes": mes_p,
        "anual": anual,      # use "empenhado"
        "parcial": parcial,  # use "liquidado"
        "fonte": {"nome": "Tesouro Nacional, SICONFI, MSC orçamentária (União)", "url": MSC},
    }
    destino = RAIZ / "data" / "gnd.json"
    destino.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Gerado {destino}")


if __name__ == "__main__":
    main()
