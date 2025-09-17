import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
from fpdf import FPDF
import io
import base64
import tempfile
import os

try:
    st.set_page_config(page_title="Análise por Nível - Educação", page_icon="st/img/favicon.ico", layout="wide")
except st.errors.StreamlitAPIException:
    pass

caminho_planilha = "xls/Pasta_1.xlsx"
caminho_logo = "img/logo_2021.png"

@st.cache_data
def load_data(path):
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip()
    def tratar_inep(x):
        if pd.isna(x):
            return ""
        if isinstance(x, float):
            return str(int(x))
        return str(x).strip()
    df["INEP"] = df["INEP"].apply(tratar_inep)
    return df

def load_logo(path):
    try:
        return Image.open(path)
    except FileNotFoundError:
        st.sidebar.error(f"Arquivo de imagem '{path}' não encontrado.")
        return None

def cor_card_por_percentual(pct):
    if pct <= 25:
        return "#FF4136", "white"
    elif pct <= 50:
        return "#FF851B", "black"
    elif pct <= 75:
        return "#B0E57C", "black"
    else:
        return "#006400", "white"

def agrupar_niveis(etapa, componente, valores):
    if etapa == 5 and componente == "LP":
        grupos = {'INSUFICIENTE': [0,1], 'BÁSICO':[2,3], 'PROFICIENTE':[4,5], 'AVANÇADO':[6,7,8,9]}
    elif etapa == 5 and componente == "MT":
        grupos = {'INSUFICIENTE': [0,1,2], 'BÁSICO':[3,4], 'PROFICIENTE':[5,6], 'AVANÇADO':[7,8,9]}
    elif etapa == 9 and componente == "LP":
        grupos = {'INSUFICIENTE': [0], 'BÁSICO':[1,2,3], 'PROFICIENTE':[4,5], 'AVANÇADO':[6,7,8]}
    elif etapa == 9 and componente == "MT":
        grupos = {'INSUFICIENTE':[0,1], 'BÁSICO':[2,3,4], 'PROFICIENTE':[5,6], 'AVANÇADO':[7,8,9]}
    else:
        grupos = {'INSUFICIENTE':[0,1], 'BÁSICO':[2,3,4], 'PROFICIENTE':[5,6], 'AVANÇADO':[7,8,9]}

    cores = {'INSUFICIENTE':'#FF4136', 'BÁSICO':'#FF851B', 'PROFICIENTE':'#B0E57C', 'AVANÇADO':'#006400'}
    text_colors = {'INSUFICIENTE':'white', 'BÁSICO':'black', 'PROFICIENTE':'black', 'AVANÇADO':'white'}

    valores_categorias, categorias, cores_list, text_colors_list = [], [], [], []
    for cat, indices in grupos.items():
        soma = sum([valores[i] if i < len(valores) else 0 for i in indices])
        valores_categorias.append(soma)
        categorias.append(cat)
        cores_list.append(cores[cat])
        text_colors_list.append(text_colors[cat])

    return categorias, valores_categorias, cores_list, text_colors_list

