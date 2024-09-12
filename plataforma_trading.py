import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px

# Conectar a la base de datos SQLite
conn = sqlite3.connect('operaciones_trading.db')
c = conn.cursor()

# Crear tabla si no existe
c.execute('''CREATE TABLE IF NOT EXISTS operaciones
             (fecha TEXT, tipo TEXT, capital REAL, riesgo REAL, stop_loss REAL, apalancamiento INTEGER,
              precio_entrada REAL, resultado REAL, ganancia_perdida REAL)''')
conn.commit()

# Función para calcular el riesgo
def calcular_riesgo(capital_btc, porcentaje_riesgo, stop_loss_porcentaje, apalancamiento, precio_entrada, es_corto):
    if es_corto:
        stop_loss_precio = precio_entrada * (1 + stop_loss_porcentaje / 100)
        stop_loss_distancia_usd = stop_loss_precio - precio_entrada
    else:
        stop_loss_precio = precio_entrada * (1 - stop_loss_porcentaje / 100)
        stop_loss_distancia_usd = precio_entrada - stop_loss_precio

    riesgo_btc = capital_btc * (porcentaje_riesgo / 100)
    stop_loss_distancia_btc = stop_loss_distancia_usd / precio_entrada
    posicion_btc = riesgo_btc / stop_loss_distancia_btc
    margen_necesario_btc = posicion_btc / apalancamiento

    return posicion_btc, margen_necesario_btc, riesgo_btc, stop_loss_precio

# Función para calcular estadísticas
def calcular_estadisticas():
    df = pd.read_sql("SELECT * FROM operaciones", conn)

    # Ganancias y pérdidas
    total_operaciones = len(df)
    operaciones_ganadoras = len(df[df['ganancia_perdida'] > 0])
    operaciones_perdedoras = len(df[df['ganancia_perdida'] <= 0])
    
    if total_operaciones > 0:
        porcentaje_asertividad = (operaciones_ganadoras / total_operaciones) * 100
        win_loss_ratio = operaciones_ganadoras / max(1, operaciones_perdedoras)  # Evitar dividir por cero
        total_ganancia = df['ganancia_perdida'].sum()
        
        st.write(f"**Total de operaciones**: {total_operaciones}")
        st.write(f"**Asertividad**: {porcentaje_asertividad:.2f}%")
        st.write(f"**Ratio Ganancias/Pérdidas**: {win_loss_ratio:.2f}")
        st.write(f"**Ganancia/Pérdida Total**: ${total_ganancia:.2f}")
    else:
        st.write("No hay operaciones registradas para mostrar estadísticas.")

# Función para mostrar gráficos
def mostrar_grafico(df):
    df['fecha'] = pd.to_datetime(df['fecha'])
    fig = px.line(df, x='fecha', y='ganancia_perdida', title='Ganancia/Pérdida a lo largo del tiempo')
    st.plotly_chart(fig)

# Función para exportar operaciones a CSV
def descargar_csv():
    df = pd.read_sql("SELECT * FROM operaciones", conn)
    csv = df.to_csv(index=False)
    st.download_button(label="Descargar CSV", data=csv, file_name='operaciones_trading.csv', mime='text/csv')

# Página principal
st.set_page_config(page_title="Plataforma de Trading", layout="centered")
st.title("💼 Plataforma de Trading - Calculadora y Estadísticas")

# Sección de la calculadora
st.header("🧮 Calculadora de Riesgo")
es_corto = st.selectbox("Tipo de Operación", ["Largo (Compra)", "Corto (Venta)"]) == "Corto (Venta)"
capital_btc = st.number_input("Capital en BTC", min_value=0.0, format="%.8f", step=0.0001)
porcentaje_riesgo = st.number_input("Porcentaje de Riesgo (%)", min_value=0.0, max_value=100.0, format="%.2f", step=0.1)
stop_loss_porcentaje = st.number_input("Stop Loss (%)", min_value=0.0, format="%.2f", step=0.1)
apalancamiento = st.number_input("Apalancamiento", min_value=1, format="%d", step=1)
precio_entrada = st.number_input("Precio de Entrada en USD", min_value=0.0, format="%.2f", step=10.0)
resultado = st.number_input("Resultado de la operación (USD)", min_value=-100000.0, max_value=100000.0, step=10.0)

if st.button("Calcular"):
    if capital_btc > 0 and porcentaje_riesgo > 0 and stop_loss_porcentaje > 0 and apalancamiento > 0 and precio_entrada > 0:
        posicion_btc, margen_necesario_btc, riesgo_btc, stop_loss_precio = calcular_riesgo(
            capital_btc, porcentaje_riesgo, stop_loss_porcentaje, apalancamiento, precio_entrada, es_corto)
        
        st.success("**Resultados del Cálculo:**")
        st.write(f"**Tamaño de la posición:** {posicion_btc:.6f} BTC")
        st.write(f"**Margen necesario:** {margen_necesario_btc:.6f} BTC")
        st.write(f"**Riesgo:** {riesgo_btc:.6f} BTC")
        st.write(f"**Precio de Stop Loss:** ${stop_loss_precio:.2f} USD")
        
        if st.button("Registrar Operación"):
            ganancia_perdida = resultado - (margen_necesario_btc * precio_entrada)  # Calcular ganancia/pérdida
            c.execute('INSERT INTO operaciones (fecha, tipo, capital, riesgo, stop_loss, apalancamiento, precio_entrada, resultado, ganancia_perdida) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                      (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                       "Corto" if es_corto else "Largo", 
                       capital_btc, porcentaje_riesgo, stop_loss_porcentaje, apalancamiento, 
                       precio_entrada, resultado, ganancia_perdida))
            conn.commit()
            st.success("Operación registrada exitosamente.")
    else:
        st.error("Por favor, completa todos los campos con valores válidos.")

# Mostrar el historial de operaciones con filtros
st.header("📋 Historial de Operaciones")
filtro_tipo = st.selectbox("Filtrar por tipo de operación", ["Todas", "Largo", "Corto"])
df = pd.read_sql("SELECT * FROM operaciones", conn)

if filtro_tipo != "Todas":
    df = df[df["tipo"] == filtro_tipo]

st.dataframe(df)

# Sección de estadísticas
st.subheader("📊 Estadísticas de Operaciones")
calcular_estadisticas()

# Mostrar gráfico de ganancias/pérdidas
st.subheader("📈 Gráfico de Ganancias y Pérdidas")
mostrar_grafico(df)

# Descargar CSV
st.sidebar.header("Exportar Datos")
descargar_csv()

# Cerrar conexión a la base de datos
conn.close()
