import streamlit as st
import csv
import pandas as pd
import glob
import plotly.graph_objects as go

st.title("HR Data Visualization")

def plot_hr_data():
    files = glob.glob('./original_data/**.csv')
    fig = go.Figure()

    for file in files:
        csv_df = pd.read_csv(file)
        start_time = pd.Timestamp(csv_df['Start time'][0])

        csv_df = pd.read_csv(file, skiprows=2)
        hr = csv_df['HR (bpm)'].dropna()

        normalize_hr = (hr - min(hr)) / (max(hr) - min(hr))

        start_time = start_time + pd.Timedelta(seconds=csv_df.index[0])
        time_range = pd.date_range(start_time, periods=len(hr), freq='S')

        fig.add_trace(go.Scatter(x=time_range, y=normalize_hr, mode='lines', name=file, hovertemplate='Time: %{x}<br>Normalized HR: %{y}<extra></extra>'))

    fig.update_xaxes(
        dtick="600000",
        tickformat="%H:%M",
        rangeslider=dict(visible=True),
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1h", step="hour", stepmode="backward"),
                dict(count=3, label="3h", step="hour", stepmode="backward"),
                dict(count=6, label="6h", step="hour", stepmode="backward"),
                dict(count=12, label="12h", step="hour", stepmode="backward"),
                dict(step="all", label="All")
            ])
        )
    )

    fig.update_layout(
        title="HR Data",
        xaxis_title="Time",
        yaxis_title="Normalized HR",
        legend_title="Files",
        hovermode="x"
    )

    return fig

fig = plot_hr_data()
st.plotly_chart(fig)
