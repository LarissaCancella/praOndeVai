"""
Deputados federais e senadores das legislaturas 56 (2019–2023) e 57 (2023–2027): partido, UF,
cargo, subsídio do cargo, gastos da cota parlamentar e presença em plenário, por ano.
Gera site/data/parlamentares.json.

Fontes
  - Câmara dos Deputados, Dados Abertos: API v2 (deputados e histórico de exercício) e arquivos
    anuais de eventos, presença em eventos e cota parlamentar (CEAP)
  - Senado Federal, Dados Abertos: votações nominais (com o registro de presença e de ausência de
    cada senador) e lista de senadores por legislatura; cota (CEAPS) no Portal da Transparência do Senado
  - Subsídio: Decretos Legislativos 276/2014 e 172/2022 (iguais para deputados e senadores)

Presença (deputados e senadores não batem ponto; não existe registro de "dias trabalhados")
  - Câmara, Plenário: frequência oficial nos dias com sessão deliberativa (serviço
    ListarPresencasParlamentar), com presença, ausência justificada (e motivo) e ausência não
    justificada. É o registro usado para o desconto de faltas. Consultado para cada nº de carteira
    parlamentar (1 a 700) em cada legislatura e associado ao deputado pelo nome devolvido.
    Em 2020, durante as sessões remotas da pandemia, a frequência só foi registrada em 13 dias.
  - Câmara, comissões: reuniões formais de comissão encerradas com presença registrada (arquivo de
    presença em eventos). Não há denominador: cada deputado integra comissões diferentes.
  - Senado: dias com votação nominal no Plenário. Em cada votação o Senado registra cada senador em
    exercício como votante, presente sem votar ou ausente com motivo (licença, missão, atividade
    parlamentar) ou sem justificativa ("NCom"). Um dia conta como presença se o senador esteve
    presente em ao menos uma votação daquele dia.
  Nenhuma das duas mede trabalho em comissões, gabinete ou nos estados.

Uso:  python etl/parlamentares.py
Requer apenas a biblioteca padrão do Python. Downloads ficam em data/raw/parl/ (cache).
"""

from __future__ import annotations

import csv
import io
import json
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path

from funcoes import get_json

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "data" / "raw" / "parl"
CAMARA_API = "https://dadosabertos.camara.leg.br/api/v2"
CAMARA_ARQ = "https://dadosabertos.camara.leg.br/arquivos"
CAMARA_CEAP = "https://www.camara.leg.br/cotas/Ano-{}.csv.zip"
SENADO_API = "https://legis.senado.leg.br/dadosabertos"
SENADO_CEAPS = "https://www.senado.gov.br/transparencia/LAI/verba/despesa_ceaps_{}.csv"

LEGISLATURAS = {56: (date(2019, 2, 1), date(2023, 1, 31)), 57: (date(2023, 2, 1), date(2027, 1, 31))}
ANO_INICIO = 2019

# Subsídio mensal de deputados e senadores (o mesmo valor para os dois cargos).
SUBSIDIO = [
    {"desde": "2015-02-01", "valor": 33763.00, "norma": "Decreto Legislativo 276/2014",
     "url": "https://www2.camara.leg.br/legin/fed/decleg/2014/decretolegislativo-276-18-dezembro-2014-779806-publicacaooriginal-145682-pl.html"},
    {"desde": "2023-01-01", "valor": 39293.32, "norma": "Decreto Legislativo 172/2022",
     "url": "https://www2.camara.leg.br/legin/fed/decleg/2022/decretolegislativo-172-21-dezembro-2022-793529-republicacao-166629-pl.html"},
    {"desde": "2023-04-01", "valor": 41650.92, "norma": "Decreto Legislativo 172/2022", "url": None},
    {"desde": "2024-02-01", "valor": 44008.52, "norma": "Decreto Legislativo 172/2022", "url": None},
    {"desde": "2025-02-01", "valor": 46366.19, "norma": "Decreto Legislativo 172/2022", "url": None},
]

