# Sistema Web de Análise Centesimal

Este projeto é um sistema completo de análise centesimal de alimentos, desenvolvido com **Streamlit** e utilizando **login seguro com e-mail e senha criptografada (bcrypt)**. Ele permite que usuários façam login, realizem análises e salvem os dados, enquanto administradores têm acesso a todas as análises do sistema.

---

## 🚀 Funcionalidades

### Usuários Padrão
- Cadastro e login com autenticação segura (bcrypt)
- Registro de novas análises centesimais
- Visualização de análises próprias
- Exportação dos resultados em Excel ou PDF

### Administradores
- Visualização completa de todas as análises
- Filtros por usuário, nome de amostra e data
- Exportação de todas as análises em Excel ou PDF

---

## 🧰 Tecnologias Utilizadas
- [Streamlit](https://streamlit.io/) — Interface web interativa
- [SQLite3](https://www.sqlite.org/index.html) — Banco de dados local
- [bcrypt](https://pypi.org/project/bcrypt/) — Criptografia de senhas
- [Pandas](https://pandas.pydata.org/) — Manipulação de dados
- [FPDF](https://py-pdf.github.io/fpdf2/) — Geração de relatórios em PDF
- [OpenPyXL](https://openpyxl.readthedocs.io/) — Exportação para Excel

---

## 🧪 Instalação Local

1. Clone este repositório:
   ```bash
   git clone https://github.com/seuusuario/analise-centesimal-web.git
   cd analise-centesimal-web
   ```

2. Crie um ambiente virtual (opcional):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate  # Windows
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Execute o app:
   ```bash
   streamlit run app.py
   ```

---

## 🌐 Publicação Online (Streamlit Cloud)

1. Crie uma conta gratuita no [Streamlit Cloud](https://streamlit.io/cloud)
2. Faça upload do seu repositório no GitHub
3. Clique em **New app** e selecione o repositório e o arquivo `app.py`
4. O deploy será feito automaticamente 🎉

---

## 📂 Estrutura do Projeto

```
analise-centesimal-web/
│
├── app.py               # Código principal do sistema
├── banco.db             # Banco de dados SQLite (criado automaticamente)
├── requirements.txt     # Dependências do projeto
├── README.md            # Instruções de uso (este arquivo)
```

---

## 📧 Contato

Se você tiver dúvidas ou sugestões, entre em contato com:
**Warley Alisson Souza**  
Email: [warleyalisson@gmail.com](mailto:warleyalisson@gmail.com)

---

Desenvolvido com ❤️ para laboratórios, pesquisadores e profissionais de alimentos.
