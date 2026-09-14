import sys
import json
import datetime
from automacao_filtro import gerar_relatorios

if __name__ == "__main__":
    params = json.loads(sys.stdin.read())
    periodos = [
        (datetime.date.fromisoformat(s), datetime.date.fromisoformat(e))
        for s, e in params["periodos"]
    ]
    gerar_relatorios(
        params["usuario"],
        params["senha"],
        params["filial"],
        periodos,
        formato=params["formato"],
        colunas=params["colunas"],
        mostrar_desativados=params["mostrar_desativados"],
        esconder_supervisores=params["esconder_supervisores"],
        unir_relatorios=params["unir_relatorios"],
    )