# Códigos de voto do Senado que indicam presença em plenário. "NCom" = não compareceu (sem justificativa).
# Os demais códigos de ausência (AP, MIS, LS, LP, LAP, etc.) são ausências justificadas.
SENADO_PRESENTE = {"Sim", "Não", "Abstenção", "P-NRV", "P-OD", "Obstrução", "Votou"}
SENADO_NAO_JUSTIFICADA = {"NCom"}


def baixar(url: str, nome: str, pausa: float = 1.0, timeout: int = 300) -> bytes:
    """Baixa com cache em data/raw/parl/<nome>."""
    destino = CACHE / nome
    if destino.exists():
        return destino.read_bytes()
    time.sleep(pausa)
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "transparencia-etl/0.1"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                dados = r.read()
            CACHE.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(dados)
            return dados
        except urllib.error.HTTPError as e:
            if e.code == 404:  # não existe (ex.: carteira sem registro de frequência): não adianta repetir
                raise
            if i == 3:
                raise RuntimeError(f"Falha ao baixar {url}: {e}") from e
            time.sleep(10 * 2 ** i)
        except Exception as e:
            if i == 3:
                raise RuntimeError(f"Falha ao baixar {url}: {e}") from e
            time.sleep(10 * 2 ** i)
    raise AssertionError


def json_cache(url: str, params: dict, nome: str) -> object:
    destino = CACHE / nome
    if destino.exists():
        return json.loads(destino.read_text(encoding="utf-8"))
    dados = get_json(url, params)
    CACHE.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return dados


def normaliza(nome: str) -> str:
    s = unicodedata.normalize("NFD", nome).encode("ascii", "ignore").decode().upper()
    return " ".join(s.replace(".", " ").replace("-", " ").replace("`", "").replace("'", "").split())


def dia(s: str) -> date:
    return datetime.fromisoformat(s[:10]).date()


def anos_ate_hoje() -> list[int]:
    return list(range(ANO_INICIO, date.today().year + 1))


# ---------------------------------------------------------------- Câmara

def deputados_da_legislatura(leg: int) -> list[dict]:
    out, pagina = [], 1
    while True:
        j = json_cache(f"{CAMARA_API}/deputados", {"idLegislatura": leg, "itens": 100, "pagina": pagina},
                       f"dep_leg{leg}_p{pagina}.json")
        out += j["dados"]
        if not any(l["rel"] == "next" for l in j.get("links", [])):
            return out
        pagina += 1


def periodos_exercicio(hist: list[dict]) -> tuple[list[tuple[date, date]], list[tuple[date, str]]]:
    """Intervalos em exercício e trocas de partido, a partir do histórico da API da Câmara."""
    eventos = sorted(hist, key=lambda h: h["dataHora"] or "")
    periodos, inicio, partidos = [], None, []
    for h in eventos:
        d = dia(h["dataHora"])
        if not partidos or partidos[-1][1] != h["siglaPartido"]:
            partidos.append((d, h["siglaPartido"]))
        em_exercicio = (h.get("situacao") or "") == "Exercício"
        if em_exercicio and inicio is None:
            inicio = d
        elif not em_exercicio and inicio is not None:
            periodos.append((inicio, d))
            inicio = None
    if inicio is not None:
        periodos.append((inicio, date.today()))
    return periodos, partidos


CAMARA_FREQ = "https://www.camara.leg.br/SitCamaraWS/sessoesreunioes.asmx/ListarPresencasParlamentar"

# Reuniões formais de comissão (fora do Plenário) contadas em "presença em comissões".
TIPOS_COMISSAO = {
    "Reunião Deliberativa", "Audiência Pública", "Audiência Pública e Deliberação",
    "Reunião de Comparecimento de Ministro(a)", "Reunião de Instalação e Eleição", "Reunião de Eleição",
    "Tomada de Depoimento",
}


