"""
Coleta a despesa da União por função (Saúde, Educação, Previdência...) de 2019 até o
último bimestre publicado e gera data/funcoes.json para o front-end.

Fontes
  - Tesouro Nacional / SICONFI, RREO Anexo 02 (despesa por função e subfunção), ente 1 = União
    https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo
  - Banco Central, série SGS 433 (IPCA mensal)
    https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados

Método (documentar no site)
  - Ano fechado: despesa EMPENHADA até o 6º bimestre (= liquidada + restos a pagar não processados).
  - Mesmo período (jan–ago): despesa LIQUIDADA até o 4º bimestre. O empenho no começo do ano
    reserva o valor anual de despesas obrigatórias, então liquidado é o que compara melhor no meio do ano.
  - Correção pela inflação: IPCA, trazendo cada valor a preços do último mês publicado.
    Ano fechado usa o índice médio do ano; jan–ago usa o índice médio de jan a ago.
  - Linha "Total das Despesas Exceto Intra-Orçamentárias" (evita dupla contagem entre órgãos).
  - "Encargos Especiais" (juros, amortização e refinanciamento da dívida, transferências constitucionais)
    fica separado: ele é maior que todas as outras funções juntas e oscila com a rolagem da dívida.

Uso:  python etl/funcoes.py  [--ano-inicio 2019] [--saida data/funcoes.json]
Requer apenas a biblioteca padrão do Python.
"""

from __future__ import annotations

import argparse
import gzip
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

SICONFI = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo"
BCB_IPCA = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"
ROTULO = "Total das Despesas Exceto Intra-Orçamentárias"
COL_EMPENHADO = "DESPESAS EMPENHADAS ATÉ"
COL_LIQUIDADO = "DESPESAS LIQUIDADAS ATÉ"
COL_DOTACAO = "DOTAÇÃO ATUALIZADA"

FUNCOES = [
    "Legislativa", "Judiciária", "Essencial à Justiça", "Administração", "Defesa Nacional",
    "Segurança Pública", "Relações Exteriores", "Assistência Social", "Previdência Social",
    "Saúde", "Trabalho", "Educação", "Cultura", "Direitos da Cidadania", "Urbanismo",
    "Habitação", "Saneamento", "Gestão Ambiental", "Ciência e Tecnologia", "Agricultura",
    "Organização Agrária", "Indústria", "Comércio e Serviços", "Comunicações", "Energia",
    "Transporte", "Desporto e Lazer", "Encargos Especiais",
]
ENCARGOS = "Encargos Especiais"

# Governos: o ano é atribuído a quem governou durante a execução.
# Observação para o site: o orçamento de 2019 foi proposto pelo governo anterior e o de 2023
# também (PLOA enviado em 2022, alterado pela PEC da Transição).
GOVERNOS = [
    {"id": "bolsonaro", "nome": "Jair Bolsonaro", "partido": "PL", "inicio": 2019, "fim": 2022},
    {"id": "lula3", "nome": "Luiz Inácio Lula da Silva", "partido": "PT", "inicio": 2023, "fim": 2026},
]


