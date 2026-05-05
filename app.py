import streamlit as st
from supabase import create_client, Client
import tempfile
import os
import json
import pandas as pd
from extrator import extrair_dados_com_azure, cruzar_dados_com_gemini

# 1. Configuração da Página
st.set_page_config(page_title="Extrator Híbrido", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    
    /* Estilo dos Botões da Sidebar */
    .stButton>button {
        background-color: #4f46e5;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        width: 100%;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #4338ca; color: white; }
    
    /* Container de Login */
    .login-box {
        text-align: center;
        padding: 40px;
        background-color: #161b22;
        border-radius: 15px;
        border: 1px solid #30363d;
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
if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = "Novo Processamento"

# 4. TELA DE LOGIN
if not st.session_state.autenticado:
    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        # Imagem de referência a login seguro
        st.image("https://cdn-icons-png.flaticon.com/512/2592/2592317.png", width=100) 
        st.title("Acesso Restrito")
        st.write("Insira suas credenciais para acessar a plataforma.")
        
        usuario_input = st.text_input("Usuário", placeholder="ex: fabricio")
        senha_input = st.text_input("Senha", type="password", placeholder="••••••••")
        
        if st.button("Entrar na Plataforma"):
            res = supabase.table("clientes").select("*").eq("usuario", usuario_input).eq("senha", senha_input).execute()
            if len(res.data) > 0:
                user = res.data[0]
                if user['status'] == 'ativo':
                    st.session_state.autenticado = True
                    st.session_state.usuario_logado = user['usuario']
                    st.session_state.cargo_usuario = user.get('cargo', 'Cliente') # Busca o cargo do banco
                    st.rerun()
                else:
                    st.error("⛔ Conta desativada.")
            else:
                st.error("Usuário ou senha inválidos.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# =========================================================================
# DASHBOARD (TELA PRINCIPAL)
# =========================================================================

# SIDEBAR NAVEGÁVEL
with st.sidebar:
    st.title("💎 Extrator V2")
    st.markdown("---")
    
    if st.button("🏠 Dashboard"):
        st.session_state.pagina_atual = "Dashboard"
    if st.button("➕ Novo Processamento"):
        st.session_state.pagina_atual = "Novo Processamento"
    if st.button("📜 Histórico"):
        st.session_state.pagina_atual = "Histórico"
    
    st.markdown("---")
    st.write(f"👤 **{st.session_state.usuario_logado}** 👋")
    st.caption(f"{st.session_state.cargo_usuario}") # Cargo dinâmico
    
    if st.button("Sair do Sistema", type="secondary"):
        st.session_state.autenticado = False
        st.rerun()

# LÓGICA DE NAVEGAÇÃO
if st.session_state.pagina_atual == "Novo Processamento":
    st.title(f"Olá, {st.session_state.usuario_logado}! 👋")
    st.write("Vamos processar novos orçamentos agora.")

    # ÁREA DE UPLOAD
    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
            st.subheader("1. Lista de Desejos")
            arquivo_txt = st.file_uploader("Suba sua lista (.txt)", type=['txt'])

    with col_b:
        with st.container(border=True):
            st.subheader("2. Orçamentos")
            arquivos_pdfs = st.file_uploader("Suba os PDFs (Máx 10)", type=['pdf'], accept_multiple_files=True)

    if st.button("🚀 Processar Análise Híbrida"):
        if not arquivo_txt or not arquivos_pdfs:
            st.warning("Selecione os arquivos primeiro.")
        else:
            texto_lista = arquivo_txt.getvalue().decode("utf-8")
            with st.spinner('Analisando documentos...'):
                lista_geral_bruta = []
                for arquivo_pdf in arquivos_pdfs:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(arquivo_pdf.getvalue())
                        caminho_tmp = tmp.name
                    try:
                        itens = extrair_dados_com_azure(caminho_tmp)
                        lista_geral_bruta.extend(itens)
                    finally:
                        if os.path.exists(camin_tmp): os.unlink(camin_tmp)
                
                if lista_geral_bruta:
                    res_ia = cruzar_dados_com_gemini(lista_geral_bruta, texto_lista)
                    try:
                        dados = json.loads(res_ia)
                        st.success("🎯 Análise Concluída!")
                        st.dataframe(pd.DataFrame(dados), use_container_width=True)
                    except:
                        st.error("Falha ao formatar resposta da IA.")
                else:
                    st.error("Nenhum dado extraído dos PDFs.")

elif st.session_state.pagina_atual == "Dashboard":
    st.title("📊 Painel de Performance")
    st.info("As estatísticas reais de economia e volume aparecerão aqui após os primeiros processamentos serem salvos no banco.")

elif st.session_state.pagina_atual == "Histórico":
    st.title("📜 Histórico de Análises")
    st.info("Em breve: Você poderá consultar todas as análises feitas anteriormente.")