def reunioes_comissao(ano: int) -> dict[str, int]:
    """{idDeputado: nº de reuniões formais de comissão com presença registrada} no ano."""
    ev = baixar(f"{CAMARA_ARQ}/eventos/csv/eventos-{ano}.csv", f"eventos-{ano}.csv").decode("utf-8-sig")
    validos = {r["id"] for r in csv.DictReader(io.StringIO(ev), delimiter=";")
               if r["descricaoTipo"] in TIPOS_COMISSAO and r["situacao"].startswith("Encerrada")
               and "Plenário da Câmara" not in (r.get("localCamara.nome") or "")}
    pres = baixar(f"{CAMARA_ARQ}/eventosPresencaDeputados/csv/eventosPresencaDeputados-{ano}.csv",
                  f"presenca-{ano}.csv").decode("utf-8-sig")
    out: dict[str, set[str]] = defaultdict(set)
    for r in csv.DictReader(io.StringIO(pres), delimiter=";"):
        if r["idEvento"] in validos:
            out[r["idDeputado"]].add(r["idEvento"])
    return {k: len(v) for k, v in out.items()}


# Nº de carteira parlamentar consultados em cada legislatura (os usados vão até ~650).
# A carteira informada nos arquivos da cota nem sempre é a da legislatura certa (ex.: a 91 é de um
# deputado em 2023–2027 e de outro em 2019–2023), por isso o ETL consulta todas e associa pelo nome.
MAX_CARTEIRA = 700


def frequencia(leg: int, carteira: str, ini: date, fim: date) -> tuple[str, list[tuple[str, str, str]]]:
    """Frequência oficial da carteira nos dias com sessão deliberativa: (nome devolvido, [(ano, situação, motivo)])."""
    nome_cache = f"freq-{leg}-{carteira}-{ini.isoformat()}-{fim.isoformat()}.xml"
    url = f"{CAMARA_FREQ}?dataIni={ini:%d/%m/%Y}&dataFim={fim:%d/%m/%Y}&numMatriculaParlamentar={carteira}"
    vazio = CACHE / (nome_cache + ".404")
    if vazio.exists():
        return "", []
    try:
        dados = baixar(url, nome_cache, pausa=0.3, timeout=60)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        vazio.touch()
        return "", []
    raiz = ET.fromstring(dados)
    dias = raiz.find("diasDeSessoes2")
    out = [((d.findtext("data") or "")[6:10], (d.findtext("frequencianoDia") or "").strip(),
            (d.findtext("justificativa") or "").strip())
           for d in (dias.findall("dia") if dias is not None else [])]
    return raiz.findtext("nomeParlamentar") or "", out


PALAVRAS_COMUNS = {"DE", "DA", "DO", "DAS", "DOS", "E", "DR", "DRA", "PASTOR", "PASTORA", "DELEGADO", "DELEGADA",
                   "CAPITAO", "CORONEL", "GENERAL", "SARGENTO", "PROFESSOR", "PROFESSORA", "BISPO", "JR", "JUNIOR", "FILHO", "NETO"}


def casar_carteira(nome_freq: str, candidatos: dict[int, tuple[set[str], str]]) -> list[int]:
    """Associa "Nome-Partido/UF" (serviço de frequência) a deputados da legislatura.
    `candidatos` = {id: (todos os nomes que o deputado já usou, UF)}. Critérios em ordem, cada um só
    vale se der um único deputado: nome igual; nome contido no outro (mesma UF); maior sobreposição de
    palavras significativas (mesma UF)."""
    nome, _, resto = nome_freq.rpartition("-")
    uf = resto.rsplit("/", 1)[-1].strip() if "/" in resto else ""
    alvo = set(normaliza(nome).split())
    mesma_uf = {i: v for i, v in candidatos.items() if not uf or v[1] == uf}
    iguais = [i for i, (nomes, _) in candidatos.items() if any(set(n.split()) == alvo for n in nomes)]
    if len(iguais) == 1:
        return iguais
    contidos = [i for i, (nomes, _) in mesma_uf.items()
                if any((t := set(n.split())) and (t <= alvo or alvo <= t) for n in nomes)]
    if len(contidos) == 1:
        return contidos
    sig = alvo - PALAVRAS_COMUNS
    nota = {i: max(len(sig & (set(n.split()) - PALAVRAS_COMUNS)) for n in nomes) for i, (nomes, _) in mesma_uf.items()}
    melhor = max(nota.values(), default=0)
    if melhor == 0:
        return []
    return [i for i, v in nota.items() if v == melhor]


