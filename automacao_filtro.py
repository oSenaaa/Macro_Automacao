from playwright.sync_api import sync_playwright
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import time

# A UI do modal só monta a query string de /api/client_reports/generate.
# Em vez de depender do calendário/dropdowns (que mudam e têm dias desabilitados),
# o robô reescreve os parâmetros diretamente na requisição.
COLUNAS_API = {
    "Data": "date",
    "Pontos": "punches",
    "Trabalhadas": "worked_hours",
    "Intervalo": "break_hours",
    "Noturno": "night_hours",
    "Feriado": "holiday",
    "Obs": "observation",
    "Jornada": "schedule",
    "Grupo de regras": "business_rules_group",
    "Planejadas": "planned_hours",
    "Distribuição de horas": "hours_distribution",
    "Atraso entrada": "late_entry_hours",
    "Saída antecipada": "early_leave_hours",
    "Fases de Horas Extras": "extra_hours_phases",
    "Horas Extras": "extra_hours",
    "Desconto": "debit_hours",
    "Fases do Banco de Horas": "hours_bank_phases",
    "Banco Dia": "hours_bank",
    "Horas Faltantes": "missed_hours",
    "Banco Acumulado": "cumulative_hours_bank",
    "Saldo projetado a expirar": "projected_expired_minutes",
    "Data estimada de expiração": "projected_expiration_date",
    "Interjornada": "cross_shifts_interval_diff_hours",
    "Ajustes": "adjustments",
    "Motivo": "reason",
    "Sobreaviso": "on_call_hours",
    "Acionamento": "on_call_activated_hours",
    "Total de Sobreaviso (Sem acionamento)": "on_call_reducing_activated_hours",
    "Fases de Intervalos não utilizados": "unused_break_phases",
    "Intervalos não utilizados": "unused_breaks",
}
COLUNAS_OBRIGATORIAS = ["Data", "Pontos"]
COLUNAS_PADRAO = ["Data", "Pontos", "Trabalhadas", "Intervalo", "Noturno", "Feriado", "Obs"]

ROTA_GERAR = "**/api/client_reports/generate**"


def _montar_url(url_original, data_inicio, data_fim, formato, colunas,
                mostrar_desativados, esconder_supervisores, unir_relatorios):
    partes = urlsplit(url_original)
    # Mantém parâmetros desconhecidos (ex.: filtro de filial, rand) e sobrescreve o resto
    gerenciados = {"report_format", "start_date", "end_date", "show_columns",
                   "active", "skip_supervisors", "pdf_one_file"}
    params = [(k, v) for k, v in parse_qsl(partes.query, keep_blank_values=True)
              if k not in gerenciados]

    nomes = COLUNAS_OBRIGATORIAS + [c for c in (colunas or COLUNAS_PADRAO)
                                    if c not in COLUNAS_OBRIGATORIAS]
    chaves = [COLUNAS_API[c] for c in nomes if c in COLUNAS_API]

    params += [
        ("report_format", formato.lower()),
        ("start_date", data_inicio.isoformat()),
        ("end_date", data_fim.isoformat()),
        ("show_columns", ",".join(chaves)),
    ]
    if not mostrar_desativados:
        params.append(("active", "true"))
    if esconder_supervisores:
        params.append(("skip_supervisors", "true"))
    if unir_relatorios and formato.upper() == "PDF":
        params.append(("pdf_one_file", "true"))

    return urlunsplit(partes._replace(query=urlencode(params)))


