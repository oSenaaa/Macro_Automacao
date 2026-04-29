from playwright.sync_api import sync_playwright
import time
import calendar

# CONFIGURAÇÕES INICIAIS 
USUARIO_TESTE = ""
SENHA_TESTE = "" # Atualize a senha se necessário!
FILIAL_ALVO = "" # Nossa filial para o filtro
MESES_PARA_GERAR = [(11, 2025), (12, 2025)] # (Mês, Ano)
TEMPO_ESPERA_FINAL = 120 # PARAMETRIZE AQUI: Tempo em segundos antes de fechar a tela (ex: 300 = 5 min)

MESES_PT = {
    1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
    5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
    9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
}

def pegar_ultimo_dia(mes, ano):
    return calendar.monthrange(ano, mes)[1]

def gerar_relatorios():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Mude para True para rodar em 2º plano depois!
        context = browser.new_context()
        page = context.new_page()

        # LOGIN
        print("Acessando a página de login...")
        page.goto("https://admin.oitchau.com.br/login") 
        page.locator("input[name='email']").fill(USUARIO_TESTE) 
        page.locator("input[name='password']").fill(SENHA_TESTE)
        page.locator("button:has-text('Acessar painel')").click()
        page.wait_for_selector("text='Folha de Frequência'", state="attached", timeout=15000)

        # NAVEGAÇÃO ÚNICA COM BETA
        url_base = "https://admin.oitchau.com.br/reports/detailed/?beta=true"
        page.goto(url_base)
        
        try:
            page.locator("svg.arrow").click()
            time.sleep(0.5) 
            page.locator("text='Folha de frequência'").click()
        except:
            pass

        page.wait_for_selector("button:has-text('Baixar relatório')", timeout=10000)

        # LOOP DE GERAÇÃO
        for mes, ano in MESES_PARA_GERAR:
            nome_mes = MESES_PT[mes]
            ultimo_dia = pegar_ultimo_dia(mes, ano)
            print(f"\nIniciando geração para: {nome_mes}/{ano}...")
            
            page.locator("button:has-text('Baixar relatório de todos')").click()
            time.sleep(1) 

            # FILTRO DE FILIAL 
            if FILIAL_ALVO:
                print(f"Buscando filial: {FILIAL_ALVO}...")
                campo_busca = page.locator("input[placeholder='Colaboradores']")
                campo_busca.wait_for(state="visible")
                
                # Clica para focar
                campo_busca.click(force=True)
                time.sleep(0.5)

                # Limpeza do campo 
                campo_busca.clear(force=True)
                time.sleep(0.2)
                page.keyboard.press("End")
                for _ in range(15):
                    page.keyboard.press("Backspace")
                time.sleep(0.5)

                # Trava a execução até a API responder. 
                with page.expect_response(lambda response: "/api/company/search" in response.url, timeout=10000):
                    campo_busca.press_sequentially(FILIAL_ALVO, delay=200)
                
                print("API respondeu! Clicando no resultado...")
                time.sleep(1) 
                
                # Clica diretamente no botão do menu
                page.locator(f"button:has-text('{FILIAL_ALVO}')").last.click(force=True)
                time.sleep(1) 
            
            # CALENDÁRIO
            page.locator("div[class^='SelectBlock']").click()
            time.sleep(0.5)
            
            seletor_dia_1 = f"td[aria-label*=' 1 de {nome_mes} de {ano}']"
            seletor_ultimo_dia = f"td[aria-label*=' {ultimo_dia} de {nome_mes} de {ano}']"
            seletor_seta_voltar = "svg:has(path[d^='M11.29'])"

            tentativas_voltar = 0
            while not page.locator(seletor_dia_1).is_visible() and tentativas_voltar < 24:
                page.locator(seletor_seta_voltar).last.click()
                time.sleep(0.3) 
                tentativas_voltar += 1

            page.locator(seletor_dia_1).first.click()
            time.sleep(0.2)
            page.locator(seletor_ultimo_dia).first.click()
            time.sleep(0.5)

            # CONFIRMAR
            print("Solicitando relatório...")
            try:
                with page.expect_response(lambda response: "/api/client_reports/generate" in response.url, timeout=15000):
                    page.locator("button:has-text('Confirmar')").click()
                
                print(f"Sucesso! Servidor processou o pedido de {nome_mes}/{ano}.")
                
                try:
                    page.locator("button:has-text('Fechar')").click(timeout=2000)
                except:
                    pass
            except Exception as e:
                print(f"Aviso: A interceptação falhou ou demorou muito para {nome_mes}/{ano}.")

            time.sleep(1) 
            page.wait_for_selector("button:has-text('Baixar relatório de todos')", state="visible")

        print(f"\n--- FINALIZADO --- O robô terminou o lote!")
        print(f"Aguardando {TEMPO_ESPERA_FINAL} segundos de segurança antes de fechar o navegador...")
        time.sleep(TEMPO_ESPERA_FINAL) 
        browser.close()

if __name__ == "__main__":
    gerar_relatorios()