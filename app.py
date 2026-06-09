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

warnings.filterwarnings('ignore', category=UserWarning)

st.set_page_config(page_title="Leitor IA Premium", page_icon="🔊", layout="centered")

st.title("🔊 Meu @Voice Aloud Web")
st.markdown("Converta Livros (PDF, EPUB, MOBI, DOCX, TXT) em Áudio Realista com IA.")

VOZES = {
    "Francisca (Feminina - Natural)": "pt-BR-FranciscaNeural",
    "Thalita (Feminina - Suave)": "pt-BR-ThalitaNeural",
    "Antonio (Masculino - Padrão)": "pt-BR-AntonioNeural",
    "Nicolau (Masculino - Robusto)": "pt-BR-NicolauNeural",
}

st.sidebar.header("⚙️ Configurações da Voz")
voz_selecionada = st.sidebar.selectbox("Escolha a Voz:", list(VOZES.keys()))
velocidade_selecionada = st.sidebar.selectbox(
    "Velocidade:", ["-50%", "-25%", "Padrão", "+25%", "+50%", "+100%"], index=2
)

vel_map = {"-50%": "-50%", "-25%": "-25%", "Padrão": "+0%", "+25%": "+25%", "+50%": "+50%", "+100%": "+100%"}
velocidade = vel_map[velocidade_selecionada]

st.subheader("📖 1. Envie seu arquivo")

# Deixamos sem restrição para o celular liberar a busca em todas as pastas
arquivo_enviado = st.file_uploader("Toque abaixo para buscar qualquer livro no seu aparelho:")

if "texto_extraido" not in st.session_state:
    st.session_state["texto_extraido"] = ""

if arquivo_enviado is not None:
    nome_arquivo = arquivo_enviado.name
    
    if st.session_state["texto_extraido"] == "":
        with st.spinner(f"Processando '{nome_arquivo}'..."):
            try:
                texto_temporario = ""
                extensao = nome_arquivo.split(".")[-1].lower()
                
                # CORREÇÃO CRÍTICA: Salva uma cópia limpa do arquivo recebido para evitar erros de leitura no celular
                nome_temporario_local = f"temp_file.{extensao}"
                with open(nome_temporario_local, "wb") as f:
                    f.write(arquivo_enviado.getbuffer())
                
                # 1. Lógica para PDF
                if extensao == 'pdf':
                    leitor_pdf = PdfReader(nome_temporario_local)
                    for pagina in leitor_pdf.pages:
                        texto_pag = pagina.extract_text()
                        if texto_pag:
                            texto_temporario += texto_pag + "\n"
                
                # 2. Lógica para DOCX
                elif extensao == 'docx':
                    doc = Document(nome_temporario_local)
                    for paragrafo in doc.paragraphs:
                        texto_temporario += paragrafo.text + "\n"
                
                # 3. Lógica para TXT
                elif extensao == 'txt':
                    with open(nome_temporario_local, "r", encoding="utf-8", errors="ignore") as f:
                        texto_temporario = f.read()
                
                # 4. Lógica para EPUB / MOBI
                elif extensao in ['epub', 'mobi']:
                    livro = epub.read_epub(nome_temporario_local)
                    for item in libro.get_items():
                        if item.get_type() == ebooklib.ITEM_DOCUMENT:
                            soup = BeautifulSoup(item.get_content(), 'html.parser')
                            texto_temporario += soup.get_text() + "\n"

                # Limpa o arquivo temporário gerado
                if os.path.exists(nome_temporario_local):
                    os.remove(nome_temporario_local)

                # Verifica se a extração funcionou
                if texto_temporario.strip():
                    st.session_state["texto_extraido"] = texto_temporario
                    st.success("✅ Arquivo carregado com sucesso!")
                else:
                    st.error("⚠️ O arquivo foi aberto, mas nenhum texto legível foi extraído dele.")
                    
            except Exception as e:
                st.error(f"Erro de compatibilidade ao abrir este arquivo específico: {e}")

# Caixa de texto editável
texto_input = st.text_area(
    "Texto do livro para leitura:", 
    value=st.session_state["texto_extraido"], 
    height=250
)

if st.button("🗑️ Limpar Texto / Trocar de Livro"):
    st.session_state["texto_extraido"] = ""
    st.rerun()

st.subheader("🎧 2. Ouvir e Baixar")

async def gerar_audio_web(texto, voz, vel):
    arquivo_saida = "audio_gerado.mp3"
    communicate = edge_tts.Communicate(texto, voice=voz, rate=vel)
    await communicate.save(arquivo_saida)
    return arquivo_saida

if st.button("🚀 Gerar Áudio com IA", use_container_width=True):
    if not texto_input.strip():
        st.warning("Insira ou carregue um texto primeiro.")
    else:
        with st.spinner("A inteligência artificial está gerando o áudio..."):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio_resultado = loop.run_until_complete(
                    gerar_audio_web(texto_input, VOZES[voz_selecionada], velocidade)
                )
                
                with open(audio_resultado, "rb") as f:
                    bytes_de_audio = f.read()
                
                st.success("✨ Áudio pronto!")
                
                # CORREÇÃO DO PLAYER: Passando explicitamente os bytes e o formato de áudio correto para o celular renderizar na tela
                st.audio(bytes_de_audio, format="audio/mpeg", start_time=0)
                
                st.download_button(
                    label="📥 Baixar arquivo MP3",
                    data=bytes_de_audio,
                    file_name="leitura_ia.mp3",
                    mime="audio/mp3",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"Erro ao sintetizar voz: {e}")
