# ---------------------- BLOCO 1: IMPORTAÇÕES E CONFIGURAÇÕES INICIAIS ----------------------
import streamlit as st
import sqlite3
from datetime import datetime
import bcrypt
import pandas as pd
import numpy as np
import statistics
import os
from fpdf import FPDF
import base64
import io
from openpyxl import Workbook

st.set_page_config(page_title="Sistema de Análises Centesimais", layout="wide")

# ---------------------- BLOCO 2: CONEXÃO COM O BANCO DE DADOS ----------------------
DB_PATH = "banco.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# ---------------------- BLOCO 3: CRIAÇÃO DAS TABELAS ----------------------
cursor.execute('''
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    senha TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'usuario'
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
    texto TEXT,
    data TEXT,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
)
''')

conn.commit()

# ---------------------- BLOCO 4: FUNÇÕES AUXILIARES DE SEGURANÇA ----------------------
def criptografar_senha(senha):
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())

def verificar_senha(senha, senha_hash):
    return bcrypt.checkpw(senha.encode('utf-8'), senha_hash)

# ---------------------- BLOCO 5 + 16: TELA DE LOGIN, CADASTRO E ROTEAMENTO ----------------------

def tela_autenticacao():
    st.title("🔒 Sistema de Análises Centesimais")

    if 'pagina' not in st.session_state:
        st.session_state['pagina'] = 'login'

    if 'user' not in st.session_state:
        modo = st.radio("Você deseja:", ["Login", "Cadastro"], key="auth_modo")

        if modo == "Login":
            with st.form("form_login"):
                email = st.text_input("Email", key="login_email")
                senha = st.text_input("Senha", type="password", key="login_senha")
                submit = st.form_submit_button("Entrar")
                if submit:
                    cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
                    user = cursor.fetchone()
                    if user and verificar_senha(senha, user[3]):
                        st.session_state['user'] = {
                            'id': user[0], 'nome': user[1], 'email': user[2], 'tipo': user[4]
                        }
                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Email ou senha incorretos.")

        elif modo == "Cadastro":
            with st.form("form_cadastro"):
                nome = st.text_input("Nome completo", key="cad_nome")
                email = st.text_input("Email", key="cad_email")
                senha = st.text_input("Senha", type="password", key="cad_senha")
                tipo = st.selectbox("Tipo de usuário", ["usuario", "admin"], key="cad_tipo")
                submit = st.form_submit_button("Cadastrar")
                if submit:
                    if nome and email and senha:
                        senha_hash = criptografar_senha(senha)
                        try:
                            cursor.execute("INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                                           (nome, email, senha_hash, tipo))
                            conn.commit()
                            st.success("Usuário cadastrado com sucesso! Faça login para continuar.")
                            st.session_state['pagina'] = 'login'
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Email já cadastrado.")
                    else:
                        st.warning("Por favor, preencha todos os campos.")
    else:
        # Redirecionamento após login
        carregar_interface()

# ---------------------- BLOCO 6: MENU PRINCIPAL E DIRECIONAMENTO ----------------------
def menu_usuario():
    st.sidebar.title("Menu")
    opcao = st.sidebar.radio("Escolha uma opção:", ["Nova Análise", "Análises Finalizadas", "Anotações", "Relatórios"])
    return opcao

# ---------------------- BLOCO 7: REDIRECIONAMENTO POR TIPO DE USUÁRIO ----------------------
def carregar_interface():
    if 'user' not in st.session_state:
        login()
    else:
        usuario = st.session_state['user']
        st.sidebar.write(f"👤 Logado como: {usuario['nome']} ({usuario['tipo']})")
        if st.sidebar.button("Sair"):
            del st.session_state['user']
            st.experimental_rerun()

        if usuario['tipo'] == 'admin':
            menu = menu_usuario()
            if menu == "Nova Análise":
                nova_analise(usuario, admin=True)
            elif menu == "Análises Finalizadas":
                analises_finalizadas(usuario, admin=True)
            elif menu == "Anotações":
                modulo_anotacoes(usuario)
            elif menu == "Relatórios":
                modulo_relatorios(usuario)
        else:
            menu = menu_usuario()
            if menu == "Nova Análise":
                nova_analise(usuario)
            elif menu == "Análises Finalizadas":
                analises_finalizadas(usuario)
            elif menu == "Anotações":
                modulo_anotacoes(usuario)
            elif menu == "Relatórios":
                modulo_relatorios(usuario)

# ---------------------- BLOCO 8: EXECUÇÃO INICIAL ----------------------
if __name__ == '__main__':
    if 'user' not in st.session_state:
        tela = st.selectbox("Você deseja:", ["Entrar", "Cadastrar"])
        if tela == "Entrar":
            login()
        else:
            cadastrar_usuario()
    else:
        carregar_interface()

# ---------------------- BLOCO 9: NOVA ANÁLISE - UMIDADE (DADOS BRUTOS + CÁLCULO) ----------------------
def nova_analise(usuario, admin=False):
    st.subheader("🧪 Nova Análise: Umidade - Método AOAC")

    nome_amostra = st.text_input("Nome da Amostra")
    st.markdown("### Coleta de dados brutos para triplicata")

    triplicata = []
    for i in range(1, 4):
        st.markdown(f"**🔁 Medida {i}**")
        peso_amostra_umida = st.number_input(f"Peso da amostra úmida (g) [{i}]", key=f"umida_{i}", step=0.0001, format="%0.4f")
        peso_cadinho = st.number_input(f"Peso do cadinho vazio (g) [{i}]", key=f"cadinho_{i}", step=0.0001, format="%0.4f")
        peso_cadinho_amostra_seca = st.number_input(f"Peso do cadinho + amostra seca (g) [{i}]", key=f"seco_{i}", step=0.0001, format="%0.4f")

        if peso_cadinho_amostra_seca > 0:
            peso_seco = peso_cadinho_amostra_seca - peso_cadinho
            umidade = ((peso_amostra_umida - peso_seco) / peso_amostra_umida) * 100
        else:
            umidade = 0

        triplicata.append(round(umidade, 2))
        st.markdown(f"🔹 Umidade estimada ({i}): `{round(umidade, 2)} %`")

    if st.button("Calcular Estatísticas e Salvar"):
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

        st.success(f"Análise de umidade registrada!")
        st.metric("Média", f"{media}%")
        st.metric("Desvio Padrão", f"{desvio}%")
        st.metric("Coef. de Variação", f"{coef_var}%")
# ---------------------- BLOCO 9-B: ANÁLISE DE CINZAS (DADOS BRUTOS + CÁLCULO) ----------------------
def analise_cinzas(usuario):
    st.subheader("🧪 Nova Análise: Cinzas - Método AOAC")

    nome_amostra = st.text_input("Nome da Amostra")
    st.markdown("### Coleta de dados brutos para triplicata")

    triplicata = []
    for i in range(1, 4):
        st.markdown(f"**🔁 Medida {i}**")
        peso_cadinho = st.number_input(f"Peso do cadinho vazio (g) [{i}]", key=f"cadinho_cz_{i}", step=0.0001, format="%0.4f")
        peso_cadinho_amostra = st.number_input(f"Peso do cadinho + amostra seca (g) [{i}]", key=f"cadinho_sec_{i}", step=0.0001, format="%0.4f")
        peso_cadinho_cinzas = st.number_input(f"Peso do cadinho + cinzas (g) [{i}]", key=f"cadinho_cin_{i}", step=0.0001, format="%0.4f")

        peso_amostra = peso_cadinho_amostra - peso_cadinho
        peso_cinzas = peso_cadinho_cinzas - peso_cadinho

        cinzas = (peso_cinzas / peso_amostra) * 100 if peso_amostra > 0 else 0
        triplicata.append(round(cinzas, 2))

        st.markdown(f"🔹 Cinzas estimadas ({i}): `{round(cinzas, 2)} %`")

    if st.button("Calcular Estatísticas e Salvar Cinzas"):
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

        st.success(f"Análise de cinzas registrada com sucesso!")
        st.metric("Média", f"{media}%")
        st.metric("Desvio Padrão", f"{desvio}%")
        st.metric("Coef. de Variação", f"{coef_var}%")
# ---------------------- BLOCO 9-C: ANÁLISE DE PROTEÍNAS (NITROGÊNIO - MÉTODO KJELDAHL AOAC) ----------------------
def analise_proteinas(usuario):
    st.subheader("🧪 Nova Análise: Proteínas (via Nitrogênio - Kjeldahl)")

    nome_amostra = st.text_input("Nome da Amostra")
    fator_conv = st.number_input("Fator de conversão para proteínas (ex: 6.25)", value=6.25)

    st.markdown("### Coleta de dados brutos para triplicata")
    triplicata = []
    for i in range(1, 4):
        st.markdown(f"**🔁 Medida {i}**")
        volume_HCl = st.number_input(f"Volume de HCl gasto na titulação (mL) [{i}]", key=f"hcl_{i}", step=0.01)
        branco = st.number_input(f"Volume de branco (mL) [{i}]", key=f"branco_{i}", step=0.01)
        normalidade = st.number_input(f"Normalidade do HCl (N) [{i}]", key=f"n_{i}", step=0.01)
        peso_amostra = st.number_input(f"Peso da amostra (g) [{i}]", key=f"peso_{i}", step=0.0001)

        nitrogenio = ((volume_HCl - branco) * normalidade * 14.007) / (peso_amostra * 1000) if peso_amostra > 0 else 0
        proteinas = nitrogenio * fator_conv
        triplicata.append(round(proteinas, 2))

        st.markdown(f"🔹 Proteína estimada ({i}): `{round(proteinas, 2)} %`")

    if st.button("Calcular Estatísticas e Salvar Proteínas"):
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

        st.success("Análise de proteínas registrada com sucesso!")
        st.metric("Média", f"{media}%")
        st.metric("Desvio Padrão", f"{desvio}%")
        st.metric("Coef. de Variação", f"{coef_var}%")

# ---------------------- BLOCO 9-D: ANÁLISE DE LIPÍDIOS (EXTRAÇÃO ETÉREA - MÉTODO AOAC) ----------------------
def analise_lipidios(usuario):
    st.subheader("🧪 Nova Análise: Lipídios (Extração Etérea - Soxhlet)")

    nome_amostra = st.text_input("Nome da Amostra")
    st.markdown("### Coleta de dados brutos para triplicata")

    triplicata = []
    for i in range(1, 4):
        st.markdown(f"**🔁 Medida {i}**")
        peso_copo_vazio = st.number_input(f"Peso do copo ou frasco vazio (g) [{i}]", key=f"frasco_vazio_{i}", step=0.0001)
        peso_copo_com_lip = st.number_input(f"Peso do frasco + lipídios extraídos (g) [{i}]", key=f"frasco_lipidios_{i}", step=0.0001)
        peso_amostra = st.number_input(f"Peso da amostra (g) [{i}]", key=f"peso_amostra_{i}", step=0.0001)

        peso_lipidios = peso_copo_com_lip - peso_copo_vazio
        lipidios = (peso_lipidios / peso_amostra) * 100 if peso_amostra > 0 else 0

        triplicata.append(round(lipidios, 2))
        st.markdown(f"🔹 Lipídios estimados ({i}): `{round(lipidios, 2)} %`")

    if st.button("Calcular Estatísticas e Salvar Lipídios"):
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

        st.success("Análise de lipídios registrada com sucesso!")
        st.metric("Média", f"{media}%")
        st.metric("Desvio Padrão", f"{desvio}%")
        st.metric("Coef. de Variação", f"{coef_var}%")

# ---------------------- BLOCO 9-E: ANÁLISE DE FIBRAS ALIMENTARES (MÉTODO AOAC 985.29) ----------------------
def analise_fibras(usuario):
    st.subheader("🧪 Nova Análise: Fibras Totais (Digestão Enzimática - AOAC 985.29)")

    nome_amostra = st.text_input("Nome da Amostra")
    st.markdown("### Coleta de dados brutos para triplicata")

    triplicata = []
    for i in range(1, 4):
        st.markdown(f"**🔁 Medida {i}**")
        peso_residuo = st.number_input(f"Peso do resíduo após digestão e filtração (g) [{i}]", key=f"residuo_{i}", step=0.0001)
        peso_proteina = st.number_input(f"Correção de proteína no resíduo (g) [{i}]", key=f"proteina_corr_{i}", step=0.0001)
        peso_cinza = st.number_input(f"Correção de cinzas no resíduo (g) [{i}]", key=f"cinza_corr_{i}", step=0.0001)
        peso_amostra = st.number_input(f"Peso da amostra (g) [{i}]", key=f"peso_fibra_{i}", step=0.0001)

        fibra_total = ((peso_residuo - peso_proteina - peso_cinza) / peso_amostra) * 100 if peso_amostra > 0 else 0
        triplicata.append(round(fibra_total, 2))

        st.markdown(f"🔹 Fibras totais estimadas ({i}): `{round(fibra_total, 2)} %`")

    if st.button("Calcular Estatísticas e Salvar Fibras"):
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

        st.success("Análise de fibras registrada com sucesso!")
        st.metric("Média", f"{media}%")
        st.metric("Desvio Padrão", f"{desvio}%")
        st.metric("Coef. de Variação", f"{coef_var}%")

# ---------------------- BLOCO 9-F: CÁLCULO DE CARBOIDRATOS POR DIFERENÇA ----------------------
def analise_carboidratos(usuario):
    st.subheader("🧪 Cálculo de Carboidratos por Diferença")

    nome_amostra = st.text_input("Nome da Amostra")
    st.markdown("### Inserção dos valores médios das análises já realizadas")

    umidade = st.number_input("Umidade média (%)", step=0.01)
    cinzas = st.number_input("Cinzas média (%)", step=0.01)
    proteinas = st.number_input("Proteínas média (%)", step=0.01)
    lipidios = st.number_input("Lipídios média (%)", step=0.01)
    fibras = st.number_input("Fibras Totais média (%)", step=0.01)

    if st.button("Calcular Carboidratos e Salvar"):
        soma = umidade + cinzas + proteinas + lipidios + fibras
        carboidratos = round(100 - soma, 2)
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO analises (usuario_id, nome_amostra, parametro, media, data)
            VALUES (?, ?, ?, ?, ?)
        """, (usuario['id'], nome_amostra, "Carboidratos (por diferença)", carboidratos, data))
        conn.commit()

        st.success("Cálculo de carboidratos registrado com sucesso!")
        st.metric("Carboidratos (%)", f"{carboidratos}%")

# ---------------------- BLOCO 10: MENU INTERATIVO (SIDEBAR) COM ACESSO A TODAS AS ANÁLISES ----------------------

def menu_analises(usuario):
    st.sidebar.header("🔬 Menu de Análises")

    opcoes_menu = {
        "Umidade": analise_umidade,
        "Cinzas": analise_cinzas,
        "Proteínas": analise_proteinas,
        "Lipídios": analise_lipidios,
        "Fibras Totais": analise_fibras,
        "Carboidratos por Diferença": analise_carboidratos,
        "Ver Análises Finalizadas": analises_finalizadas
    }

    escolha = st.sidebar.selectbox("Escolha o tipo de análise:", list(opcoes_menu.keys()))

    # Chama a função associada à escolha
    if escolha in opcoes_menu:
        opcoes_menu[escolha](usuario)

# ---------------------- BLOCO 11: VISUALIZAÇÃO DE ANÁLISES FINALIZADAS COM EDIÇÃO E EXCLUSÃO ----------------------

def analises_finalizadas(usuario):
    st.subheader("📊 Análises Finalizadas")

    # Filtro por parâmetro
    filtro_param = st.selectbox(
        "Filtrar por parâmetro",
        ["Todos", "Umidade", "Cinzas", "Proteínas", "Lipídios", "Fibras Totais", "Carboidratos (por diferença)"]
    )

    query = "SELECT * FROM analises WHERE usuario_id = ?"
    params = [usuario['id']]

    if filtro_param != "Todos":
        query += " AND parametro = ?"
        params.append(filtro_param)

    df = pd.read_sql_query(query, conn, params=params)

    if df.empty:
        st.info("Nenhuma análise cadastrada para este filtro.")
        return

    df_exibicao = df[[
        'id', 'nome_amostra', 'parametro', 'valor1', 'valor2', 'valor3',
        'media', 'desvio_padrao', 'coef_var', 'data'
    ]].copy()

    df_exibicao.columns = [
        "ID", "Amostra", "Análise", "V1", "V2", "V3",
        "Média", "DP", "CV (%)", "Data"
    ]

    st.dataframe(df_exibicao, use_container_width=True)

    with st.expander("🧹 Excluir Análise"):
        id_excluir = st.number_input("Digite o ID da análise a excluir", step=1)
        if st.button("Excluir", key="botao_excluir"):
            cursor.execute(
                "DELETE FROM analises WHERE id = ? AND usuario_id = ?",
                (id_excluir, usuario['id'])
            )
            conn.commit()
            st.success("Análise excluída com sucesso!")
            st.experimental_rerun()

    with st.expander("📝 Editar Análise"):
        id_editar = st.number_input("Digite o ID da análise a editar", step=1, key="input_editar_id")
        novo_valor = st.number_input("Novo valor médio (%)", step=0.01)
        if st.button("Salvar Edição", key="botao_editar"):
            cursor.execute(
                "UPDATE analises SET media = ? WHERE id = ? AND usuario_id = ?",
                (novo_valor, id_editar, usuario['id'])
            )
            conn.commit()
            st.success("Valor atualizado com sucesso!")
            st.experimental_rerun()

# ---------------------- BLOCO 12: GERAÇÃO DE RELATÓRIOS (PDF E EXCEL) ----------------------

def modulo_relatorios(usuario):
    st.subheader("📄 Relatórios de Análises")
    opcao = st.radio("Escolha a opção de exportação:", [
        "Exportar Todas as Análises",
        "Exportar por Tipo de Análise"
    ])

    if opcao == "Exportar Todas as Análises":
        exportar_analises_completas(usuario)

    elif opcao == "Exportar por Tipo de Análise":
        exportar_analises_filtradas(usuario)


def exportar_analises_completas(usuario):
    df = pd.read_sql_query(
        "SELECT * FROM analises WHERE usuario_id = ? ORDER BY data DESC",
        conn, params=(usuario['id'],)
    )

    if df.empty:
        st.warning("Nenhuma análise disponível para exportação.")
        return

    st.success(f"{len(df)} análises prontas para exportação.")

    st.download_button(
        label="📥 Baixar Excel",
        data=converter_para_excel(df),
        file_name="relatorio_analises_completo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.download_button(
        label="📥 Baixar PDF",
        data=converter_para_pdf(df),
        file_name="relatorio_analises_completo.pdf",
        mime="application/pdf"
    )


def exportar_analises_filtradas(usuario):
    parametros = pd.read_sql_query(
        "SELECT DISTINCT parametro FROM analises WHERE usuario_id = ?",
        conn, params=(usuario['id'],)
    )['parametro'].tolist()

    if not parametros:
        st.warning("Nenhum parâmetro disponível para filtragem.")
        return

    escolha = st.selectbox("Selecione o parâmetro desejado:", parametros)

    df = pd.read_sql_query(
        "SELECT * FROM analises WHERE usuario_id = ? AND parametro = ? ORDER BY data DESC",
        conn, params=(usuario['id'], escolha)
    )

    if df.empty:
        st.warning("Nenhum dado encontrado para este parâmetro.")
        return

    st.download_button(
        label="📥 Baixar Excel",
        data=converter_para_excel(df),
        file_name=f"relatorio_{escolha.replace(' ', '_').lower()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.download_button(
        label="📥 Baixar PDF",
        data=converter_para_pdf(df),
        file_name=f"relatorio_{escolha.replace(' ', '_').lower()}.pdf",
        mime="application/pdf"
    )


def converter_para_excel(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Análises")
    return buffer.getvalue()


def converter_para_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt="Relatório de Análises", ln=True, align='C')
    pdf.ln(5)

    for index, row in df.iterrows():
        linha = f"{row['data']} | {row['nome_amostra']} | {row['parametro']} | Média: {row['media']}%"
        pdf.cell(200, 8, txt=linha, ln=True)

    return pdf.output(dest='S').encode('latin-1')


# ---------------------- BLOCO 13: MÓDULO DE ANOTAÇÕES (BLOCOS DE TEXTO) ----------------------

def modulo_anotacoes(usuario):
    st.subheader("🗒️ Minhas Anotações")

    # Inserção de nova anotação
    with st.expander("➕ Nova anotação"):
        titulo = st.text_input("Título da Anotação")
        conteudo = st.text_area("Conteúdo da anotação")

        if st.button("Salvar anotação"):
            if titulo.strip() == "" or conteudo.strip() == "":
                st.warning("Preencha todos os campos antes de salvar.")
            else:
                data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO anotacoes (usuario_id, titulo, conteudo, data) VALUES (?, ?, ?, ?)",
                    (usuario['id'], titulo, conteudo, data)
                )
                conn.commit()
                st.success("Anotação salva com sucesso!")
                st.experimental_rerun()

    # Exibição das anotações existentes
    df_anotacoes = pd.read_sql_query(
        "SELECT * FROM anotacoes WHERE usuario_id = ? ORDER BY data DESC",
        conn, params=(usuario['id'],)
    )

    if df_anotacoes.empty:
        st.info("Nenhuma anotação registrada.")
        return

    for _, row in df_anotacoes.iterrows():
        with st.expander(f"📝 {row['titulo']} ({row['data']})"):
            st.markdown(f"📌 {row['conteudo']}")

            col1, col2 = st.columns(2)

            # Botão de edição
            with col1:
                if st.button(f"✏️ Editar", key=f"editar_{row['id']}"):
                    novo_conteudo = st.text_area("Editar anotação", value=row['conteudo'], key=f"editar_area_{row['id']}")
                    if st.button("Salvar edição", key=f"salvar_{row['id']}"):
                        cursor.execute(
                            "UPDATE anotacoes SET conteudo = ? WHERE id = ?",
                            (novo_conteudo, row['id'])
                        )
                        conn.commit()
                        st.success("Anotação atualizada com sucesso!")
                        st.experimental_rerun()

            # Botão de exclusão
            with col2:
                if st.button("🗑️ Excluir", key=f"excluir_{row['id']}"):
                    cursor.execute("DELETE FROM anotacoes WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.warning("Anotação excluída!")
                    st.experimental_rerun()

# ---------------------- BLOCO 14: PAINEL ADMINISTRATIVO ----------------------

def painel_admin():
    st.title("🔐 Painel do Administrador")
    
    st.subheader("📊 Visualização Global das Análises")
    df = pd.read_sql_query("SELECT * FROM analises ORDER BY data DESC", conn)

    if df.empty:
        st.info("Nenhuma análise registrada até o momento.")
        return

    st.dataframe(df, use_container_width=True)

    # ---------------------- EXPORTAÇÃO DE DADOS ----------------------
    st.subheader("📤 Exportação de Dados")
    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="📥 Baixar Excel Geral",
            data=converter_excel(df),
            file_name="relatorio_geral_admin.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col2:
        st.download_button(
            label="📥 Baixar PDF Geral",
            data=converter_pdf(df),
            file_name="relatorio_geral_admin.pdf",
            mime="application/pdf"
        )

    # ---------------------- BUSCA POR AMOSTRA ----------------------
    st.subheader("🔎 Buscar por Nome da Amostra")
    busca = st.text_input("Digite parte do nome da amostra")

    if busca:
        df_filtrado = df[df['nome_amostra'].str.contains(busca, case=False, na=False)]
        if not df_filtrado.empty:
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("Nenhuma amostra encontrada com esse termo.")

    # ---------------------- RESUMO ESTATÍSTICO ----------------------
    st.subheader("📈 Resumo Estatístico por Tipo de Análise")
    resumo = df.groupby("parametro")["media"].agg(['count', 'mean', 'std']).reset_index()
    resumo.columns = ["Análise", "Total de Amostras", "Média Geral (%)", "Desvio Padrão"]

    st.dataframe(resumo, use_container_width=True)


# ---------------------- BLOCO 15: ESTRUTURA PADRÃO PARA NOVAS METODOLOGIAS ----------------------

def nova_metodologia_padrao(nome_parametro, campos, usuario_id):
    st.subheader(f"📐 Nova Metodologia: {nome_parametro}")

    nome_amostra = st.text_input("Nome da Amostra")

    st.markdown("### Coleta de Dados para Triplicata")
    dados_triplicata = []

    for i in range(1, 4):
        st.markdown(f"**🔁 Medida {i}**")
        valores = []
        for campo in campos:
            valor = st.number_input(f"{campo.replace('_', ' ').capitalize()} ({i})", step=0.01, key=f"{campo}_{i}")
            valores.append(valor)
        dados_triplicata.append(np.mean(valores))  # Combina os campos de uma única medida

    if st.button("📊 Calcular Estatísticas e Salvar"):
        try:
            media = round(np.mean(dados_triplicata), 2)
            desvio = round(statistics.stdev(dados_triplicata), 2) if len(set(dados_triplicata)) > 1 else 0.0
            coef_var = round((desvio / media) * 100, 2) if media != 0 else 0.0
            data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                INSERT INTO analises (usuario_id, nome_amostra, parametro, valor1, valor2, valor3, media, desvio_padrao, coef_var, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                usuario_id, nome_amostra, nome_parametro,
                round(dados_triplicata[0], 2),
                round(dados_triplicata[1], 2),
                round(dados_triplicata[2], 2),
                media, desvio, coef_var, data))
            conn.commit()

            st.success("Nova metodologia registrada com sucesso!")
            st.metric("Média", f"{media}%")
            st.metric("Desvio Padrão", f"{desvio}%")
            st.metric("Coef. de Variação", f"{coef_var}%")

        except Exception as e:
            st.error(f"Erro ao registrar a metodologia: {e}")



# ---------------------- BLOCO 17: FINALIZAÇÃO E CONTROLE GERAL ----------------------

def pagina_nao_encontrada():
    st.error("Página não encontrada. Por favor, volte ao menu principal.")
    if st.button("🔙 Voltar ao início"):
        st.session_state['pagina'] = 'login'
        st.experimental_rerun()

# ---------------------- EXECUÇÃO ----------------------
if __name__ == "__main__":
    tela_autenticacao()
    # ---------------------- FIM DO SISTEMA ----------------------
