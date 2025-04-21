# 🧪 Sistema de Análises Centesimais

Este é um sistema completo e extensível para análises centesimais de alimentos, desenvolvido em **Python** com a biblioteca **Streamlit**, com suporte a **coleta em triplicata**, cálculos estatísticos, anotações, relatórios e gerenciamento por múltiplos usuários com níveis de acesso distintos.

---

## 📌 Funcionalidades

- ✅ Autenticação com email e senha (criptografia via bcrypt)
- ✅ Cadastro e login de usuários (usuário padrão e administrador)
- ✅ Registro de análises por triplicata com:
  - Média
  - Desvio Padrão
  - Coeficiente de Variação
- ✅ Tipos de análises implementadas:
  - Umidade
  - Cinzas
  - Proteínas (via nitrogênio - Kjeldahl)
  - Lipídios (extração etérea - Soxhlet)
  - Fibras Totais (digestão enzimática)
  - Carboidratos por diferença
- ✅ Geração de relatórios em PDF e Excel
- ✅ Módulo de anotações com edição e exclusão
- ✅ Painel administrativo com filtros, buscas e visão geral
- ✅ Estrutura preparada para novos métodos analíticos

---

## 🗃️ Estrutura do Projeto


## ▶️ Como Executar Localmente

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/sistema-centesimal.git
cd sistema-centesimal

2. Crie e ative o ambiente virtual
bash
Copiar
Editar
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows
3. Instale as dependências
bash
Copiar
Editar
pip install -r requirements.txt
4. Execute a aplicação
bash
Copiar
Editar
streamlit run app.py
🧰 Tecnologias Utilizadas
Python 3.12+

Streamlit

SQLite3

bcrypt

pandas

numpy

statistics

openpyxl

fpdf

📥 Relatórios Gerados
📄 PDF: simples, com dados formatados por amostra e tipo de análise

📊 Excel: ideal para uso em relatórios acadêmicos ou planilhas laboratoriais

🛡️ Acesso por Permissão
Usuário padrão: registra suas próprias análises e anotações

Administrador: tem acesso a todas as análises do sistema, exportações globais, e painel estatístico geral

💡 Futuros Recursos Planejados
🔍 Busca avançada por parâmetros e data

📲 Upload de imagens para análises visuais

🔐 Autenticação com OAuth (Google)

☁️ Integração com banco remoto (PostgreSQL)

📊 Dashboards com gráficos interativos

👨‍🔬 Autor
Warley Alisson Souza
Desenvolvedor | Nutricionista | Mestrando em Ciências de Alimentos - UFMG
📧 warleyalisson@gmail.com

⚖️ Licença
Este projeto é livre para uso acadêmico, pesquisa e desenvolvimento. Sinta-se à vontade para adaptar e expandir conforme a sua necessidade.

Sistema de Análises Centesimais – Pronto para laboratório, pronto para pesquisa.

yaml
Copiar
Editar

---









