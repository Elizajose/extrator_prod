import streamlit as st
from supabase import create_client, Client
import tempfile
import os
import json
import pandas as pd
from extrator import extrair_dados_com_azure, cruzar_dados_com_gemini

# 1. Configuração da Página
st.set_page_config(page_title="Extrator Híbrido V2", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO CSS (Foco em Centralização e Modernidade) ---
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
    
    /* Forçar centralização da imagem de perfil no login */
    .img-center {
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 100px;
        margin-bottom: 20px;
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

# 4. TELA DE LOGIN (CORRIGIDA: ÍCONE AZUL E CENTRALIZADO)
if not st.session_state.autenticado:
    _, col_login, _ = st.columns([1, 1.2, 1]) # Ajustei a largura para o box ficar mais elegante
    
    with col_login:
        st.write("##") # Espaçamento vertical
        with st.container(border=True):
            # Ícone de Perfil Azul e Branco Centralizado via HTML
            st.markdown(
                '<img src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png" class="img-center">', 
                unsafe_allow_html=True
            )
            
            st.markdown("<h2 style='text-align: center;'>Acesso Restrito</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #8b949e;'>Insira suas credenciais para acessar a plataforma.</p>", unsafe_allow_html=True)
            
            # Campos com Placeholders Cinzas
            usuario_input = st.text_input("Usuário", placeholder="Insira seu usuário")
            senha_input = st.text_input("Senha", type="password", placeholder="Insira sua senha")
            
            st.write(" ") 
            
            if st.button("Entrar na Plataforma", use_container_width=True):
                try:
                    res = supabase.table("clientes").select("*").eq("usuario", usuario_input).eq("senha", senha_input).execute()
                    if len(res.data) > 0:
                        user = res.data[0]
                        if user['status'] == 'ativo':
                            st.session_state.autenticado = True
                            st.session_state.usuario_logado = user['usuario']
                            # Pega o cargo dinamicamente da coluna 'cargo'
                            st.session_state.cargo_usuario = user.get('cargo', 'Cliente')
                            st.rerun()
                        else:
                            st.error("⛔ Conta inativa. Contate o suporte.")
                    else:
                        st.error("Usuário ou senha incorretos.")
                except Exception as e:
                    st.error(f"Erro: {e}")
    st.stop()

# =========================================================================
# DASHBOARD (TELA PRINCIPAL)
# =========================================================================

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
    st.caption(f"{st.session_state.cargo_usuario}")
    
    if st.button("Sair do Sistema", type="secondary"):
        st.session_state.autenticado = False
        st.rerun()

if st.session_state.pagina_atual == "Novo Processamento":
    st.title(f"Olá, {st.session_state.usuario_logado}! 👋")
    st.write("Vamos processar novos orçamentos agora.")

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
                    except Exception as e:
                        st.error(f"Erro no PDF {arquivo_pdf.name}: {e}")
                    finally:
                        if os.path.exists(caminho_tmp):
                            os.unlink(camin_tmp)
                
                if lista_geral_bruta:
                    res_ia = cruzar_dados_com_gemini(lista_geral_bruta, texto_lista)
                    try:
                        dados = json.loads(res_ia)
                        st.success("🎯 Análise Concluída!")
                        st.dataframe(pd.DataFrame(dados), use_container_width=True)
                    except:
                        st.error("Falha ao formatar resposta da IA.")
                else:
                    st.error("Nenhum dado extraído.")

elif st.session_state.pagina_atual == "Dashboard":
    st.title("📊 Painel de Performance")
    st.info("Estatísticas reais em breve.")

elif st.session_state.pagina_atual == "Histórico":
    st.title("📜 Histórico de Análises")
    st.info("Em breve: Consulta de processamentos anteriores.")
