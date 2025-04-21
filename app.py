# ---------------------- BLOCO 1: IMPORTAÇÕES E CONFIGURAÇÕES INICIAIS ----------------------
import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import statistics
from datetime import datetime
import bcrypt
from fpdf import FPDF
from io import BytesIO
from openpyxl import Workbook

# Configurações iniciais da página
st.set_page_config(
    page_title="Sistema de Análises Centesimais",
    layout="wide"
)

# ---------------------- BLOCO 2: CONEXÃO COM BANCO DE DADOS E CRIAÇÃO DAS TABELAS ----------------------
DB_PATH = "banco.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Tabela de usuários
cursor.execute('''
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    senha TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'usuario'
)
''')

# Tabela de análises
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

# Tabela de anotações
cursor.execute('''
CREATE TABLE IF NOT EXISTS anotacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    titulo TEXT,
    texto TEXT,
    data TEXT,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
)
''')

conn.commit()

# ---------------------- BLOCO 3: FUNÇÕES AUXILIARES DE SEGURANÇA (CRIPTOGRAFIA) ----------------------
def criptografar_senha(senha: str) -> bytes:
    """Criptografa uma senha em formato seguro usando bcrypt."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())

def verificar_senha(senha: str, senha_hash: bytes) -> bool:
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash)

# ---------------------- BLOCO 4: INTERFACE DE AUTENTICAÇÃO (LOGIN & CADASTRO DE USUÁRIOS) ----------------------

def cadastrar_usuario():
    st.subheader("📋 Cadastro de Usuário")
    with st.form("form_cadastro"):
        nome = st.text_input("Nome completo", key="cadastro_nome")
        email = st.text_input("Email", key="cadastro_email")
        senha = st.text_input("Senha", type="password", key="cadastro_senha")
        tipo = st.selectbox("Tipo de usuário", ["usuario", "admin"], key="cadastro_tipo")
        cadastrar = st.form_submit_button("Cadastrar")

    if cadastrar:
        senha_hash = criptografar_senha(senha)
        try:
            cursor.execute("INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                           (nome, email, senha_hash, tipo))
            conn.commit()
            st.success("Usuário cadastrado com sucesso!")
        except sqlite3.IntegrityError:
            st.error("Email já cadastrado.")

def login():
    st.subheader("🔐 Login")
    with st.form("form_login"):
        email = st.text_input("Email", key="login_email")
        senha = st.text_input("Senha", type="password", key="login_senha")
        entrar = st.form_submit_button("Entrar")

    if entrar:
        cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
        user = cursor.fetchone()
        if user and verificar_senha(senha, user[3]):
            st.session_state['user'] = {
                'id': user[0],
                'nome': user[1],
                'email': user[2],
                'tipo': user[4]
            }
            st.success("Login realizado com sucesso!")
            st.rerun()
        else:
            st.error("Email ou senha incorretos.")


# ---------------------- BLOCO 5: ROTEAMENTO INICIAL (TELA DE AUTENTICAÇÃO E MENU DO USUÁRIO) ----------------------

def tela_autenticacao():
    if 'user' not in st.session_state:
        aba = st.radio("Você deseja:", ["Entrar", "Cadastrar"], horizontal=True)
        if aba == "Entrar":
            login()
        else:
            cadastrar_usuario()
    else:
        usuario = st.session_state['user']
        st.sidebar.write(f"👤 Logado como: {usuario['nome']} ({usuario['tipo']})")

        if st.sidebar.button("🚪 Sair"):
            del st.session_state['user']
            st.success("Sessão encerrada.")
            st.rerun()

        if usuario['tipo'] == 'admin':
            painel_admin()
        else:
            menu_analises(usuario)

# ---------------------- BLOCO 6: INTERFACE PRINCIPAL DE ANÁLISES ----------------------

def menu_analises(usuario):
    st.sidebar.header("🔬 Menu de Análises")
    opcao = st.sidebar.selectbox("Escolha o tipo de análise:", (
        "Umidade",
        "Cinzas",
        "Proteínas",
        "Lipídios",
        "Fibras Totais",
        "Carboidratos por Diferença",
        "Ver Análises Finalizadas",
        "Minhas Anotações",
        "Relatórios"
    ))

    if opcao == "Umidade":
        analise_umidade(usuario)
    elif opcao == "Cinzas":
        analise_cinzas(usuario)
    elif opcao == "Proteínas":
        analise_proteinas(usuario)
    elif opcao == "Lipídios":
        analise_lipidios(usuario)
    elif opcao == "Fibras Totais":
        analise_fibras(usuario)
    elif opcao == "Carboidratos por Diferença":
        analise_carboidratos(usuario)
    elif opcao == "Ver Análises Finalizadas":
        analises_finalizadas(usuario)
    elif opcao == "Minhas Anotações":
        modulo_anotacoes(usuario)
    elif opcao == "Relatórios":
        modulo_relatorios(usuario)


# ---------------------- BLOCO 8: TELA DE LOGIN E AUTENTICAÇÃO ----------------------

def cadastrar_usuario():
    st.subheader("📋 Cadastro de Novo Usuário")
    nome = st.text_input("Nome completo", key="cadastro_nome")
    email = st.text_input("Email", key="cadastro_email")
    senha = st.text_input("Senha", type="password", key="cadastro_senha")
    tipo = st.selectbox("Tipo de usuário", ["usuario", "admin"], key="cadastro_tipo")

    if st.button("Cadastrar", key="botao_cadastro"):
        if nome and email and senha:
            senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt())
            try:
                cursor.execute("INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)", (nome, email, senha_hash, tipo))
                conn.commit()
                st.success("Usuário cadastrado com sucesso!")
            except sqlite3.IntegrityError:
                st.error("Este e-mail já está cadastrado.")
        else:
            st.warning("Por favor, preencha todos os campos.")

def login():
    st.subheader("🔐 Login")
    email = st.text_input("Email", key="login_email")
    senha = st.text_input("Senha", type="password", key="login_senha")

    if st.button("Entrar", key="botao_login"):
        cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
        user = cursor.fetchone()
        if user and bcrypt.checkpw(senha.encode(), user[3]):
            st.session_state['usuario'] = {
                "id": user[0],
                "nome": user[1],
                "email": user[2],
                "tipo": user[4]
            }
            st.success("Login realizado com sucesso!")
            st.experimental_rerun()
        else:
            st.error("Email ou senha incorretos.")

# ---------------------- BLOCO 9: SISTEMA DE AUTENTICAÇÃO E ROTEAMENTO ----------------------

def tela_autenticacao():
    if 'usuario' not in st.session_state:
        opcao = st.radio("Bem-vindo! Escolha uma opção:", ["Entrar", "Cadastrar"], key="selecao_autenticacao")
        if opcao == "Entrar":
            login()
        elif opcao == "Cadastrar":
            cadastrar_usuario()
    else:
        usuario = st.session_state['usuario']
        st.sidebar.success(f"Logado como: {usuario['nome']} ({usuario['tipo']})")
        if st.sidebar.button("🚪 Sair", key="botao_sair"):
            st.session_state.clear()
            st.experimental_rerun()

        if usuario['tipo'] == "admin":
            menu_admin(usuario)
        else:
            menu_usuario(usuario)

def menu_usuario(usuario):
    st.sidebar.header("📋 Menu do Usuário")
    opcao = st.sidebar.radio("Escolha uma opção:", ["Nova Análise", "Minhas Análises", "Anotações", "Relatórios"], key="menu_usuario")

    if opcao == "Nova Análise":
        menu_analises(usuario)
    elif opcao == "Minhas Análises":
        analises_finalizadas(usuario)
    elif opcao == "Anotações":
        modulo_anotacoes(usuario)
    elif opcao == "Relatórios":
        modulo_relatorios(usuario)

def menu_admin(usuario):
    st.sidebar.header("🛠️ Painel do Administrador")
    opcao = st.sidebar.radio("Escolha uma opção:", ["Painel Geral", "Anotações", "Relatórios"], key="menu_admin")

    if opcao == "Painel Geral":
        painel_admin()
    elif opcao == "Anotações":
        modulo_anotacoes(usuario)
    elif opcao == "Relatórios":
        modulo_relatorios(usuario)
# ---------------------- BLOCO 10: EXECUÇÃO PRINCIPAL DO SISTEMA ----------------------

if __name__ == "__main__":
    st.set_page_config(page_title="Sistema de Análises Centesimais", layout="wide")
    tela_autenticacao()

# ---------------------- BLOCO 11: ANÁLISE DE UMIDADE ----------------------
def analise_umidade(usuario):
    st.subheader("🔬 Nova Análise: Umidade (Estufa - AOAC)")
    nome_amostra = st.text_input("Nome da Amostra", key="umidade_nome")

    st.markdown("### Coleta de dados brutos para triplicata")
    triplicata = []

    for i in range(1, 4):
        st.markdown(f"**🔁 Medida {i}**")
        peso_cadinho_vazio = st.number_input(f"Peso do cadinho vazio (g) [{i}]", key=f"cad_um_{i}", step=0.0001)
        peso_cadinho_amostra = st.number_input(f"Peso do cadinho + amostra antes da estufa (g) [{i}]", key=f"cad_amu_{i}", step=0.0001)
        peso_cadinho_seco = st.number_input(f"Peso do cadinho + amostra seca (g) [{i}]", key=f"cad_sec_{i}", step=0.0001)

        peso_umida = peso_cadinho_amostra - peso_cadinho_vazio
        peso_seca = peso_cadinho_seco - peso_cadinho_vazio
        umidade = ((peso_umida - peso_seca) / peso_umida) * 100 if peso_umida > 0 else 0
        triplicata.append(round(umidade, 2))

        st.markdown(f"🔹 Umidade estimada ({i}): `{round(umidade, 2)} %`")

    if st.button("Calcular Estatísticas e Salvar Umidade"):
        media = round(np.mean(triplicata), 2)
        desvio = round(statistics.stdev(triplicata), 2) if len(set(triplicata)) > 1 else 0.0
        coef_var = round((desvio / media) * 100, 2) if media != 0 else 0.0
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO analises (usuario_id, nome_amostra, parametro, valor1, valor2, valor3, media, desvio_padrao, coef_var, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (usuario['id'], nome_amostra, "Umidade",
              triplicata[0], triplicata[1], triplicata[2],
              media, desvio, coef_var, data))
        conn.commit()

        st.success("Análise de umidade registrada com sucesso!")
        st.metric("Média", f"{media}%")
        st.metric("Desvio Padrão", f"{desvio}%")
        st.metric("Coef. de Variação", f"{coef_var}%")

# ---------------------- BLOCO ANÁLISE: CINZAS (AOAC) ----------------------
def analise_cinzas(usuario):
    st.subheader("🧪 Análise de Cinzas - Método AOAC")

    nome_amostra = st.text_input("Nome da Amostra", key="cinzas_nome_amostra")

    st.markdown("### Coleta de Dados para Triplicata")

    triplicata = []
    for i in range(1, 4):
        st.markdown(f"**🔁 Medida {i}**")
        peso_cadinho = st.number_input(f"Peso do cadinho vazio (g) [{i}]", key=f"cinzas_cadinho_vazio_{i}", step=0.0001, format="%.4f")
        peso_cadinho_amostra = st.number_input(f"Peso do cadinho + amostra seca (g) [{i}]", key=f"cinzas_cadinho_amostra_{i}", step=0.0001, format="%.4f")
        peso_cadinho_cinzas = st.number_input(f"Peso do cadinho + cinzas (g) [{i}]", key=f"cinzas_cadinho_cinza_{i}", step=0.0001, format="%.4f")

        peso_amostra = peso_cadinho_amostra - peso_cadinho
        peso_cinzas = peso_cadinho_cinzas - peso_cadinho

        cinzas = (peso_cinzas / peso_amostra) * 100 if peso_amostra > 0 else 0
        triplicata.append(round(cinzas, 2))

        st.markdown(f"🔹 Cinzas estimadas ({i}): `{round(cinzas, 2)} %`")

    if st.button("Calcular e Salvar Análise de Cinzas", key="btn_salvar_cinzas"):
        media = round(np.mean(triplicata), 2)
        desvio = round(statistics.stdev(triplicata), 2) if len(set(triplicata)) > 1 else 0.0
        coef_var = round((desvio / media) * 100, 2) if media != 0 else 0.0
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO analises (usuario_id, nome_amostra, parametro, valor1, valor2, valor3, media, desvio_padrao, coef_var, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (usuario['id'], nome_amostra, "Cinzas",
              triplicata[0], triplicata[1], triplicata[2],
              media, desvio, coef_var, data))
        conn.commit()

        st.success("✅ Análise de cinzas registrada com sucesso!")
        st.metric("Média", f"{media}%")
        st.metric("Desvio Padrão", f"{desvio}%")
        st.metric("Coef. de Variação", f"{coef_var}%")

# ---------------------- BLOCO ANÁLISE: PROTEÍNAS (KJELDAHL - AOAC) ----------------------
def analise_proteinas(usuario):
    st.subheader("🧪 Análise de Proteínas - Método Kjeldahl")

    nome_amostra = st.text_input("Nome da Amostra", key="proteina_nome_amostra")
    fator_conv = st.number_input("Fator de conversão (ex: 6.25)", value=6.25, step=0.01, key="fator_kjeldahl")

    st.markdown("### Coleta de Dados para Triplicata")

    triplicata = []
    for i in range(1, 4):
        st.markdown(f"**🔁 Medida {i}**")
        volume_HCl = st.number_input(f"Volume de HCl (mL) [{i}]", key=f"prot_hcl_{i}", step=0.01)
        branco = st.number_input(f"Volume de branco (mL) [{i}]", key=f"prot_branco_{i}", step=0.01)
        normalidade = st.number_input(f"Normalidade do HCl (N) [{i}]", key=f"prot_n_{i}", step=0.01)
        peso_amostra = st.number_input(f"Peso da amostra (g) [{i}]", key=f"prot_peso_{i}", step=0.0001)

        if peso_amostra > 0:
            nitrogenio = ((volume_HCl - branco) * normalidade * 14.007) / (peso_amostra * 1000)
            proteinas = nitrogenio * fator_conv
        else:
            proteinas = 0

        triplicata.append(round(proteinas, 2))
        st.markdown(f"🔹 Proteína estimada ({i}): `{round(proteinas, 2)} %`")

    if st.button("Calcular e Salvar Análise de Proteínas", key="btn_salvar_proteinas"):
        media = round(np.mean(triplicata), 2)
        desvio = round(statistics.stdev(triplicata), 2) if len(set(triplicata)) > 1 else 0.0
        coef_var = round((desvio / media) * 100, 2) if media != 0 else 0.0
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO analises (usuario_id, nome_amostra, parametro, valor1, valor2, valor3, media, desvio_padrao, coef_var, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (usuario['id'], nome_amostra, "Proteínas",
              triplicata[0], triplicata[1], triplicata[2],
              media, desvio, coef_var, data))
        conn.commit()

        st.success("✅ Análise de proteínas registrada com sucesso!")
        st.metric("Média", f"{media}%")
        st.metric("Desvio Padrão", f"{desvio}%")
        st.metric("Coef. de Variação", f"{coef_var}%")

# ---------------------- BLOCO ANÁLISE: LIPÍDIOS (EXTRAÇÃO ETÉREA - AOAC) ----------------------
def analise_lipidios(usuario):
    st.subheader("🧪 Análise de Lipídios - Extração Etérea (Soxhlet)")

    nome_amostra = st.text_input("Nome da Amostra", key="lipidios_nome_amostra")
    st.markdown("### Coleta de Dados para Triplicata")

    triplicata = []
    for i in range(1, 4):
        st.markdown(f"**🔁 Medida {i}**")
        peso_frasco_vazio = st.number_input(f"Peso do frasco vazio (g) [{i}]", key=f"lip_frasco_vazio_{i}", step=0.0001)
        peso_frasco_com_lip = st.number_input(f"Peso do frasco com lipídios (g) [{i}]", key=f"lip_frasco_com_lip_{i}", step=0.0001)
        peso_amostra = st.number_input(f"Peso da amostra (g) [{i}]", key=f"lip_peso_amostra_{i}", step=0.0001)

        peso_lipidios = peso_frasco_com_lip - peso_frasco_vazio
        lipidios = (peso_lipidios / peso_amostra) * 100 if peso_amostra > 0 else 0

        triplicata.append(round(lipidios, 2))
        st.markdown(f"🔹 Lipídios estimados ({i}): `{round(lipidios, 2)} %`")

    if st.button("Calcular e Salvar Análise de Lipídios", key="btn_salvar_lipidios"):
        media = round(np.mean(triplicata), 2)
        desvio = round(statistics.stdev(triplicata), 2) if len(set(triplicata)) > 1 else 0.0
        coef_var = round((desvio / media) * 100, 2) if media != 0 else 0.0
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO analises (usuario_id, nome_amostra, parametro, valor1, valor2, valor3, media, desvio_padrao, coef_var, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (usuario['id'], nome_amostra, "Lipídios",
              triplicata[0], triplicata[1], triplicata[2],
              media, desvio, coef_var, data))
        conn.commit()

        st.success("✅ Análise de lipídios registrada com sucesso!")
        st.metric("Média", f"{media}%")
        st.metric("Desvio Padrão", f"{desvio}%")
        st.metric("Coef. de Variação", f"{coef_var}%")

# ---------------------- BLOCO ANÁLISE: FIBRAS TOTAIS (AOAC 985.29) ----------------------
def analise_fibras(usuario):
    st.subheader("🧪 Análise de Fibras Totais - AOAC 985.29 (Digestão Enzimática)")

    nome_amostra = st.text_input("Nome da Amostra", key="fibras_nome_amostra")
    st.markdown("### Coleta de Dados para Triplicata")

    triplicata = []
    for i in range(1, 4):
        st.markdown(f"**🔁 Medida {i}**")
        peso_residuo = st.number_input(f"Peso do resíduo (g) [{i}]", key=f"fibra_residuo_{i}", step=0.0001)
        correcao_proteina = st.number_input(f"Correção de proteína (g) [{i}]", key=f"fibra_proteina_{i}", step=0.0001)
        correcao_cinzas = st.number_input(f"Correção de cinzas (g) [{i}]", key=f"fibra_cinzas_{i}", step=0.0001)
        peso_amostra = st.number_input(f"Peso da amostra (g) [{i}]", key=f"fibra_amostra_{i}", step=0.0001)

        fibra_total = ((peso_residuo - correcao_proteina - correcao_cinzas) / peso_amostra) * 100 if peso_amostra > 0 else 0
        triplicata.append(round(fibra_total, 2))

        st.markdown(f"🔹 Fibras estimadas ({i}): `{round(fibra_total, 2)} %`")

    if st.button("Calcular e Salvar Análise de Fibras", key="btn_salvar_fibras"):
        media = round(np.mean(triplicata), 2)
        desvio = round(statistics.stdev(triplicata), 2) if len(set(triplicata)) > 1 else 0.0
        coef_var = round((desvio / media) * 100, 2) if media != 0 else 0.0
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO analises (usuario_id, nome_amostra, parametro, valor1, valor2, valor3, media, desvio_padrao, coef_var, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (usuario['id'], nome_amostra, "Fibras Totais",
              triplicata[0], triplicata[1], triplicata[2],
              media, desvio, coef_var, data))
        conn.commit()

        st.success("✅ Análise de fibras registrada com sucesso!")
        st.metric("Média", f"{media}%")
        st.metric("Desvio Padrão", f"{desvio}%")
        st.metric("Coef. de Variação", f"{coef_var}%")

# ---------------------- BLOCO ANÁLISE: CARBOIDRATOS POR DIFERENÇA ----------------------
def analise_carboidratos(usuario):
    st.subheader("🧪 Cálculo de Carboidratos por Diferença")

    nome_amostra = st.text_input("Nome da Amostra", key="carb_nome_amostra")
    st.markdown("### Inserção das Médias das Demais Análises")

    umidade = st.number_input("Umidade (%)", step=0.01, key="carb_umidade")
    cinzas = st.number_input("Cinzas (%)", step=0.01, key="carb_cinzas")
    proteinas = st.number_input("Proteínas (%)", step=0.01, key="carb_proteinas")
    lipidios = st.number_input("Lipídios (%)", step=0.01, key="carb_lipidios")
    fibras = st.number_input("Fibras Totais (%)", step=0.01, key="carb_fibras")

    if st.button("Calcular e Salvar Carboidratos", key="btn_salvar_carb"):
        soma = umidade + cinzas + proteinas + lipidios + fibras
        carboidratos = round(100 - soma, 2)
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO analises (usuario_id, nome_amostra, parametro, media, data)
            VALUES (?, ?, ?, ?, ?)
        """, (usuario['id'], nome_amostra, "Carboidratos por Diferença", carboidratos, data))
        conn.commit()

        st.success("✅ Cálculo de carboidratos registrado com sucesso!")
        st.metric("Carboidratos", f"{carboidratos}%")

