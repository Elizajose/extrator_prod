import streamlit as st
from supabase import create_client, Client
import tempfile
import os
import json
import pandas as pd
from extrator import extrair_dados_com_azure, cruzar_dados_com_gemini

# 1. Configuração da Página (DEVE ser o primeiro comando Streamlit)
st.set_page_config(page_title="Extrator Híbrido V2", layout="wide")

# 2. Conectando com o Banco de Dados (Supabase)
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    # AQUI ESTÁ A CORREÇÃO: Agora ele vai mostrar o erro real vindo do Python/Supabase
    st.error(f"Erro ao conectar com o banco de dados. Detalhes: {e}")
    st.stop()

# 3. Gerenciamento de Sessão (Memória do Login)
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# 4. Tela de Login (Se não estiver logado, mostra o formulário e bloqueia o resto)
if not st.session_state.autenticado:
    st.title("🔒 Acesso Restrito")
    st.markdown("Por favor, faça login para acessar o Extrator Híbrido.")
    
    # Criando colunas para o formulário não ficar gigante na tela
    col_vazia1, col_login, col_vazia2 = st.columns([1, 2, 1])
    
    with col_login:
        usuario_input = st.text_input("Usuário")
        senha_input = st.text_input("Senha", type="password")
        
        if st.button("Entrar", use_container_width=True):
            # Vai no Supabase e procura o usuário e senha digitados
            resposta = supabase.table("clientes").select("*").eq("usuario", usuario_input).eq("senha", senha_input).execute()
            
            # Se achou alguém no banco de dados...
            if len(resposta.data) > 0:
                cliente = resposta.data[0]
                
                # Regra de negócio: O cliente pagou? (Status: ativo)
                if cliente['status'] == 'ativo':
                    st.session_state.autenticado = True
                    st.session_state.usuario_logado = cliente['usuario']
                    st.success("Login aprovado! Redirecionando...")
                    st.rerun() # Atualiza a página para carregar o sistema
                else:
                    st.error("⛔ Acesso bloqueado (Status: Inadimplente). Entre em contato com o suporte financeiro.")
            else:
                st.error("Usuário ou senha incorretos.")
                
    # O st.stop() é crucial! Ele barra tudo que estiver abaixo dele se o login não for feito.
    st.stop()

# =========================================================================
# DAQUI PARA BAIXO SÓ RODA SE O USUÁRIO PASSOU PELO LOGIN (ESTÁ AUTENTICADO)
# =========================================================================

# Menu Lateral (Sidebar) com as informações da conta
st.sidebar.success(f"Logado como: {st.session_state.usuario_logado}")
if st.sidebar.button("Sair do Sistema"):
    st.session_state.autenticado = False
    st.rerun()

# Seu app principal começa aqui!
st.title("🚀 Extrator de Orçamentos V2")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Lista de Desejos")
    arquivo_txt = st.file_uploader("Suba sua lista (.txt)", type=['txt'])

with col2:
    st.subheader("2. Orçamentos")
    arquivos_pdfs = st.file_uploader("Suba até 10 PDFs", type=['pdf'], accept_multiple_files=True)
    if arquivos_pdfs and len(arquivos_pdfs) > 10:
        st.error("Limite de 10 arquivos excedido! Por favor, remova alguns.")
        arquivos_pdfs = None

st.markdown("---")

if st.button("📊 Processar Análise Híbrida"):
    if not arquivo_txt or not arquivos_pdfs:
        st.warning("Opa! Preciso da lista TXT e de pelo menos um PDF para trabalhar.")
    else:
        texto_lista = arquivo_txt.getvalue().decode("utf-8")
        
        with st.spinner('Azure lendo tabelas e Gemini comparando itens...'):
            lista_geral_bruta = []
            
            for arquivo_pdf in arquivos_pdfs:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(arquivo_pdf.getvalue())
                    caminho_temporario = tmp.name
                
                try:
                    # Motor 1: Azure
                    itens_deste_pdf = extrair_dados_com_azure(caminho_temporario)
                    lista_geral_bruta.extend(itens_deste_pdf)
                except Exception as e:
                    st.error(f"Erro no arquivo {arquivo_pdf.name}: {e}")
                finally:
                    if os.path.exists(caminho_temporario):
                        os.unlink(caminho_temporario)
            
            if lista_geral_bruta:
                # Motor 2: Gemini
                resultado_str = cruzar_dados_com_gemini(lista_geral_bruta, texto_lista)
                
                try:
                    dados_finais = json.loads(resultado_str)
                    df_resultado = pd.DataFrame(dados_finais)
                    
                    st.success("🎯 Análise de Menor Preço Concluída!!")
                    st.dataframe(df_resultado, use_container_width=True)
                    
                    # Botão para baixar CSV
                    csv = df_resultado.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Baixar Resultado (CSV)", csv, "analise_precos.csv", "text/csv")
                    
                except Exception as e:
                    st.error(f"Erro ao processar resposta da IA: {resultado_str}")
            else:
                st.error("O Azure não conseguiu extrair dados dos PDFs. Verifique se são PDFs de orçamentos válidos.")