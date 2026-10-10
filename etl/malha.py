"""
Malha das UFs (IBGE, qualidade mínima) convertida em caminhos SVG prontos para o mapa do site.
Gera site/data/ufs.json: {"viewBox": "...", "ufs": {"SP": {"path": "M...Z", "cx": x, "cy": y}}}.

Projeção equiretangular com correção do cosseno na latitude média do país (-15°): simples,
sem biblioteca, e com distorção pequena na escala de um mapa coroplético.

Uso:  python etl/malha.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from funcoes import get_json
from transferencias import UFS

RAIZ = Path(__file__).resolve().parent.parent
MALHA = "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
LARGURA = 600
COS = math.cos(math.radians(-15))


def aneis(geom: dict) -> list[list[list[float]]]:
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    return [anel for poli in geom["coordinates"] for anel in poli]


def main() -> None:
    g = get_json(MALHA, {"intrarregiao": "UF", "formato": "application/vnd.geo+json", "qualidade": "minima"})
    feats = {UFS[f["properties"]["codarea"]]: aneis(f["geometry"]) for f in g["features"]}
    pts = [p for rs in feats.values() for r in rs for p in r]
    x0, x1 = min(p[0] for p in pts) * COS, max(p[0] for p in pts) * COS
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    esc = LARGURA / (x1 - x0)
    altura = (y1 - y0) * esc

    def xy(p: list[float]) -> tuple[float, float]:
        return round((p[0] * COS - x0) * esc, 1), round((y1 - p[1]) * esc, 1)

    ufs = {}
    for uf, rs in sorted(feats.items()):
        partes, area, cx, cy = [], 0.0, 0.0, 0.0
        for r in rs:
            q = [xy(p) for p in r]
            partes.append("M" + "L".join(f"{x},{y}" for x, y in q) + "Z")
            for (xa, ya), (xb, yb) in zip(q, q[1:] + q[:1]):  # centroide do polígono (fórmula do laço)
                c = xa * yb - xb * ya
                area += c
                cx += (xa + xb) * c
                cy += (ya + yb) * c
        ufs[uf] = {"path": "".join(partes), "cx": round(cx / (3 * area), 1), "cy": round(cy / (3 * area), 1)}

    saida = {"viewBox": f"0 0 {LARGURA} {round(altura, 1)}", "fonte": "IBGE, malha de UFs (qualidade mínima)", "ufs": ufs}
    destino = RAIZ / "site" / "data" / "ufs.json"
    destino.write_text(json.dumps(saida, separators=(",", ":")), encoding="utf-8")
    print(f"Gerado {destino} ({destino.stat().st_size // 1024} KB, {len(ufs)} UFs)")


if __name__ == "__main__":
    main()
