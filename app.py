"""
Agente Comercial Mave - Servidor Principal
==========================================
Recebe mensagem do vendedor (com ou sem arquivo),
junta com os documentos da Mave, manda pro Claude
e devolve a resposta.

Arquivos suportados: PDF, imagens, .txt, .csv, .docx
"""

import os
import glob
import base64
import io
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
import anthropic

# ============================================================
# CONFIGURAÇÃO
# ============================================================

MODELO = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096

# Documentos ficam na mesma pasta, com prefixo "doc___"
PASTA_BASE = os.path.dirname(__file__)

TIPOS_IMAGEM = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
TIPOS_TEXTO = {".txt", ".csv", ".md", ".json", ".log"}
TIPOS_PDF = {".pdf"}
TIPOS_DOCX = {".docx"}
TODOS_TIPOS = TIPOS_IMAGEM | TIPOS_TEXTO | TIPOS_PDF | TIPOS_DOCX
MAX_TAMANHO = 10 * 1024 * 1024  # 10MB

# ============================================================
# CARREGAR DOCUMENTOS DA MAVE (roda 1x ao ligar)
# ============================================================

def carregar_documentos():
    """Lê todos os arquivos doc___*.txt da pasta raiz."""
    documentos = []
    arquivos = sorted(glob.glob(os.path.join(PASTA_BASE, "doc___*.txt")))
    for caminho in arquivos:
        nome_arquivo = os.path.basename(caminho)
        # Remove o prefixo "doc___" pra mostrar o nome limpo
        nome_limpo = nome_arquivo.replace("doc___", "")
        if nome_limpo == "PROMPT_MANUS.txt":
            continue
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                conteudo = f.read()
            documentos.append(f"=== DOCUMENTO: {nome_limpo} ===\n{conteudo}\n")
            print(f"  Carregado: {nome_limpo} ({len(conteudo):,} chars)")
        except Exception as e:
            print(f"  ERRO ao ler {nome_limpo}: {e}")
    texto = "\n".join(documentos)
    print(f"\nTotal: {len(documentos)} docs, {len(texto):,} chars")
    return texto


def carregar_system_prompt():
    """Lê o doc___PROMPT_MANUS.txt."""
    caminho = os.path.join(PASTA_BASE, "doc___PROMPT_MANUS.txt")
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Você é o agente comercial interno da Mave. Ajude o vendedor."


print("=" * 50)
print("Carregando documentos da Mave...")
print("=" * 50)
SYSTEM_PROMPT = carregar_system_prompt()
DOCUMENTOS = carregar_documentos()
SYSTEM_COMPLETO = f"""{SYSTEM_PROMPT}

<base_de_conhecimento>
{DOCUMENTOS}
</base_de_conhecimento>
"""
print(f"\nSystem prompt: {len(SYSTEM_COMPLETO):,} chars (~{len(SYSTEM_COMPLETO)//4:,} tokens)")
print("=" * 50)

# ============================================================
# PROCESSAMENTO DE ARQUIVOS DO VENDEDOR
# ============================================================

def extrair_texto_pdf(conteudo_bytes):
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(conteudo_bytes))
        textos = [p.extract_text() for p in reader.pages if p.extract_text()]
        return "\n\n".join(textos) if textos else "[PDF sem texto extraível]"
    except Exception as e:
        return f"[Erro ao ler PDF: {e}]"


def extrair_texto_docx(conteudo_bytes):
    try:
        from docx import Document
        doc = Document(io.BytesIO(conteudo_bytes))
        textos = [p.text for p in doc.paragraphs if p.text.strip()]
        for tabela in doc.tables:
            for linha in tabela.rows:
                celulas = [c.text.strip() for c in linha.cells if c.text.strip()]
                if celulas:
                    textos.append(" | ".join(celulas))
        return "\n".join(textos) if textos else "[DOCX sem texto]"
    except Exception as e:
        return f"[Erro ao ler DOCX: {e}]"