# ---------------------- BLOCO VISUALIZAÇÃO: ANÁLISES FINALIZADAS ----------------------
def analises_finalizadas(usuario):
    st.subheader("📊 Análises Finalizadas")

    parametros_disponiveis = [
        "Todos", "Umidade", "Cinzas", "Proteínas", 
        "Lipídios", "Fibras Totais", "Carboidratos por Diferença"
    ]
    filtro_param = st.selectbox("Filtrar por parâmetro:", parametros_disponiveis, key="filtro_analise_finalizada")

    query = "SELECT * FROM analises WHERE usuario_id = ?"
    params = [usuario['id']]

    if filtro_param != "Todos":
        query += " AND parametro = ?"
        params.append(filtro_param)

    df = pd.read_sql_query(query, conn, params=params)

    if df.empty:
        st.info("Nenhuma análise encontrada.")
        return

    df_exibicao = df[['id', 'nome_amostra', 'parametro', 'valor1', 'valor2', 'valor3', 'media', 'desvio_padrao', 'coef_var', 'data']].copy()
    df_exibicao = df_exibicao.rename(columns={
        'nome_amostra': 'Amostra',
        'parametro': 'Análise',
        'valor1': 'V1',
        'valor2': 'V2',
        'valor3': 'V3',
        'media': 'Média',
        'desvio_padrao': 'DP',
        'coef_var': 'CV (%)',
        'data': 'Data'
    })

    st.dataframe(df_exibicao, use_container_width=True)

    with st.expander("🧹 Excluir Análise"):
        id_excluir = st.number_input("ID da análise a excluir:", min_value=1, step=1, key="excluir_id")
        if st.button("Excluir", key="btn_excluir"):
            cursor.execute("DELETE FROM analises WHERE id = ? AND usuario_id = ?", (id_excluir, usuario['id']))
            conn.commit()
            st.success("Análise excluída com sucesso!")

    with st.expander("📝 Editar Média da Análise"):
        id_editar = st.number_input("ID da análise a editar:", min_value=1, step=1, key="editar_id")
        novo_valor = st.number_input("Novo valor médio (%):", step=0.01, key="novo_valor_media")
        if st.button("Salvar edição", key="btn_editar_media"):
            cursor.execute("UPDATE analises SET media = ? WHERE id = ? AND usuario_id = ?", (novo_valor, id_editar, usuario['id']))
            conn.commit()
            st.success("Valor médio atualizado com sucesso!")

