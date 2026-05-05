import streamlit as st
from supabase import create_client, Client
import tempfile
import os
import json
import pandas as pd
from extrator import extrair_dados_com_azure, cruzar_dados_com_gemini

# 1. Configuração da Página
st.set_page_config(page_title="Extrator Híbrido V2", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO CSS (O "Tapa no Visual") ---
st.markdown("""
<style>
    /* Fundo principal */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Estilização dos Cards de Métricas */
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }

    /* Botão Principal Estilo Referência */
    .stButton>button {
        background-color: #4f46e5;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #4338ca;
        border: none;
        color: white;
    }

    /* Sidebar customizada */
    section[data-testid="stSidebar"] {
        background-color: #0d1117;
        border-right: 1px solid #30363d;
    }
</style>
""", unsafe_allow_html=True)

# 2. Conectando com o Banco de Dados
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Erro ao conectar com o banco de dados. Detalhes: {e}")
    st.stop()

# 3. Gerenciamento de Sessão
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# 4. TELA DE LOGIN (Estilizada)
if not st.session_state.autenticado:
    col_v1, col_login, col_v2 = st.columns([1, 1.5, 1])
    
    with col_login:
        st.image("https://cdn-icons-png.flaticon.com/512/6166/6166548.png", width=80) # Ícone meramente ilustrativo
        st.title("Acesso Restrito")
        st.write("Faça login para acessar o Extrator Híbrido.")
        
        usuario_input = st.text_input("Usuário", placeholder="Digite seu usuário")
        senha_input = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        
        if st.button("Entrar", use_container_width=True):
            resposta = supabase.table("clientes").select("*").eq("usuario", usuario_input).eq("senha", senha_input).execute()
            if len(resposta.data) > 0:
                cliente = resposta.data[0]
                if cliente['status'] == 'ativo':
                    st.session_state.autenticado = True
                    st.session_state.usuario_logado = cliente['usuario']
                    st.rerun()
                else:
                    st.error("⛔ Acesso bloqueado (Inadimplente).")
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()

# =========================================================================
# DASHBOARD (TELA PRINCIPAL PÓS-LOGIN)
# =========================================================================

# SIDEBAR ESTILO REFERÊNCIA
with st.sidebar:
    st.title("💎 Extrator V2")
    st.markdown("---")
    st.button("🏠 Dashboard", use_container_width=True)
    st.button("➕ Novo Processamento", use_container_width=True)
    st.button("📜 Histórico", use_container_width=True)
    st.markdown("---")
    
    # Perfil do Usuário na parte inferior
    st.write(f"👤 **{st.session_state.usuario_logado}**")
    st.caption("Administrador")
    if st.button("Sair do Sistema"):
        st.session_state.autenticado = False
        st.rerun()

# CONTEÚDO PRINCIPAL
st.title(f"Olá, {st.session_state.usuario_logado}! 👋")
st.write("Vamos encontrar os melhores preços para você.")

# CARDS DE MÉTRICAS (Igual à imagem)
m1, m2, m3 = st.columns(3)
with m1:
    st.markdown('<div class="metric-card">📑 <br> Processamentos <br> <h2>24</h2> <small style="color:green">+12 este mês</small></div>', unsafe_allow_html=True)
with m2:
    st.markdown('<div class="metric-card">💰 <br> Economia Estimada <br> <h2>R$ 45.230</h2> <small style="color:green">este mês</small></div>', unsafe_allow_html=True)
with m3:
    st.markdown('<div class="metric-card">🏢 <br> Fornecedores <br> <h2>128</h2> <small>ativos</small></div>', unsafe_allow_html=True)

st.markdown("### Novo Processamento")

# ÁREA DE UPLOAD
col_a, col_b = st.columns(2)

with col_a:
    with st.container(border=True):
        st.subheader("1. Lista de Desejos")
        st.caption("Envie sua lista de produtos (.txt)")
        arquivo_txt = st.file_uploader("Upload TXT", type=['txt'], label_visibility="collapsed")

with col_b:
    with st.container(border=True):
        st.subheader("2. Orçamentos")
        st.caption("Envie até 10 arquivos de orçamentos (PDF)")
        arquivos_pdfs = st.file_uploader("Upload PDFs", type=['pdf'], accept_multiple_files=True, label_visibility="collapsed")

if st.button("🚀 Processar Análise Híbrida", use_container_width=True):
    if not arquivo_txt or not arquivos_pdfs:
        st.warning("Selecione os arquivos primeiro.")
    else:
        # ... (Mantém a mesma lógica de processamento que já funcionava) ...
        texto_lista = arquivo_txt.getvalue().decode("utf-8")
        with st.spinner('Analisando...'):
            lista_geral_bruta = []
            for arquivo_pdf in arquivos_pdfs:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(arquivo_pdf.getvalue())
                    caminho_temporario = tmp.name
                try:
                    itens_deste_pdf = extrair_dados_com_azure(caminho_temporario)
                    lista_geral_bruta.extend(itens_deste_pdf)
                finally:
                    if os.path.exists(caminho_temporario): os.unlink(caminho_temporario)
            
            if lista_geral_bruta:
                resultado_str = cruzar_dados_com_gemini(lista_geral_bruta, texto_lista)
                try:
                    dados_finais = json.loads(resultado_str)
                    df_resultado = pd.DataFrame(dados_finais)
                    st.success("🎯 Resultado da Análise")
                    st.dataframe(df_resultado, use_container_width=True)
                    csv = df_resultado.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Baixar CSV", csv, "analise.csv", "text/csv")
                except:
                    st.error("Erro na resposta da IA.")