def ceap_camara(ano: int) -> dict[str, float]:
    z = zipfile.ZipFile(io.BytesIO(baixar(CAMARA_CEAP.format(ano), f"ceap-camara-{ano}.zip")))
    leitor = csv.DictReader(io.TextIOWrapper(z.open(z.infolist()[0]), encoding="utf-8-sig"), delimiter=";")
    out: dict[str, float] = defaultdict(float)
    for r in leitor:
        if r.get("ideCadastro"):
            out[r["ideCadastro"]] += float((r["vlrLiquido"] or "0").replace(",", "."))
    return out


def camara() -> tuple[list[dict], list[str]]:
    anos = anos_ate_hoje()
    ceap = {a: ceap_camara(a) for a in anos}

    ids: dict[int, dict] = {}
    for leg in LEGISLATURAS:
        for d in deputados_da_legislatura(leg):
            ids.setdefault(d["id"], {"nome": d["nome"], "uf": d["siglaUf"], "legislaturas": set()})["legislaturas"].add(leg)

    comissoes = {a: reunioes_comissao(a) for a in anos}
    hoje = date.today()

    # histórico (períodos em exercício e partidos)
    base = {}
    for n, (i, info) in enumerate(sorted(ids.items())):
        hist = json_cache(f"{CAMARA_API}/deputados/{i}/historico", {}, f"hist-{i}.json")["dados"]
        hist = [h for h in hist if h.get("idLegislatura") in LEGISLATURAS]
        periodos, partidos = periodos_exercicio(hist)
        base[i] = (info, hist, periodos, partidos)
        if n % 200 == 0:
            print(f"  histórico {n}/{len(ids)}", flush=True)

    # Frequência oficial no Plenário: uma consulta por carteira e legislatura, cobrindo a legislatura
    # inteira (serviço lento, ~1–2 s; com 8 consultas simultâneas o servidor derruba as conexões, 3 funcionam).
    # Cada carteira é associada ao deputado da legislatura pelo nome devolvido, só com candidato único.
    # todos os nomes que cada deputado usou (o nome parlamentar muda: "Dayany do Capitão" → "Dayany Bittencourt")
    candidatos: dict[int, dict[int, tuple[set[str], str]]] = {leg: {} for leg in LEGISLATURAS}
    for i, (info, hist, _, _) in base.items():
        for leg in info["legislaturas"]:
            nomes = {info["nome"]} | {h.get("nome") or "" for h in hist if h.get("idLegislatura") == leg} \
                    | {h.get("nomeEleitoral") or "" for h in hist if h.get("idLegislatura") == leg}
            candidatos[leg][i] = ({normaliza(n) for n in nomes if n.strip()}, info["uf"])
    consultas = [(leg, str(c), l_ini, min(l_fim, hoje)) for leg, (l_ini, l_fim) in LEGISLATURAS.items()
                 for c in range(1, MAX_CARTEIRA + 1)]
    print(f"  {len(consultas)} consultas de frequência", flush=True)
    freq: dict[tuple[int, int], Counter] = defaultdict(Counter)
    motivos: dict[tuple[int, int], Counter] = defaultdict(Counter)
    sem_par, ambiguas, falhas = [], [], []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futuros = {pool.submit(frequencia, *q): q for q in consultas}
        for k, fut in enumerate(as_completed(futuros)):
            leg, c = futuros[fut][:2]
            try:
                nome_freq, dias = fut.result()
            except Exception as e:  # falha persistente numa consulta: registra e segue
                falhas.append(f"leg {leg} carteira {c}: {e}")
                continue
            if k % 200 == 0:
                print(f"  frequência {k}/{len(consultas)}", flush=True)
            if not dias:
                continue
            cand = casar_carteira(nome_freq, candidatos[leg])
            if len(cand) != 1:
                (ambiguas if cand else sem_par).append(f"{nome_freq} (leg {leg}, carteira {c})")
                continue
            for ano, situacao, motivo in dias:
                if ano.isdigit():
                    freq[(cand[0], int(ano))][situacao] += 1
                    if motivo:
                        motivos[(cand[0], int(ano))][motivo] += 1
    print(f"  frequência: {len(falhas)} falhas, {len(sem_par)} carteiras sem deputado, {len(ambiguas)} ambíguas", flush=True)
    for nome, lista in (("falhas", falhas), ("sem deputado", sem_par), ("ambíguas", ambiguas)):
        if lista:
            print(f"  {nome}:", lista[:15])
    nome_diferente = sem_par + ambiguas

    out = []
    for i, (info, hist, periodos, partidos) in base.items():
        por_ano = {}
        for a in anos:
            dias = sum(max(0, (min(b, date(a, 12, 31) + timedelta(1)) - max(x, date(a, 1, 1))).days) for x, b in periodos)
            gasto = ceap[a].get(str(i), 0.0)
            f = freq.get((i, a), Counter())
            if dias or gasto or f:
                por_ano[str(a)] = {
                    "dias_sessao": sum(f.values()), "presencas": f["Presença"],
                    "ausencias_justificadas": f["Ausência justificada"], "ausencias_nao_justificadas": f["Ausência"],
                    "motivos": dict(motivos[(i, a)].most_common()),
                    "reunioes_comissao": comissoes[a].get(str(i), 0),
                    "dias_exercicio": dias, "cota": round(gasto, 2),
                }
        if not por_ano:
            continue
        out.append({"id": i, "nome": info["nome"].strip(), "uf": info["uf"], "cargo": "Deputado(a) federal",
                    "legislaturas": sorted(info["legislaturas"]),
                    "partidos": [{"desde": d.isoformat(), "partido": p} for d, p in partidos],
                    "condicao": sorted({h.get("condicaoEleitoral") or "" for h in hist} - {""}),
                    "anos": por_ano})
    return out, nome_diferente