async def processar_arquivo(arquivo: UploadFile):
    nome = arquivo.filename or "arquivo"
    ext = os.path.splitext(nome)[1].lower()

    if ext not in TODOS_TIPOS:
        return ("texto", f"[Tipo não suportado: {ext}. Envie PDF, imagem, .txt, .csv ou .docx]")

    conteudo = await arquivo.read()
    if len(conteudo) > MAX_TAMANHO:
        return ("texto", f"[Arquivo muito grande: {len(conteudo)/(1024*1024):.1f}MB. Máximo: 10MB]")

    if ext in TIPOS_IMAGEM:
        media_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
        return ("imagem", {
            "tipo_media": media_types[ext],
            "dados_b64": base64.b64encode(conteudo).decode("utf-8"),
            "nome": nome,
        })

    if ext in TIPOS_TEXTO:
        try:
            texto = conteudo.decode("utf-8")
        except UnicodeDecodeError:
            texto = conteudo.decode("latin-1")
        return ("texto", f"[Arquivo '{nome}']\n{texto}")

    if ext in TIPOS_PDF:
        return ("texto", f"[PDF '{nome}']\n{extrair_texto_pdf(conteudo)}")

    if ext in TIPOS_DOCX:
        return ("texto", f"[DOCX '{nome}']\n{extrair_texto_docx(conteudo)}")

    return ("texto", f"[Não processado: {nome}]")

# ============================================================
# SERVIDOR
# ============================================================

app = FastAPI(title="Agente Comercial Mave")
cliente = anthropic.Anthropic()
conversas = {}


@app.get("/", response_class=HTMLResponse)
async def pagina_principal():
    """Serve a página do chat."""
    caminho = os.path.join(PASTA_BASE, "index.html")
    with open(caminho, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/chat")
async def chat(
    mensagem: str = Form(default=""),
    session_id: str = Form(default="default"),
    arquivo: UploadFile = File(default=None),
):
    try:
        mensagem = mensagem.strip()
        if not mensagem and (not arquivo or not arquivo.filename):
            return JSONResponse(content={"erro": "Envie uma mensagem ou arquivo"}, status_code=400)

        if session_id not in conversas:
            conversas[session_id] = []
        historico = conversas[session_id]

        content_parts = []
        nome_arquivo = None

        # Processa arquivo se enviado
        if arquivo and arquivo.filename:
            nome_arquivo = arquivo.filename
            tipo, dados = await processar_arquivo(arquivo)

            if tipo == "imagem":
                content_parts.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": dados["tipo_media"],
                        "data": dados["dados_b64"],
                    }
                })
                if not mensagem:
                    mensagem = f"O vendedor enviou a imagem '{dados['nome']}'. Analise e ajude conforme o contexto comercial."
            else:
                content_parts.append({"type": "text", "text": dados})
                if not mensagem:
                    mensagem = f"O vendedor enviou o arquivo '{nome_arquivo}'. Analise o conteúdo e ajude."

        content_parts.append({"type": "text", "text": mensagem})
        historico.append({"role": "user", "content": content_parts})

        if len(historico) > 20:
            historico = historico[-20:]
            conversas[session_id] = historico

        resposta = cliente.messages.create(
            model=MODELO,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_COMPLETO,
            messages=historico,
        )

        texto_resposta = resposta.content[0].text
        historico.append({"role": "assistant", "content": texto_resposta})

        return JSONResponse(content={"resposta": texto_resposta, "arquivo_recebido": nome_arquivo})

    except anthropic.APIError as e:
        print(f"Erro API: {e}")
        return JSONResponse(content={"erro": f"Erro na API: {str(e)}"}, status_code=500)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(content={"erro": f"Erro interno: {str(e)}"}, status_code=500)


@app.post("/nova-conversa")
async def nova_conversa(request: Request):
    dados = await request.json()
    session_id = dados.get("session_id", "default")
    conversas[session_id] = []
    return JSONResponse(content={"status": "ok"})


@app.get("/saude")
async def saude():
    return {"status": "ok", "documentos_carregados": DOCUMENTOS != ""}