def get_json(url: str, params: dict, tentativas: int = 4) -> object:
    full = url + "?" + urllib.parse.urlencode(params)
    for i in range(tentativas):
        try:
            req = urllib.request.Request(full, headers={"Accept": "application/json",
                                                        "User-Agent": "transparencia-etl/0.1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                corpo = r.read()
            if corpo[:2] == b"\x1f\x8b":  # o IBGE responde em gzip mesmo sem pedir
                corpo = gzip.decompress(corpo)
            return json.loads(corpo.decode("utf-8"))
        except Exception as e:  # rede instável nas APIs públicas é comum
            if i == tentativas - 1:
                raise RuntimeError(f"Falha ao baixar {full}: {e}") from e
            time.sleep(2 ** i)
    raise AssertionError


RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def rreo_anexo02(ano: int, periodo: int) -> list[dict]:
    """Itens do RREO Anexo 02 da União. Lista vazia se o bimestre ainda não foi publicado.
    Bimestres publicados ficam em cache em data/raw/."""
    cache = RAW / f"rreo_a02_{ano}_{periodo}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    itens, offset = [], 0
    while True:
        j = get_json(SICONFI, {
            "an_exercicio": ano, "nr_periodo": periodo, "co_tipo_demonstrativo": "RREO",
            "no_anexo": "RREO-Anexo 02", "id_ente": 1, "offset": offset,
        })
        itens += j.get("items", [])
        if not j.get("hasMore"):
            break
        offset += len(j.get("items", []))
    if itens:
        RAW.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(itens, ensure_ascii=False), encoding="utf-8")
    return itens


def _chave(coluna: str) -> str | None:
    return ("empenhado" if coluna.startswith(COL_EMPENHADO) else
            "liquidado" if coluna.startswith(COL_LIQUIDADO) else
            "dotacao" if coluna.startswith(COL_DOTACAO) else None)


def por_funcao(itens: list[dict]) -> dict[str, dict[str, float]]:
    """{funcao: {"empenhado": R$, "liquidado": R$, "dotacao": R$}} só com as 28 funções."""
    out: dict[str, dict[str, float]] = {}
    for i in itens:
        if i.get("rotulo") != ROTULO:
            continue
        nome = (i.get("conta") or "").strip()
        if nome not in FUNCOES:
            continue  # subfunções e linhas de total ficam de fora
        chave = _chave(i.get("coluna") or "")
        if chave:
            out.setdefault(nome, {})[chave] = float(i["valor"])
    return out


def por_subfuncao(itens: list[dict]) -> dict[str, dict[str, dict[str, float]]]:
    """{funcao: {subfuncao: {"empenhado": R$, "liquidado": R$}}}.

    O Anexo 02 não traz o código da função pai: cada função vem seguida das suas subfunções,
    terminando em "FUxx - Administração Geral" e "FUxx - Demais Subfunções". Usa essa ordem
    (dentro de cada coluna) e confere que as subfunções somam o total da função."""
    out: dict = {}
    totais: dict = {}
    atual: dict[str, str | None] = {}
    for i in itens:
        if i.get("rotulo") != ROTULO:
            continue
        chave = _chave(i.get("coluna") or "")
        if chave not in ("empenhado", "liquidado"):
            continue
        nome = (i.get("conta") or "").strip()
        if nome in FUNCOES:
            atual[chave] = nome
            totais[(nome, chave)] = float(i["valor"])
            continue
        if nome.isupper() or nome.startswith("TOTAL"):
            atual[chave] = None  # linhas de total (I), (II), (III)
            continue
        pai = atual.get(chave)
        if pai is None:
            continue
        if nome[:2] == "FU" and " - " in nome:
            nome = nome.split(" - ", 1)[1]
        d = out.setdefault(pai, {}).setdefault(nome, {})
        d[chave] = d.get(chave, 0.0) + float(i["valor"])
    for (f, chave), v in totais.items():
        soma = sum(s.get(chave, 0.0) for s in out.get(f, {}).values())
        if abs(soma - v) > max(1.0, abs(v) * 1e-6):
            raise ValueError(f"Subfunções de {f} ({chave}) somam {soma:.2f}, função = {v:.2f}")
    return out


def ipca_indice(ano_inicio: int) -> tuple[dict[str, float], str]:
    """Índice encadeado mensal {"AAAA-MM": índice} e o último mês disponível."""
    hoje = date.today()
    dados = get_json(BCB_IPCA, {"formato": "json", "dataInicial": f"01/01/{ano_inicio}",
                                "dataFinal": hoje.strftime("%d/%m/%Y")})
    idx, acc = {}, 1.0
    for d in dados:
        dd, mm, aaaa = d["data"].split("/")
        acc *= 1 + float(d["valor"]) / 100
        idx[f"{aaaa}-{mm}"] = acc
    return idx, max(idx)


def fator(idx: dict[str, float], base: str, ano: int, ate_mes: int) -> float:
    meses = [idx[f"{ano}-{m:02d}"] for m in range(1, ate_mes + 1) if f"{ano}-{m:02d}" in idx]
    return idx[base] / (sum(meses) / len(meses))


def media(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ano-inicio", type=int, default=2019)
    ap.add_argument("--saida", default=str(Path(__file__).resolve().parent.parent / "data" / "funcoes.json"))
    args = ap.parse_args()

    ano_atual = date.today().year
    idx, base = ipca_indice(args.ano_inicio)

    anual: dict[int, dict] = {}    # anos fechados, 6º bimestre
    parcial: dict[int, dict] = {}  # mesmo período de todos os anos
    sub_anual: dict[int, dict] = {}
    sub_parcial: dict[int, dict] = {}
    ultimo_periodo_atual = 0

    # descobre o último bimestre publicado do ano corrente
    for p in range(6, 0, -1):
        itens = rreo_anexo02(ano_atual, p)
        if itens:
            ultimo_periodo_atual = p
            parcial[ano_atual] = por_funcao(itens)
            sub_parcial[ano_atual] = por_subfuncao(itens)
            break
    if not ultimo_periodo_atual:
        raise SystemExit(f"Nenhum bimestre de {ano_atual} publicado ainda.")
    mes_corte = ultimo_periodo_atual * 2

    for ano in range(args.ano_inicio, ano_atual):
        itens = rreo_anexo02(ano, 6)
        anual[ano], sub_anual[ano] = por_funcao(itens), por_subfuncao(itens)
        itens = rreo_anexo02(ano, ultimo_periodo_atual)
        parcial[ano], sub_parcial[ano] = por_funcao(itens), por_subfuncao(itens)
        print(f"{ano}: ok", flush=True)

    deflator_anual = {str(a): fator(idx, base, a, 12) for a in sorted(anual)}
    deflator_parcial = {str(a): fator(idx, base, a, mes_corte) for a in sorted(parcial)}

    def real(valor: float, ano: int, ate_mes: int) -> float:
        return valor * fator(idx, base, ano, ate_mes) / 1e9  # R$ bilhões a preços de `base`

    funcoes_out = []
    for f in FUNCOES:
        serie_anual = {str(a): round(real(anual[a].get(f, {}).get("empenhado", 0.0), a, 12), 3)
                       for a in sorted(anual)}
        serie_nominal = {str(a): round(anual[a].get(f, {}).get("empenhado", 0.0) / 1e9, 3)
                         for a in sorted(anual)}
        serie_parcial = {str(a): round(real(parcial[a].get(f, {}).get("liquidado", 0.0), a, mes_corte), 3)
                         for a in sorted(parcial)}
        serie_parcial_nominal = {str(a): round(parcial[a].get(f, {}).get("liquidado", 0.0) / 1e9, 3)
                                 for a in sorted(parcial)}
        nomes_sub = list(dict.fromkeys(s for a in sub_anual for s in sub_anual[a].get(f, {})))
        subfuncoes = [{
            "subfuncao": s,
            "anual_nominal": {str(a): round(sub_anual[a].get(f, {}).get(s, {}).get("empenhado", 0.0) / 1e9, 3)
                              for a in sorted(sub_anual)},
            "parcial_nominal": {str(a): round(sub_parcial[a].get(f, {}).get(s, {}).get("liquidado", 0.0) / 1e9, 3)
                                for a in sorted(sub_parcial)},
        } for s in nomes_sub]
        por_gov = {}
        for g in GOVERNOS:
            anos = range(g["inicio"], g["fim"] + 1)
            por_gov[g["id"]] = {
                "media_anual": media([serie_anual[str(a)] for a in anos if str(a) in serie_anual]),
                "anos_fechados": [a for a in anos if str(a) in serie_anual],
                "media_parcial": media([serie_parcial[str(a)] for a in anos if str(a) in serie_parcial]),
            }
        funcoes_out.append({"funcao": f, "encargos": f == ENCARGOS, "anual_real": serie_anual,
                            "anual_nominal": serie_nominal, "parcial_real": serie_parcial,
                            "parcial_nominal": serie_parcial_nominal,
                            "governos": por_gov, "subfuncoes": subfuncoes})

    def total(serie: str, ano: str, com_encargos: bool) -> float:
        return round(sum(x[serie][ano] for x in funcoes_out if com_encargos or not x["encargos"]), 3)

    saida = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "unidade": f"R$ bilhões, a preços de {base} (IPCA)",
        "preco_base": base,
        "parcial": {"ate_mes": mes_corte, "bimestre": ultimo_periodo_atual,
                    "descricao": f"janeiro a {['', 'fevereiro', 'abril', 'junho', 'agosto', 'outubro', 'dezembro'][ultimo_periodo_atual]}"},
        "governos": GOVERNOS,
        "deflator": {"anual": deflator_anual, "parcial": deflator_parcial},
        "totais": {
            "anual_sem_encargos": {a: total("anual_real", a, False) for a in map(str, sorted(anual))},
            "anual_com_encargos": {a: total("anual_real", a, True) for a in map(str, sorted(anual))},
            "parcial_sem_encargos": {a: total("parcial_real", a, False) for a in map(str, sorted(parcial))},
        },
        "funcoes": funcoes_out,
        "fontes": [
            {"nome": "Tesouro Nacional, SICONFI, RREO Anexo 02 (União)", "url": SICONFI},
            {"nome": "Banco Central, SGS 433 (IPCA)", "url": BCB_IPCA},
        ],
    }
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Gerado {args.saida}  (base {base}, parcial até o mês {mes_corte})")


if __name__ == "__main__":
    main()
