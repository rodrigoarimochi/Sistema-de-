# Conversor B2B → VTEX (sistema web)

## Arquivos
- `app.py` — interface web (Streamlit)
- `conversor.py` — lógica de conversão (a mesma validada nas tabelas B2B-1 e B2B-2)
- `requirements.txt` — dependências

## Deploy gratuito em 5 passos (Streamlit Community Cloud)

1. Crie um repositório no GitHub (pode ser privado) e suba estes 3 arquivos.
2. Acesse https://share.streamlit.io e faça login com sua conta GitHub.
3. Clique em "New app", selecione o repositório, branch e o arquivo `app.py`.
4. (Opcional, recomendado para multi-cliente) Em **Settings → Secrets**, adicione:
   ```
   SENHA_ACESSO = "escolha-uma-senha-aqui"
   ```
   Isso ativa uma tela de senha antes do uso — compartilhe a senha só com quem
   deve acessar. Sem essa configuração, qualquer pessoa com o link acessa.
5. Clique em "Deploy". Em 1-2 minutos você recebe uma URL pública tipo
   `https://seu-app.streamlit.app` — esse é o link para compartilhar com os
   clientes/transportadoras.

## Rodar localmente antes de publicar (opcional, para testar)
```bash
pip install -r requirements.txt
streamlit run app.py
```
Abre em `http://localhost:8501`.

## Limitações do plano gratuito
- App "dorme" após um tempo sem uso e demora ~30s para acordar no próximo
  acesso — normal, sem custo.
- 1 GB de RAM — suficiente para este processamento (testado com 422 mil
  linhas sem problema).
- Se o uso crescer muito (muitos usuários simultâneos, arquivos maiores),
  migrar para um plano pago do Streamlit Cloud ou outro host (Render, Railway)
  é só trocar onde ele está hospedado — o código não muda.

## Evoluções futuras possíveis
- Login individual por cliente (em vez de senha única) — dá pra usar
  `streamlit-authenticator` ou integrar com um provedor de login.
- Histórico de conversões por cliente — precisaria de um banco de dados
  simples (SQLite já resolveria no plano gratuito).
- Envio direto pra VTEX via API, sem precisar baixar o arquivo — possível,
  mas exige as credenciais/endpoint da API de frete da VTEX de cada conta.
- Cálculo do ICMS por UF, se você fornecer a tabela de alíquotas.
