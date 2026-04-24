import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
import os
import re
import math

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
# タイトル
# ---------------------------------------------------------
st.title("HONOKA Swimming Record Dashboard")

# ---------------------------------------------------------
# 列名を正規化
# ---------------------------------------------------------
def normalize_columns(df):
    new_cols = []
    for col in df.columns:
        c = str(col)
        c = c.replace(" ", "").replace("　", "")
        c = c.replace("ヒヅケ", "日付")
        new_cols.append(c)
    df.columns = new_cols
    return df

# ---------------------------------------------------------
# 競泳表記 → 秒（内部計算用）
# ---------------------------------------------------------
def time_to_seconds(t):
    if t is None:
        return None

    # pandas Timestamp（01:41.11 がこれになることがある）
    if isinstance(t, pd.Timestamp):
        return t.hour * 3600 + t.minute * 60 + t.second + t.microsecond / 1e6

    # Excel の日付シリアル（例：45710）
    if isinstance(t, (int, float)) and t > 30000:
        return None

    # Excel の時刻シリアル（例：1.17E-3）
    if isinstance(t, (int, float)):
        if 0 < t < 1:
            return t * 86400
        else:
            return float(t)

    s = str(t).strip()
    s = s.replace("：", ":")

    # 競泳表記（4'39"09）
    m = re.match(r"(\d+)'(\d+)[\"”]?(\d+)", s)
    if m:
        minutes = int(m.group(1))
        seconds = int(m.group(2))
        ms = int(m.group(3))
        return minutes * 60 + seconds + ms / 100

    # 分:秒.ミリ秒（01:41.11）
    if ":" in s:
        try:
            m, sec = s.split(":")
            return int(m) * 60 + float(sec)
        except:
            pass

    # 秒のみ
    try:
        return float(s)
    except:
        return None

# ---------------------------------------------------------
# 秒 → 競泳表記（表示用）
# ---------------------------------------------------------
def seconds_to_swim_format(sec):
    if sec is None or (isinstance(sec, float) and math.isnan(sec)):
        return "―"
    m = int(sec // 60)
    s = sec % 60
    return f"{m}'{s:05.2f}"

# ---------------------------------------------------------
# Excel 読み込み
# ---------------------------------------------------------
file_path = "穂果記録.xlsx"

events = ["フリー", "バッタ", "ブレ", "バック", "メドレー"]
event = st.selectbox("種目を選択してください", events)

sheet_name = event

data = pd.read_excel(file_path, sheet_name=sheet_name)

# 最初の6列だけ使う（列ズレ対策）
data = data.iloc[:, :6]

data.columns = ["日付", "学年", "距離", "長水路or短水路", "タイム", "会場"]
data = normalize_columns(data)

data["タイム"] = data["タイム"].apply(time_to_seconds)

data["距離"] = pd.to_numeric(data["距離"], errors="coerce")
data = data.dropna(subset=["距離"])
data["距離"] = data["距離"].astype(int)

# ---------------------------------------------------------
# 距離選択（ブレだけ 50/100）
# ---------------------------------------------------------
if event == "メドレー":
    distance_list = [100, 200, 400]
elif event == "ブレ":
    distance_list = [50, 100, 200, 400]
else:
    distance_list = sorted(data["距離"].unique())

distance = st.selectbox("距離を選択してください", distance_list)

# ---------------------------------------------------------
# 長水路／短水路／全記録
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

# NaN のタイムは除外
filtered = filtered[filtered["タイム"].notna()]

if filtered.empty:
    st.error(f"{event} の {distance}m（{course}）のデータがありません")
    st.stop()

# ---------------------------------------------------------
# グラフ描画（内部は秒）
# ---------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(filtered["日付"], filtered["タイム"], color="gray", linewidth=2)

color_map = {"長水路": "tab:blue", "短水路": "tab:red"}

for c in ["長水路", "短水路"]:
    df_c = filtered[filtered["長水路or短水路"] == c]
    if not df_c.empty:
        ax.scatter(df_c["日付"], df_c["タイム"], color=color_map[c], label=c, s=60)

ax.set_xlabel("日付")
ax.set_ylabel("タイム")
ax.set_title(f"{event} {distance}m（{course}）の記録推移")
ax.grid(True)

if course == "全記録":
    ax.legend()

# Y軸を競泳表記に変換
yticks = ax.get_yticks()
ax.set_yticklabels([seconds_to_swim_format(t) for t in yticks])

st.pyplot(fig)

# ---------------------------------------------------------
# 最新記録（表示は競泳表記）
# ---------------------------------------------------------
latest = filtered.iloc[-1]

st.subheader("最新の記録")
st.write(f"日付：{latest['日付']}")
st.write(f"タイム：{seconds_to_swim_format(latest['タイム'])}")
st.write(f"会場：{latest['会場']}")

# ---------------------------------------------------------
# ベストタイム（表示は競泳表記）
# ---------------------------------------------------------
best_short = data[(data["距離"] == distance) & (data["長水路or短水路"] == "短水路") & (data["タイム"].notna())]
best_long  = data[(data["距離"] == distance) & (data["長水路or短水路"] == "長水路") & (data["タイム"].notna())]

st.subheader("ベストタイム（短水路）")
if not best_short.empty:
    t = best_short["タイム"].min()
    d = best_short.loc[best_short["タイム"].idxmin(), "日付"]
    st.write(f"ベストタイム：**{seconds_to_swim_format(t)}**")
    st.write(f"更新日：{d}")
else:
    st.write("データなし")

st.subheader("ベストタイム（長水路）")
if not best_long.empty:
    t = best_long["タイム"].min()
    d = best_long.loc[best_long["タイム"].idxmin(), "日付"]
    st.write(f"ベストタイム：**{seconds_to_swim_format(t)}**")
    st.write(f"更新日：{d}")
else:
    st.write("データなし")

st.subheader("新しい記録を追加")

with st.form("add_record_form"):
    f_event = st.selectbox("種目", ["フリー", "バッタ", "ブレ", "バック", "メドレー"])
    f_date = st.date_input("日付")
    f_grade = st.text_input("学年（例：小5）")
    f_distance = st.selectbox("距離", [50, 100])
    f_course = st.selectbox("長水路 or 短水路", ["長水路", "短水路"])
    f_time = st.text_input("タイム（例：47.55 または 1'41\"11）")
    f_place = st.text_input("会場")

    submitted = st.form_submit_button("追加")

if submitted:
    sec = time_to_seconds(f_time)

    new_row = pd.DataFrame({
        "日付": [pd.to_datetime(f_date)],
        "学年": [f_grade],
        "距離": [f_distance],
        "長水路or短水路": [f_course],
        "タイム": [sec],
        "会場": [f_place]
    })

    df = pd.read_excel(file_path, sheet_name=f_event)
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_excel(file_path, sheet_name=f_event, index=False)

    st.success("記録を追加しました！")
    st.rerun()
