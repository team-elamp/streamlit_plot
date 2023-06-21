import csv
import pandas as pd
import glob
import plotly.graph_objects as go

# 各csvを1つの図にplotしたい

# orinal_data内のfileを取得する
files = glob.glob('./original_data/**.csv')

# グラフを表示する領域を，figオブジェクトとして作成．
fig = go.Figure()

for file in files:
    # 1行目のヘッダー内にstart timeあるからそれを読み込む
    csv_df = pd.read_csv(file)
    start_time = pd.Timestamp(csv_df['Start time'][0])

    # 2行目のヘッダー内にHR(bpm)があるから読み込む
    csv_df = pd.read_csv(file, skiprows=2)
    hr = csv_df['HR (bpm)'].dropna()

    # HRの正規化を行う
    normalize_hr = (hr - min(hr)) / (max(hr) - min(hr))

    # start_timeデータをリサンプリングして、hrデータと同じ長さにする
    start_time = start_time + pd.Timedelta(seconds=csv_df.index[0])
    time_range = pd.date_range(start_time, periods=len(hr), freq='S')

    # HRデータをプロットする
    fig.add_trace(go.Scatter(x=time_range, y=normalize_hr, mode='lines', name=file, hovertemplate='Time: %{x}<br>Normalized HR: %{y}<extra></extra>'))

# 10分ごとに目盛りを表示する
fig.update_xaxes(
    dtick="600000",  # 10分ごとの目盛り
    tickformat="%H:%M",  # 時間の形式
    rangeslider=dict(visible=True),  # range selectorを追加
    rangeselector=dict(  # range selectorの設定
        buttons=list([
            dict(count=1, label="1h", step="hour", stepmode="backward"),
            dict(count=3, label="3h", step="hour", stepmode="backward"),
            dict(count=6, label="6h", step="hour", stepmode="backward"),
            dict(count=12, label="12h", step="hour", stepmode="backward"),
            dict(step="all", label="All")
        ])
    )
)

# グラフの表示設定を更新
fig.update_layout(
    title="HR Data",
    xaxis_title="Time",
    yaxis_title="Normalized HR",
    legend_title="Files",
    hovermode="x",  # ホバー時にx軸に沿ってデータを表示
    updatemenus=[  # グラフの表示/非表示を切り替えるメニューを追加
        dict(
            type="dropdown",
            showactive=True,
            buttons=[
                dict(
                    label="All",
                    method="update",
                    args=[{"visible": [True for _ in files]}]
                ),
                *[
                    dict(
                        label=file,
                        method="update",
                        args=[{"visible": [True if f == file else False for f in files]}]
                    )
                    for file in files
                ]
            ]
        )
    ]
)

# グラフを表示
fig.show()
