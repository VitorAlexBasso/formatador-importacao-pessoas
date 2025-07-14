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
with st.expander("📤 Fazer Upload da Planilha", expanded=True):
    uploaded_file = st.file_uploader(
        "Selecione seu arquivo",
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

# Target output structure
TARGET_COLUMNS = [
    'codigo', 'razao_social', 'fantasia', 'cpf', 'tipo',
    'email', 'celular', 'cep', 'endereco', 'numero',
    'bairro', 'cidade', 'uf', 'observacao'
]

def clean_document(doc):
    """Clean and validate CPF/CNPJ numbers"""
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
            mapped[target] = np.nan
    return mapped

def process_data(uploaded_file):
    """Main processing pipeline"""
    if uploaded_file is None:
        return None
    
    # Read file
    with st.spinner("Lendo arquivo..."):
        df = read_data_file(uploaded_file)
        if df is None:
            return None
    
    # Map columns
    with st.spinner("Mapeando colunas..."):
        mapped_data = map_columns(df)
    
    # Clean and transform data
    with st.spinner("Processando dados..."):
        # Document cleaning
        mapped_data['cpf'], mapped_data['tipo'] = zip(*mapped_data['cpf'].apply(clean_document))
        
        # Handle missing values
        mapped_data['razao_social'] = mapped_data['razao_social'].fillna("NÃO INFORMADO")
        
        # Create output dataframe
        output_df = pd.DataFrame({k: mapped_data.get(k, '') for k in TARGET_COLUMNS})
        
        # Remove duplicates
        output_df = output_df.drop_duplicates(subset=['cpf'], keep='first')
    
    return output_df

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
    
    1. **Erro de formatação**:
       - Verifique se todas as linhas têm o mesmo número de colunas
       - Certifique-se de que campos com vírgulas estão entre aspas (`"`)
    
    2. **Problemas de encoding**:
       - Tente salvar seu CSV como UTF-8 antes de enviar
    
    3. **Dados faltantes**:
       - Colunas não reconhecidas serão preenchidas com vazio
    """)

# Footer
st.markdown("---")
st.caption("Ferramenta desenvolvida para padronização de dados pessoais")
