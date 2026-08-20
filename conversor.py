"""
conversor.py
=============================================================================
Lógica pura de conversão TABELA B2B (Packslog) -> layout VTEX.

Recebe os bytes de um .xlsx e devolve um DataFrame pronto para ser usado
pelo aplicativo Streamlit.
=============================================================================
"""

import pandas as pd
import numpy as np
import io


class ErroConversao(Exception):
    """Erro esperado (planilha fora do padrão)."""
    pass


ABA_CEP = "Abrangência"
ABA_MATRIZ = "Tabela Matriz"

COL_CEP_INICIAL = "CEP Inicial"
COL_CEP_FINAL = "CEP Final"
COL_UF = "UF"
COL_REGIAO = "Região Tarifária"
COL_AREA_RISCO = "Área de Risco?"
COL_PRAZO_DIAS = "PRAZO ENTREGA"

MAX_VOLUME_PADRAO = 100000000
COUNTRY_PADRAO = "BRA"
MINIMUM_VALUE_INSURANCE_PADRAO = 1

LINHA_KEY_REGIAO = 2
LINHA_DADOS_INICIO = 5
LINHA_DADOS_FIM = 38
LINHA_ADICIONAL_KG = 38
LINHA_GRIS = 39
LINHA_GRIS_RISCO = 40
LINHA_ADVALOREM = 41
LINHA_ADVALOREM_RISCO = 42

ROMANO_PARA_ARABICO = {
    "I": "1",
    "II": "2",
    "III": "3",
    "IV": "4",
    "V": "5",
}


def regiao_romano_para_chave(uf, regiao_romana):
    regiao_romana = str(regiao_romana).strip()
    partes = regiao_romana.rsplit(" ", 1)

    if len(partes) == 2 and partes[1] in ROMANO_PARA_ARABICO:
        nome, numero_romano = partes
        regiao_final = f"{nome} {ROMANO_PARA_ARABICO[numero_romano]}"
    else:
        regiao_final = regiao_romana

    return f"{str(uf).strip()}-{regiao_final}"


def parse_numero_br(valor):
    """Converte números brasileiros/textos para float."""
    if isinstance(valor, str):
        valor = valor.strip().replace(",", ".")
    return float(valor)


def kg_para_unidade_vtex(valor_kg):
    """Mantém o valor do peso em kg."""
    return parse_numero_br(valor_kg)


def formatar_vtex_decimal(valor):
    """
    Formata número no padrão VTEX solicitado:
        0       -> 0,000000
        300     -> 300,000000
        1.5     -> 1,500000
        25.75   -> 25,750000
    """
    if pd.isna(valor) or valor == "" or valor is None:
        return ""
    return f"{float(valor):.6f}".replace(".", ",")


def dias_para_timecost(dias):
    """Formato TimeCost sem zero à esquerda nos dias (ex: 1.00:00:00)."""
    return f"{int(dias)}.00:00:00"


def is_area_risco(valor):
    return str(valor).strip().lower() in (
        "sim",
        "true",
        "1",
        "s",
        "yes",
    )


def _carregar_matriz(xls):
    df_raw = pd.read_excel(
        xls,
        sheet_name=ABA_MATRIZ,
        header=None
    )

    chaves_regiao = df_raw.iloc[LINHA_KEY_REGIAO, 2:]
    faixas_peso = []

    for i in range(LINHA_DADOS_INICIO, LINHA_DADOS_FIM):
        peso_ini = parse_numero_br(df_raw.iat[i, 0])
        peso_fim = parse_numero_br(df_raw.iat[i, 1])
        faixas_peso.append((peso_ini, peso_fim, i))

    dados_regiao = {}

    for col in range(2, df_raw.shape[1]):
        chave = chaves_regiao.get(col)
        if pd.isna(chave):
            continue

        chave = str(chave).strip()
        tarifas = {}

        for peso_ini, peso_fim, linha in faixas_peso:
            tarifas[(peso_ini, peso_fim)] = df_raw.iat[linha, col]

        dados_regiao[chave] = {
            "tarifas": tarifas,
            "adicional_kg": df_raw.iat[LINHA_ADICIONAL_KG, col],
            "gris": df_raw.iat[LINHA_GRIS, col],
            "gris_risco": df_raw.iat[LINHA_GRIS_RISCO, col],
            "advalorem": df_raw.iat[LINHA_ADVALOREM, col],
            "advalorem_risco": df_raw.iat[LINHA_ADVALOREM_RISCO, col],
        }

    return (
        dados_regiao,
        [(p[0], p[1]) for p in faixas_peso]
    )


