import asyncio
import os
import re
import streamlit as st
import edge_tts
from pypdf import PdfReader
from docx import Document
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import warnings

warnings.filterwarnings('ignore', category=UserWarning)

st.set_page_config(page_title="Leitor IA Inteligente", page_icon="🔊", layout="centered")

st.title("🔊 Meu @Voice Aloud Web")
st.markdown("Transforme seus livros em áudio fluido e sem quebras de linha erradas.")

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

# FUNÇÃO MÁGICA: Limpa o texto igual ao @Voice Aloud
def limpar_e_juntar_texto(texto_sujo):
    if not texto_sujo:
        return ""
    
    # 1. Corrige hifens de quebra de linha (ex: com-\nputador -> computador)
    texto = re.sub(r'(\w+)-\n\s*(\w+)', r'\1\2', texto_sujo)
    
    # 2. Junta linhas que foram quebradas no meio de uma frase
    # Se a linha não termina com ponto final, exclamação ou interrogação, ela se junta à próxima
    linhas = texto.split('\n')
    texto_junto = []
    linha_atual = ""
    
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            if linha_atual:
                texto_junto.append(linha_atual)
                linha_atual = ""
            continue
        
        if linha_atual:
            # Se a linha atual não termina com pontuação de fim de frase, junta com espaço
            if linha_atual[-1] not in ['.', '!', '?', ':', ';', '"', '»']:
                linha_atual += " " + linha
            else:
                texto_junto.append(linha_atual)
                linha_atual = linha
        else:
            linha_atual = linha
            
    if linha_atual:
        texto_junto.append(linha_atual)
        
    texto_final = "\n\n".join(texto_junto)
    
    # 3. Remove excessos de espaços e quebras múltiplas
    texto_final = re.sub(r' +', ' ', texto_final)
    
    return texto_final.strip()

st.subheader("📖 1. Envie seu arquivo")
arquivo_enviado = st.file_uploader("Toque abaixo para buscar seu livro:")

if "texto_extraido" not in st.session_state:
    st.session_state["texto_extraido"] = ""

if arquivo_enviado is not None:
    nome_arquivo = arquivo_enviado.name
    
    if st.session_state["texto_extraido"] == "":
        with st.spinner(f"Processando e formatando '{nome_arquivo}'..."):
            try:
                texto_bruto = ""
                extensao = nome_arquivo.split(".")[-1].lower()
                
                nome_temporario_local = f"temp_file.{extensao}"
                with open(nome_temporario_local, "wb") as f:
                    f.write(arquivo_enviado.getbuffer())
                
                if extensao == 'pdf':
                    leitor_pdf = PdfReader(nome_temporario_local)
                    for pagina in leitor_pdf.pages:
                        texto_pag = pagina.extract_text()
                        if texto_pag:
                            texto_bruto += texto_pag + "\n"
                
                elif extensao == 'docx':
                    doc = Document(nome_temporario_local)
                    for paragrafo in doc.paragraphs:
                        texto_bruto += paragrafo.text + "\n"
                
                elif extensao == 'txt':
                    with open(nome_temporario_local, "r", encoding="utf-8", errors="ignore") as f:
                        texto_bruto = f.read()
                
                elif extensao in ['epub', 'mobi']:
                    livro = epub.read_epub(nome_temporario_local)
                    for item in livro.get_items():
                        if item.get_type() == ebooklib.ITEM_DOCUMENT:
                            soup = BeautifulSoup(item.get_content(), 'html.parser')
                            texto_bruto += soup.get_text() + "\n"

                if os.path.exists(nome_temporario_local):
                    os.remove(nome_temporario_local)

                # Aplica a limpeza inteligente no texto bruto extraído
                if texto_bruto.strip():
                    st.session_state["texto_extraido"] = limpar_e_juntar_texto(texto_bruto)
                    st.success("✅ Arquivo carregado e formatado!")
                else:
                    st.error("⚠️ Não encontramos texto legível neste arquivo.")
                    
            except Exception as e:
                st.error(f"Erro ao abrir arquivo: {e}. Tente converter para TXT ou PDF padrão.")

texto_input = st.text_area(
    "Texto do livro (Formatado para leitura fluida):", 
    value=st.session_state["texto_extraido"], 
    height=250
)

if st.button("🗑️ Limpar Texto / Trocar de Livro"):
    st.session_state["texto_extraido"] = ""
    st.rerun()

st.subheader("🎧 2. Ouvir e Baixar")

async def gerar_audio_web(texto, voz, vel):
    arquivo_saida = "audio_gerado.mp3"
    # Processa blocos de texto mantendo estabilidade
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
                st.audio(bytes_de_audio, format="audio/mp3", start_time=0)
                
                st.download_button(
                    label="📥 Baixar arquivo MP3",
                    data=bytes_de_audio,
                    file_name="leitura_ia.mp3",
                    mime="audio/mp3",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"Erro ao gerar áudio: {e}")
