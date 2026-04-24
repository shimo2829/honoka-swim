import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
import os
import re
import datetime

# ---------------------------------------------------------
# 日本語フォント設定
# ---------------------------------------------------------
font_path = os.path.join(os.path.dirname(__file__), "ipaexg.ttf")
font_manager.fontManager.addfont(font_path)
plt.rcParams["font.family"] = "IPAexGothic"

# ---------------------------------------------------------
# ページ設定
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
# 列名正規化（スペース完全除去）
# ---------------------------------------------------------
def normalize_columns(df):
    new_cols = []
    for col in df.columns:
        c = str(col)

        # 半角・全角スペース除去
        c = c.replace(" ", "").replace("　", "")

        # 不可視文字除去
        c = re.sub(r"[\u200B-\u200F\uFEFF]", "", c)

        # 列名ゆれ修正
        c = c.replace("ヒヅケ", "日付")

        new_cols.append(c)

    df.columns = new_cols
    return df

# ---------------------------------------------------------
# 秒 → 競技タイム表記
# ---------------------------------------------------------
def seconds_to_competition_time(sec):
    m = int(sec // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 100))
    return f"{m}'{s:02d}\"{ms:02d}"

# ---------------------------------------------------------
# Y軸用：秒 → 分:秒
# ---------------------------------------------------------
def sec_to_minsec(sec):
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m}:{s:02d}"

# ---------------------------------------------------------
# タイムを秒に変換
# ---------------------------------------------------------
def time_to_seconds(t):
    if t is None:
        return None

    t = str(t).strip()
    if t == "" or t.lower() == "nan":
        return None

    t = t.replace("’", "'").replace("‘", "'")
    t = t.replace("“", '"').replace("”", '"')

    match = re.match(r"(\d+)'(\d+)" + r'"' + r"(\d+)", t)
    if match:
        m, s, ms = match.groups()
        return int(m) * 60 + int(s) + int(ms) / 100

    match = re.match(r"(\d+):(\d+)\.(\d+)", t)
    if match:
        m, s, ms = match.groups()
        return int(m) * 60 + int(s) + int(ms) / 100

    match = re.match(r"(\d+):(\d+)$", t)
    if match:
        m, s = match.groups()
        return int(m) * 60 + int(s)

    match = re.match(r"(\d+)分(\d+)秒(\d+)", t)
    if match:
        m, s, ms = match.groups()
        return int(m) * 60 + int(s) + int(ms) / 100

    return None

# ---------------------------------------------------------
# Excel 読み込み（G列以降を強制無視）
# ---------------------------------------------------------
file_path = "穂果記録.xlsx"

events = ["フリー", "バッタ", "ブレ", "バック", "メドレー"]
event = st.selectbox("種目を選択してください", events)

sheet_name = event

# ★ G列以降を完全無視（A〜Fだけ残す）
data = pd.read_excel(file_path, sheet_name=sheet_name)
data = data.iloc[:, :6]

data = normalize_columns(data)

# ---------------------------------------------------------
# 必要列チェック
# ---------------------------------------------------------
required = ["日付", "距離", "長水路or短水路", "タイム"]
for col in required:
    if col not in data.columns:
        st.error(f"必要な列「{col}」が見つかりません")
        st.write("現在の列名：", list(data.columns))
        st.stop()

# ---------------------------------------------------------
# 日付を datetime に統一
# ---------------------------------------------------------
data["日付"] = pd.to_datetime(data["日付"], errors="coerce")

# ---------------------------------------------------------
# 距離の揺れ吸収（50, ５０, 50.0 すべてOK）
# ---------------------------------------------------------
data["距離"] = (
    data["距離"]
    .astype(str)
    .str.replace("m", "", regex=False)
    .str.replace("Ｍ", "", regex=False)
    .str.replace("　", "", regex=False)
    .str.strip()
)
data["距離"] = pd.to_numeric(data["距離"], errors="coerce")

# ---------------------------------------------------------
# 長水路/短水路の揺れ吸収（スペース完全除去）
# ---------------------------------------------------------
data["長水路or短水路"] = (
    data["長水路or短水路"]
    .astype(str)
    .str.replace(" ", "")
    .str.replace("　", "")
    .str.strip()
)

# ---------------------------------------------------------
# タイムを秒に変換
# ---------------------------------------------------------
data["タイム"] = data["タイム"].astype(str).apply(time_to_seconds)

# ---------------------------------------------------------
# 欠損除去
# ---------------------------------------------------------
data = data.dropna(subset=["日付", "距離", "タイム"])

# ---------------------------------------------------------
# 距離フィルタ
# ---------------------------------------------------------
if event == "メドレー":
    distance_list = [100, 200, 400]
else:
    distance_list = sorted(data["距離"].unique())

distance = st.selectbox("距離を選択してください", distance_list)

# ---------------------------------------------------------
# 長水路／短水路／全記録
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
# グラフ描画（Y軸：分:秒）
# ---------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(filtered["日付"], filtered["タイム"], color="gray", linewidth=2)

color_map = {"長水路": "tab:blue", "短水路": "tab:red"}

for c in ["長水路", "短水路"]:
    df_c = filtered[filtered["長水路or短水路"] == c]
    if not df_c.empty:
        ax.scatter(df_c["日付"], df_c["タイム"], color=color_map[c], label=c, s=60)

y_min = int(filtered["タイム"].min() // 10 * 10)
y_max = int(filtered["タイム"].max() // 10 * 10 + 10)

ax.set_ylim(y_min, y_max)
ax.set_yticks(range(y_min, y_max + 1, 10))
ax.set_yticklabels([sec_to_minsec(t) for t in range(y_min, y_max + 1, 10)])

ax.set_yticks([t for t in range(y_min, y_max + 1, 1)], minor=True)
ax.grid(which="minor", linestyle="--", linewidth=0.3, alpha=0.5)

ax.set_xlabel("日付")
ax.set_ylabel("タイム（分:秒）")
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
st.write(f"タイム：{seconds_to_competition_time(latest['タイム'])}")
st.write(f"会場：{latest.get('会場', '―')}")

# ---------------------------------------------------------
# ベストタイム
# ---------------------------------------------------------
best_short = data[(data["距離"] == distance) & (data["長水路or短水路"] == "短水路")]
best_long  = data[(data["距離"] == distance) & (data["長水路or短水路"] == "長水路")]

st.subheader("ベストタイム（短水路）")
if not best_short.empty:
    t = best_short["タイム"].min()
    d = best_short.loc[best_short["タイム"].idxmin(), "日付"]
    st.write(f"ベストタイム：**{seconds_to_competition_time(t)}**")
    st.write(f"更新日：{d}")
else:
    st.write("データなし")

st.subheader("ベストタイム（長水路）")
if not best_long.empty:
    t = best_long["タイム"].min()
    d = best_long.loc[best_long["タイム"].idxmin(), "日付"]
    st.write(f"ベストタイム：**{seconds_to_competition_time(t)}**")
    st.write(f"更新日：{d}")
else:
    st.write("データなし")