def gerar_relatorios(usuario, senha, filial, periodos_para_gerar,
                     formato="PDF", colunas=None,
                     mostrar_desativados=False, esconder_supervisores=False,
                     unir_relatorios=False):
    desconhecidas = [c for c in (colunas or []) if c not in COLUNAS_API]
    if desconhecidas:
        print(f"Aviso: colunas sem mapeamento serão ignoradas: {desconhecidas}")

    falhas = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="pt-BR",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # login
        print("Acessando a página de login...")
        page.goto("https://admin.oitchau.com.br/login")
        page.locator("input[name='email']").fill(usuario)
        page.locator("input[name='password']").fill(senha)
        page.locator("button:has-text('Acessar painel')").click()
        page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
        page.wait_for_load_state("load", timeout=15000)
        time.sleep(2)

        page.goto("https://admin.oitchau.com.br/reports/detailed")
        time.sleep(3)
        page.wait_for_selector("button:has-text('Baixar relatório de todos')", timeout=20000)

        # looping de geração
        for data_inicio, data_fim in periodos_para_gerar:

            str_inicio = data_inicio.strftime("%d/%m/%Y")
            str_fim = data_fim.strftime("%d/%m/%Y")
            print(f"\nIniciando geração para: {str_inicio} até {str_fim}...")

            page.locator("button:has-text('Baixar relatório de todos')").click()
            page.locator("[data-testid='ModalDialog']").wait_for(state="visible", timeout=10000)
            time.sleep(1)

            # ── Filtro filial (único campo ainda preenchido pela UI) ──────
            if filial:
                print(f"Buscando filial: {filial}...")
                campo_busca = page.locator("input[placeholder='Colaboradores']")
                campo_busca.wait_for(state="visible")
                campo_busca.click(force=True)
                time.sleep(0.5)

                campo_busca.clear(force=True)
                time.sleep(0.2)
                page.keyboard.press("End")
                for _ in range(15):
                    page.keyboard.press("Backspace")
                time.sleep(0.5)

                with page.expect_response(lambda response: "/api/company/search" in response.url, timeout=10000):
                    campo_busca.press_sequentially(filial, delay=200)

                print("API respondeu! Clicando no resultado...")
                time.sleep(1)
                page.locator(f"button:has-text('{filial}')").last.click(force=True)
                time.sleep(1)

            # ── Confirmar, reescrevendo os parâmetros da requisição ──────
            print("Solicitando relatório...")
            interceptou = [False]

            def _reescrever_query(route, request, _ini=data_inicio, _fim=data_fim):
                interceptou[0] = True
                nova_url = _montar_url(request.url, _ini, _fim, formato, colunas,
                                       mostrar_desativados, esconder_supervisores,
                                       unir_relatorios)
                print(f"  [api] url original: {request.url}")
                print(f"  [api] url enviada:  {nova_url}")
                route.continue_(url=nova_url)

            page.route(ROTA_GERAR, _reescrever_query)
            try:
                with page.expect_response(lambda response: "/api/client_reports/generate" in response.url, timeout=15000) as resp_info:
                    page.locator("button:has-text('Confirmar')").click()
                resposta = resp_info.value
                if not interceptou[0]:
                    raise RuntimeError("requisição não foi interceptada")
                if not resposta.ok:
                    raise RuntimeError(f"API respondeu {resposta.status}: {resposta.text()[:300]}")
                print(f"Sucesso! Servidor processou o pedido de {str_inicio} a {str_fim}.")
            except Exception as e:
                print(f"ERRO ao gerar {str_inicio} a {str_fim}: {e}")
                falhas.append(f"{str_inicio} a {str_fim}")
            finally:
                page.unroute(ROTA_GERAR)

            try:
                page.locator("button:has-text('Fechar')").click(timeout=2000)
            except Exception:
                pass
            if page.locator("[data-testid='ModalDialog']").count():
                try:
                    page.locator("[data-testid='ModalDialog'] button:has-text('Cancelar')").click(timeout=2000)
                except Exception:
                    pass

            time.sleep(1)
            page.wait_for_selector("button:has-text('Baixar relatório de todos')", state="visible")

        print(f"\n--- FINALIZADO --- O robô terminou o lote!")
        time.sleep(5)
        browser.close()

    if falhas:
        raise RuntimeError(f"{len(falhas)} período(s) falharam: {', '.join(falhas)}")
