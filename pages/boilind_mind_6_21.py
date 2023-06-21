import streamlit as st
import csv
import pandas as pd
import glob
import plotly.graph_objects as go


def plot_hr(glob_files_path:str):
    files = glob.glob(glob_files_path)
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


st.title('ボーリングマインド 6/21 プロット')
'''
目的：ダンサー内で心拍同期が起きているかどうか\n
詳細:ボーリングマインドのリハーサル時にダンサーの左腕にpolar verity senseをつけてもらい、パフォーマンスをしていただきました。\n
その時の心拍(HR)をプロットしました。 また、心拍同期は心拍の増減のタイミングが同期しているかがなので、個人ごとに心拍を正規化（最小値を0最大値を1とする）し、プロットしました。\n
'''
st.caption('下のグラフ内の右のファイル名をクリックすると、ファイルごとに表示・非表示が切り替えられます！\nまた、グラフ右上の拡張ボタンを押すと、グラフが大きく表示されます！')
option = st.selectbox(
'表示するカテゴリ',
('all','audience','dancer')
)


files_path = ''
if option == 'all':
    files_path = './boiling_mind_6_21_data/**/*.CSV'
    fig = plot_hr(files_path)
    st.plotly_chart(fig)
elif option == 'audience':
    files_path = './boiling_mind_6_21_data/audience/*.CSV'
    fig = plot_hr(files_path)
    st.plotly_chart(fig)
elif option == 'dancer':
    files_path = './boiling_mind_6_21_data/dancer/*.CSV'
    fig = plot_hr(files_path)
    st.plotly_chart(fig)

