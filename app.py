import asyncio
import os
import streamlit as st
import edge_tts
from pypdf import PdfReader
from docx import Document
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import warnings

# Ignorar avisos chatos de bibliotecas antigas de e-book
warnings.filterwarnings('ignore', category=UserWarning)

st.set_page_config(page_title="Meu Leitor IA Super", page_icon="🔊", layout="centered")

st.title("🔊 Meu @Voice Aloud Web")
st.markdown("Converta Livros (PDF, EPUB, MOBI, DOCX, TXT) em Áudio Realista com IA.")

VOZES = {
    "Francisca (Feminina - Natural)": "pt-BR-FranciscaNeural",
    "Thalita (Feminina - Suave)": "pt-BR-ThalitaNeural",
    "Antonio (Masculino - Padrão)": "pt-BR-AntonioNeural",
    "Nicolau (Masculino - Robusto)": "pt-BR-NicolauNeural",
}

# Configurações na barra lateral
st.sidebar.header("⚙️ Configurações da Voz")
voz_selecionada = st.sidebar.selectbox("Escolha a Voz:", list(VOZES.keys()))
velocidade_selecionada = st.sidebar.selectbox(
    "Velocidade:", ["-50%", "-25%", "Padrão", "+25%", "+50%", "+100%"], index=2
)

# CORREÇÃO DO ERRO INVALID RATE: Mudado de +0Hz para +0%
vel_map = {"-50%": "-50%", "-25%": "-25%", "Padrão": "+0%", "+25%": "+25%", "+50%": "+50%", "+100%": "+100%"}
velocidade = vel_map[velocidade_selecionada]

st.subheader("📖 1. Envie seu arquivo")

# CORREÇÃO DO FILTRO DE EPUB: Removido o 'type=' para o celular mostrar todos os seus arquivos na pasta!
arquivo_enviado = st.file_uploader(
    "Selecione seu livro ou artigo (Formatos aceitos internamente: PDF, TXT, DOCX, EPUB, MOBI)"
)

# Inicializa a variável no sistema do Streamlit para não sumir ao clicar em botões
if "texto_extraido" not in st.session_state:
    st.session_state["texto_extraido"] = ""

# Processamento do arquivo enviado
if arquivo_enviado is not None:
    nome_arquivo = arquivo_enviado.name
    
    # Executa apenas se a memória estiver vazia (evita loops infinitos)
    if st.session_state["texto_extraido"] == "":
        with st.spinner(f"Processando arquivo '{nome_arquivo}'... Aguarde."):
            try:
                texto_temporario = ""
                
                # 1. Lógica para PDF
                if nome_arquivo.lower().endswith('.pdf'):
                    leitor_pdf = PdfReader(arquivo_enviado)
                    for pagina in leitor_pdf.pages:
                        texto_pag = pagina.extract_text()
                        if texto_pag:
                            texto_temporario += texto_pag + "\n"
                
                # 2. Lógica para DOCX (Word)
                elif nome_arquivo.lower().endswith('.docx'):
                    doc = Document(arquivo_enviado)
                    for paragrafo in doc.paragraphs:
                        texto_temporario += paragrafo.text + "\n"
                
                # 3. Lógica para TXT
                elif nome_arquivo.lower().endswith('.txt'):
                    texto_temporario = arquivo_enviado.read().decode("utf-8", errors="ignore")
                
                # 4. Lógica para EPUB / MOBI (Livros Digitais)
                elif nome_arquivo.lower().endswith('.epub') or nome_arquivo.lower().endswith('.mobi'):
                    # Salva temporariamente o arquivo na nuvem para a biblioteca conseguir ler
                    with open("temp_book.epub", "wb") as f:
                        f.write(arquivo_enviado.getbuffer())
                    
                    livro = epub.read_epub("temp_book.epub")
                    for item in livro.get_items():
                        if item.get_type() == ebooklib.ITEM_DOCUMENT:
                            # Remove tags HTML de dentro do arquivo ePub/Mobi
                            soup = BeautifulSoup(item.get_content(), 'html.parser')
                            texto_temporario += soup.get_text() + "\n"
                    
                    if os.path.exists("temp_book.epub"):
                        os.remove("temp_book.epub")
                
                else:
                    st.error("⚠️ Formato de arquivo não suportado. Por favor, envie PDF, TXT, DOCX, EPUB ou MOBI.")

                # Se conseguiu extrair algo, joga na memória da tela
                if texto_temporario.strip():
                    st.session_state["texto_extraido"] = texto_temporario
                    st.success("✅ Arquivo processado e carregado abaixo!")
                    
            except Exception as e:
                st.error(f"Erro ao ler o arquivo: {e}")

# Caixa de texto onde o conteúdo aparece automaticamente (e você pode editar)
texto_input = st.text_area(
    "Conteúdo para leitura (Você pode apagar partes ou colar novos textos aqui):", 
    value=st.session_state["texto_extraido"], 
    height=250
)

# Botão para limpar o texto e enviar outro arquivo
if st.button("🗑️ Limpar Texto / Trocar de Arquivo"):
    st.session_state["texto_extraido"] = ""
    st.rerun()

# 3. Gerador do Áudio
st.subheader("🎧 2. Ouvir e Baixar")

async def gerar_audio_web(texto, voz, vel):
    arquivo_saida = "audio_gerado.mp3"
    communicate = edge_tts.Communicate(texto, voice=voz, rate=vel)
    await communicate.save(arquivo_saida)
    return arquivo_saida

if st.button("🚀 Gerar Áudio com IA", use_container_width=True):
    if not texto_input.strip():
        st.warning("O campo de texto está vazio. Envie um arquivo ou digite algo.")
    else:
        if len(texto_input) > 50000:
            st.info("ℹ️ O texto é longo. O processamento da IA pode demorar alguns segundos a mais.")
            
        with st.spinner("A inteligência artificial está convertendo seu texto... Aguarde."):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio_resultado = loop.run_until_complete(
                    gerar_audio_web(texto_input, VOZES[voz_selecionada], velocidade)
                )
                
                with open(audio_resultado, "rb") as f:
                    bytes_de_audio = f.read()
                
                st.success("✨ Áudio gerado com sucesso!")
                st.audio(bytes_de_audio, format="audio/mp3")
                
                st.download_button(
                    label="📥 Baixar arquivo MP3",
                    data=bytes_de_audio,
                    file_name="leitura_ia.mp3",
                    mime="audio/mp3",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"Ocorreu um erro ao gerar o áudio: {e}")
