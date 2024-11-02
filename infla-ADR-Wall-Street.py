import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import timedelta

# Cargar datos de inflación desde el archivo CSV
@st.cache_data
def load_cpi_data():
    try:
        cpi = pd.read_csv('CPIAUCSL.csv')
    except FileNotFoundError:
        st.error("El archivo 'inflaciónargentina2.csv' no se encontró. Asegúrate de que el archivo esté en el mismo directorio que este script.")
        st.stop()

    # Asegurar que las columnas necesarias existan
    if 'Date' not in cpi.columns or 'CPI_MoM' not in cpi.columns:
        st.error("El archivo CSV debe contener las columnas 'Date' y 'CPI_MoM'.")
        st.stop()

    # Convertir la columna 'Date' a datetime
    cpi['Date'] = pd.to_datetime(cpi['Date'], format='%Y-%m-%d')
    cpi.set_index('Date', inplace=True)

    # Calcular la inflación acumulada
    cpi['Cumulative_Inflation'] = (1 + cpi['CPI_MoM']).cumprod()

    # Resamplear a diario y rellenar
    daily = cpi['Cumulative_Inflation'].resample('D').interpolate(method='linear')
    
    # Asegurar que el índice sea tz-naive
    daily = daily.tz_localize(None)

    return daily

daily_cpi = load_cpi_data()

# ------------------------------
# Crear la aplicación Streamlit
st.title('Ajustadora de acciones del Merval por inflación - MTaurus - [X: MTaurus_ok](https://x.com/MTaurus_ok)')

# Subheader para el calculador de inflación
st.subheader('1- Calculador de precios por inflación')

# Entrada del usuario: elegir si ingresar el valor para la fecha de inicio o fin
value_choice = st.radio(
    "¿Quieres ingresar el valor para la fecha de inicio o la fecha de fin?",
    ('Fecha de Inicio', 'Fecha de Fin'),
    key='value_choice_radio'
)

if value_choice == 'Fecha de Inicio':
    start_date = st.date_input(
        'Selecciona la fecha de inicio:',
        min_value=daily_cpi.index.min().date(),
        max_value=daily_cpi.index.max().date(),
        value=daily_cpi.index.min().date(),
        key='start_date_input'
    )
    end_date = st.date_input(
        'Selecciona la fecha de fin:',
        min_value=daily_cpi.index.min().date(),
        max_value=daily_cpi.index.max().date(),
        value=daily_cpi.index.max().date(),
        key='end_date_input'
    )
    start_value = st.number_input(
        'Ingresa el valor en la fecha de inicio (en ARS):',
        min_value=0.0,
        value=100.0,
        key='start_value_input'
    )

    # Filtrar los datos para las fechas seleccionadas
    try:
        start_inflation = daily_cpi.loc[pd.to_datetime(start_date)]
        end_inflation = daily_cpi.loc[pd.to_datetime(end_date)]
    except KeyError as e:
        st.error(f"Error al obtener la inflación para las fechas seleccionadas: {e}")
        st.stop()

    # Calcular el valor ajustado para la fecha de fin
    end_value = start_value * (end_inflation / start_inflation)

    # Mostrar los resultados
    st.write(f"Valor inicial el {start_date}: ARS {start_value}")
    st.write(f"Valor ajustado el {end_date}: ARS {end_value:.2f}")

else:
    start_date = st.date_input(
        'Selecciona la fecha de inicio:',
        min_value=daily_cpi.index.min().date(),
        max_value=daily_cpi.index.max().date(),
        value=daily_cpi.index.min().date(),
        key='start_date_end_date_input'
    )
    end_date = st.date_input(
        'Selecciona la fecha de fin:',
        min_value=start_date,
        max_value=daily_cpi.index.max().date(),
        value=daily_cpi.index.max().date(),
        key='end_date_end_date_input'
    )
    end_value = st.number_input(
        'Ingresa el valor en la fecha de fin (en ARS):',
        min_value=0.0,
        value=100.0,
        key='end_value_input'
    )

    # Filtrar los datos para las fechas seleccionadas
    try:
        start_inflation = daily_cpi.loc[pd.to_datetime(start_date)]
        end_inflation = daily_cpi.loc[pd.to_datetime(end_date)]
    except KeyError as e:
        st.error(f"Error al obtener la inflación para las fechas seleccionadas: {e}")
        st.stop()

    # Calcular el valor ajustado para la fecha de inicio
    start_value = end_value / (end_inflation / start_inflation)

    # Mostrar los resultados
    st.write(f"Valor ajustado el {start_date}: ARS {start_value:.2f}")
    st.write(f"Valor final el {end_date}: ARS {end_value}")

