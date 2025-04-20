# app.py - Bloco 1 de N: Banco, Autenticação e Sessão Inicial

import streamlit as st
import sqlite3
import bcrypt
from datetime import datetime
import pandas as pd
import io
from fpdf import FPDF

# -------------------- BANCO DE DADOS --------------------
conn = sqlite3.connect('banco.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    email TEXT UNIQUE,
    senha_hash TEXT,
    tipo TEXT
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS analises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    nome_amostra TEXT,
    parametro TEXT,
    valor1 REAL,
    valor2 REAL,
    valor3 REAL,
    media REAL,
    desvio_padrao REAL,
    coef_var REAL,
    data TEXT,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS anotacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    titulo TEXT,
    conteudo TEXT,
    data TEXT,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
)''')
conn.commit()

# -------------------- AUTENTICAÇÃO --------------------
def hash_senha(senha):
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())

def verificar_senha(senha, senha_hash):
    return bcrypt.checkpw(senha.encode('utf-8'), senha_hash)

def cadastrar_usuario(nome, email, senha, tipo="padrao"):
    try:
        senha_hash = hash_senha(senha)
        cursor.execute("INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES (?, ?, ?, ?)",
                       (nome, email, senha_hash, tipo))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def autenticar(email, senha):
    cursor.execute("SELECT id, nome, senha_hash, tipo FROM usuarios WHERE email = ?", (email,))
    dados = cursor.fetchone()
    if dados and verificar_senha(senha, dados[2]):
        return {'id': dados[0], 'nome': dados[1], 'tipo': dados[3]}
    return None

# -------------------- TELAS DE LOGIN E CADASTRO --------------------
def tela_login():
    st.subheader("Login")
    email = st.text_input("Email")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        user = autenticar(email, senha)
        if user:
            st.session_state['user'] = user
            st.rerun()
        else:
            st.error("Email ou senha incorretos.")

def tela_cadastro():
    st.subheader("Cadastro de Usuário")
    nome = st.text_input("Nome completo")
    email = st.text_input("Email")
    senha = st.text_input("Senha", type="password")
    if st.button("Cadastrar"):
        if cadastrar_usuario(nome, email, senha):
            st.success("Cadastro realizado com sucesso. Faça login.")
        else:
            st.error("Email já cadastrado.")

# -------------------- MENU PRINCIPAL --------------------
def menu_inicial():
    st.title("Análises centesimais")
    st.image("/mnt/data/532de271-3a2a-4ddf-a4cb-2ea3b77fadfc.png", use_column_width=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔬 Análises"):
            st.session_state['pagina'] = 'analises'
    with col2:
        if st.button("📝 Anotações"):
            st.session_state['pagina'] = 'anotacoes'
    with col3:
        if st.button("📊 Relatórios"):
            st.session_state['pagina'] = 'relatorios'

# -------------------- EXECUÇÃO PRINCIPAL --------------------
st.set_page_config("Análise Centesimal", layout="centered")

if 'user' not in st.session_state:
    menu = st.sidebar.radio("Acesso", ["Login", "Cadastro"])
    if menu == "Login":
        tela_login()
    else:
        tela_cadastro()
elif 'pagina' not in st.session_state:
    menu_inicial()
# app.py - Bloco 2 de N: Nova Análise em Triplicata + Visualização de Resultados

# -------------------- NOVA ANÁLISE EM TRIPLICATA --------------------
def nova_analise(usuario):
    st.subheader("Cadastrar Nova Análise")
    nome_amostra = st.text_input("Nome da Amostra")
    parametro = st.selectbox("Parâmetro analisado", ["Umidade", "Cinzas", "Proteínas", "Lipídios", "Fibras"])

    col1, col2, col3 = st.columns(3)
    with col1:
        valor1 = st.number_input("Valor 1 (%)", step=0.01, format="%.2f")
    with col2:
        valor2 = st.number_input("Valor 2 (%)", step=0.01, format="%.2f")
    with col3:
        valor3 = st.number_input("Valor 3 (%)", step=0.01, format="%.2f")

    if st.button("Salvar Análise"):
        valores = [valor1, valor2, valor3]
        media = round(sum(valores) / 3, 2)
        desvio = round(pd.Series(valores).std(ddof=1), 2)
        cv = round((desvio / media) * 100 if media != 0 else 0, 2)

        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO analises (
                usuario_id, nome_amostra, parametro, valor1, valor2, valor3,
                media, desvio_padrao, coef_var, data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            usuario['id'], nome_amostra, parametro,
            valor1, valor2, valor3, media, desvio, cv, data
        ))
        conn.commit()
        st.success(f"Análise de {parametro} registrada com sucesso. Média: {media}%, DP: {desvio}, CV: {cv}%")

# -------------------- VISUALIZAR ANÁLISES FINALIZADAS --------------------
def analises_finalizadas(usuario):
    st.subheader("Análises Finalizadas")
    df = pd.read_sql_query(
        f"SELECT * FROM analises WHERE usuario_id = {usuario['id']} ORDER BY data DESC",
        conn
    )
    if df.empty:
        st.info("Nenhuma análise cadastrada.")
        return

    filtro_param = st.selectbox("Filtrar por parâmetro", ["Todos"] + sorted(df['parametro'].unique()))
    if filtro_param != "Todos":
        df = df[df['parametro'] == filtro_param]

    st.dataframe(df[['nome_amostra', 'parametro', 'valor1', 'valor2', 'valor3', 'media', 'desvio_padrao', 'coef_var', 'data']])

# -------------------- CONTROLE DE FLUXO PARA MÓDULO ANÁLISES --------------------
def modulo_analises(usuario):
    st.title("📊 Módulo de Análises")
    aba = st.radio("Escolha a opção:", ["Nova Análise", "Análises Finalizadas"])
    if aba == "Nova Análise":
        nova_analise(usuario)
    elif aba == "Análises Finalizadas":
        analises_finalizadas(usuario)

# Chamado no menu_principal quando pagina='analises':
if 'pagina' in st.session_state and st.session_state['pagina'] == 'analises':
    modulo_analises(st.session_state['user'])
# app.py - Bloco 3 de N: Módulo de Anotações do Usuário

# -------------------- ANOTAÇÕES --------------------
def nova_anotacao(usuario):
    st.subheader("Criar Nova Anotação")
    titulo = st.text_input("Título da anotação")
    conteudo = st.text_area("Conteúdo da anotação", height=200)

    if st.button("Salvar Anotação"):
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO anotacoes (usuario_id, titulo, conteudo, data)
            VALUES (?, ?, ?, ?)
        """, (usuario['id'], titulo, conteudo, data))
        conn.commit()
        st.success("Anotação salva com sucesso!")


def visualizar_anotacoes(usuario):
    st.subheader("Minhas Anotações")
    df = pd.read_sql_query(
        f"SELECT * FROM anotacoes WHERE usuario_id = {usuario['id']} ORDER BY data DESC",
        conn
    )

    if df.empty:
        st.info("Nenhuma anotação encontrada.")
        return

    for _, row in df.iterrows():
        with st.expander(f"📝 {row['titulo']} — {row['data']}"):
            st.markdown(row['conteudo'])
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("🗑️ Excluir", key=f"del_ano_{row['id']}"):
                    cursor.execute("DELETE FROM anotacoes WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.experimental_rerun()
            with col2:
                novo_conteudo = st.text_area("Editar Conteúdo", value=row['conteudo'], key=f"edit_ano_{row['id']}")
                if st.button("💾 Salvar Edição", key=f"save_ano_{row['id']}"):
                    cursor.execute("UPDATE anotacoes SET conteudo = ? WHERE id = ?", (novo_conteudo, row['id']))
                    conn.commit()
                    st.success("Anotação atualizada com sucesso!")
                    st.experimental_rerun()

# -------------------- CONTROLE DE FLUXO PARA MÓDULO ANOTAÇÕES --------------------
def modulo_anotacoes(usuario):
    st.title("📝 Módulo de Anotações")
    aba = st.radio("Escolha a opção:", ["Criar Nova Anotação", "Visualizar Anotações"])
    if aba == "Criar Nova Anotação":
        nova_anotacao(usuario)
    elif aba == "Visualizar Anotações":
        visualizar_anotacoes(usuario)

# Chamado no menu_principal quando pagina='anotacoes':
if 'pagina' in st.session_state and st.session_state['pagina'] == 'anotacoes':
    modulo_anotacoes(st.session_state['user'])

# app.py - Bloco 4 de N: Módulo de Relatórios (Exportação e Impressão)

# -------------------- EXPORTAÇÃO E RELATÓRIOS --------------------
def exportar_excel_pdf(usuario):
    st.subheader("📊 Exportação de Relatórios")

    df = pd.read_sql_query(
        f"SELECT * FROM analises WHERE usuario_id = {usuario['id']} ORDER BY data DESC",
        conn
    )

    if df.empty:
        st.info("Nenhuma análise disponível para exportação.")
        return

    st.markdown("### Visualização das Análises")
    st.dataframe(df)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Exportar para Excel")
        buffer_xlsx = io.BytesIO()
        df.to_excel(buffer_xlsx, index=False, sheet_name='Analises')
        st.download_button(
            label="📥 Baixar Excel",
            data=buffer_xlsx.getvalue(),
            file_name="analises_triplicata.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col2:
        st.markdown("#### Exportar para PDF")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        for _, row in df.iterrows():
            pdf.cell(190, 10, txt=f"Amostra: {row['nome_amostra']} - {row['parametro']} ({row['data']})", ln=True)
            pdf.cell(190, 10, txt=f"Valores: {row['valor1']}, {row['valor2']}, {row['valor3']} | Média: {row['media']} | DP: {row['desvio_padrao']} | CV: {row['coef_var']}%", ln=True)
            pdf.ln(4)
        buffer_pdf = io.BytesIO()
        pdf.output(buffer_pdf)
        st.download_button(
            label="📄 Baixar PDF",
            data=buffer_pdf.getvalue(),
            file_name="relatorio_triplicata.pdf",
            mime="application/pdf"
        )

# -------------------- MÓDULO DE RELATÓRIOS --------------------
def modulo_relatorios(usuario):
    st.title("📄 Módulo de Relatórios")
    aba = st.radio("Escolha a opção:", ["Exportar e Imprimir Resultados"])
    if aba == "Exportar e Imprimir Resultados":
        exportar_excel_pdf(usuario)

# Chamado no menu_principal quando pagina='relatorios':
if 'pagina' in st.session_state and st.session_state['pagina'] == 'relatorios':
    modulo_relatorios(st.session_state['user'])