# ---------------------------------------------------------------- Senado

def votacoes_senado(ano: int, mes: int) -> list[dict]:
    ini = date(ano, mes, 1)
    fim = (ini + timedelta(32)).replace(day=1) - timedelta(1)
    if ini > date.today():
        return []
    nome = f"votsen-{ano}{mes:02d}.json"
    if fim >= date.today():  # mês corrente: não guardar em cache
        return get_json(f"{SENADO_API}/votacao", {"dataInicio": ini.isoformat(), "dataFim": date.today().isoformat()}) or []
    return json_cache(f"{SENADO_API}/votacao", {"dataInicio": ini.isoformat(), "dataFim": fim.isoformat()}, nome) or []


def ceaps_senado(ano: int) -> dict[str, float]:
    texto = baixar(SENADO_CEAPS.format(ano), f"ceaps-{ano}.csv").decode("latin-1")
    linhas = texto.splitlines()
    if linhas and linhas[0].startswith('"ULTIMA ATUALIZACAO'):
        linhas = linhas[1:]
    out: dict[str, float] = defaultdict(float)
    for r in csv.DictReader(linhas, delimiter=";"):
        v = (r.get("VALOR_REEMBOLSADO") or "0").replace(".", "").replace(",", ".")
        try:
            out[normaliza(r["SENADOR"])] += float(v)
        except ValueError:
            pass
    return out


