"""
app.py — Conversor B2B -> VTEX (interface web em Streamlit)
=============================================================================
Como rodar localmente:
    pip install -r requirements.txt
    streamlit run app.py

Como publicar de graça:
    1. Suba esta pasta (app.py, conversor.py, requirements.txt) num repositório
       no GitHub (pode ser privado).
    2. Acesse https://share.streamlit.io , conecte sua conta GitHub e aponte
       para o repositório -> ele publica automaticamente com HTTPS.
    3. Em "Settings -> Secrets" do Streamlit Cloud, defina uma senha de acesso
       (veja SENHA_ACESSO abaixo) para controlar quem usa o sistema.
=============================================================================
"""

import streamlit as st
import io
from datetime import datetime

from conversor import converter_planilha, ErroConversao

st.set_page_config(page_title="Conversor B2B → VTEX", page_icon="📦", layout="centered")

# -----------------------------------------------------------------------
# Controle de acesso simples (opcional).
# Defina st.secrets["SENHA_ACESSO"] no painel do Streamlit Cloud para ativar.
# Sem essa secret configurada, o app fica aberto para quem tiver o link.
# -----------------------------------------------------------------------
SENHA_CONFIGURADA = st.secrets.get("SENHA_ACESSO") if hasattr(st, "secrets") else None

if SENHA_CONFIGURADA:
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.title("📦 Conversor B2B → VTEX")
        senha = st.text_input("Senha de acesso", type="password")
        if st.button("Entrar"):
            if senha == SENHA_CONFIGURADA:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
        st.stop()

# -----------------------------------------------------------------------
# App principal
# -----------------------------------------------------------------------
st.title("📦 Conversor B2B → VTEX")
st.markdown(
    "Envie a planilha de tarifas no padrão Packslog (abas **Abrangência** e "
    "**Tabela Matriz**) e baixe o arquivo pronto para importar na VTEX."
)

arquivo = st.file_uploader("Selecione o arquivo .xlsx", type=["xlsx"])

if arquivo is not None:
    st.write(f"Arquivo recebido: **{arquivo.name}** ({arquivo.size / 1024:.0f} KB)")

    if st.button("Converter para VTEX", type="primary"):
        barra = st.progress(0.0, text="Iniciando conversão...")

        def atualizar_progresso(fracao):
            barra.progress(min(fracao, 1.0), text=f"Processando faixas de CEP... {fracao*100:.0f}%")

        try:
            df_saida, avisos = converter_planilha(arquivo.getvalue(), progresso_callback=atualizar_progresso)
        except ErroConversao as e:
            barra.empty()
            st.error(f"Não foi possível converter o arquivo: {e}")
            st.stop()
        except Exception as e:
            barra.empty()
            st.error(
                "Ocorreu um erro inesperado ao processar o arquivo. "
                "Confirme se ele segue exatamente o layout padrão Packslog."
            )
            st.exception(e)
            st.stop()

        barra.progress(1.0, text="Concluído!")
        st.success(f"Conversão concluída: {len(df_saida):,} linhas geradas.".replace(",", "."))

        for aviso in avisos:
            st.warning(aviso)

        st.dataframe(df_saida.head(20), use_container_width=True)

        nome_base = arquivo.name.rsplit(".", 1)[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")

        buffer_xlsx = io.BytesIO()
        df_saida.to_excel(buffer_xlsx, index=False, engine="openpyxl")
        buffer_xlsx.seek(0)

        buffer_csv = io.StringIO()
        df_saida.to_csv(buffer_csv, index=False, sep=";", encoding="utf-8-sig")

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "⬇️ Baixar .xlsx",
                data=buffer_xlsx,
                file_name=f"VTEX_{nome_base}_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with col2:
            st.download_button(
                "⬇️ Baixar .csv",
                data=buffer_csv.getvalue().encode("utf-8-sig"),
                file_name=f"VTEX_{nome_base}_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True,
            )

st.markdown("---")
st.caption(
    "O arquivo enviado é processado apenas em memória durante a conversão e não é "
    "armazenado no servidor."
)