# Subheader para la ajustadora de acciones
st.subheader('2- Ajustadora de acciones por inflación')

# Entrada del usuario: ingresar tickers de acciones (separados por comas)
tickers_input = st.text_input(
    'Ingresa los tickers de acciones separados por comas (por ejemplo, AAPL.BA, MSFT.BA, META):',
    key='tickers_input'
)

# Entrada del usuario: elegir el período de SMA para el primer ticker
sma_period = st.number_input(
    'Ingresa el número de periodos para el SMA del primer ticker:',
    min_value=1,
    value=10,
    key='sma_period_input'
)

# Entrada del usuario: seleccionar la fecha de inicio para los datos mostrados en el gráfico
plot_start_date = st.date_input(
    'Selecciona la fecha de inicio para los datos mostrados en el gráfico:',
    min_value=daily_cpi.index.min().date(),
    max_value=daily_cpi.index.max().date(),
    value=(daily_cpi.index.max() - timedelta(days=365)).date(),  # Por defecto, 1 año atrás
    key='plot_start_date_input'
)

# Opción para mostrar los valores ajustados por inflación como porcentajes
show_percentage = st.checkbox('Mostrar valores ajustados por inflación como porcentajes', value=False)

# Diccionario para almacenar los datos de acciones procesados
stock_data_dict_nominal = {}
stock_data_dict_adjusted = {}

if tickers_input:
    tickers = [ticker.strip().upper() for ticker in tickers_input.split(',')]
    fig = go.Figure()

    # Descargar y procesar datos para cada ticker
    for ticker in tickers:
        try:
            # Realizar la solicitud a la API de Stock Analysis
            params = {
                'range': '10Y',
                'period': 'Daily',
            }
            response = requests.get(f'https://api.stockanalysis.com/api/symbol/s/{ticker}/history', params=params, headers={'accept': '*/*'})
            stock_data = pd.DataFrame(response.json()['data'])
            st.write(stock_data)
            print(stock_data.head())
            print(stock_data.columns)

            if stock_data.empty:
                st.error(f"No se encontraron datos para el ticker {ticker}. Verifica que el ticker sea correcto y esté activo.")
                continue

            # Procesar las fechas
            stock_data['Date'] = pd.to_datetime(stock_data['t'])  # Ajusta el nombre de la columna si es necesario
            stock_data.set_index('Date', inplace=True)

            # Asegurarse que el índice sea de tipo datetime y tz-naive
            stock_data.index = pd.to_datetime(stock_data.index).tz_localize(None)

            # Unir con los datos de inflación
            stock_data = stock_data.join(daily_cpi, how='left')
            # Rellenar hacia adelante cualquier dato de inflación faltante
            stock_data['Cumulative_Inflation'].ffill(inplace=True)
            # Eliminar cualquier fila restante con NaN en 'Cumulative_Inflation'
            stock_data.dropna(subset=['Cumulative_Inflation'], inplace=True)

            # Calcular 'Inflation_Adjusted_Close'
            stock_data['Inflation_Adjusted_Close'] = stock_data['a'] * (
                stock_data['Cumulative_Inflation'].iloc[-1] / stock_data['Cumulative_Inflation']
            )

            # Almacenar los datos en los diccionarios
            stock_data_dict_nominal[ticker] = stock_data['a']
            stock_data_dict_adjusted[ticker] = stock_data['Inflation_Adjusted_Close']

            # Graficar los precios ajustados por inflación
            if show_percentage:
                # Calcular variación porcentual
                stock_data['Inflation_Adjusted_Percentage'] = (
                    stock_data['Inflation_Adjusted_Close'] / stock_data['Inflation_Adjusted_Close'].iloc[0] - 1
                ) * 100
                fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Inflation_Adjusted_Percentage'], mode='lines', name=f'{ticker} - Ajustado (%)'))
            else:
                fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Inflation_Adjusted_Close'], mode='lines', name=f'{ticker} - Ajustado'))

        except Exception as e:
            st.error(f"Error al procesar el ticker {ticker}: {e}")

    # Mostrar el gráfico final
    fig.update_layout(title='Valores de acciones ajustados por inflación',
                      xaxis_title='Fecha',
                      yaxis_title='Precio Ajustado (ARS)',
                      template='plotly_white')
    st.plotly_chart(fig)

