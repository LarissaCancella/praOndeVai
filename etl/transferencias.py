"""
Transferências da União a estados, municípios e entidades, por UF do favorecido, de 2019 até o
último mês publicado. Gera site/data/mapa.json para o mapa do site.

Fontes
  - CGU, Portal da Transparência, "Transferências" (arquivos mensais em CSV, sem chave)
    https://portaldatransparencia.gov.br/download-de-dados/transferencias/AAAAMM
  - IBGE, Censo 2022, população residente por UF (agregado 4709, variável 93)
  - Banco Central, IPCA (mesmo índice de etl/funcoes.py)

Método
  - Cada arquivo traz o valor transferido no mês. Ano fechado = soma de jan a dez; recorte parcial =
    soma de jan até o mesmo mês de corte do comparador (data/funcoes.json → parcial.ate_mes).
  - Correção pela inflação mês a mês: valor × IPCA(base) / IPCA(mês).
  - Categorias: "constitucionais" = tipo "Constitucionais e Royalties" (FPE, FPM, Fundeb, royalties,
    repartidas por fórmula legal); "demais" = "Legais, Voluntárias e Específicas" (SUS fundo a fundo,
    complementação do Fundeb, convênios, emendas); "investimento" = linhas com grupo de despesa 4.
  - Por habitante: população do Censo 2022 para todos os anos (mesmo denominador nos dois períodos).
  - Linhas sem UF válida entram em "NI" (não identificado) e aparecem separadas no site.
  - Nos estados entram só repasses a governos (administração pública estadual, municipal e demais
    órgãos e fundos públicos). Entidades privadas, empresas, agentes intermediários e organismos
    internacionais com UF vão para "FORA" (fora do mapa, contabilizados no método).

Uso:  python etl/transferencias.py
Os arquivos mensais agregados ficam em data/raw/transf/ (cache); os .zip são apagados após o uso.
"""

from __future__ import annotations

import csv
import io
import json
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

from funcoes import get_json, ipca_indice

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "data" / "raw" / "transf"
PORTAL = "https://portaldatransparencia.gov.br/download-de-dados/transferencias/{}"
IBGE_POP = "https://servicodados.ibge.gov.br/api/v3/agregados/4709/periodos/2022/variaveis/93"

UFS = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA",
    "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS",
    "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}
SIGLAS = set(UFS.values())
CONSTITUCIONAIS = "Constitucionais e Royalties"

# colunas do CSV (cabeçalho com acentos em latin-1; índices conferidos em 2022 e 2025)
C_TIPO, C_FAV, C_UF, C_GND, C_ACAO, C_NOME_ACAO, C_VALOR = 1, 2, 3, 19, 16, 17, 35

# Tipo de favorecido → código curto. O mapa usa só governos (E, M e P: estados, municípios e
# demais órgãos e fundos públicos, como fundos de saúde). "O" (entidades privadas, empresas, agentes
# intermediários, organismos internacionais) fica fora do mapa: a sede do favorecido não indica
# o estado beneficiado (ex.: Conta de Desenvolvimento Energético, gerida em SP).
FAVORECIDO = {
    "Administração Pública Estadual ou do Distrito Federal": "E",
    "Administração Pública Municipal": "M",
    "Administração Pública": "P",
}
GOVERNOS_FAV = {"E", "M", "P"}


def baixar(mes: str, tentativas: int = 5) -> bytes | None:
    """O servidor da CGU bloqueia temporariamente (HTTP 405) após muitos downloads seguidos:
    espera entre arquivos e tenta de novo com espera crescente. None = mês não publicado."""
    req = urllib.request.Request(PORTAL.format(mes), headers={"User-Agent": "transparencia-etl/0.1"})
    for i in range(tentativas):
        time.sleep(20 if i == 0 else 120 * 2 ** (i - 1))
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                dados = r.read()
            if dados[:2] == b"PK":
                return dados
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
        print(f"  {mes}: tentativa {i + 1} falhou, aguardando", flush=True)
    return None


