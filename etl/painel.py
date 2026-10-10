"""
Junta data/funcoes.json (RREO + IPCA) e data/gnd.json (MSC) em site/data/painel.json,
o único arquivo de dados que o front-end carrega.

Por função, guarda as séries em R$ bilhões, nominais e reais (a preços de `preco_base`):
  - anual:   despesa empenhada, anos fechados (RREO)
  - parcial: despesa liquidada até o mês de corte, todos os anos (RREO)
  - inv_fin: parte das séries acima que é GND 5, inversões financeiras (MSC)
  - subfuncoes: quebra por subfunção com código (MSC), exceto Encargos Especiais, que usa o RREO

Também confere, ano a ano, que a soma da MSC bate com o RREO para cada função e registra a
diferença em `conferencia` (exibida na página "Método").

Uso:  python etl/painel.py
"""

from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENCARGOS = "Encargos Especiais"
REFINANCIAMENTO = {"841", "842"}  # fora do RREO; só aparece na MSC

# Portaria MOG nº 42/1999, com alterações. 241, 242, 245 e 246: Portaria SOF/MPO nº 169/2024
# (vigente a partir de 2025; a 244 deixou de ser usada pela União).
SUBFUNCOES = {
    "031": "Ação Legislativa", "032": "Controle Externo", "061": "Ação Judiciária",
    "062": "Defesa do Interesse Público no Processo Judiciário", "091": "Defesa da Ordem Jurídica",
    "092": "Representação Judicial e Extrajudicial", "121": "Planejamento e Orçamento",
    "122": "Administração Geral", "123": "Administração Financeira", "124": "Controle Interno",
    "125": "Normatização e Fiscalização", "126": "Tecnologia da Informação",
    "127": "Ordenamento Territorial", "128": "Formação de Recursos Humanos",
    "129": "Administração de Receitas", "130": "Administração de Concessões",
    "131": "Comunicação Social", "151": "Defesa Aérea", "152": "Defesa Naval",
    "153": "Defesa Terrestre", "181": "Policiamento", "182": "Defesa Civil",
    "183": "Informação e Inteligência", "211": "Relações Diplomáticas",
    "212": "Cooperação Internacional", "241": "Assistência ao Idoso / à Pessoa Idosa",
    "242": "Assistência à Pessoa com Deficiência", "243": "Assistência à Criança e ao Adolescente",
    "244": "Assistência Comunitária", "245": "Serviços Socioassistenciais", "246": "Segurança de Renda",
    "271": "Previdência Básica", "272": "Previdência do Regime Estatutário",
    "273": "Previdência Complementar", "274": "Previdência Especial", "301": "Atenção Básica",
    "302": "Assistência Hospitalar e Ambulatorial", "303": "Suporte Profilático e Terapêutico",
    "304": "Vigilância Sanitária", "305": "Vigilância Epidemiológica", "306": "Alimentação e Nutrição",
    "331": "Proteção e Benefícios ao Trabalhador", "332": "Relações de Trabalho",
    "333": "Empregabilidade", "334": "Fomento ao Trabalho", "361": "Ensino Fundamental",
    "362": "Ensino Médio", "363": "Ensino Profissional", "364": "Ensino Superior",
    "365": "Educação Infantil", "366": "Educação de Jovens e Adultos", "367": "Educação Especial",
    "368": "Educação Básica", "391": "Patrimônio Histórico, Artístico e Arqueológico",
    "392": "Difusão Cultural", "421": "Custódia e Reintegração Social",
    "422": "Direitos Individuais, Coletivos e Difusos", "423": "Assistência aos Povos Indígenas",
    "451": "Infraestrutura Urbana", "452": "Serviços Urbanos", "453": "Transportes Coletivos Urbanos",
    "481": "Habitação Rural", "482": "Habitação Urbana", "511": "Saneamento Básico Rural",
    "512": "Saneamento Básico Urbano", "541": "Preservação e Conservação Ambiental",
    "542": "Controle Ambiental", "543": "Recuperação de Áreas Degradadas", "544": "Recursos Hídricos",
    "545": "Meteorologia", "571": "Desenvolvimento Científico",
    "572": "Desenvolvimento Tecnológico e Engenharia",
    "573": "Difusão do Conhecimento Científico e Tecnológico", "601": "Promoção da Produção Vegetal",
    "602": "Promoção da Produção Animal", "603": "Defesa Sanitária Vegetal",
    "604": "Defesa Sanitária Animal", "605": "Abastecimento", "606": "Extensão Rural",
    "607": "Irrigação", "608": "Promoção da Produção Agropecuária", "609": "Defesa Agropecuária",
    "631": "Reforma Agrária", "632": "Colonização", "661": "Promoção Industrial",
    "662": "Produção Industrial", "663": "Mineração", "664": "Propriedade Industrial",
    "665": "Normalização e Qualidade", "691": "Promoção Comercial", "692": "Comercialização",
    "693": "Comércio Exterior", "694": "Serviços Financeiros", "695": "Turismo",
    "721": "Comunicações Postais", "722": "Telecomunicações", "751": "Conservação de Energia",
    "752": "Energia Elétrica", "753": "Combustíveis Minerais", "754": "Biocombustíveis",
    "781": "Transporte Aéreo", "782": "Transporte Rodoviário", "783": "Transporte Ferroviário",
    "784": "Transporte Hidroviário", "785": "Transportes Especiais", "811": "Desporto de Rendimento",
    "812": "Desporto Comunitário", "813": "Lazer", "841": "Refinanciamento da Dívida Interna",
    "842": "Refinanciamento da Dívida Externa", "843": "Serviço da Dívida Interna",
    "844": "Serviço da Dívida Externa", "845": "Outras Transferências",
    "846": "Outros Encargos Especiais", "847": "Transferências para a Educação Básica",
}


