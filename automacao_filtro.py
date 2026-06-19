from playwright.sync_api import sync_playwright
import time

MESES_PT = {
    1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
    5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
    9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
}

def _toggle_checkbox(page, label, valor_desejado):
    try:
        lbl = page.locator(f"label:has-text('{label}')").first
        chk = lbl.locator("input[type='checkbox']")
        chk.wait_for(state="attached", timeout=3000)
        if chk.is_checked() != valor_desejado:
            lbl.click()
            time.sleep(0.2)
    except Exception as e:
        print(f"  Aviso: checkbox '{label}' não processado: {e}")


def gerar_relatorios(usuario, senha, filial, periodos_para_gerar,
                     formato="PDF", colunas=None,
                     mostrar_desativados=False, esconder_supervisores=False,
                     unir_relatorios=False):
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
        campo_senha = page.locator("input[name='password']")
        campo_senha.fill(senha)
        campo_senha.press("Enter")

        page.wait_for_load_state("load", timeout=20000)
        time.sleep(2)

        page.goto("https://admin.oitchau.com.br/reports/detailed")
        time.sleep(5)
        page.wait_for_selector("button:has-text('Baixar relatório de todos')", timeout=20000)

        # looping de geração
        for data_inicio, data_fim in periodos_para_gerar:

            str_inicio = data_inicio.strftime("%d/%m/%Y")
            str_fim = data_fim.strftime("%d/%m/%Y")
            print(f"\nIniciando geração para: {str_inicio} até {str_fim}...")

            page.locator("button:has-text('Baixar relatório de todos')").click()
            time.sleep(2)

            # ── 1. Datas (primeiro, modal ainda sem dropdowns abertos) ────
            # Clica no display de período (span com texto da data) para abrir o calendário
            page.locator(".atlaskit-portal-container").locator(
                "text=/\\d{1,2}$/"
            ).first.click(force=True)
            time.sleep(1)

            nome_mes_inicio = MESES_PT[data_inicio.month]
            nome_mes_fim = MESES_PT[data_fim.month]

            seletor_inicio = f"td[aria-label*=' {data_inicio.day} de {nome_mes_inicio} de {data_inicio.year}']"
            seletor_fim = f"td[aria-label*=' {data_fim.day} de {nome_mes_fim} de {data_fim.year}']"

            tentativas_voltar = 0
            while not page.locator(seletor_inicio).is_visible() and tentativas_voltar < 36:
                # dispatch_event bypassa verificação de viewport (DayPicker fica fora do fluxo)
                page.locator(".DayPickerNavigation_button").first.dispatch_event("click")
                time.sleep(0.3)
                tentativas_voltar += 1

            page.locator(seletor_inicio).first.dispatch_event("click")
            time.sleep(0.3)
            page.locator(seletor_fim).first.dispatch_event("click")
            time.sleep(0.5)

            # Fechar calendário clicando no título do modal (acima do DayPicker)
            if page.locator(".DayPicker").is_visible():
                page.locator("[data-testid='ModalDialog']").locator("text='Baixar relatório de todos'").click(force=True)
                time.sleep(0.3)

            # ── 2. Formato ───────────────────────────────────────────────
            print(f"Selecionando formato: {formato}...")
            try:
                page.locator("input[data-testid='newSelectComponent.input']").click()
                time.sleep(0.5)
                page.locator(f"[data-testid='newSelectComponent.option']:has-text('{formato}')").first.click()
                time.sleep(0.5)
            except Exception as e:
                print(f"Aviso: não foi possível selecionar formato '{formato}': {e}")

            # ── 3. Colunas ───────────────────────────────────────────────
            if colunas is not None:
                print("Configurando colunas...")
                try:
                    col_chevron = page.locator("label").filter(has_text="Incluir colunas").locator("..").locator("button").first
                    col_chevron.click()
                    time.sleep(0.5)

                    opts = page.locator("[data-testid='optionsList.option']").all()
                    for opt in opts:
                        try:
                            opt_text = opt.locator("div").first.inner_text().strip()
                            is_disabled = "disabledOption" in (opt.get_attribute("class") or "")
                            is_selected = opt.locator("svg").count() > 0
                            user_wants = opt_text in colunas

                            if is_disabled:
                                continue
                            if is_selected and not user_wants:
                                opt.click()
                                time.sleep(0.2)
                            elif not is_selected and user_wants:
                                opt.click()
                                time.sleep(0.2)
                        except Exception:
                            pass

                    page.locator("label").filter(has_text="Incluir colunas").locator("..").locator("button").first.click()
                    time.sleep(0.3)
                except Exception as e:
                    print(f"Aviso: configuração de colunas falhou: {e}")

            # ── 4. Checkboxes ────────────────────────────────────────────
            _toggle_checkbox(page, "Mostrar colaboradores desativados", mostrar_desativados)
            _toggle_checkbox(page, "Esconder os supervisores", esconder_supervisores)
            if unir_relatorios:
                _toggle_checkbox(page, "Unir todos os relatórios em um arquivo", True)

            # ── 5. Filtro filial ─────────────────────────────────────────
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

            # ── 6. Confirmar ─────────────────────────────────────────────
            print("Solicitando relatório...")
            try:
                with page.expect_response(lambda response: "/api/client_reports/generate" in response.url, timeout=15000):
                    page.locator("button:has-text('Confirmar')").click()
                print(f"Sucesso! Servidor processou o pedido de {str_inicio} a {str_fim}.")
                try:
                    page.locator("button:has-text('Fechar')").click(timeout=2000)
                except:
                    pass
            except Exception as e:
                print(f"Aviso: A interceptação falhou ou demorou muito para {str_inicio} a {str_fim}.")

            time.sleep(1)
            page.wait_for_selector("button:has-text('Baixar relatório de todos')", state="visible")

        tempo_espera_final = len(periodos_para_gerar) * 15
        print(f"\n--- FINALIZADO --- O robô terminou o lote!")
        print(f"Aguardando {tempo_espera_final} segundos de segurança antes de fechar o navegador...")
        time.sleep(tempo_espera_final)
        browser.close()