# ---------------------- BLOCO RELATÓRIOS: EXPORTAÇÃO EM PDF E EXCEL ----------------------
def modulo_relatorios(usuario):
    st.subheader("📄 Relatórios de Análises")
    aba = st.radio("Escolha uma opção:", ["Exportar Todas as Análises", "Exportar por Tipo de Análise"], key="opcao_relatorio")

    if aba == "Exportar Todas as Análises":
        exportar_geral(usuario)
    elif aba == "Exportar por Tipo de Análise":
        exportar_por_parametro(usuario)


def exportar_geral(usuario):
    df = pd.read_sql_query("SELECT * FROM analises WHERE usuario_id = ?", conn, params=(usuario['id'],))
    if df.empty:
        st.info("Nenhuma análise cadastrada.")
        return

    st.download_button(
        label="📥 Baixar Excel",
        data=converter_excel(df),
        file_name="analises_geral.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.download_button(
        label="📥 Baixar PDF",
        data=converter_pdf(df),
        file_name="analises_geral.pdf",
        mime="application/pdf"
    )


def exportar_por_parametro(usuario):
    df = pd.read_sql_query("SELECT DISTINCT parametro FROM analises WHERE usuario_id = ?", conn, params=(usuario['id'],))
    parametros = df['parametro'].tolist()

    if not parametros:
        st.info("Nenhuma análise disponível.")
        return

    escolha = st.selectbox("Selecione o parâmetro:", parametros, key="parametro_exportacao")
    df_filtrado = pd.read_sql_query(
        "SELECT * FROM analises WHERE usuario_id = ? AND parametro = ?",
        conn, params=(usuario['id'], escolha)
    )

    st.download_button(
        label="📥 Baixar Excel",
        data=converter_excel(df_filtrado),
        file_name=f"analise_{escolha}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.download_button(
        label="📥 Baixar PDF",
        data=converter_pdf(df_filtrado),
        file_name=f"analise_{escolha}.pdf",
        mime="application/pdf"
    )


