import asyncio
import os
import streamlit as st
import edge_tts
from pypdf import PdfReader

# Configurações iniciais da página web
st.set_page_config(page_title="Meu Leitor IA", page_icon="🔊", layout="centered")

st.title("🔊 Meu @Voice Aloud Web")
st.markdown("Transforme seus arquivos de texto e livros em áudios realistas com IA.")

# Dicionário de vozes excelentes em Português
VOZES = {
    "Francisca (Feminina - Natural)": "pt-BR-FranciscaNeural",
    "Thalita (Feminina - Suave)": "pt-BR-ThalitaNeural",
    "Antonio (Masculino - Padrão)": "pt-BR-AntonioNeural",
    "Nicolau (Masculino - Robusto)": "pt-BR-NicolauNeural",
}

# 1. Configurações na barra lateral (Sidebar)
st.sidebar.header("⚙️ Configurações da Voz")
voz_selecionada = st.sidebar.selectbox("Escolha a Voz:", list(VOZES.keys()))
velocidade_selecionada = st.sidebar.selectbox(
    "Velocidade da leitura:", 
    ["-50%", "-25%", "Padrão", "+25%", "+50%", "+100%"], 
    index=2
)

# Mapeamento de velocidade para a API
vel_map = {"-50%": "-50%", "-25%": "-25%", "Padrão": "+0Hz", "+25%": "+25%", "+50%": "+50%", "+100%": "+100%"}
velocidade = vel_map[velocidade_selecionada]

# 2. Área de Upload de Arquivos
st.subheader("📖 1. Envie seu arquivo ou digite o texto")
arquivo_enviado = st.file_uploader("Traga seu livro ou artigo (Formatos aceitos: PDF ou TXT)", type=["pdf", "txt"])

texto_final = ""

if arquivo_enviado is not None:
    nome_arquivo = arquivo_enviado.name
    if nome_arquivo.endswith('.pdf'):
        with st.spinner("Extraindo texto do PDF..."):
            leitor_pdf = PdfReader(arquivo_enviado)
            for pagina in leitor_pdf.pages:
                texto_final += pagina.extract_text() + "\n"
        st.success("PDF processado com sucesso!")
    elif nome_arquivo.endswith('.txt'):
        texto_final = arquivo_enviado.read().decode("utf-8")
        st.success("Arquivo de texto processado com sucesso!")

texto_input = st.text_area(
    "Conteúdo para leitura:", 
    value=texto_final, 
    height=250
)

# 3. Função assíncrona para gerar o áudio
async def gerar_audio_web(texto, voz, vel):
    arquivo_saida = "audio_gerado.mp3"
    communicate = edge_tts.Communicate(texto, voice=voz, rate=vel)
    await communicate.save(arquivo_saida)
    return arquivo_saida

# 4. Botão para Processar e Gerar o Player
st.subheader("🎧 2. Ouvir e Baixar")

if st.button("🚀 Gerar Áudio com IA", use_container_width=True):
    if not texto_input.strip():
        st.warning("Por favor, digite algum texto ou faça o upload de um arquivo primeiro.")
    else:
        with st.spinner("A inteligência artificial está convertendo seu texto em áudio... Aguarde."):
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
