# app.py
import streamlit as st
import sqlite3
import bcrypt
from datetime import datetime
import pandas as pd
from fpdf import FPDF
import io
import altair as alt

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
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS analises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    tipo_analise TEXT,
    nome_amostra TEXT,
    resultado REAL,
    data TEXT,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
)
''')
conn.commit()

# -------------------- FUNÇÕES AUXILIARES --------------------
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

# -------------------- TELA DE CADASTRO E LOGIN --------------------
def tela_cadastro():
    st.subheader("Cadastro de Usuário")
    nome = st.text_input("Nome completo")
    email = st.text_input("Email")
    senha = st.text_input("Senha", type="password")
    if st.button("Cadastrar"):
        if cadastrar_usuario(nome, email, senha):
            st.success("Cadastro realizado com sucesso! Faça login na aba ao lado.")
        else:
            st.error("Email já cadastrado.")

def tela_login():
    st.subheader("Login")
    email = st.text_input("Email")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        user = autenticar(email, senha)
        if user:
            st.session_state['user'] = user
            st.session_state['logged_in'] = True
        else:
            st.error("Email ou senha incorretos.")

# -------------------- ANÁLISES INDIVIDUAIS --------------------
def realizar_analise(usuario_id):
    st.header("Nova Análise")
    tipo = st.selectbox("Escolha a análise", ["Proteínas", "Carboidratos", "Lipídios", "Umidade", "Cinzas", "Fibras"])
    nome_amostra = st.text_input("Nome da amostra")
    resultado = None

    if tipo == "Proteínas":
        n = st.number_input("Nitrogênio (g)", step=0.01)
        if st.button("Calcular Proteínas"):
            resultado = n * 6.25
    elif tipo == "Carboidratos":
        um = st.number_input("Umidade (%)", step=0.01)
        ci = st.number_input("Cinzas (%)", step=0.01)
        pr = st.number_input("Proteínas (%)", step=0.01)
        li = st.number_input("Lipídios (%)", step=0.01)
        fb = st.number_input("Fibras (%)", step=0.01)
        if st.button("Calcular Carboidratos"):
            resultado = 100 - (um + ci + pr + li + fb)
    elif tipo == "Lipídios":
        peso_extrato = st.number_input("Peso do extrato etéreo (g)", step=0.01)
        peso_amostra = st.number_input("Peso da amostra (g)", step=0.01)
        if st.button("Calcular Lipídios"):
            resultado = (peso_extrato / peso_amostra) * 100

    if resultado is not None:
        st.success(f"Resultado: {resultado:.2f} %")
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO analises (usuario_id, tipo_analise, nome_amostra, resultado, data)
            VALUES (?, ?, ?, ?, ?)
        """, (usuario_id, tipo, nome_amostra, resultado, data))
        conn.commit()

# -------------------- VISUALIZAÇÃO, FILTROS E EXPORTAÇÃO --------------------
def minhas_analises(usuario):
    st.subheader("Minhas Análises")
    df = pd.read_sql_query(f"SELECT * FROM analises WHERE usuario_id = {usuario['id']} ORDER BY data DESC", conn)
    if df.empty:
        st.info("Nenhuma análise encontrada.")
        return
    filtro_tipo = st.selectbox("Filtrar por tipo de análise", ["Todos"] + sorted(df['tipo_analise'].unique().tolist()))
    if filtro_tipo != "Todos":
        df = df[df['tipo_analise'] == filtro_tipo]
    st.dataframe(df)
    if not df.empty:
        chart = alt.Chart(df).mark_bar().encode(
            x='nome_amostra',
            y='resultado',
            color='tipo_analise'
        ).properties(width=700)
        st.altair_chart(chart)
        if st.button("Exportar minhas análises em PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            for i, row in df.iterrows():
                for col in df.columns:
                    pdf.cell(200, 10, txt=f"{col}: {row[col]}", ln=True)
                pdf.ln(5)
            buffer = io.BytesIO()
            pdf.output(buffer)
            st.download_button("Download PDF", buffer.getvalue(), file_name="minhas_analises.pdf")

# -------------------- PAINEL ADMINISTRADOR --------------------
def painel_admin():
    st.title("Painel do Administrador")
    df = pd.read_sql_query('''
        SELECT u.nome as usuario, a.* FROM analises a
        JOIN usuarios u ON a.usuario_id = u.id
        ORDER BY a.data DESC
    ''', conn)
    if df.empty:
        st.info("Nenhuma análise cadastrada ainda.")
        return
    usuario_filtro = st.selectbox("Filtrar por usuário", ["Todos"] + sorted(df['usuario'].unique().tolist()))
    tipo_filtro = st.selectbox("Filtrar por tipo de análise", ["Todos"] + sorted(df['tipo_analise'].unique().tolist()))
    if usuario_filtro != "Todos":
        df = df[df['usuario'] == usuario_filtro]
    if tipo_filtro != "Todos":
        df = df[df['tipo_analise'] == tipo_filtro]
    st.dataframe(df)
    if not df.empty:
        chart = alt.Chart(df).mark_bar().encode(
            x='usuario',
            y='resultado',
            color='tipo_analise'
        ).properties(width=700)
        st.altair_chart(chart)
        if st.button("Exportar todas análises em PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            for i, row in df.iterrows():
                for col in df.columns:
                    pdf.cell(200, 10, txt=f"{col}: {row[col]}", ln=True)
                pdf.ln(5)
            buffer = io.BytesIO()
            pdf.output(buffer)
            st.download_button("Download PDF", buffer.getvalue(), file_name="todas_analises.pdf")

# -------------------- APP --------------------
st.set_page_config(page_title="Análise Centesimal", layout="centered")

if 'user' not in st.session_state:
    aba = st.sidebar.radio("Acesso", ["Login", "Cadastro"])
    if aba == "Login":
        tela_login()
    else:
        tela_cadastro()
else:
    user = st.session_state['user']
    st.sidebar.title(f"Olá, {user['nome']}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()
    if user['tipo'] == 'admin':
        painel_admin()
    else:
        menu = st.sidebar.radio("Menu", ["Nova Análise", "Minhas Análises"])
        if menu == "Nova Análise":
            realizar_analise(user['id'])
        elif menu == "Minhas Análises":
            minhas_analises(user)
