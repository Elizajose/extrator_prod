import streamlit as st
import tempfile
import os
import json
import pandas as pd
from extrator import extrair_dados_com_azure, cruzar_dados_com_gemini

# [MANTER O SEU CÓDIGO DE INTERFACE AQUI EM CIMA: Título, Upload de TXT e Upload dos PDFs com limite de 10]

if st.button("🚀 Processar Análise"):
    if not arquivo_txt or not arquivos_pdfs:
        st.warning("Por favor, suba a lista de compras e os orçamentos.")
    else:
        texto_lista = arquivo_txt.getvalue().decode("utf-8")
        
        with st.spinner('Lendo PDFs com Azure e cruzando dados com IA...'):
            lista_geral_bruta = []
            
            # Passo 1: Extração mecânica de todos os PDFs
            for arquivo_pdf in arquivos_pdfs:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(arquivo_pdf.getvalue())
                    caminho_temporario = tmp.name
                
                try:
                    itens_deste_pdf = extrair_dados_com_azure(caminho_temporario)
                    lista_geral_bruta.extend(itens_deste_pdf)
                except Exception as e:
                    st.error(f"Falha de leitura no arquivo {arquivo_pdf.name}: {e}")
                finally:
                    if os.path.exists(caminho_temporario):
                        os.unlink(caminho_temporario)
            
            # Passo 2: Raciocínio lógico e semântico via Gemini
            if lista_geral_bruta:
                resultado_str = cruzar_dados_com_gemini(lista_geral_bruta, texto_lista)
                
                if "Erro" in resultado_str:
                    st.error(resultado_str)
                else:
                    try:
                        dados_finais = json.loads(resultado_str)
                        # Exibindo o resultado final na tela em formato de tabela
                        df_resultado = pd.DataFrame(dados_finais)
                        st.success("Análise concluída com sucesso!")
                        st.dataframe(df_resultado, use_container_width=True)
                    except json.JSONDecodeError:
                        st.error("Falha ao organizar o resultado final.")
            else:
                st.warning("Nenhum item válido foi encontrado em nenhum dos orçamentos.")

# [MANTER O SEU CÓDIGO DE DOWNLOAD DE PDF/EXCEL AQUI EMBAIXO]