import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

# Configure page
st.set_page_config(
    page_title="Formatador de Planilhas - Importação de Pessoas", 
    layout="centered",
    page_icon="🧾"
)

# App title and description
st.title("🧾 Formatador de Planilhas para Importação de Pessoas")
st.markdown("""
Faça upload de uma planilha com dados diversos (CPF, Razão Social, Email, etc.) e receba um arquivo formatado para importação.
""")

# File uploader with explicit CSV support
uploaded_file = st.file_uploader(
    "📁 Faça o upload da planilha",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=False,
    help="Formatos suportados: Excel (.xlsx, .xls) ou CSV (.csv)"
)

# Column mapping dictionary
COLUMN_MAPPING = {
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

# Target output columns
TARGET_COLUMNS = [
    'codigo', 'razao_social', 'fantasia', 'cpf', 'rg', 'inscricao_estadual', 'inscricao_municipal',
    'tipo', 'telefone', 'celular', 'email', 'site', 'data_nascimento', 'cep', 'endereco',
    'numero', 'complemento', 'bairro', 'ponto_referencia', 'cidade', 'uf', 'pais', 'brasileiro',
    'passaporte', 'sexo', 'veiculo', 'estado_civil', 'profissao', 'observacao'
]

def identify_column(possible_names, available_columns):
    """Find matching column name from possible variations"""
    for name in possible_names:
        for col in available_columns:
            if name.lower() in str(col).lower():
                return col
    return None

def detect_document_type(doc):
    """Identify if document is CPF (F) or CNPJ (J)"""
    doc = re.sub(r'\D', '', str(doc))
    if len(doc) == 11:
        return "F"
    elif len(doc) == 14:
        return "J"
    return ""

def select_most_complete_row(duplicates):
    """Select the row with most complete data from duplicates"""
    return duplicates.loc[duplicates.count(axis=1).idxmax()]

if uploaded_file is not None:
    try:
        # Read file based on type
        if uploaded_file.name.lower().endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(uploaded_file, encoding='latin1')
        else:
            df = pd.read_excel(uploaded_file)
        
        # Map source columns to target format
        mapped_data = {}
        for target_col, possible_names in COLUMN_MAPPING.items():
            src_col = identify_column(possible_names, df.columns)
            if src_col:
                mapped_data[target_col] = df[src_col].astype(str)
            else:
                mapped_data[target_col] = np.nan
        
        # Clean and standardize document numbers
        mapped_data['cpf'] = mapped_data['cpf'].apply(lambda x: re.sub(r'\D', '', str(x)))
        mapped_data['cpf'] = mapped_data['cpf'].apply(lambda x: x if len(x) in [11, 14] else np.nan)
        mapped_data['cpf'] = mapped_data['cpf'].fillna("")
        mapped_data['tipo'] = mapped_data['cpf'].apply(detect_document_type)
        
        # Handle missing names
        mapped_data['razao_social'] = mapped_data['razao_social'].fillna("NOME NAO INFORMADO")
        
        # Only show fantasy name for companies (PJ) when different from legal name
        mapped_data['fantasia'] = np.where(
            (mapped_data['tipo'] == 'J') & 
            (mapped_data['fantasia'].notna()) & 
            (mapped_data['fantasia'] != mapped_data['razao_social']),
            mapped_data['fantasia'],
            ''
        )
        
        # Create output dataframe
        output_df = pd.DataFrame(columns=TARGET_COLUMNS)
        
        # Populate output with mapped data
        for field in ['razao_social', 'fantasia', 'cpf', 'tipo', 'celular', 
                     'email', 'cep', 'bairro', 'endereco', 'numero', 'cidade', 'uf']:
            output_df[field] = mapped_data.get(field, '')
        
        # Remove duplicates keeping most complete records
        output_df['temp_cpf'] = output_df['cpf']
        output_df = output_df.groupby('temp_cpf', as_index=False).apply(select_most_complete_row).reset_index(drop=True)
        output_df.drop(columns='temp_cpf', inplace=True)
        
        # Convert all columns to string
        output_df = output_df.astype(str)
        
        # Show success message
        st.success(f"✅ Planilha formatada com sucesso! {len(output_df)} registros processados.")
        
        # Create download button
        output_buffer = BytesIO()
        output_df.to_excel(output_buffer, index=False)
        output_buffer.seek(0)
        
        st.download_button(
            label="📥 Baixar Planilha Formatada",
            data=output_buffer,
            file_name="planilha_formatada_importacao.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # Show preview
        st.subheader("Pré-visualização dos dados")
        st.dataframe(output_df.head())
        
    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {str(e)}")
        st.info("Verifique se o arquivo está no formato correto e tente novamente.")
