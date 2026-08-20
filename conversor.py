# -----------------------------------------------------------------------
# Formatação dos campos numéricos no padrão VTEX
# -----------------------------------------------------------------------
def formatar_vtex_decimal(valor):
    if pd.isna(valor):
        return ""
    return f"{float(valor):.6f}".replace(".", ",")

df_saida["WeightStart"] = df_saida["WeightStart"].apply(formatar_vtex_decimal)
df_saida["WeightEnd"] = df_saida["WeightEnd"].apply(formatar_vtex_decimal)
df_saida["MinimumValueInsurance"] = df_saida["MinimumValueInsurance"].apply(formatar_vtex_decimal)
