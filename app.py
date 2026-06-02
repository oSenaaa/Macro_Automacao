import streamlit as st
import datetime
import calendar
import os
from automacao_filtro import gerar_relatorios

# install unico do servidor
@st.cache_resource
def install_playwright():
    os.system("playwright install chromium")

install_playwright()

# lógica de datas
def subtrair_meses(data, meses):
    mes = data.month - meses
    ano = data.year
    while mes <= 0:
        mes += 12
        ano -= 1
    max_dia = calendar.monthrange(ano, mes)[1]
    dia = min(data.day, max_dia)
    return datetime.date(ano, mes, dia)

def gerar_lista_periodos(data_inicio_base, data_fim_base, qtd_periodos):
    periodos = []
    for i in range(qtd_periodos):
        inicio = subtrair_meses(data_inicio_base, i)
        fim = subtrair_meses(data_fim_base, i)
        periodos.append((inicio, fim))
    return periodos

# ui
st.set_page_config(page_title="Automação Oitchau", page_icon="🤖", layout="centered")

st.title("Luquinhas Generator")
st.write("Use esta ferramenta para gerar relatórios em lote e em segundo plano!")

st.warning("""
**⚠️ ATENÇÃO IMPORTANTE:** O perfil das credenciais inseridas já precisa estar no ambiente da empresa a ser gerado com o acesso de **Admin**.
Além disso, o **último acesso** desse login no Oitchau precisa ter sido obrigatoriamente nessa empresa.
""", icon="🚨")

st.divider()

st.subheader("🔑 Credenciais de Acesso")
col1, col2 = st.columns(2)
with col1:
    email_usuario = st.text_input("E-mail do Oitchau")
with col2:
    senha_usuario = st.text_input("Senha", type="password")

st.divider()

st.subheader("⚙️ Configurações do Relatório")

filial_selecionada = st.text_input("Nome da Filial (deixe em branco para gerar de Todos):")
st.caption("⚠️ *Atenção: O nome deve ser escrito **exatamente** como está na plataforma.*")

st.markdown("<br>", unsafe_allow_html=True)

# calendário base
hoje = datetime.date.today()
mes_passado = hoje.replace(day=1) - datetime.timedelta(days=1)
primeiro_dia_mes_passado = mes_passado.replace(day=1)

st.markdown("#### 📅 Período de Fechamento Base")
st.write("Defina o período exato de fechamento. O robô usará esses dias como referência para os meses anteriores.")

datas_selecionadas = st.date_input(
    "Selecione as Datas (Início e Fim):",
    value=(primeiro_dia_mes_passado, mes_passado),
    format="DD/MM/YYYY"
)

# ciclos de geração
opcao_periodo = st.selectbox(
    "Gerar relatórios (com esse mesmo formato de dias) para:", [
    "Apenas o período selecionado acima",
    "Últimos 3 ciclos (para trás)",
    "Últimos 6 ciclos (para trás)",
    "Últimos 12 ciclos (para trás)"
])

if opcao_periodo == "Apenas o período selecionado acima": qtd_ciclos = 1
elif opcao_periodo == "Últimos 3 ciclos (para trás)": qtd_ciclos = 3
elif opcao_periodo == "Últimos 6 ciclos (para trás)": qtd_ciclos = 6
else: qtd_ciclos = 12

# resumo dos períodos
if len(datas_selecionadas) == 2:
    lista_de_periodos = gerar_lista_periodos(datas_selecionadas[0], datas_selecionadas[1], qtd_ciclos)
    st.info(f"📌 **O robô vai gerar os seguintes {qtd_ciclos} período(s):**")
    resumo_texto = ""
    for inicio, fim in lista_de_periodos:
        resumo_texto += f"- De {inicio.strftime('%d/%m/%Y')} até {fim.strftime('%d/%m/%Y')}\n"
    st.markdown(resumo_texto)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tipo e formato ──────────────────────────────────────────────
col_tipo, col_sub = st.columns(2)
with col_tipo:
    tipo_relatorio = st.radio(
        "Tipo de Documento:",
        options=["PDF", "Excel"],
        horizontal=True
    )
with col_sub:
    if tipo_relatorio == "Excel":
        opcao_excel = st.radio(
            "Formato Excel:",
            options=["XLSX", "CSV"],
            horizontal=True
        )
        formato_final = opcao_excel
    else:
        st.markdown("**Formato:** PDF")
        formato_final = "PDF"

# ── Opções adicionais (condicionais por formato) ─────────────────
st.markdown("**Opções adicionais:**")
mostrar_desativados  = st.checkbox("Mostrar colaboradores desativados")
esconder_supervisores = st.checkbox("Esconder os supervisores")
if tipo_relatorio == "PDF":
    unir_relatorios = st.checkbox("Unir todos os relatórios em um arquivo")
else:
    unir_relatorios = False

# ── Colunas ──────────────────────────────────────────────────────
COLUNAS_DISPONIVEIS = [
    "Data", "Jornada", "Grupo de regras", "Pontos", "Planejadas", "Trabalhadas",
    "Intervalo", "Noturno", "Distribuição de horas", "Atraso entrada", "Saída antecipada",
    "Fases de Horas Extras", "Horas Extras", "Desconto", "Fases do Banco de Horas",
    "Banco Dia", "Horas Faltantes", "Banco Acumulado", "Saldo projetado a expirar",
    "Data estimada de expiração", "Interjornada", "Feriado", "Ajustes", "Motivo", "Obs",
    "Sobreaviso", "Acionamento", "Total de Sobreaviso (Sem acionamento)",
    "Fases de Intervalos não utilizados", "Intervalos não utilizados",
]

colunas_selecionadas = st.multiselect(
    "Colunas a incluir no relatório:",
    options=COLUNAS_DISPONIVEIS,
    default=["Data", "Pontos", "Trabalhadas", "Intervalo", "Noturno", "Feriado", "Obs"],
)
st.caption("⚠️ As colunas **Data** e **Pontos** são obrigatórias na plataforma e sempre serão incluídas.")

st.divider()

# action button
if st.button("🚀 Gerar Relatórios", type="primary", use_container_width=True):
    if not email_usuario or not senha_usuario:
        st.error("Por favor, preencha o e-mail e a senha para continuar!")
    elif len(datas_selecionadas) != 2:
        st.warning("Por favor, selecione uma data de **INÍCIO** e uma data de **FIM** no calendário.")
    else:
        st.success(f"Pedido recebido! Autenticando como {email_usuario}...")
        with st.spinner(f"O robô está rodando em 2º plano para a filial '{filial_selecionada or 'TODAS'}'. Isso pode levar alguns minutos..."):
            try:
                gerar_relatorios(
                    email_usuario, senha_usuario, filial_selecionada, lista_de_periodos,
                    formato=formato_final,
                    colunas=colunas_selecionadas,
                    mostrar_desativados=mostrar_desativados,
                    esconder_supervisores=esconder_supervisores,
                    unir_relatorios=unir_relatorios,
                )
                st.balloons()
                st.success(f"Tudo pronto! Foram gerados {qtd_ciclos} relatórios com sucesso. Verifique o seu e-mail!")
            except Exception as e:
                st.error(f"Puxa, o robô encontrou um problema: {e}")
