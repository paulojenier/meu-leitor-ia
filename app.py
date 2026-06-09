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

st.set_page_config(page_title="Leitor IA Persistente", page_icon="🔊", layout="centered")

st.title("🔊 Meu @Voice Aloud Web")
st.markdown("Transforme seus livros em áudio de forma estável e sem perder seus downloads.")

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

# Caminho físico fixo onde salvaremos o áudio para ele nunca sumir sozinho
ARQUIVO_FINAL_FISICO = "audio_gerado_permanente.mp3"

def limpar_e_juntar_texto(texto_sujo):
    if not texto_sujo:
        return ""
    texto = re.sub(r'(\w+)-\n\s*(\w+)', r'\1\2', texto_sujo)
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
    return re.sub(r' +', ' ', texto_final).strip()

st.subheader("📖 1. Envie seu arquivo")
arquivo_enviado = st.file_uploader("Toque abaixo para buscar seu livro:")

# Inicialização segura das variáveis de estado do aplicativo
if "texto_extraido" not in st.session_state:
    st.session_state["texto_extraido"] = ""
if "audio_disponivel" not in st.session_state:
    # Se o arquivo físico já existir no servidor de uma execução anterior, deixa ele ativo
    st.session_state["audio_disponivel"] = os.path.exists(ARQUIVO_FINAL_FISICO)

if arquivo_enviado is not None:
    nome_arquivo = arquivo_enviado.name
    if st.session_state["texto_extraido"] == "":
        with st.spinner(f"Processando '{nome_arquivo}'..."):
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

                if texto_bruto.strip():
                    st.session_state["texto_extraido"] = limpar_e_juntar_texto(texto_bruto)
                    st.success("✅ Arquivo carregado!")
                else:
                    st.error("⚠️ Não encontramos texto legível neste arquivo.")
            except Exception as e:
                st.error(f"Erro ao abrir arquivo: {e}")

texto_input = st.text_area(
    "Texto do livro para leitura:", 
    value=st.session_state["texto_extraido"], 
    height=250
)

# Botão de limpar modificado para apagar também o arquivo físico de áudio antigo
if st.button("🗑️ Limpar Texto / Trocar de Livro"):
    st.session_state["texto_extraido"] = ""
    st.session_state["audio_disponivel"] = False
    if os.path.exists(ARQUIVO_FINAL_FISICO):
        os.remove(ARQUIVO_FINAL_FISICO)
    st.rerun()

st.subheader("🎧 2. Ouvir e Baixar")

async def gerar_audio_em_blocos(texto_completo, voz, vel):
    paragrafos = [p.strip() for p in texto_completo.split("\n\n") if p.strip()]
    if len(paragrafos) <= 1:
        paragrafos = [p.strip() for p in texto_completo.split("\n") if p.strip()]

    if os.path.exists(ARQUIVO_FINAL_FISICO):
        os.remove(ARQUIVO_FINAL_FISICO)

    with open(ARQUIVO_FINAL_FISICO, "wb") as f_completo:
        barra_progresso = st.progress(0, text="Iniciando geração...")
        total_partes = len(paragrafos)
        
        for idx, paragrafo in enumerate(paragrafos):
            porcentagem = int(((idx + 1) / total_partes) * 100)
            barra_progresso.progress(porcentagem, text=f"Processando parte {idx+1} de {total_partes}...")
            
            if len(paragrafo) > 2000:
                pedacos_sub = [paragrafo[i:i+2000] for i in range(0, len(paragrafo), 2000)]
            else:
                pedacos_sub = [paragrafo]

            for pedaco in pedacos_sub:
                if not pedaco.strip():
                    continue
                
                arquivo_temp = f"temp_part_{idx}.mp3"
                try:
                    communicate = edge_tts.Communicate(pedaco, voice=voz, rate=vel)
                    await communicate.save(arquivo_temp)
                    
                    if os.path.exists(arquivo_temp):
                        with open(arquivo_temp, "rb") as f_temp:
                            f_completo.write(f_temp.read())
                        os.remove(arquivo_temp)
                        
                    await asyncio.sleep(0.1)
                except Exception as e:
                    await asyncio.sleep(1)
                    communicate = edge_tts.Communicate(pedaco, voice=voz, rate=vel)
                    await communicate.save(arquivo_temp)
                    if os.path.exists(arquivo_temp):
                        with open(arquivo_temp, "rb") as f_temp:
                            f_completo.write(f_temp.read())
                        os.remove(arquivo_temp)

        barra_progresso.empty()
    return ARQUIVO_FINAL_FISICO

if st.button("🚀 Gerar Áudio com IA", use_container_width=True):
    if not texto_input.strip():
        st.warning("Insira ou carregue um texto primeiro.")
    else:
        with st.spinner("Gerando áudio... Se você mudar de aba, aguarde o fim do processo antes de baixar."):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    gerar_audio_em_blocos(texto_input, VOZES[voz_selecionada], velocidade)
                )
                # Sinaliza que o áudio foi criado fisicamente no servidor com sucesso
                st.session_state["audio_disponivel"] = True
                st.success("✨ Áudio completo gerado!")
                
            except Exception as e:
                st.error(f"Erro ao processar áudio: {e}")

# BLOCO DE PERSISTÊNCIA: Sempre exibe o player e o download se o arquivo existir no disco,
# mesmo se a página tiver sido reiniciada porque você mudou de aba.
if st.session_state["audio_disponivel"] and os.path.exists(ARQUIVO_FINAL_FISICO):
    try:
        with open(ARQUIVO_FINAL_FISICO, "rb") as f:
            bytes_de_audio = f.read()
        
        st.write("---")
        st.audio(bytes_de_audio, format="audio/mp3", start_time=0)
        
        st.download_button(
            label="📥 Baixar arquivo MP3 (Salvo no servidor)",
            data=bytes_de_audio,
            file_name="leitura_ia_persistente.mp3",
            mime="audio/mp3",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Erro ao carregar arquivo salvo: {e}")
