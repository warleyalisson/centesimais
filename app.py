# app.py
# Versão atualizada com painel lateral, integração entre análises,
# preenchimento automático, edição e exclusão de análises

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

def carregar_ultimo_resultado(usuario_id, tipo):
    cursor.execute("""
        SELECT resultado FROM analises 
        WHERE usuario_id = ? AND tipo_analise = ?
        ORDER BY id DESC LIMIT 1
    """, (usuario_id, tipo))
    res = cursor.fetchone()
    return res[0] if res else None

def deletar_analise(analise_id):
    cursor.execute("DELETE FROM analises WHERE id = ?", (analise_id,))
    conn.commit()

def atualizar_analise(analise_id, novo_resultado):
    cursor.execute("UPDATE analises SET resultado = ? WHERE id = ?", (novo_resultado, analise_id))
    conn.commit()

# -------------------- PÁGINAS PRINCIPAIS --------------------
def nova_analise(usuario):
    st.subheader("Nova Análise")
    tipo = st.selectbox("Tipo de Análise", ["Proteínas", "Carboidratos", "Lipídios"])
    nome = st.text_input("Nome da Amostra")

    valor = None
    if tipo == "Proteínas":
        n = st.number_input("Nitrogênio (g)", step=0.01)
        if st.button("Calcular Proteína"):
            valor = n * 6.25

    elif tipo == "Carboidratos":
        default_pr = carregar_ultimo_resultado(usuario['id'], "Proteínas") or 0.0
        default_li = carregar_ultimo_resultado(usuario['id'], "Lipídios") or 0.0
        pr = st.number_input("Proteínas (%)", value=default_pr, step=0.01)
        li = st.number_input("Lipídios (%)", value=default_li, step=0.01)
        um = st.number_input("Umidade (%)", step=0.01)
        ci = st.number_input("Cinzas (%)", step=0.01)
        fb = st.number_input("Fibras (%)", step=0.01)
        if st.button("Calcular Carboidratos"):
            valor = 100 - (um + ci + pr + li + fb)

    elif tipo == "Lipídios":
        extrato = st.number_input("Peso do extrato etéreo (g)", step=0.01)
        peso = st.number_input("Peso da amostra (g)", step=0.01)
        if st.button("Calcular Lipídios"):
            valor = (extrato / peso) * 100

    if valor is not None:
        st.success(f"Resultado: {valor:.2f}%")
        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO analises (usuario_id, tipo_analise, nome_amostra, resultado, data)
            VALUES (?, ?, ?, ?, ?)
        """, (usuario['id'], tipo, nome, valor, dt))
        conn.commit()
        st.info("Análise salva com sucesso!")


def minhas_analises(usuario):
    st.subheader("Minhas Análises")
    df = pd.read_sql_query(f"SELECT * FROM analises WHERE usuario_id = {usuario['id']} ORDER BY data DESC", conn)
    if df.empty:
        st.info("Nenhuma análise encontrada.")
        return

    st.dataframe(df)

    for _, row in df.iterrows():
        st.markdown(f"### {row['tipo_analise']} - {row['nome_amostra']}")
        col1, col2, col3 = st.columns(3)
        with col1:
            novo = st.number_input(f"Editar resultado ID {row['id']}", value=row['resultado'], step=0.01, key=f"edit_{row['id']}")
            if st.button("Atualizar", key=f"update_{row['id']}"):
                atualizar_analise(row['id'], novo)
                st.success("Atualizado com sucesso!")
                st.experimental_rerun()
        with col2:
            if st.button("Excluir", key=f"delete_{row['id']}"):
                deletar_analise(row['id'])
                st.warning("Análise excluída!")
                st.experimental_rerun()


def painel_admin():
    st.subheader("Painel do Administrador")
    df = pd.read_sql_query('''
        SELECT u.nome AS usuario, a.* FROM analises a
        JOIN usuarios u ON a.usuario_id = u.id
        ORDER BY data DESC
    ''', conn)
    if df.empty:
        st.info("Nenhuma análise disponível.")
        return
    st.dataframe(df)

# -------------------- AUTENTICAÇÃO E INICIALIZAÇÃO --------------------
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
    st.subheader("Cadastro")
    nome = st.text_input("Nome completo")
    email = st.text_input("Email")
    senha = st.text_input("Senha", type="password")
    if st.button("Cadastrar"):
        if cadastrar_usuario(nome, email, senha):
            st.success("Cadastro realizado com sucesso. Faça login.")
        else:
            st.error("Email já cadastrado.")

# -------------------- INTERFACE PRINCIPAL --------------------
st.set_page_config("Análise Centesimal", layout="centered")

if 'user' not in st.session_state:
    menu = st.sidebar.radio("Acesso", ["Login", "Cadastro"])
    if menu == "Login":
        tela_login()
    else:
        tela_cadastro()
else:
    user = st.session_state['user']
    st.sidebar.markdown(f"### Bem-vindo, {user['nome']}")
    opcao = st.sidebar.radio("Menu", ["Nova Análise", "Minhas Análises", "Admin"] if user['tipo'] == 'admin' else ["Nova Análise", "Minhas Análises"])
    if st.sidebar.button("Logout"):
        del st.session_state['user']
        st.rerun()

    if opcao == "Nova Análise":
        nova_analise(user)
    elif opcao == "Minhas Análises":
        minhas_analises(user)
    elif opcao == "Admin" and user['tipo'] == 'admin':
        painel_admin()
