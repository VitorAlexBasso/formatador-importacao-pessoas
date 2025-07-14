import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

# Configure app
st.set_page_config(
    page_title="Formatador de Dados Pessoais",
    layout="centered",
    page_icon="🧑‍💼"
)

# App title and description
st.title("🧑‍💼 Formatador de Dados para Importação")
st.markdown("""
Transforme planilhas com dados pessoais em formato padronizado para importação.
Suporta CSV e Excel (XLSX, XLS).
""")

# File upload section
uploaded_file = st.file_uploader(
    "Selecione seu arquivo (CSV ou Excel)",
    type=["csv", "xlsx", "xls"],
    help="Arquivos CSV devem usar vírgulas e ter cabeçalhos"
)

# Column mapping configuration
COLUMN_MAPPINGS = {
    'razao_social': ['nome', 'razao social', 'cliente', 'empresa'],
    'fantasia': ['fantasia', 'nome fantasia'],
    'cpf': ['cpf', 'cnpj', 'documento'],
    'email': ['email', 'e-mail'],
    'celular': ['celular', 'whatsapp', 'telefone'],
    'cep': ['cep', 'código postal'],
    'endereco': ['endereco', 'logradouro', 'rua'],
    'numero': ['numero', 'número'],
    'cidade': ['cidade', 'município'],
    'uf': ['uf', 'estado']
}

def clean_document(doc):
    """Clean and validate CPF/CNPJ numbers"""
    if pd.isna(doc) or doc == "":
        return "", ""
    doc = re.sub(r'\D', '', str(doc))
    if len(doc) == 11:
        return doc, "F"
    elif len(doc) == 14:
        return doc, "J"
    return "", ""

def read_data_file(file):
    """Read uploaded file with robust error handling"""
    try:
        if file.name.lower().endswith('.csv'):
            # Try multiple encodings and delimiters
            for encoding in ['utf-8', 'latin1']:
                try:
                    return pd.read_csv(
                        file,
                        encoding=encoding,
                        sep=None,  # Auto-detect delimiter
                        engine='python',
                        on_bad_lines='warn'
                    )
                except UnicodeDecodeError:
                    continue
            raise ValueError("Não foi possível ler o arquivo CSV")
        else:
            return pd.read_excel(file)
    except Exception as e:
        st.error(f"Erro na leitura do arquivo: {str(e)}")
        return None

def map_columns(df):
    """Map source columns to target format"""
    mapped = {}
    for target, sources in COLUMN_MAPPINGS.items():
        for source in sources:
            if source.lower() in [col.lower() for col in df.columns]:
                mapped[target] = df[source].astype(str)
                break
        else:
            mapped[target] = pd.Series([""] * len(df), dtype=str
    return mapped

def process_data(file):
    """Main processing pipeline"""
    if file is None:
        return None
    
    # Read file
    with st.spinner("Lendo arquivo..."):
        df = read_data_file(file)
        if df is None or df.empty:
            st.error("O arquivo está vazio ou não pôde ser lido")
            return None
    
    # Map columns
    with st.spinner("Mapeando colunas..."):
        mapped_data = map_columns(df)
        if 'cpf' not in mapped_data:
            st.error("Nenhuma coluna de CPF/CNPJ encontrada no arquivo")
            return None
    
    # Clean and transform data
    with st.spinner("Processando dados..."):
        try:
            # Document cleaning
            documents = mapped_data['cpf'].apply(clean_document)
            mapped_data['cpf'], mapped_data['tipo'] = zip(*documents)
            
            # Handle missing values
            mapped_data['razao_social'] = mapped_data.get('razao_social', pd.Series(["NÃO INFORMADO"] * len(df)))
            
            # Create output dataframe
            output_cols = [
                'codigo', 'razao_social', 'fantasia', 'cpf', 'tipo',
                'email', 'celular', 'cep', 'endereco', 'numero',
                'bairro', 'cidade', 'uf', 'observacao'
            ]
            output_df = pd.DataFrame({k: mapped_data.get(k, "") for k in output_cols})
            
            # Remove duplicates
            output_df = output_df.drop_duplicates(subset=['cpf'], keep='first')
            return output_df
            
        except Exception as e:
            st.error(f"Erro no processamento: {str(e)}")
            return None

# Main app flow
if uploaded_file:
    result = process_data(uploaded_file)
    
    if result is not None:
        st.success(f"✅ Processamento concluído! {len(result)} registros formatados.")
        
        # Show preview
        st.subheader("Pré-visualização")
        st.dataframe(result.head())
        
        # Download button
        output = BytesIO()
        result.to_excel(output, index=False)
        output.seek(0)
        
        st.download_button(
            label="⬇️ Baixar Planilha Formatada",
            data=output,
            file_name="dados_formatados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Troubleshooting section
with st.expander("⚠️ Problemas com CSV?"):
    st.markdown("""
    **Soluções para erros comuns:**
    
    1. **Certifique-se que seu arquivo tem cabeçalhos**
    2. **Coluna CPF/CNPJ deve existir com um destes nomes:**
       - cpf, cnpj, documento
    3. **Para problemas de formatação:**
       - Salve como Excel (.xlsx) e tente novamente
    """)