def converter_excel(df):
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Análises')
    return output.getvalue()


def converter_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt="Relatório de Análises", ln=True, align='C')
    pdf.ln(10)
    for index, row in df.iterrows():
        pdf.cell(200, 6, txt=f"{row['nome_amostra']} | {row['parametro']} | Média: {row['media']}%", ln=True)
    return pdf.output(dest='S').encode('latin-1')
# ---------------------- BLOCO ANOTAÇÕES: GERENCIAMENTO DE NOTAS PELO USUÁRIO ----------------------
def modulo_anotacoes(usuario):
    st.subheader("🗒️ Minhas Anotações")

    # Exibir anotações existentes
    anotacoes = pd.read_sql_query(
        "SELECT id, titulo, conteudo, data FROM anotacoes WHERE usuario_id = ? ORDER BY data DESC",
        conn, params=(usuario['id'],)
    )

    # Formulário para nova anotação
    with st.expander("➕ Nova anotação"):
        titulo = st.text_input("Título da anotação", key="nova_titulo")
        conteudo = st.text_area("Conteúdo", key="nova_conteudo")
        if st.button("Salvar anotação", key="btn_salvar_anotacao"):
            data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO anotacoes (usuario_id, titulo, conteudo, data) VALUES (?, ?, ?, ?)",
                (usuario['id'], titulo, conteudo, data)
            )
            conn.commit()
            st.success("Anotação salva com sucesso!")
            st.experimental_rerun()

    # Exibição das anotações existentes
    if not anotacoes.empty:
        for _, row in anotacoes.iterrows():
            with st.expander(f"📝 {row['titulo']} ({row['data']})"):
                st.write(row['conteudo'])

                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✏️ Editar", key=f"edit_btn_{row['id']}"):
                        novo_conteudo = st.text_area("Editar conteúdo", value=row['conteudo'], key=f"edit_txt_{row['id']}")
                        if st.button("Salvar edição", key=f"save_edit_{row['id']}"):
                            cursor.execute(
                                "UPDATE anotacoes SET conteudo = ? WHERE id = ?",
                                (novo_conteudo, row['id'])
                            )
                            conn.commit()
                            st.success("Anotação atualizada com sucesso!")
                            st.experimental_rerun()

                with col2:
                    if st.button("🗑️ Excluir", key=f"del_btn_{row['id']}"):
                        cursor.execute("DELETE FROM anotacoes WHERE id = ?", (row['id'],))
                        conn.commit()
                        st.warning("Anotação excluída!")
                        st.experimental_rerun()