def converter_planilha(arquivo_bytes, progresso_callback=None):
    """
    Recebe os bytes de um .xlsx no padrão Packslog.
    Retorna: (df_saida, avisos)
    """
    avisos = []

    # 1. Abrir arquivo Excel
    try:
        xls = pd.ExcelFile(io.BytesIO(arquivo_bytes))
    except Exception as e:
        raise ErroConversao(f"Não consegui abrir o arquivo como Excel válido: {e}")

    # 2. Verificar abas obrigatórias
    for aba in (ABA_CEP, ABA_MATRIZ):
        if aba not in xls.sheet_names:
            raise ErroConversao(
                f"A aba '{aba}' não foi encontrada. "
                f"Abas presentes: {', '.join(xls.sheet_names)}."
            )

    # 3. Ler aba Abrangência
    df_cep = pd.read_excel(xls, sheet_name=ABA_CEP)

    colunas_necessarias = [
        COL_CEP_INICIAL,
        COL_CEP_FINAL,
        COL_UF,
        COL_REGIAO,
        COL_AREA_RISCO,
        COL_PRAZO_DIAS,
    ]

    faltando = [c for c in colunas_necessarias if c not in df_cep.columns]
    if faltando:
        raise ErroConversao(
            f"Colunas faltando na aba '{ABA_CEP}': {', '.join(faltando)}."
        )

    # 4. Carregar matriz de preços
    try:
        dados_regiao, faixas_peso = _carregar_matriz(xls)
    except Exception as e:
        raise ErroConversao(
            f"Erro ao interpretar a 'Tabela Matriz': {e}"
        )

    if not dados_regiao:
        raise ErroConversao("Nenhuma região foi detectada na 'Tabela Matriz'.")

    # 5. Criar chave de região
    df_cep = df_cep.copy()
    df_cep["_chave_regiao"] = df_cep.apply(
        lambda r: regiao_romano_para_chave(r[COL_UF], r[COL_REGIAO]),
        axis=1
    )

    chaves_sem_match = sorted(
        set(df_cep["_chave_regiao"]) - set(dados_regiao.keys())
    )

    if chaves_sem_match:
        avisos.append(
            f"{len(chaves_sem_match)} combinações UF+Região não têm "
            f"correspondência na Matriz (ex: {', '.join(chaves_sem_match[:5])})."
        )

    # 6. Criar linhas VTEX
    linhas_saida = []
    total = len(df_cep)

    for pos, (idx, row) in enumerate(df_cep.iterrows()):
        chave = row["_chave_regiao"]
        info = dados_regiao.get(chave)
        risco = is_area_risco(row[COL_AREA_RISCO])
        zip_start = str(row[COL_CEP_INICIAL]).strip()
        zip_end = str(row[COL_CEP_FINAL]).strip()
        time_cost = dias_para_timecost(row[COL_PRAZO_DIAS])

        if info is None:
            for peso_ini, peso_fim in faixas_peso:
                linhas_saida.append({
                    "ZipCodeStart": zip_start,
                    "ZipCodeEnd": zip_end,
                    "PolygonName": "",
                    "WeightStart": kg_para_unidade_vtex(peso_ini),
                    "WeightEnd": kg_para_unidade_vtex(peso_fim),
                    "AbsoluteMoneyCost": np.nan,
                    "PricePercent": np.nan,
                    "PriceByExtraWeight": np.nan,
                    "MaxVolume": MAX_VOLUME_PADRAO,
                    "TimeCost": time_cost,
                    "Country": COUNTRY_PADRAO,
                    "MinimumValueInsurance": MINIMUM_VALUE_INSURANCE_PADRAO,
                })
            continue

        if risco:
            price_percent = (
                parse_numero_br(info["gris_risco"]) +
                parse_numero_br(info["advalorem_risco"])
            )
        else:
            price_percent = (
                parse_numero_br(info["gris"]) +
                parse_numero_br(info["advalorem"])
            )

        extra_kg = parse_numero_br(info["adicional_kg"])

        for peso_ini, peso_fim in faixas_peso:
            tarifa = info["tarifas"][(peso_ini, peso_fim)]
            linhas_saida.append({
                "ZipCodeStart": zip_start,
                "ZipCodeEnd": zip_end,
                "PolygonName": "",
                "WeightStart": kg_para_unidade_vtex(peso_ini),
                "WeightEnd": kg_para_unidade_vtex(peso_fim),
                "AbsoluteMoneyCost": parse_numero_br(tarifa),
                "PricePercent": price_percent,
                "PriceByExtraWeight": extra_kg,
                "MaxVolume": MAX_VOLUME_PADRAO,
                "TimeCost": time_cost,
                "Country": COUNTRY_PADRAO,
                "MinimumValueInsurance": MINIMUM_VALUE_INSURANCE_PADRAO,
            })

        if progresso_callback and (pos + 1) % 500 == 0:
            progresso_callback((pos + 1) / total)

    # 7. Montar DataFrame final
    df_saida = pd.DataFrame(linhas_saida)

    # 8. FORMATAÇÃO VTEX: 6 casas decimais com vírgula em todos os campos numéricos
    colunas_decimais = [
        "WeightStart",
        "WeightEnd",
        "AbsoluteMoneyCost",
        "PricePercent",
        "PriceByExtraWeight",
        "MaxVolume",
        "MinimumValueInsurance"
    ]

    for col in colunas_decimais:
        df_saida[col] = df_saida[col].apply(formatar_vtex_decimal)

    return df_saida, avisos
