# Agente Comercial Mave

Assistente de vendas inteligente para o time comercial da Mave.

---

## COMO COLOCAR NO AR (passo a passo)

Você vai precisar de 3 contas (todas gratuitas pra criar):

1. **GitHub** (github.com) - pra guardar o código
2. **Railway** (railway.app) - pra rodar o servidor
3. **Anthropic** (console.anthropic.com) - pra usar o Claude

---

### PASSO 1: Criar conta no GitHub

1. Acesse github.com e clique em "Sign up"
2. Crie sua conta com e-mail e senha
3. Após confirmar o e-mail, você estará logado

### PASSO 2: Subir o código pro GitHub

1. Na página inicial do GitHub, clique no botão verde **"New"** (ou vá em github.com/new)
2. Em "Repository name", digite: `mave-agente`
3. Deixe como **Public**
4. Clique em **"Create repository"**
5. Na página seguinte, clique em **"uploading an existing file"**
6. Arraste TODA a pasta do projeto (app.py, Procfile, requirements.txt, a pasta static/ e a pasta docs/) pra dentro
7. Clique em **"Commit changes"**

**IMPORTANTE:** Todos os arquivos ficam soltos na raiz, sem pastas:
```
mave-agente/
├── app.py
├── index.html
├── Procfile
├── requirements.txt
├── README.md
├── doc___PROMPT_MANUS.txt
├── doc___Base_Conhecimento_Videos_MAVE.txt
├── doc___Catalogo_Imagens_Agente_Vendas_MAVE.txt
└── doc___... (todos os outros .txt com prefixo doc___)
```
Os documentos da Mave têm o prefixo `doc___` no nome pra o servidor identificá-los.

### PASSO 3: Pegar a chave da API do Claude

1. Acesse console.anthropic.com
2. Crie uma conta
3. Vá em "API Keys" no menu lateral
4. Clique em "Create Key"
5. Copie a chave (começa com "sk-ant-...")
6. **GUARDE essa chave** - você vai usar no passo seguinte

### PASSO 4: Deploy no Railway

1. Acesse railway.app
2. Clique em "Login" e entre com sua conta do GitHub
3. No dashboard, clique em **"New Project"**
4. Escolha **"Deploy from GitHub Repo"**
5. Selecione o repositório `mave-agente`
6. O Railway vai começar a fazer o deploy automaticamente
7. **ANTES de funcionar**, você precisa adicionar a chave do Claude:
   - Clique no serviço que apareceu
   - Vá na aba **"Variables"**
   - Clique em **"New Variable"**
   - Nome: `ANTHROPIC_API_KEY`
   - Valor: cole a chave que você copiou no passo 3 (sk-ant-...)
   - Clique em "Add"
8. O Railway vai reiniciar automaticamente
9. Vá na aba **"Settings"** → **"Networking"** → **"Generate Domain"**
10. Clique e ele vai gerar um link tipo `mave-agente-xxxx.up.railway.app`
11. **Esse é o link que seus vendedores vão acessar!**

---

## QUANTO CUSTA

- **Railway:** ~US$ 5/mês (plano Hobby)
- **API do Claude:** depende do uso, ~US$ 0,003 por pergunta do vendedor
- **GitHub:** gratuito

---

## PROBLEMAS COMUNS

**"Application error" ao abrir o link:**
→ Verifique se a variável ANTHROPIC_API_KEY está configurada corretamente

**Demora pra responder:**
→ Normal! O Claude leva 5-15 segundos pra ler todos os documentos e responder

**"Erro na API":**
→ Verifique se você tem créditos na conta da Anthropic (console.anthropic.com → Billing)