def agrega_mes(mes: str) -> dict | None:
    """{"UF|cat|inv|acao|fav": valor} do mês, com cache em JSON. None se o mês não foi publicado."""
    cache = CACHE / f"{mes}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    dados = baixar(mes)
    if dados is None:
        return None
    z = zipfile.ZipFile(io.BytesIO(dados))
    leitor = csv.reader(io.TextIOWrapper(z.open(z.infolist()[0]), encoding="latin-1"), delimiter=";")
    cab = next(leitor)
    if not cab[C_VALOR].startswith("VALOR TRANSFERIDO") or cab[C_UF] != "UF" or not cab[C_FAV].startswith("TIPO FAVORECIDO"):
        raise ValueError(f"Layout inesperado em {mes}: {cab}")
    out: dict[str, float] = {}
    nomes: dict[str, str] = {}
    for l in leitor:
        uf = l[C_UF].strip()
        uf = uf if uf in SIGLAS else "NI"
        cat = "constitucionais" if l[C_TIPO] == CONSTITUCIONAIS else "demais"
        inv = "1" if l[C_GND].strip() == "4" else "0"
        acao = l[C_ACAO].strip()
        nomes[acao] = l[C_NOME_ACAO].strip()
        fav = FAVORECIDO.get(l[C_FAV].strip(), "O")
        k = f"{uf}|{cat}|{inv}|{acao}|{fav}"
        out[k] = out.get(k, 0.0) + float(l[C_VALOR].replace(".", "").replace(",", ".") or 0)
    res = {"valores": out, "acoes": nomes}
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    return res


TESOURO_CKAN = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
TESOURO_ESTADOS = "8add38c3-cf27-4428-940e-806548cac95c"  # "Transferências Constitucionais Para Estados"
ACAO_FPE = "0044"


def confere_fpe(meses: dict[str, dict], amostra: list[str]) -> list[dict]:
    """Compara o FPE por UF (ação 0044) do Portal da Transparência com o arquivo mensal do
    Tesouro Nacional. Retorna uma linha por mês com o total e a maior diferença por UF."""
    recursos = get_json(TESOURO_CKAN, {"id": TESOURO_ESTADOS})["result"]["resources"]
    urls: dict[str, tuple[str, str]] = {}
    for r in recursos:  # o mesmo mês pode ter várias versões; fica a mais recente
        nome = r["name"].replace(".csv", "")
        if nome.startswith("Transferencia_Mensal_Estados_"):
            mes, mod = nome[-6:], r.get("last_modified") or ""
            # sem data de modificação, vale a ordem da lista (a versão publicada por último vem depois)
            if mes not in urls or mod >= urls[mes][1]:
                urls[mes] = (r["url"], mod)
    out = []
    for mes in amostra:
        if mes not in urls or mes not in meses:
            continue
        req = urllib.request.Request(urls[mes][0], headers={"User-Agent": "transparencia-etl/0.1"})
        with urllib.request.urlopen(req, timeout=120) as r:
            texto = r.read().decode("latin-1")
        tes: dict[str, float] = {}
        for l in csv.reader(io.StringIO(texto), delimiter=";"):
            if len(l) > 7 and l[6] == "FPE" and l[7] == "FPE":
                tes[l[0]] = tes.get(l[0], 0.0) + sum(float(x or 0) for x in l[3:6])
        portal: dict[str, float] = {}
        for k, v in meses[mes]["valores"].items():
            uf, _, _, acao, _ = k.split("|")
            if acao == ACAO_FPE:
                portal[uf] = portal.get(uf, 0.0) + v
        difs = [abs(portal.get(uf, 0.0) - tes.get(uf, 0.0)) for uf in SIGLAS]
        out.append({"mes": f"{mes[:4]}-{mes[4:]}", "fpe_portal": round(sum(portal.values()) / 1e9, 4),
                    "fpe_tesouro": round(sum(tes.values()) / 1e9, 4), "maior_dif_uf_reais": round(max(difs), 2)})
    return out


def populacao() -> dict[str, int]:
    j = get_json(IBGE_POP, {"localidades": "N3[all]"})
    return {UFS[s["localidade"]["id"]]: int(s["serie"]["2022"]) for s in j[0]["resultados"][0]["series"]}