def r3(x: float) -> float:
    return round(x, 3)


def main() -> None:
    fun = json.loads((RAIZ / "data" / "funcoes.json").read_text(encoding="utf-8"))
    gnd = json.loads((RAIZ / "data" / "gnd.json").read_text(encoding="utf-8"))
    defl = fun["deflator"]
    anos_a = sorted(defl["anual"])
    anos_p = sorted(defl["parcial"])

    def soma_msc(recorte: str, ano: str, funcao: str, campo: str, so_gnd: str | None = None,
                 subfuncao: str | None = None) -> float:
        subs = gnd[recorte].get(ano, {}).get(funcao, {})
        total = 0.0
        for cod, gs in subs.items():
            if cod in REFINANCIAMENTO or (subfuncao and cod != subfuncao):
                continue
            for g, v in gs.items():
                if so_gnd is None or g == so_gnd:
                    total += v[campo]
        return total / 1e9

    def par(nominal: dict[str, float], recorte: str) -> dict:
        d = defl[recorte]
        return {"nominal": {a: r3(v) for a, v in nominal.items()},
                "real": {a: r3(v * d[a]) for a, v in nominal.items()}}

    funcoes, conferencia = [], []
    for f in fun["funcoes"]:
        nome = f["funcao"]
        inv_a = {a: soma_msc("anual", a, nome, "empenhado", "5") for a in anos_a}
        inv_p = {a: soma_msc("parcial", a, nome, "liquidado", "5") for a in anos_p}

        for a in anos_a:
            msc, rreo = soma_msc("anual", a, nome, "empenhado"), f["anual_nominal"][a]
            if abs(msc - rreo) > 0.01 and nome != ENCARGOS:
                conferencia.append({"funcao": nome, "ano": a, "recorte": "anual",
                                    "rreo": r3(rreo), "msc": r3(msc), "dif": r3(msc - rreo)})
        for a in anos_p:
            msc, rreo = soma_msc("parcial", a, nome, "liquidado"), f["parcial_nominal"][a]
            if abs(msc - rreo) > 0.01 and nome != ENCARGOS:
                conferencia.append({"funcao": nome, "ano": a, "recorte": "parcial",
                                    "rreo": r3(rreo), "msc": r3(msc), "dif": r3(msc - rreo)})

        if nome == ENCARGOS:
            subs = [{"cod": None, "nome": s["subfuncao"],
                     "anual": par(s["anual_nominal"], "anual"),
                     "parcial": par(s["parcial_nominal"], "parcial")} for s in f["subfuncoes"]]
        else:
            codigos = sorted({c for rec in ("anual", "parcial") for a in gnd[rec]
                              for c in gnd[rec][a].get(nome, {})})
            subs = []
            for c in codigos:
                sa = {a: soma_msc("anual", a, nome, "empenhado", subfuncao=c) for a in anos_a}
                sp = {a: soma_msc("parcial", a, nome, "liquidado", subfuncao=c) for a in anos_p}
                if max(sa.values(), default=0) < 0.005 and max(sp.values(), default=0) < 0.005:
                    continue
                subs.append({"cod": c, "nome": SUBFUNCOES.get(c, f"Subfunção {c}"),
                             "anual": par(sa, "anual"), "parcial": par(sp, "parcial")})
        subs.sort(key=lambda s: -s["anual"]["real"].get(anos_a[-1], 0))

        funcoes.append({
            "nome": nome, "encargos": nome == ENCARGOS,
            "anual": par(f["anual_nominal"], "anual"),
            "parcial": par(f["parcial_nominal"], "parcial"),
            "inv_fin": {"anual": par(inv_a, "anual"), "parcial": par(inv_p, "parcial")},
            "subfuncoes": subs,
        })

    saida = {
        "gerado_em": fun["gerado_em"],
        "preco_base": fun["preco_base"],
        "parcial": fun["parcial"],
        "anos_anual": anos_a, "anos_parcial": anos_p,
        "governos": fun["governos"],
        "funcoes": funcoes,
        "conferencia": conferencia,
        "fontes": fun["fontes"] + [gnd["fonte"]],
    }
    destino = RAIZ / "site" / "data" / "painel.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Gerado {destino} ({destino.stat().st_size // 1024} KB), "
          f"{len(conferencia)} divergências MSC × RREO acima de R$ 10 mi")
    for c in conferencia:
        print("  ", c)


if __name__ == "__main__":
    main()
