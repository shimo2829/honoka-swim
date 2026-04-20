import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# ページ設定（スマホ対応）
# ---------------------------------------------------------
st.set_page_config(
    page_title="穂果 Swimming Record Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# パスワード認証
# ---------------------------------------------------------
PASSWORD = "0128"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("穂果 Swimming Record Dashboard")
    pw = st.text_input("パスワードを入力してください", type="password")

    if pw == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    elif pw != "":
        st.error("パスワードが違います")

    st.stop()

# ---------------------------------------------------------
# 認証後タイトル
# ---------------------------------------------------------
st.title("HONOKA Swimming Record Dashboard")

# ---------------------------------------------------------
# 列名を正規化（揺れ対策）
# ---------------------------------------------------------
def normalize_columns(df):
    new_cols = []
    for col in df.columns:
        c = str(col)
        c = c.replace(" ", "")
        c = c.replace("　", "")
        c = c.replace("ヒヅケ", "日付")
        new_cols.append(c)
    df.columns = new_cols
    return df

# ---------------------------------------------------------
# Excel 読み込み
# ---------------------------------------------------------
file_path = "穂果記録.xlsx"

events = ["フリー", "バッタ", "ブレ", "バック"]
event = st.selectbox("種目を選択してください", events)

sheet_name = event

# ---------------------------------------------------------
# データ読み込み（A〜F列）
# ---------------------------------------------------------
data = pd.read_excel(file_path, sheet_name=sheet_name, usecols="A:F")
data = normalize_columns(data)

# ---------------------------------------------------------
# 必要な列チェック
# ---------------------------------------------------------
required = ["日付", "距離", "長水路or短水路", "タイム"]

for col in required:
    if col not in data.columns:
        st.error(f"必要な列「{col}」が見つかりません")
        st.write("現在の列名：", list(data.columns))
        st.stop()

# ---------------------------------------------------------
# 距離フィルタ
# ---------------------------------------------------------
distance_list = sorted(data["距離"].unique())
distance = st.selectbox("距離を選択してください", distance_list)

# ---------------------------------------------------------
# 長水路／短水路／全記録フィルタ
# ---------------------------------------------------------
course = st.selectbox("長水路／短水路を選択", ["長水路", "短水路", "全記録"])

# ---------------------------------------------------------
# データ絞り込み
# ---------------------------------------------------------
if course == "全記録":
    filtered = data[data["距離"] == distance]
else:
    filtered = data[
        (data["距離"] == distance) &
        (data["長水路or短水路"] == course)
    ]

if filtered.empty:
    st.error(f"{event} の {distance}m（{course}）のデータがありません")
    st.stop()

# ---------------------------------------------------------
# ベストタイム
# ---------------------------------------------------------
best_time = filtered["タイム"].min()
best_date = filtered.loc[filtered["タイム"].idxmin(), "日付"]

# ---------------------------------------------------------
# グラフ描画（単軸・色分け）
# ---------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5))

if course == "全記録":
    # 色設定
    color_map = {"長水路": "tab:blue", "短水路": "tab:red"}

    for c in ["長水路", "短水路"]:
        df_c = filtered[filtered["長水路or短水路"] == c]
        if not df_c.empty:
            ax.plot(
                df_c["日付"],
                df_c["タイム"],
                marker="o",
                label=c,
                color=color_map[c]
            )

    ax.legend()

else:
    ax.plot(filtered["日付"], filtered["タイム"], marker="o")

ax.set_xlabel("日付")
ax.set_ylabel("タイム")
ax.set_title(f"{event} {distance}m（{course}）の記録推移")
ax.grid(True)
st.pyplot(fig)

# ---------------------------------------------------------
# 最新記録
# ---------------------------------------------------------
latest = filtered.iloc[-1]
st.subheader("最新の記録")
st.write(f"日付：{latest['日付']}")
st.write(f"タイム：{latest['タイム']}")
st.write(f"会場：{latest['会場']}")

# ---------------------------------------------------------
# ベストタイム
# ---------------------------------------------------------
st.subheader("ベストタイム")
st.write(f"ベストタイム：**{best_time} 秒**")
st.write(f"更新日：{best_date}")