def make_fig(etapa, componente, inep, edicao, df):
    filtro = (df['INEP'] == inep) & (df['ETAPA'] == etapa) & (df['COMP_ CURRICULAR'] == componente) & (df['EDIÇÃO'] == edicao)
    df_sel = df.loc[filtro]

    if df_sel.empty:
        return None, None, None

    nivel_cols = [f"Nivel {i}" for i in range(11) if f"Nivel {i}" in df_sel.columns]
    valores_str = df_sel[nivel_cols].fillna("0").replace("-", "0")
    valores = valores_str.apply(pd.to_numeric, errors="coerce").fillna(0).values.flatten()

    categorias, valores_categorias, cores, text_colors = agrupar_niveis(etapa, componente, valores)

    fig = go.Figure()
    for val, cor, tcor, cat in zip(valores_categorias, cores, text_colors, categorias):
        fig.add_trace(go.Bar(
            y=[""],
            x=[val],
            name=cat,
            orientation="h",
            marker_color=cor,
            text=[f"{val:.1f}%"],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color=tcor, size=14, family="Arial Bold"),
        ))

    fig.update_layout(
        barmode="stack",
        height=180,
        margin=dict(t=40,b=20,l=20,r=180),
        showlegend=True,
        legend=dict(title="Categorias",x=1,y=0.5,xanchor="left",yanchor="middle",font=dict(size=14)),
        xaxis=dict(range=[0, 100],showgrid=False,zeroline=False,ticksuffix="%"),
        yaxis=dict(showticklabels=False),
        title=f"Desempenho em {componente} - {etapa}º Ano - INEP: {inep} - Edição: {edicao}",
        title_font=dict(size=18,family="Arial"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig, categorias, valores_categorias

def show_aprendizagem_adequada_card(valor, small=False):
    valor_rounded = round(valor, 0)
    bg_color, text_color = cor_card_por_percentual(valor_rounded)
    width = "180px" if small else "250px"
    padding = "10px" if small else "15px"
    font_size = "36px" if small else "48px"
    st.markdown(
        f"""
        <div style='background-color:{bg_color}; color:{text_color}; padding:{padding}; border-radius:10px; width:{width};
        margin:auto; box-shadow: 2px 2px 5px rgba(0,0,0,0.15); text-align:center;'>
            <h5>Aprendizagem Adequada</h5>
            <h1 style='font-size:{font_size}; margin:0;'>{valor_rounded:.0f}%</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

def criar_pdf(nome_escola, etapa, componente, resultados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Relatório SAEB - {nome_escola} - Etapa {etapa} - {componente}", 0, 1, "C")
    pdf.ln(10)

    for res in resultados:
        titulo = f"Edição: {res['edicao']}"
        aprendizagem = f"Aprendizagem Adequada: {res['aprendizagem']:.0f}%"
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, titulo, 0, 1)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, aprendizagem, 0, 1)
        pdf.ln(5)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
            tmpfile.write(res['fig_bytes'])
            tmpfile.flush()
            pdf.image(tmpfile.name, w=pdf.w - 40)
            os.unlink(tmpfile.name)
        pdf.ln(10)

    return pdf.output(dest="S").encode("latin1")

st.markdown("""
<style>
.css-1l02zno { justify-content: center; gap: 2.5rem; }
.stSelectbox > label { font-weight: 600; font-size: 18px; }
a:hover { background-color: #0b5ed7 !important; cursor: pointer; }
</style>
""", unsafe_allow_html=True)

logo = load_logo(caminho_logo)
if logo:
    st.sidebar.image(logo, use_container_width=True)

df = load_data(caminho_planilha)
inep_codigos = set(df["INEP"].dropna().unique())

st.sidebar.title("Busca por Código INEP")
inep_digitado = st.sidebar.text_input("Digite o código INEP da escola ou município").strip()

if inep_digitado and inep_digitado in inep_codigos:
    inep_selecionado = inep_digitado
else:
    inep_selecionado = None
    if inep_digitado:
        st.sidebar.error("Código INEP não encontrado. Digite um código válido.")

if inep_selecionado:
    st.title("📊 Análise de Desempenho SAEB por Níveis")

    nome_escola = df.loc[df["INEP"] == inep_selecionado, "NO_MUNICIPIO"].iloc[0]
    st.markdown(f"#### Escola / Município: {nome_escola}")

    st.markdown("Selecione a etapa e o componente curricular para visualizar os resultados.")

    etapas_disponiveis = sorted(df[df["INEP"] == inep_selecionado]["ETAPA"].unique())
    componentes_disponiveis = sorted(df[df["INEP"] == inep_selecionado]["COMP_ CURRICULAR"].unique())

    col1, col2 = st.columns(2)
    with col1:
        etapa = st.selectbox("Etapa", etapas_disponiveis)
    with col2:
        componente = st.selectbox("Componente Curricular", componentes_disponiveis)

    edicoes = sorted(df[(df["INEP"] == inep_selecionado) & (df["ETAPA"] == etapa) & (df["COMP_ CURRICULAR"] == componente)]["EDIÇÃO"].unique())
    resultados_pdf = []

    for ed in edicoes:
        fig, categorias, valores_categorias = make_fig(etapa, componente, inep_selecionado, ed, df)
        if fig:
            st.markdown(f"### Edição: {ed}")
            col_grafico, col_card = st.columns([4, 1])
            with col_grafico:
                st.plotly_chart(fig, use_container_width=True)
            with col_card:
                aprendizado = valores_categorias[2] + valores_categorias[3]
                show_aprendizagem_adequada_card(aprendizado, small=True)
            st.markdown("<br>", unsafe_allow_html=True)
            img_bytes = fig.to_image(format="png")
            resultados_pdf.append({'edicao': ed, 'fig_bytes': img_bytes, 'aprendizagem': aprendizado})

    if st.button("📄 Gerar PDF e Baixar Relatório"):
        pdf_bytes = criar_pdf(nome_escola, etapa, componente, resultados_pdf)
        st.download_button(
            label="Clique aqui para baixar o PDF",
            data=pdf_bytes,
            file_name=f"Relatorio_SAEB_{nome_escola}.pdf",
            mime="application/pdf"
        )
else:
    st.title("📊 Análise de Desempenho SAEB por Níveis")
    st.info("Informe um código INEP válido para exibir os resultados.")

st.markdown("---")
st.markdown(
    """
    <div style="background:#f9f9f9; border-radius:10px; padding:15px; font-family: Arial, sans-serif; max-width: 900px; margin: auto;">
        <h3>Tipos de Aprendizado</h3>
        <ul style="list-style-type:none; padding:0;">
            <li><strong>Avançado:</strong> Aprendizado além da expectativa. Recomenda-se para os alunos neste nível atividades desafiadoras.</li>
            <li><strong>Proficiente:</strong> Os alunos neste nível encontram-se preparados para continuar os estudos. Recomenda-se atividades de aprofundamento.</li>
            <li><strong>Básico:</strong> Os alunos neste nível precisam melhorar. Sugere-se atividades de reforço.</li>
            <li><strong>Insuficiente:</strong> Os alunos neste nível apresentaram pouquíssimo aprendizado. É necessário a recuperação de conteúdos.</li>
        </ul>
        <p><small>Fonte: <a href="https://qedu.org.br/" target="_blank">https://qedu.org.br/</a> INEP, 2023.</small></p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <footer style="text-align:center; color:#888; margin-top:50px; padding:15px 0; font-size:14px; font-family: Arial, sans-serif; border-top: 1px solid #ddd;">
    © 2025 Desenvolvido por sua equipe de análise
    </footer>
    """,
    unsafe_allow_html=True,
)
