# --------------------- BLOCO 1: Setup e Autenticação ---------------------
import streamlit as st
import sqlite3
import bcrypt
import pandas as pd
import io
from fpdf import FPDF
from datetime import datetime

# --------------------- BANCO DE DADOS ---------------------
conn = sqlite3.connect("banco.db", check_same_thread=False)
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
    parametro TEXT,
    valor1 REAL,
    valor2 REAL,
    valor3 REAL,
    media REAL,
    desvio_padrao REAL,
    coef_var REAL,
    data TEXT,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS anotacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    titulo TEXT,
    conteudo TEXT,
    data TEXT,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
)
''')

conn.commit()

# --------------------- FUNÇÕES DE LOGIN ---------------------

def hash_senha(senha):
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())

def verificar_senha(senha, senha_hash):
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash)

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

# --------------------- TELAS DE LOGIN E CADASTRO ---------------------

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
            st.success("Cadastro realizado. Faça login.")
        else:
            st.error("Email já cadastrado.")
# --------------------- BLOCO 2: Menu Inicial e Navegação ---------------------

st.set_page_config("Análise Centesimal", layout="centered")

# --------------------- MENU PRINCIPAL COM BOTÕES ---------------------

def menu_inicial():
    st.title("Análises centesimais")
    try:
        st.image("logo.png", use_container_width=True)  # imagem local no repositório
    except:
        st.warning("⚠️ Logo não encontrada.")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔬 Análises"):
            st.session_state['pagina'] = 'analises'
    with col2:
        if st.button("📝 Anotações"):
            st.session_state['pagina'] = 'anotacoes'
    with col3:
        if st.button("📄 Relatórios"):
            st.session_state['pagina'] = 'relatorios'

# --------------------- CONTROLE DE FLUXO E SESSÃO ---------------------

def menu_principal():
    user = st.session_state['user']
    menu_inicial()

    st.sidebar.markdown(f"👤 **Usuário:** {user['nome']}")
    if st.sidebar.button("🚪 Logout"):
        del st.session_state['user']
        if 'pagina' in st.session_state:
            del st.session_state['pagina']
        st.rerun()

# --------------------- EXECUÇÃO PRINCIPAL ---------------------

if 'user' not in st.session_state:
    menu = st.sidebar.radio("Acesso", ["Login", "Cadastro"])
    if menu == "Login":
        tela_login()
    else:
        tela_cadastro()
else:
    menu_principal()

# --------------------- BLOCO 3: Módulo de Análises - Umidade (Triplicata) ---------------------

def nova_analise_umidade(usuario):
    st.header("🔬 Coleta de Dados — Umidade (triplicata)")
    st.markdown("Método AOAC 925.10 — Secagem em estufa a 105 °C até peso constante.")

    nome_amostra = st.text_input("Nome da Amostra")
    coleta_completa = True
    dados = []

    for i in range(1, 4):
        st.subheader(f"🧪 Repetição {i}")
        col1, col2, col3 = st.columns(3)
        with col1:
            cadinho = st.number_input(f"Peso do cadinho (g) - R{i}", key=f"cad{i}", step=0.001)
        with col2:
            com_amostra = st.number_input(f"Cadinho + amostra úmida (g) - R{i}", key=f"umida{i}", step=0.001)
        with col3:
            apos_secagem = st.number_input(f"Peso após secagem (g) - R{i}", key=f"seca{i}", step=0.001)

        if cadinho and com_amostra and apos_secagem:
            peso_umida = com_amostra - cadinho
            peso_seca = apos_secagem - cadinho
            umidade = round((peso_umida - peso_seca) / peso_umida * 100, 2) if peso_umida else 0
            dados.append(umidade)

        else:
            coleta_completa = False

    if coleta_completa and nome_amostra and len(dados) == 3:
        media = round(sum(dados) / 3, 2)
        desvio = round(pd.Series(dados).std(ddof=1), 2)
        cv = round((desvio / media) * 100 if media else 0, 2)
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 🔒 Salvamento automático
        cursor.execute("""
            INSERT INTO analises (
                usuario_id, nome_amostra, parametro, valor1, valor2, valor3,
                media, desvio_padrao, coef_var, data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            usuario['id'], nome_amostra, "Umidade",
            dados[0], dados[1], dados[2],
            media, desvio, cv, data
        ))
        conn.commit()

        st.success("✔️ Coleta concluída e salva com sucesso!")
        st.subheader("📈 Resultados")
        st.write(f"Valores individuais: {dados}")
        st.write(f"Média: **{media}%**, DP: **{desvio}**, CV: **{cv}%**")
    else:
        st.info("Preencha todos os campos de todas as repetições para concluir.")
        # --------------------- CINZAS (AOAC 923.03) ---------------------
def nova_analise_cinzas(usuario):
    st.header("🔬 Coleta de Dados — Cinzas (triplicata)")
    st.markdown("Método AOAC 923.03 — Incineração em mufla a 550 °C.")

    nome_amostra = st.text_input("Nome da Amostra", key="cinzas_nome")
    coleta_completa = True
    resultados = []

    for i in range(1, 4):
        st.subheader(f"🧪 Repetição {i}")
        cadinho = st.number_input(f"Peso do cadinho vazio (g) - R{i}", key=f"cinz_cad{i}", step=0.001)
        com_amostra = st.number_input(f"Peso com amostra úmida (g) - R{i}", key=f"cinz_amost{i}", step=0.001)
        com_cinzas = st.number_input(f"Peso após incineração (g) - R{i}", key=f"cinz_final{i}", step=0.001)

        if cadinho and com_amostra and com_cinzas:
            peso_amostra = com_amostra - cadinho
            peso_cinzas = com_cinzas - cadinho
            teor = round((peso_cinzas / peso_amostra) * 100, 2) if peso_amostra else 0
            resultados.append(teor)
        else:
            coleta_completa = False

    if coleta_completa and nome_amostra and len(resultados) == 3:
        salvar_analise(usuario, nome_amostra, "Cinzas", resultados)

# --------------------- PROTEÍNAS (AOAC 920.87) ---------------------
def nova_analise_proteinas(usuario):
    st.header("🔬 Coleta de Dados — Proteínas (triplicata)")
    st.markdown("Método AOAC 920.87 — Determinação de nitrogênio (Kjeldahl), fator 6.25")

    nome_amostra = st.text_input("Nome da Amostra", key="prot_nome")
    resultados = []
    coleta_completa = True

    for i in range(1, 4):
        teor_n = st.number_input(f"Teor de nitrogênio (%) - R{i}", key=f"prot_n{i}", step=0.01)
        if teor_n:
            prot = round(teor_n * 6.25, 2)
            resultados.append(prot)
        else:
            coleta_completa = False

    if coleta_completa and nome_amostra and len(resultados) == 3:
        salvar_analise(usuario, nome_amostra, "Proteínas", resultados)

# --------------------- LIPÍDIOS (AOAC 920.39) ---------------------
def nova_analise_lipidios(usuario):
    st.header("🔬 Coleta de Dados — Lipídios (triplicata)")
    st.markdown("Método AOAC 920.39 — Extração com solvente e evaporação da fração etérea.")

    nome_amostra = st.text_input("Nome da Amostra", key="lip_nome")
    coleta_completa = True
    resultados = []

    for i in range(1, 4):
        amostra = st.number_input(f"Peso da amostra (g) - R{i}", key=f"lip_amo{i}", step=0.001)
        frasco = st.number_input(f"Peso do frasco vazio (g) - R{i}", key=f"lip_fras{i}", step=0.001)
        com_res = st.number_input(f"Frasco + extrato (g) - R{i}", key=f"lip_final{i}", step=0.001)

        if amostra and frasco and com_res:
            extrato = com_res - frasco
            lip = round((extrato / amostra) * 100, 2)
            resultados.append(lip)
        else:
            coleta_completa = False

    if coleta_completa and nome_amostra and len(resultados) == 3:
        salvar_analise(usuario, nome_amostra, "Lipídios", resultados)

# --------------------- FIBRAS (AOAC 985.29) ---------------------
def nova_analise_fibras(usuario):
    st.header("🔬 Coleta de Dados — Fibras (triplicata)")
    st.markdown("Método AOAC 985.29 — Digestão enzimática + resíduo seco.")

    nome_amostra = st.text_input("Nome da Amostra", key="fib_nome")
    coleta_completa = True
    resultados = []

    for i in range(1, 4):
        peso_amostra = st.number_input(f"Peso da amostra (g) - R{i}", key=f"fib_am{i}", step=0.001)
        cadinho = st.number_input(f"Peso do cadinho vazio (g) - R{i}", key=f"fib_cad{i}", step=0.001)
        peso_final = st.number_input(f"Peso final com resíduo (g) - R{i}", key=f"fib_final{i}", step=0.001)

        if peso_amostra and cadinho and peso_final:
            res = peso_final - cadinho
            fibra = round((res / peso_amostra) * 100, 2)
            resultados.append(fibra)
        else:
            coleta_completa = False

    if coleta_completa and nome_amostra and len(resultados) == 3:
        salvar_analise(usuario, nome_amostra, "Fibras", resultados)

# --------------------- SALVAMENTO PADRÃO PARA TODAS AS ANÁLISES ---------------------
def salvar_analise(usuario, nome_amostra, parametro, valores):
    media = round(sum(valores) / 3, 2)
    desvio = round(pd.Series(valores).std(ddof=1), 2)
    cv = round((desvio / media) * 100 if media else 0, 2)
    data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO analises (
            usuario_id, nome_amostra, parametro,
            valor1, valor2, valor3,
            media, desvio_padrao, coef_var, data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        usuario['id'], nome_amostra, parametro,
        valores[0], valores[1], valores[2],
        media, desvio, cv, data
    ))
    conn.commit()
    st.success(f"✔️ {parametro} salva com sucesso! Média: {media}% | CV: {cv}%")
    # --------------------- BLOCO 5: Painel por Amostra + Cálculo Carboidratos/VET ---------------------

def calcular_carboidratos(amostra, usuario_id):
    # Recupera os parâmetros de uma amostra
    cursor.execute("""
        SELECT parametro, media FROM analises
        WHERE usuario_id = ? AND nome_amostra = ?
    """, (usuario_id, amostra))
    linhas = cursor.fetchall()
    dados = {param: valor for param, valor in linhas}

    obrigatorios = ["Umidade", "Cinzas", "Proteínas", "Lipídios", "Fibras"]

    if all(p in dados for p in obrigatorios):
        soma = sum(dados[p] for p in obrigatorios)
        carbo = round(100 - soma, 2)

        # Evita duplicidade
        cursor.execute("""
            SELECT 1 FROM analises
            WHERE usuario_id = ? AND nome_amostra = ? AND parametro = 'Carboidratos'
        """, (usuario_id, amostra))
        if cursor.fetchone() is None:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO analises (
                    usuario_id, nome_amostra, parametro,
                    valor1, valor2, valor3,
                    media, desvio_padrao, coef_var, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                usuario_id, amostra, "Carboidratos",
                carbo, carbo, carbo, carbo, 0.00, 0.00, now
            ))
            conn.commit()
        return carbo
    return None

def painel_amostras(usuario):
    st.header("📋 Painel de Análises por Amostra")

    cursor.execute("""
        SELECT DISTINCT nome_amostra FROM analises
        WHERE usuario_id = ?
        ORDER BY nome_amostra
    """, (usuario['id'],))
    amostras = [linha[0] for linha in cursor.fetchall()]

    if not amostras:
        st.info("Nenhuma amostra registrada.")
        return

    for amostra in amostras:
        st.subheader(f"🧪 {amostra}")
        calcular_carboidratos(amostra, usuario['id'])  # tenta calcular carboidratos

        cursor.execute("""
            SELECT parametro, media FROM analises
            WHERE usuario_id = ? AND nome_amostra = ?
        """, (usuario['id'], amostra))
        registros = cursor.fetchall()
        dados = {param: round(media, 2) for param, media in registros}

        df = pd.DataFrame(dados.items(), columns=["Parâmetro", "Média (%)"])
        st.dataframe(df, use_container_width=True)

        if all(p in dados for p in ["Proteínas", "Lipídios", "Carboidratos"]):
            vet = round(dados["Proteínas"] * 4 + dados["Carboidratos"] * 4 + dados["Lipídios"] * 9, 2)
            st.success(f"🔥 VET: **{vet} kcal/100g**")
        else:
            st.warning("VET não pode ser calculado (faltam parâmetros).")
# --------------------- BLOCO 6: Exportação Geral e por Parâmetro ---------------------

def exportar_geral(usuario):
    st.subheader("📤 Exportar Todas as Análises")
    df = pd.read_sql_query(
        "SELECT * FROM analises WHERE usuario_id = ? ORDER BY data DESC",
        conn, params=(usuario['id'],)
    )

    if df.empty:
        st.info("Nenhuma análise registrada.")
        return

    st.dataframe(df)

    col1, col2 = st.columns(2)

    with col1:
        buffer_xlsx = io.BytesIO()
        df.to_excel(buffer_xlsx, index=False, sheet_name='Analises')
        st.download_button(
            label="📥 Baixar Excel",
            data=buffer_xlsx.getvalue(),
            file_name="analises_completas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col2:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        for _, row in df.iterrows():
            pdf.cell(190, 10, txt=f"{row['nome_amostra']} - {row['parametro']} ({row['data']})", ln=True)
            pdf.cell(190, 10, txt=f"R1: {row['valor1']}  R2: {row['valor2']}  R3: {row['valor3']} | Média: {row['media']}% | CV: {row['coef_var']}%", ln=True)
            pdf.ln(4)
        buffer_pdf = io.BytesIO()
        pdf.output(buffer_pdf)
        st.download_button(
            label="📄 Baixar PDF",
            data=buffer_pdf.getvalue(),
            file_name="relatorio_analises.pdf",
            mime="application/pdf"
        )

def exportar_por_parametro(usuario):
    st.subheader("📤 Exportar por Tipo de Análise")

    df = pd.read_sql_query(
        "SELECT * FROM analises WHERE usuario_id = ? ORDER BY nome_amostra, parametro, data DESC",
        conn, params=(usuario['id'],)
    )

    if df.empty:
        st.info("Nenhuma análise encontrada para exportar.")
        return

    parametros = sorted(df['parametro'].unique())
    parametro = st.selectbox("Escolha o tipo de análise:", parametros)

    df_filtrado = df[df['parametro'] == parametro]

    st.markdown(f"**{len(df_filtrado)} registros encontrados para '{parametro}'**")
    st.dataframe(df_filtrado)

    col1, col2 = st.columns(2)

    with col1:
        buffer_xlsx = io.BytesIO()
        df_filtrado.to_excel(buffer_xlsx, index=False, sheet_name=parametro)
        st.download_button(
            label="📥 Baixar Excel",
            data=buffer_xlsx.getvalue(),
            file_name=f"{parametro}_analises.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col2:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        for _, row in df_filtrado.iterrows():
            pdf.cell(190, 10, txt=f"{row['nome_amostra']} ({row['data']}) - {parametro}", ln=True)
            pdf.cell(190, 10, txt=f"Valores: {row['valor1']}, {row['valor2']}, {row['valor3']} | Média: {row['media']} | CV: {row['coef_var']}%", ln=True)
            pdf.ln(4)
        buffer_pdf = io.BytesIO()
        pdf.output(buffer_pdf)
        st.download_button(
            label="📄 Baixar PDF",
            data=buffer_pdf.getvalue(),
            file_name=f"{parametro}_analises.pdf",
            mime="application/pdf"
        )

# --------------------- BLOCO FINAL: Módulo de Relatórios (integração no menu) ---------------------

def modulo_relatorios(usuario):
    st.title("📄 Módulo de Relatórios")
    aba = st.radio("Escolha a opção:", [
        "Exportar Todas as Análises",
        "Exportar por Tipo de Análise"
    ])
    if aba == "Exportar Todas as Análises":
        exportar_geral(usuario)
    elif aba == "Exportar por Tipo de Análise":
        exportar_por_parametro(usuario)

# Chamada do módulo no menu principal:
if 'pagina' in st.session_state and st.session_state['pagina'] == 'relatorios':
    modulo_relatorios(st.session_state['user'])
