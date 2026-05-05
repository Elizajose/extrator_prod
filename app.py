import streamlit as st
import tempfile
import os
import json
import pandas as pd
from extrator import extrair_dados_com_azure, cruzar_dados_com_gemini

st.set_page_config(page_title="Extrator Híbrido V2", layout="wide")

st.title("🚀 Extrator de Orçamentos V2")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Lista de Desejos")
    # Criando a variável que faltava!
    arquivo_txt = st.file_uploader("Suba sua lista (.txt)", type=['txt'])

with col2:
    st.subheader("2. Orçamentos")
    # Criando a segunda variável com o limite de 10 que você pediu!
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
                    
                    # Botão para baixar Excel (precisa do openpyxl instalado!)
                    csv = df_resultado.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Baixar Resultado (CSV)", csv, "analise_precos.csv", "text/csv")
                    
                except Exception as e:
                    st.error(f"Erro ao processar resposta da IA: {resultado_str}")
            else:
                st.error("O Azure não conseguiu extrair dados dos PDFs. Verifique se são PDFs de orçamentos válidos.")