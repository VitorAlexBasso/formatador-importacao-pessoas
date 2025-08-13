import streamlit as st
import pandas as pd
import numpy as np
import re
import unicodedata
from io import BytesIO

# ========== CONFIGURATION ==========
st.set_page_config(
    page_title="Formatador de Dados Pessoais",
    layout="centered",
    page_icon="📊"
)

# ========== CONSTANTS ==========
COLUMN_MAPPINGS = {
    'razao_social': ['nome e sobrenome', 'nome completo', 'razao social', 'razão social', 'cliente', 'empresa', 'contato', 'responsavel', 'responsável', 'nome'],
    'sobrenome': ['sobrenome', 'ultimo nome', 'último nome', 'sobre nome', 'ultimo sobrenome', 'apelido'],
    'primeiro_nome': ['primeiro nome', 'nome', 'nome do cliente', 'nome pessoa'],
    'fantasia': ['fantasia', 'nome fantasia'],
    'cpf': ['cpf/cnpj', 'cpf', 'cnpj', 'documento'],
    'email': ['email', 'e-mail'],
    'celular': ['celular', 'whatsapp', 'telefone', 'telefone celular'],
    'cep': ['cep', 'codigo postal', 'código postal'],
    'endereco': ['endereco', 'endereço', 'logradouro', 'rua'],
    'numero': ['numero', 'número', 'num'],
    'bairro': ['bairro', 'distrito'],
    'cidade': ['cidade', 'municipio', 'município'],
    'uf': ['uf', 'estado', 'unidade federativa'],
    'observacoes': ['observacoes', 'observações', 'obs', 'observacao', 'observacões']
}

TARGET_COLUMNS = [
    'codigo', 'razao_social', 'fantasia', 'cpf', 'tipo_pessoa',
    'email', 'celular', 'cep', 'endereco', 'numero', 'complemento',
    'bairro', 'cidade', 'uf', 'observacoes'
]

# ========== FUNCTIONS ==========
def strip_accents(s: str) -> str:
    if not isinstance(s, str):
        s = str(s) if s is not None else ""
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def norm_text(s: str) -> str:
    s = strip_accents(s).lower()
    return re.sub(r'\s+', ' ', s).strip()

def clean_str_series(ser: pd.Series) -> pd.Series:
    ser = ser.astype(str).replace({np.nan: ""})
    ser = ser.map(lambda x: "" if norm_text(x) in {"nan", "none", "na", "n/a", ""} else x.strip())
    return ser

def clean_document(doc):
    if pd.isna(doc) or str(doc).strip() == "":
        return "", ""
    doc_clean = re.sub(r"\D", "", str(doc))
    if len(doc_clean) == 11:
        return doc_clean, "F"
    elif len(doc_clean) == 14:
        return doc_clean, "J"
    return doc_clean, ""

def read_uploaded_file(file):
    try:
        if file.name.lower().endswith('.csv'):
            for encoding in ['utf-8', 'latin1', 'iso-8859-1', 'windows-1252']:
                try:
                    return pd.read_csv(file, encoding=encoding, sep=None, engine='python', on_bad_lines='warn')
                except (UnicodeDecodeError, pd.errors.ParserError):
                    file.seek(0)
                    continue
            raise ValueError("Não foi possível determinar a codificação do arquivo CSV")
        else:
            return pd.read_excel(file, dtype=object)
    except Exception as e:
        st.error(f"ERRO NA LEITURA: {str(e)}")
        return None

def map_source_columns(df):
    mapped = {}
    for target_col, possible_names in COLUMN_MAPPINGS.items():
        for src_col in df.columns:
            if any(name.lower() in norm_text(str(src_col)) for name in possible_names):
                mapped[target_col] = clean_str_series(df[src_col])
                break
        else:
            mapped[target_col] = pd.Series([""] * len(df), dtype=str)
    return mapped

def process_data(file):
    if file is None:
        return None
    
    with st.spinner("Lendo arquivo..."):
        df = read_uploaded_file(file)
        if df is None or df.empty:
            st.error("Arquivo vazio ou inválido")
            return None
    
    with st.spinner("Mapeando colunas..."):
        mapped_data = map_source_columns(df)
        
        if 'cpf' not in mapped_data or mapped_data['cpf'].eq("").all():
            st.error("Nenhuma coluna de documento (CPF/CNPJ) encontrada")
            return None
    
    with st.spinner("Processando dados..."):
        try:
            documents = mapped_data['cpf'].apply(clean_document)
            mapped_data['cpf'], mapped_data['tipo_pessoa'] = zip(*documents)
            
            # Monta razao_social
            rs = mapped_data['razao_social']
            sn = mapped_data['sobrenome']
            pn = mapped_data['primeiro_nome']
            
            rs_has_space = rs.str.contains(r"\s", regex=True)
            need_concat = (~rs_has_space) & (rs != "") & (sn != "")
            rs = rs.where(~need_concat, (rs + " " + sn).str.strip())
            
            empty_rs = (rs == "")
            rs = rs.where(~empty_rs, (pn + " " + sn).str.strip())
            rs = rs.map(lambda x: x if x.strip() else "NÃO INFORMADO")
            
            mapped_data['razao_social'] = rs
            
            output_df = pd.DataFrame({
                col: mapped_data.get(col.lower(), [""] * len(df))
                for col in TARGET_COLUMNS
            })
            
            output_df['uf'] = output_df['uf'].astype(str).str.strip().str.upper().str[:2]
            
            output_df = output_df.drop_duplicates(subset=['cpf'], keep='first').reset_index(drop=True)
            
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
    
    uploaded_file = st.file_uploader(
        "Selecione seu arquivo",
        type=["csv", "xlsx", "xls"],
        help="Arquivos CSV devem conter cabeçalhos na primeira linha"
    )
    
    if uploaded_file:
        result = process_data(uploaded_file)
        
        if result is not None:
            st.success(f"✅ Processamento concluído! {len(result)} registros formatados.")
            st.subheader("Pré-visualização dos dados")
            st.dataframe(result.head())
            
            output = BytesIO()
            result.to_excel(output, index=False)
            output.seek(0)
            
            st.download_button(
                label="⬇️ Baixar Planilha Formatada",
                data=output,
                file_name="dados_pessoais_formatados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
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
