# app.py - Sistema Completo de Análise Centesimal com Login, Cálculo, Estatísticas e Exportação

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
    umidade REAL,
    cinzas REAL,
    proteinas REAL,
    lipidios REAL,
    fibras REAL,
    carboidratos REAL,
    vet REAL,
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

# -------------------- NOVA ANÁLISE --------------------
def nova_analise(usuario):
    st.subheader("Nova Análise Centesimal")
    nome_amostra = st.text_input("Nome da Amostra")

    col1, col2 = st.columns(2)
    with col1:
        peso_umido = st.number_input("Peso da Amostra Úmida (g)", step=0.01)
        peso_seco = st.number_input("Peso Após Secagem (g)", step=0.01)
        peso_cinzas = st.number_input("Peso das Cinzas (g)", step=0.01)
    with col2:
        nitrogenio = st.number_input("Nitrogênio Determinado (g)", step=0.01)
        extrato_eterio = st.number_input("Peso do Extrato Etéreo (g)", step=0.01)
        peso_fibra = st.number_input("Peso do Resíduo de Fibra (g)", step=0.01)

    if st.button("Calcular e Salvar Análise"):
        umidade = ((peso_umido - peso_seco) / peso_umido) * 100
        cinzas = (peso_cinzas / peso_umido) * 100
        proteinas = nitrogenio * 6.25
        lipidios = (extrato_eterio / peso_umido) * 100
        fibras = (peso_fibra / peso_umido) * 100
        carboidratos = 100 - (umidade + cinzas + proteinas + lipidios + fibras)
        vet = proteinas * 4 + lipidios * 9 + carboidratos * 4

        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO analises (
                usuario_id, nome_amostra, umidade, cinzas, proteinas,
                lipidios, fibras, carboidratos, vet, data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (usuario['id'], nome_amostra, umidade, cinzas, proteinas,
              lipidios, fibras, carboidratos, vet, data))
        conn.commit()
        st.success(f"Análise salva com sucesso! VET: {vet:.2f} kcal/100g")

# -------------------- VISUALIZAÇÃO E EDIÇÃO --------------------
def minhas_analises(usuario):
    st.subheader("Minhas Análises Cadastradas")
    df = pd.read_sql_query(
        f"SELECT * FROM analises WHERE usuario_id = {usuario['id']} ORDER BY data DESC",
        conn
    )

    if df.empty:
        st.info("Nenhuma análise registrada.")
        return

    st.dataframe(df)

    for _, row in df.iterrows():
        with st.expander(f"{row['nome_amostra']} - {row['data']}"):
            novo_nome = st.text_input("Nome da Amostra", value=row['nome_amostra'], key=f"nome{row['id']}")
            novo_umidade = st.number_input("Umidade (%)", value=row['umidade'], key=f"um{row['id']}")
            novo_cinzas = st.number_input("Cinzas (%)", value=row['cinzas'], key=f"cin{row['id']}")
            novo_proteinas = st.number_input("Proteínas (%)", value=row['proteinas'], key=f"prot{row['id']}")
            novo_lipidios = st.number_input("Lipídios (%)", value=row['lipidios'], key=f"lip{row['id']}")
            novo_fibras = st.number_input("Fibras (%)", value=row['fibras'], key=f"fib{row['id']}")
            novo_carboidratos = 100 - (novo_umidade + novo_cinzas + novo_proteinas + novo_lipidios + novo_fibras)
            novo_vet = novo_proteinas * 4 + novo_lipidios * 9 + novo_carboidratos * 4

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Salvar Alterações", key=f"save{row['id']}"):
                    cursor.execute("""
                        UPDATE analises
                        SET nome_amostra=?, umidade=?, cinzas=?, proteinas=?, lipidios=?, fibras=?, carboidratos=?, vet=?
                        WHERE id=?
                    """, (
                        novo_nome, novo_umidade, novo_cinzas, novo_proteinas,
                        novo_lipidios, novo_fibras, novo_carboidratos, novo_vet, row['id']
                    ))
                    conn.commit()
                    st.success("Alterações salvas com sucesso!")
                    st.experimental_rerun()
            with col2:
                if st.button("Excluir Análise", key=f"del{row['id']}"):
                    cursor.execute("DELETE FROM analises WHERE id=?", (row['id'],))
                    conn.commit()
                    st.warning("Análise excluída!")
                    st.experimental_rerun()

# -------------------- ESTATÍSTICA --------------------
def validacao_estatistica(usuario):
    st.subheader("Validação Estatística dos Meus Resultados")
    df = pd.read_sql_query(f"SELECT * FROM analises WHERE usuario_id = {usuario['id']}", conn)
    if df.empty:
        st.info("Nenhuma análise disponível para análise estatística.")
        return
    st.markdown("### Estatísticas Descritivas")
    colunas = ['umidade', 'cinzas', 'proteinas', 'lipidios', 'fibras', 'carboidratos', 'vet']
    resumo = df[colunas].agg(['mean', 'std', 'min', 'max']).transpose()
    resumo.columns = ['Média', 'Desvio Padrão', 'Mínimo', 'Máximo']
    resumo = resumo.round(2)
    st.dataframe(resumo)

# -------------------- EXPORTAÇÃO --------------------
def exportar_analises(usuario):
    st.subheader("Exportação dos Meus Resultados")
    df = pd.read_sql_query(f"SELECT * FROM analises WHERE usuario_id = {usuario['id']} ORDER BY data DESC", conn)
    if df.empty:
        st.info("Nenhuma análise disponível para exportação.")
        return
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Exportar para Excel")
        buffer_xlsx = io.BytesIO()
        df.to_excel(buffer_xlsx, index=False, sheet_name='Analises')
        st.download_button("📊 Baixar Excel", buffer_xlsx.getvalue(), file_name="analises.xlsx")
    with col2:
        st.markdown("#### Exportar para PDF")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        for _, row in df.iterrows():
            pdf.cell(200, 10, txt=f"{row['nome_amostra']} - {row['data']}", ln=True)
            pdf.cell(200, 10, txt=f"U:{row['umidade']} C:{row['cinzas']} P:{row['proteinas']} L:{row['lipidios']} F:{row['fibras']} CHO:{row['carboidratos']} VET:{row['vet']}", ln=True)
            pdf.ln(3)
        buffer_pdf = io.BytesIO()
        pdf.output(buffer_pdf)
        st.download_button("📄 Baixar PDF", buffer_pdf.getvalue(), file_name="relatorio.pdf")

# -------------------- MENU --------------------
def menu_principal():
    user = st.session_state['user']
    st.sidebar.title(f"Olá, {user['nome']}")
    opcoes = ["Nova Análise", "Minhas Análises", "Validação Estatística", "Exportar Resultados"]
    escolha = st.sidebar.radio("Menu", opcoes)
    if st.sidebar.button("Logout"):
        del st.session_state['user']
        st.rerun()
    if escolha == "Nova Análise":
        nova_analise(user)
    elif escolha == "Minhas Análises":
        minhas_analises(user)
    elif escolha == "Validação Estatística":
        validacao_estatistica(user)
    elif escolha == "Exportar Resultados":
        exportar_analises(user)

# -------------------- EXECUÇÃO --------------------
st.set_page_config("Análise Centesimal", layout="centered")
if 'user' not in st.session_state:
    menu = st.sidebar.radio("Acesso", ["Login", "Cadastro"])
    if menu == "Login":
        tela_login()
    else:
        tela_cadastro()
else:
    menu_principal()
