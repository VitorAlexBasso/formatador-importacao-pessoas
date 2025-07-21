import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

# ========== CONFIGURATION ==========
st.set_page_config(
    page_title="Formatador de Dados Pessoais",
    layout="centered",
    page_icon="📊"
)

# ========== CONSTANTS ==========
COLUMN_MAPPINGS = {
    'razao_social': ['nome', 'razao social', 'cliente', 'empresa'],
    'fantasia': ['fantasia', 'nome fantasia'],
    'cpf': ['cpf', 'documento', 'cnpj', 'cpf/cnpj'],  # Alterado para priorizar 'cpf'
    'email': ['email', 'e-mail'],
    'celular': ['celular', 'whatsapp', 'telefone', 'telefone celular'],
    'cep': ['cep', 'código postal'],
    'endereco': ['endereco', 'logradouro', 'rua'],
    'numero': ['numero', 'número', 'num'],
    'bairro': ['bairro', 'distrito'],
    'cidade': ['cidade', 'município', 'municipio'],
    'uf': ['uf', 'estado', 'unidade federativa']
}

TARGET_COLUMNS = [
    'codigo', 'razao_social', 'fantasia', 'cpf', 'tipo_pessoa',  # Alterado 'documento' para 'cpf'
    'email', 'celular', 'cep', 'endereco', 'numero', 'complemento',
    'bairro', 'cidade', 'uf', 'observacoes'
]

# ========== FUNCTIONS ==========
def clean_document(doc):
    """Clean and classify document numbers"""
    if pd.isna(doc) or str(doc).strip() == "":
        return "", ""
    
    doc_clean = re.sub(r'\D', '', str(doc))
    if len(doc_clean) == 11:
        return doc_clean, "F"
    elif len(doc_clean) == 14:
        return doc_clean, "J"
    return doc_clean, ""

def read_uploaded_file(file):
    """Handle all file reading scenarios"""
    try:
        if file.name.lower().endswith('.csv'):
            # Try multiple encodings and delimiters
            for encoding in ['utf-8', 'latin1', 'iso-8859-1', 'windows-1252']:
                try:
                    return pd.read_csv(
                        file,
                        encoding=encoding,
                        sep=None,  # Auto-detect delimiter
                        engine='python',
                        on_bad_lines='warn'
                    )
                except (UnicodeDecodeError, pd.errors.ParserError):
                    file.seek(0)
                    continue
            raise ValueError("Não foi possível determinar a codificação do arquivo CSV")
        else:
            return pd.read_excel(file)
    except Exception as e:
        st.error(f"ERRO NA LEITURA: {str(e)}")
        return None

def map_source_columns(df):
    """Intelligently map source columns to target format"""
    mapped = {}
    for target_col, possible_names in COLUMN_MAPPINGS.items():
        # Find first matching column
        for src_col in df.columns:
            if any(name.lower() in str(src_col).lower() for name in possible_names):
                mapped[target_col] = df[src_col].astype(str)
                break
        else:
            mapped[target_col] = pd.Series([""] * len(df), dtype=str)
    return mapped

def process_data(file):
    """Main data processing pipeline"""
    if file is None:
        return None
    
    # Step 1: Read file
    with st.spinner("Lendo arquivo..."):
        df = read_uploaded_file(file)
        if df is None or df.empty:
            st.error("Arquivo vazio ou inválido")
            return None
    
    # Step 2: Map columns
    with st.spinner("Mapeando colunas..."):
        mapped_data = map_source_columns(df)
        
        # Validate required columns
        if not any(doc in mapped_data for doc in ['cpf', 'documento', 'cnpj']):  # Atualizado para incluir 'cpf'
            st.error("Nenhuma coluna de documento (CPF/CNPJ) encontrada")
            return None
    
    # Step 3: Clean and transform
    with st.spinner("Processando dados..."):
        try:
            # Clean document numbers - agora usando 'cpf' como chave
            documents = mapped_data['cpf'].apply(clean_document)
            mapped_data['cpf'], mapped_data['tipo_pessoa'] = zip(*documents)
            
            # Set default values
            mapped_data['razao_social'] = mapped_data.get('razao_social', pd.Series(["NÃO INFORMADO"] * len(df)))
            
            # Create output DataFrame
            output_df = pd.DataFrame({
                col: mapped_data.get(col.lower(), [""] * len(df))
                for col in TARGET_COLUMNS
            })
            
            # Remove duplicates
            output_df = output_df.drop_duplicates(
                subset=['cpf'],  # Alterado para 'cpf'
                keep='first'
            ).reset_index(drop=True)
            
            return output_df
            
        except Exception as e:
            st.error(f"ERRO NO PROCESSAMENTO: {str(e)}")
            return None

# ========== UI COMPONENTS ==========
def main():
    st.title("📊 Formatador de Dados Pessoais")
    st.markdown("""
    **Transforme seus dados em formato padronizado para importação**  
    Suporta arquivos CSV e Excel (XLSX, XLS)
    """)
    
    # File upload
    uploaded_file = st.file_uploader(
        "Selecione seu arquivo",
        type=["csv", "xlsx", "xls"],
        help="Arquivos CSV devem conter cabeçalhos na primeira linha"
    )
    
    # Process data when file is uploaded
    if uploaded_file:
        result = process_data(uploaded_file)
        
        if result is not None:
            st.success(f"✅ Processamento concluído! {len(result)} registros formatados.")
            
            # Preview
            st.subheader("Pré-visualização dos dados")
            st.dataframe(result.head())
            
            # Download
            output = BytesIO()
            result.to_excel(output, index=False)
            output.seek(0)
            
            st.download_button(
                label="⬇️ Baixar Planilha Formatada",
                data=output,
                file_name="dados_pessoais_formatados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # Help section
    with st.expander("ℹ️ Precisa de ajuda?"):
        st.markdown("""
        **Soluções para problemas comuns:**
        
        1. **Erro ao ler arquivo CSV**:
           - Verifique se o arquivo usa vírgulas como separador
           - Campos com quebras de linha devem estar entre aspas
           - Tente salvar como Excel (.xlsx) se persistir
        
        2. **Colunas não reconhecidas**:
           - Certifique-se que seu arquivo contém cabeçalhos
           - Nomes alternativos para CPF/CNPJ: 'documento', 'cpf/cnpj'
        
        3. **Dados faltantes**:
           - Campos não encontrados serão preenchidos com vazio
        """)

if __name__ == "__main__":
    main()
