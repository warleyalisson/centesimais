# app.py
import streamlit as st
import sqlite3
import bcrypt
from datetime import datetime
import pandas as pd
from fpdf import FPDF
import io

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
    nome_amostra TEXT,
    umidade REAL,
    cinzas REAL,
    proteinas REAL,
    lipidios REAL,
    fibras REAL,
    carboidratos REAL,
    vet REAL,
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

# -------------------- TELA DE CADASTRO --------------------
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

# -------------------- TELA DE LOGIN --------------------
def tela_login():
    st.subheader("Login")
    email = st.text_input("Email")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        user = autenticar(email, senha)
        if user:
            st.session_state['user'] = user
        else:
            st.error("Email ou senha incorretos.")

# -------------------- ANÁLISE CENTESIMAL --------------------
def calcular_e_salvar(usuario_id, nome_amostra, valores):
    peso_seco = valores['peso_cadinho_amostra_seca'] - valores['peso_cadinho_seco']
    umidade = ((valores['peso_amostra_umida'] - peso_seco) / valores['peso_amostra_umida']) * 100
    cinzas = ((valores['peso_cadinho_cinzas'] - valores['peso_cadinho_seco']) / valores['peso_amostra_umida']) * 100
    proteinas = valores['nitrogenio'] * 6.25
    lipidios = (valores['peso_extrato_eterio'] / valores['peso_amostra_umida']) * 100
    fibras = (valores['peso_residuo_fibra'] / valores['peso_amostra_umida']) * 100
    carboidratos = 100 - (umidade + cinzas + proteinas + lipidios + fibras)
    vet = proteinas*4 + lipidios*9 + carboidratos*4

    data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO analises (usuario_id, nome_amostra, umidade, cinzas, proteinas, lipidios,
                              fibras, carboidratos, vet, data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (usuario_id, nome_amostra, umidade, cinzas, proteinas, lipidios, fibras, carboidratos, vet, data))
    conn.commit()
    return umidade, cinzas, proteinas, lipidios, fibras, carboidratos, vet

def painel_usuario(usuario):
    st.title(f"Bem-vindo, {usuario['nome']}")
    st.header("Nova Análise Centesimal")

    with st.form("form_analise"):
        nome_amostra = st.text_input("Nome da amostra")
        valores = {
            'peso_amostra_umida': st.number_input("Peso da amostra úmida (g)", step=0.01),
            'peso_cadinho_seco': st.number_input("Peso do cadinho seco (g)", step=0.01),
            'peso_cadinho_amostra_seca': st.number_input("Peso do cadinho + amostra seca (g)", step=0.01),
            'peso_cadinho_cinzas': st.number_input("Peso do cadinho com cinzas (g)", step=0.01),
            'nitrogenio': st.number_input("Nitrogênio determinado (g)", step=0.01),
            'peso_extrato_eterio': st.number_input("Peso do extrato etéreo (g)", step=0.01),
            'peso_residuo_fibra': st.number_input("Peso do resíduo de fibra (g)", step=0.01)
        }
        submitted = st.form_submit_button("Calcular e Salvar")

        if submitted:
            res = calcular_e_salvar(usuario['id'], nome_amostra, valores)
            st.success(f"Análise registrada com sucesso! VET: {res[-1]:.2f} kcal/100g")

    st.header("Minhas análises")
    df = pd.read_sql_query(f"SELECT * FROM analises WHERE usuario_id = {usuario['id']} ORDER BY data DESC", conn)
    st.dataframe(df)

# -------------------- PAINEL ADMINISTRADOR --------------------
def painel_admin():
    st.title("Painel do Administrador")
    st.subheader("Todas as Análises")
    df = pd.read_sql_query('''
        SELECT u.nome as usuario, a.* FROM analises a
        JOIN usuarios u ON a.usuario_id = u.id
        ORDER BY a.data DESC
    ''', conn)

    filtro_usuario = st.selectbox("Filtrar por usuário (opcional)", ["Todos"] + sorted(df['usuario'].unique().tolist()))
    if filtro_usuario != "Todos":
        df = df[df['usuario'] == filtro_usuario]

    st.dataframe(df)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Exportar para Excel"):
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False)
            st.download_button("Download Excel", buffer.getvalue(), file_name="analises.xlsx")

    with col2:
        if st.button("Gerar PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)
            for i, row in df.iterrows():
                for col in df.columns:
                    pdf.cell(190, 10, txt=f"{col}: {row[col]}", ln=1)
                pdf.cell(190, 5, txt="-"*90, ln=1)
            buffer = io.BytesIO()
            pdf.output(buffer)
            st.download_button("Download PDF", buffer.getvalue(), file_name="analises.pdf")

# -------------------- APP STREAMLIT --------------------
st.set_page_config(page_title="Análise Centesimal", layout="centered")

if 'user' not in st.session_state:
    aba = st.sidebar.radio("Acesso", ["Login", "Cadastro"])
    if aba == "Login":
        tela_login()
    else:
        tela_cadastro()
else:
    user = st.session_state['user']
    if user['tipo'] == 'admin':
        painel_admin()
    else:
        painel_usuario(user)
