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
# タイムを秒に変換（競泳タイム対応）
# ---------------------------------------------------------
def time_to_seconds(t):
    if t is None:
        return None

    t = str(t).strip()

    # 01:41.11 → 分:秒.ミリ秒
    if ":" in t:
        try:
            m, s = t.split(":")
            return int(m) * 60 + float(s)
        except:
            return None

    # 58.87 → 秒
    try:
        return float(t)
    except:
        return None

# ---------------------------------------------------------
# Excel 読み込み
# ---------------------------------------------------------
file_path = "穂果記録.xlsx"

events = ["フリー", "バッタ", "ブレ", "バック", "メドレー"]
event = st.selectbox("種目を選択してください", events)

sheet_name = event

# ---------------------------------------------------------
# データ読み込み（A〜F列）
# ---------------------------------------------------------
data = pd.read_excel(file_path, sheet_name=sheet_name, usecols="A:F")

# ★ 列名を強制的に上書き（不可視文字対策）
data.columns = ["日付", "学年", "距離", "長水路or短水路", "タイム", "会場"]

# 正規化
data = normalize_columns(data)

# タイム変換（競泳タイム → 秒）
data["タイム"] = data["タイム"].apply(time_to_seconds)

# ★ 距離を安全に整数化（空白セル対策）
data["距離"] = pd.to_numeric(data["距離"], errors="coerce")
data = data.dropna(subset=["距離"])
data["距離"] = data["距離"].astype(int)

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
# 距離フィルタ（メドレーは固定）
# ---------------------------------------------------------
if event == "メドレー":
    distance_list = [200, 400]
else:
    distance_list = sorted(data["距離"].unique())

distance = st.selectbox("距離を選択してください", distance_list)

# ---------------------------------------------------------
# 長水路／短水路／全記録フィルタ（全記録をデフォルト）
# ---------------------------------------------------------
course = st.selectbox("長水路／短水路を選択", ["全記録", "短水路", "長水路"])

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
# グラフ描画
# ---------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(filtered["日付"], filtered["タイム"], color="gray", linewidth=2)

color_map = {"長水路": "tab:blue", "短水路": "tab:red"}

for c in ["長水路", "短水路"]:
    df_c = filtered[filtered["長水路or短水路"] == c]
    if not df_c.empty:
        ax.scatter(df_c["日付"], df_c["タイム"], color=color_map[c], label=c, s=60)

ax.set_xlabel("日付")
ax.set_ylabel("タイム（秒）")
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
st.write(f"タイム：{latest['タイム']} 秒")
st.write(f"会場：{latest['会場']}")

# ---------------------------------------------------------
# ベストタイム（短水路・長水路）
# ---------------------------------------------------------
best_short = data[(data["距離"] == distance) & (data["長水路or短水路"] == "短水路")]
best_long  = data[(data["距離"] == distance) & (data["長水路or短水路"] == "長水路")]

st.subheader("ベストタイム（短水路）")
if not best_short.empty and best_short["タイム"].notna().any():
    t = best_short["タイム"].min()
    d = best_short.loc[best_short["タイム"].idxmin(), "日付"]
    st.write(f"ベストタイム：**{t} 秒**")
    st.write(f"更新日：{d}")
else:
    st.write("データなし")

st.subheader("ベストタイム（長水路）")
if not best_long.empty and best_long["タイム"].notna().any():
    t = best_long["タイム"].min()
    d = best_long.loc[best_long["タイム"].idxmin(), "日付"]
    st.write(f"ベストタイム：**{t} 秒**")
    st.write(f"更新日：{d}")
else:
    st.write("データなし")