def senado() -> tuple[list[dict], Counter]:
    anos = anos_ate_hoje()
    # dia → senador → situação mais favorável no dia (presente > justificada > não justificada)
    situacao: dict[int, dict[str, dict[date, int]]] = defaultdict(lambda: defaultdict(dict))
    info: dict[int, dict] = {}
    codigos = Counter()
    partidos_ano: dict[int, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for a in anos:
        for m in range(1, 13):
            for v in votacoes_senado(a, m):
                d = dia(v["dataSessao"])
                if d < LEGISLATURAS[56][0]:
                    continue
                for p in v.get("votos") or []:
                    cod = p["codigoParlamentar"]
                    sigla = p.get("siglaVotoParlamentar") or ""
                    codigos[sigla] += 1
                    nivel = (2 if sigla in SENADO_PRESENTE or sigla.startswith("Presidente") else
                             0 if sigla in SENADO_NAO_JUSTIFICADA else 1)
                    atual = situacao[cod][str(a)].get(d, -1)
                    situacao[cod][str(a)][d] = max(atual, nivel)
                    info.setdefault(cod, {"nome": p["nomeParlamentar"], "uf": p["siglaUFParlamentar"]})
                    partidos_ano[cod][str(a)][p.get("siglaPartidoParlamentar") or ""] += 1
        print(f"Senado {a}: ok", flush=True)

    # A CEAPS identifica o senador só pelo nome. Casa pelo nome parlamentar exato e, se não houver,
    # pelas palavras do nome (um contido no outro), aceitando só quando há um único candidato.
    nomes = {cod: set(normaliza(s["nome"]).split()) for cod, s in info.items()}
    ceaps: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    sem_par: dict[str, float] = defaultdict(float)
    for a in anos:
        for nome_ceaps, v in ceaps_senado(a).items():
            t = set(nome_ceaps.split())
            cand = [c for c, n in nomes.items() if n == t] or [c for c, n in nomes.items() if n <= t or t <= n]
            if len(cand) == 1:
                ceaps[cand[0]][a] += v
            else:
                sem_par[f"{a} {nome_ceaps}"] += v
    out = []
    for cod, s in info.items():
        por_ano = {}
        for a in map(str, anos):
            dias = situacao[cod].get(a, {})
            gasto = ceaps[cod].get(int(a), 0.0)
            if dias or gasto:
                niveis = Counter(dias.values())
                por_ano[a] = {"dias_votacao": len(dias), "presencas": niveis[2], "ausencias_justificadas": niveis[1],
                              "ausencias_nao_justificadas": niveis[0], "cota": round(gasto, 2),
                              "partido": partidos_ano[cod][a].most_common(1)[0][0] if partidos_ano[cod][a] else None}
        out.append({"id": cod, "nome": s["nome"], "uf": s["uf"], "cargo": "Senador(a)", "anos": por_ano})
    if sem_par:
        print("CEAPS sem senador correspondente:", {k: round(v) for k, v in sem_par.items()})
    return out, codigos, {k: round(v, 2) for k, v in sem_par.items()}


def main() -> None:
    deps, freq_descartada = camara()
    sens, codigos, ceaps_sem_par = senado()
    print("Códigos de voto do Senado:", dict(codigos.most_common()))
    saida = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "anos": [str(a) for a in anos_ate_hoje()],
        "subsidio": SUBSIDIO,
        "codigos_voto_senado": dict(codigos.most_common()),
        "ceaps_sem_par": ceaps_sem_par,
        "frequencia_carteiras_sem_par": freq_descartada,
        "tipos_reuniao_comissao": sorted(TIPOS_COMISSAO),
        "deputados": deps,
        "senadores": sens,
        "fontes": [
            {"nome": "Câmara dos Deputados, Dados Abertos (deputados, histórico, eventos, presença)", "url": "https://dadosabertos.camara.leg.br"},
            {"nome": "Câmara dos Deputados, Cota para o Exercício da Atividade Parlamentar", "url": "https://www.camara.leg.br/transparencia/gastos-parlamentares"},
            {"nome": "Senado Federal, Dados Abertos (votações nominais)", "url": f"{SENADO_API}/votacao"},
            {"nome": "Senado Federal, Cota para o Exercício da Atividade Parlamentar dos Senadores (CEAPS)", "url": "https://www12.senado.leg.br/transparencia/dados-abertos-transparencia/dados-abertos-ceaps"},
        ],
    }
    destino = RAIZ / "site" / "data" / "parlamentares.json"
    destino.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Gerado {destino} ({destino.stat().st_size // 1024} KB): {len(deps)} deputados, {len(sens)} senadores")


if __name__ == "__main__":
    main()
