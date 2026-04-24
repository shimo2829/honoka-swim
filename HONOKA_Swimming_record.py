import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
import os

# ---------------------------------------------------------
# 日本語フォント設定（文字化け対策）
# ---------------------------------------------------------
font_path = os.path.join(os.path.dirname(__file__), "ipaexg.ttf")
font_manager.fontManager.addfont(font_path)
plt.rcParams["font.family"] = "IPAexGothic"

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

# ★★★ ここで列名を強制的に上書き（不可視文字対策の決定打）★★★
data.columns = ["日付", "学年", "距離", "長水路or短水路", "タイム", "会場"]

# 正規化（スペース削除など）
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
    filtered = data[data["距離"] == distance].sort_values("日付")
else:
    filtered = data[
        (data["距離"] == distance) &
        (data["長水路or短水路"] == course)
    ].sort_values("日付")

if filtered.empty:
    st.error(f"{event} の {distance}m（{course}）のデータがありません")
    st.stop()

# ---------------------------------------------------------
# グラフ描画（全記録は1本の線＋点の色分け）
# ---------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5))

# 1本の線（全記録でも1本）
ax.plot(filtered["日付"], filtered["タイム"], color="gray", linewidth=2)

# 点の色分け：長水路→青、短水路→赤
color_map = {
    "長水路": "tab:blue",
    "短水路": "tab:red"
}

for c in ["長水路", "短水路"]:
    df_c = filtered[filtered["長水路or短水路"] == c]
    if not df_c.empty:
        ax.scatter(
            df_c["日付"],
            df_c["タイム"],
            color=color_map[c],
            label=c,
            s=60
        )

ax.set_xlabel("日付")
ax.set_ylabel("タイム")
ax.set_title(f"{event} {distance}m（{course}）の記録推移")
ax.grid(True)

if course == "全記録":
    ax.legend()

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
# ベストタイム（短水路・長水路を別々に計算）
# ---------------------------------------------------------
best_short = data[(data["距離"] == distance) & (data["長水路or短水路"] == "短水路")]
best_long  = data[(data["距離"] == distance) & (data["長水路or短水路"] == "長水路")]

st.subheader("ベストタイム（短水路）")
if not best_short.empty:
    t = best_short["タイム"].min()
    d = best_short.loc[best_short["タイム"].idxmin(), "日付"]
    st.write(f"ベストタイム：**{t} 秒**")
    st.write(f"更新日：{d}")
else:
    st.write("データなし")

st.subheader("ベストタイム（長水路）")
if not best_long.empty:
    t = best_long["タイム"].min()
    d = best_long.loc[best_long["タイム"].idxmin(), "日付"]
    st.write(f"ベストタイム：**{t} 秒**")
    st.write(f"更新日：{d}")
else:
    st.write("データなし")
