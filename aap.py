from flask import Flask, render_template, request, send_file
import pandas as pd
import gspread
import plotly.graph_objects as go
import io
import os

app = Flask(__name__)

# Configuración de Google Sheets (Usa variables de entorno en Railway)
def get_gspread_client():
    # En Railway configuraremos una variable 'GOOGLE_CREDS' con el JSON
    import json
    creds_dict = json.loads(os.environ.get("GOOGLE_CREDS"))
    gc = gspread.service_account_from_dict(creds_dict)
    return gc

@app.route('/', methods=['GET', 'POST'])
def index():
    # 1. Carga de datos (Igual a tu lógica actual)
    gc = get_gspread_client()
    sh = gc.open_by_key("1c_jufd-06AgiNObBkz0KL0jfqlESKEKiqwFHZwr_9Xg")
    df = pd.DataFrame(sh.worksheet("Resumen Diario Outsourcing").get_all_records())
    df.columns = df.columns.str.strip().str.lower()
    
    # Limpieza de SKU y Pago
    df['sku totales'] = df['sku totales'].astype(str).str.replace(r'[\.\,]', '', regex=True)
    df['sku totales'] = pd.to_numeric(df['sku totales'], errors='coerce').fillna(0).astype(int)
    
    # 2. Lógica de Negocio y Gráficos (Plotly genera el HTML del gráfico)
    # Aquí puedes procesar los filtros que vengan por POST
    
    return render_template('index.html', tables=[df.to_html(classes='data')], titles=df.columns.values)

if __name__ == '__main__':
    # Railway usa la variable de entorno PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)