# ---------------------- BLOCO PAINEL ADMINISTRATIVO: VISUALIZAÇÃO E EXPORTAÇÃO GLOBAL DE ANÁLISES ----------------------
def painel_admin():
    st.title("🔐 Painel do Administrador")
    st.subheader("📊 Visualização Geral de Todas as Análises")

    df = pd.read_sql_query("SELECT * FROM analises ORDER BY data DESC", conn)

    if df.empty:
        st.info("Nenhuma análise registrada no sistema.")
        return

    st.dataframe(df, use_container_width=True)

    # 🔎 Filtro por nome de amostra
    st.subheader("🔍 Buscar por Nome da Amostra")
    busca = st.text_input("Digite parte do nome da amostra", key="busca_admin")
    if busca:
        df_filtrado = df[df['nome_amostra'].str.contains(busca, case=False)]
        st.dataframe(df_filtrado, use_container_width=True)

    # 📥 Exportações
    st.subheader("📁 Exportar Todos os Dados")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Baixar Excel",
            data=converter_excel(df),
            file_name="analises_geral_admin.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with col2:
        st.download_button(
            label="📥 Baixar PDF",
            data=converter_pdf(df),
            file_name="analises_geral_admin.pdf",
            mime="application/pdf"
        )

    # 📈 Estatísticas por tipo de análise
    st.subheader("📊 Resumo Estatístico por Tipo de Análise")
    resumo = df.groupby("parametro")["media"].agg(['count', 'mean', 'std']).reset_index()
    resumo.columns = ["Análise", "Total", "Média Geral", "Desvio Padrão"]
    st.dataframe(resumo, use_container_width=True)