def main() -> None:
    fun = json.loads((RAIZ / "data" / "funcoes.json").read_text(encoding="utf-8"))
    base, ate_mes = fun["preco_base"], fun["parcial"]["ate_mes"]
    idx, _ = ipca_indice(2019)

    # coleta de jan/2019 até o mês de corte do ano corrente (o mesmo do comparador). Os arquivos
    # mais recentes do Portal chegam incompletos: em 09/10/2026 o de set/2026 não tinha nenhuma
    # transferência constitucional.
    meses, hoje = {}, date.today()
    limite = min((int(base[:4]), int(base[5:])), (hoje.year, ate_mes))
    for ano in range(2019, hoje.year + 1):
        for m in range(1, 13):
            if (ano, m) > limite:
                break
            chave = f"{ano}{m:02d}"
            res = agrega_mes(chave)
            if res is None:
                if ano == hoje.year:
                    break
                raise SystemExit(f"Mês {chave} não encontrado no Portal da Transparência.")
            if not any(k.split("|")[1] == "constitucionais" for k in res["valores"]):
                raise SystemExit(f"Mês {chave} parece incompleto (sem transferências constitucionais). "
                                 f"Apague data/raw/transf/{chave}.json e tente mais tarde.")
            meses[chave] = res
            print(f"{chave}: ok", flush=True)
    ultimo = max(meses)
    ano_atual = int(ultimo[:4])
    if int(ultimo[4:]) < ate_mes:
        raise SystemExit(f"Transferências só até {ultimo}; o recorte parcial vai até o mês {ate_mes}.")

    def fator(mes: str) -> float:
        return idx[base] / idx[f"{mes[:4]}-{mes[4:]}"]

    anos_anual = [str(a) for a in range(2019, ano_atual)]
    anos_parcial = [str(a) for a in range(2019, ano_atual + 1)]
    categorias = ("todas", "constitucionais", "demais", "investimento")

    def entra(cat: str, k_cat: str, k_inv: str) -> bool:
        return cat == "todas" or (cat == "investimento" and k_inv == "1") or cat == k_cat

    # séries[cat][uf][recorte][valores][ano]. Nos estados entram só repasses a governos; "NI" (sem UF)
    # soma todos os favorecidos; "FORA" = favorecidos não governamentais com UF (fora do mapa).
    vazio = lambda: {r: {v: {} for v in ("real", "nominal")} for r in ("anual", "parcial")}
    series = {c: {uf: vazio() for uf in sorted(SIGLAS) + ["NI", "FORA"]} for c in categorias}
    acoes_uf: dict[str, dict[str, dict[str, float]]] = {}  # uf → acao → ano → real (ano fechado)
    nomes_acao: dict[str, str] = {}

    for mes, res in sorted(meses.items()):
        ano, m = mes[:4], int(mes[4:])
        f = fator(mes)
        nomes_acao.update(res["acoes"])
        for k, v in res["valores"].items():
            uf, k_cat, k_inv, acao, fav = k.split("|")
            if uf != "NI" and fav not in GOVERNOS_FAV:
                uf = "FORA"
            for c in categorias:
                if not entra(c, k_cat, k_inv):
                    continue
                s = series[c][uf]
                if ano in anos_anual:
                    s["anual"]["nominal"][ano] = s["anual"]["nominal"].get(ano, 0.0) + v
                    s["anual"]["real"][ano] = s["anual"]["real"].get(ano, 0.0) + v * f
                if m <= ate_mes:
                    s["parcial"]["nominal"][ano] = s["parcial"]["nominal"].get(ano, 0.0) + v
                    s["parcial"]["real"][ano] = s["parcial"]["real"].get(ano, 0.0) + v * f
            if ano in anos_anual and uf in SIGLAS:
                a = acoes_uf.setdefault(uf, {}).setdefault(acao, {})
                a[ano] = a.get(ano, 0.0) + v * f

    def bi(d: dict) -> dict:
        return {r: {v: {a: round(x / 1e9, 4) for a, x in sorted(d[r][v].items())} for v in d[r]} for r in d}

    pop = populacao()
    # só dezembros: o arquivo mensal do Tesouro sai no dia 8 com o mês em andamento e a versão
    # final pode demorar (em 09/10/2026 o de ago/2026 ainda era o parcial de 08/08)
    amostra = [f"{a}12" for a in anos_anual]
    conferencia = confere_fpe(meses, amostra)
    for c in conferencia:
        print("  conferência FPE:", c)
    principais = {}
    for uf, acoes in acoes_uf.items():
        top = sorted(acoes.items(), key=lambda x: -sum(x[1].values()))[:10]
        principais[uf] = [{"acao": a, "nome": nomes_acao.get(a, a),
                           "anual_real": {ano: round(x / 1e9, 4) for ano, x in sorted(s.items())}} for a, s in top]

    saida = {
        "preco_base": base,
        "parcial": fun["parcial"],
        "ultimo_mes": f"{ultimo[:4]}-{ultimo[4:]}",
        "anos_anual": anos_anual, "anos_parcial": anos_parcial,
        "populacao": {"fonte": "IBGE, Censo 2022", "uf": pop},
        "series": {c: {uf: bi(s) for uf, s in series[c].items()} for c in categorias},
        "principais_acoes": principais,
        "conferencia_fpe": conferencia,
        "fontes": [
            {"nome": "CGU, Portal da Transparência, Transferências (arquivos mensais)", "url": PORTAL.format("AAAAMM")},
            {"nome": "IBGE, Censo 2022, população por UF", "url": IBGE_POP},
            {"nome": "Tesouro Nacional, Transferências Constitucionais Para Estados (conferência do FPE)",
             "url": f"https://www.tesourotransparente.gov.br/ckan/dataset/{TESOURO_ESTADOS}"},
        ],
    }
    destino = RAIZ / "site" / "data" / "mapa.json"
    destino.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Gerado {destino} ({destino.stat().st_size // 1024} KB), meses {min(meses)}–{ultimo}")


if __name__ == "__main__":
    main()
