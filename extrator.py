import json
import streamlit as st
import re
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from google import genai

# Puxando chaves do cofre
AZURE_ENDPOINT = st.secrets["AZURE_ENDPOINT"]
AZURE_KEY = st.secrets["AZURE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# Inicializando motores
azure_client = DocumentAnalysisClient(endpoint=AZURE_ENDPOINT, credential=AzureKeyCredential(AZURE_KEY))
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# MOTOR 1: OPERACIONAL (AZURE) - Lê as tabelas com perfeição
# ==========================================
def extrair_dados_com_azure(caminho_pdf):
    with open(caminho_pdf, "rb") as f:
        poller = azure_client.begin_analyze_document("prebuilt-invoice", document=f)
    
    recibos = poller.result()
    itens_extraidos = []

    for recibo in recibos.documents:
        nome_empresa = str(recibo.fields.get("VendorName").value) if recibo.fields.get("VendorName") else "Não informado"
        cnpj = str(recibo.fields.get("VendorTaxId").value) if recibo.fields.get("VendorTaxId") else "Não informado"
        
        if recibo.fields.get("Items"):
            for item in recibo.fields.get("Items").value:
                # 1. Pegar Descrição
                descricao = str(item.value.get("Description").value) if item.value.get("Description") else "Sem descrição"
                
                # 2. Lógica Híbrida para Preço (Tenta UnitPrice, depois Amount, depois TotalPrice)
                preco_obj = item.value.get("UnitPrice") or item.value.get("Amount") or item.value.get("TotalPrice")
                
                preco = 0.0
                if preco_obj:
                    # Se o Azure já converteu para número, usamos direto
                    if isinstance(preco_obj.value, (int, float)):
                        preco = float(preco_obj.value)
                    # Se vier como texto (com vírgula), limpamos manualmente
                    else:
                        try:
                            texto_preco = str(preco_obj.content).replace('.', '').replace(',', '.')
                            preco = float(texto_preco)
                        except:
                            preco = 0.0

                confianca = float(item.value.get("Description").confidence) if item.value.get("Description") else 0.0

                itens_extraidos.append({
                    "descricao_loja": descricao,
                    "preco_unitario": preco,
                    "nome_empresa": nome_empresa,
                    "cnpj": cnpj,
                    "relation_score": confianca
                })
    return itens_extraidos

# ==========================================
# MOTOR 2: CÉREBRO (GEMINI) - Cruze semântica e resolve abreviações
# ==========================================
def cruzar_dados_com_gemini(lista_todos_itens, texto_lista):
    json_itens_azure = json.dumps(lista_todos_itens, ensure_ascii=False, indent=2)
    
    prompt = f"""
    Sua tarefa é atuar como um analista de compras especialista em cruzamento de dados.
    Eu extraí mecanicamente todos os itens de vários orçamentos. Você deve cruzar a [LISTA DE BUSCA] com a [LISTA DE TODOS OS ORÇAMENTOS] e retornar apenas o fornecedor vencedor (menor preço) para cada produto buscado.

    [LISTA DE BUSCA]:
    {texto_lista}

    [LISTA DE TODOS OS ORÇAMENTOS]:
    {json_itens_azure}
    
    Regras de Extração CRÍTICAS:
    1. SEMÂNTICA E ABREVIAÇÕES: Você entende variações. "Smart 40 PL" é o mesmo que "TV 40 polegadas". Agrupe mentalmente itens que significam o mesmo produto solicitado.
    2. ANTI-FALSO POSITIVO: Ignore acessórios ou peças de manutenção.
    3. MENOR PREÇO FINAL: Após agrupar os itens válidos para o mesmo produto, compare os preços e retorne APENAS o campeão (o mais barato).
    4. PRESERVE DADOS: Mantenha os valores originais de "nome_empresa", "cnpj", "descricao_loja" e "relation_score" do item vencedor.
    
    Retorne ESTRITAMENTE UMA LISTA JSON de objetos com as chaves exatas: "produto_buscado", "descricao_loja", "preco_unitario", "nome_empresa", "cnpj", "relation_score". 
    """
    
    try:
        resposta = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        texto = resposta.text
        match = re.search(r'\[.*\]', texto, re.DOTALL)
        if match:
            return match.group(0)
        else:
            return "Erro na IA: Nenhum formato JSON válido foi encontrado."
    except Exception as e:
        return f"Erro na comunicação com a IA: {str(e)}"