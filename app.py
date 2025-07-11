import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

st.set_page_config(page_title="Formatador de Planilhas - Importação de Pessoas", layout="centered")

st.title("🧾 Formatador de Planilhas para Importação de Pessoas")

st.markdown("Faça upload de uma planilha com dados diversos (CPF, Razão Social, Email, etc.) e receba um arquivo formatado para importação.")

uploaded_file = st.file_uploader("📁 Faça o upload da planilha", type=["xlsx", "xls", "csv"])

# Dicionário de sinônimos para mapear colunas variadas
colunas_referencia = {
    'razao_social': ['nome', 'razao', 'razao_social', 'cliente', 'empresa'],
    'fantasia': ['fantasia', 'nome_fantasia'],
    'cpf': ['cpf', 'cnpj', 'documento'],
    'email': ['email', 'e-mail'],
    'celular': ['celular', 'whatsapp', 'telefone_celular', 'telefone'],
    'cep': ['cep'],
    'bairro': ['bairro'],
    'endereco': ['endereco', 'logradouro', 'rua'],
    'numero': ['numero', 'número', 'num'],
    'cidade': ['cidade', 'municipio'],
    'uf': ['uf', 'estado']
}

def identificar_coluna(possibilidades, colunas):
    for nome in possibilidades:
        for c in colunas:
            if nome.lower() in str(c).lower():
                return c
    return None

def detectar_tipo(doc):
    doc = re.sub(r'\D', '', str(doc))
    if len(doc) == 11:
        return "F"
    elif len(doc) == 14:
        return "J"
    return ""

def escolher_mais_completo(duplicatas):
    return duplicatas.loc[duplicatas.count(axis=1).idxmax()]

if uploaded_file.name.endswith('.csv'):
    try:
        df_origem = pd.read_csv(uploaded_file, encoding='utf-8')
    except UnicodeDecodeError:
        df_origem = pd.read_csv(uploaded_file, encoding='latin1')
else:
    df_origem = pd.read_excel(uploaded_file)

    colunas = df_origem.columns
    dados = {}

    # Preencher campos de destino com base na identificação
    for destino, sinonimos in colunas_referencia.items():
        coluna = identificar_coluna(sinonimos, colunas)
        if coluna:
            dados[destino] = df_origem[coluna].astype(str)
        else:
            dados[destino] = np.nan

    # Ajustar e validar os campos obrigatórios
    dados['cpf'] = dados['cpf'].apply(lambda x: re.sub(r'\D', '', str(x)))
    dados['cpf'] = dados['cpf'].apply(lambda x: x if len(x) in [11, 14] else np.nan)
    dados['cpf'] = dados['cpf'].fillna("")
    dados['tipo'] = dados['cpf'].apply(detectar_tipo)
    dados['razao_social'] = dados['razao_social'].fillna("NOME NAO INFORMADO")

    # Corrigir nome fantasia: preencher apenas se for PJ e se houver dado diferente de razao_social
    dados['fantasia'] = np.where(
        (dados['tipo'] == 'J') & (dados['fantasia'].notna()) & (dados['fantasia'] != dados['razao_social']),
        dados['fantasia'],
        ''
    )

    # Criar DataFrame final com 27 colunas do modelo
    colunas_finais = [
        'codigo', 'razao_social', 'fantasia', 'cpf', 'rg', 'inscricao_estadual', 'inscricao_municipal',
        'tipo', 'telefone', 'celular', 'email', 'site', 'data_nascimento', 'cep', 'endereco',
        'numero', 'complemento', 'bairro', 'ponto_referencia', 'cidade', 'uf', 'pais', 'brasileiro',
        'passaporte', 'sexo', 'veiculo', 'estado_civil', 'profissao', 'observacao'
    ]
    df_final = pd.DataFrame(columns=colunas_finais)

    # Preencher apenas os campos definidos pelo usuário
    for campo in ['razao_social', 'fantasia', 'cpf', 'tipo', 'celular', 'email', 'cep', 'bairro', 'endereco', 'numero', 'cidade', 'uf']:
        df_final[campo] = dados.get(campo, '')

    # Remover duplicados por CPF, mantendo o mais completo
    df_final['cpf_temp'] = df_final['cpf']
    df_final = df_final.groupby('cpf_temp', as_index=False).apply(escolher_mais_completo).reset_index(drop=True)
    df_final.drop(columns='cpf_temp', inplace=True)

    # Garantir que todas as colunas sejam do tipo texto
    for col in df_final.columns:
        df_final[col] = df_final[col].astype(str)

    st.success("✅ Planilha formatada com sucesso!")

    # Gerar arquivo para download
    buffer = BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        label="📥 Baixar Planilha Formatada",
        data=buffer,
        file_name="planilha_formatada_para_importacao.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
