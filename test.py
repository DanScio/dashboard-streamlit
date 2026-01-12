import pandas as pd
file_path = "data/dashboard_novembre.xlsx"

#----------------LETTURA EXCEL
df_raw = pd.read_excel(
    file_path,
    sheet_name="Main Per Grafico",
    header=None
)

print(df_raw)