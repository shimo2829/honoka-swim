import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
import os
import re
import math
import base64
import requests
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# ---------------------------------------------------------
# GitHub secrets 読み込み
# ---------------------------------------------------------
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]
GITHUB_FILE_PATH = st.secrets["GITHUB_FILE_PATH"]

# ---------------------------------------------------------
# GitHub から Excel を取得
# ---------------------------------------------------------
def download_excel_from_github(repo, file_path, token, local_path="temp.xlsx"):
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {"Authorization": f"token {token}"}

    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = base64.b64decode(res.json()["content"])
        with open(local_path, "wb") as f:
            f.write(content)
        return local_path
    else:
        st.error("GitHub からファイルを取得できませんでした")
        return None

# ---------------------------------------------------------
# GitHub へ Excel をアップロード
# ---------------------------------------------------------
def update_excel_to_github(local_path, repo, file_path, token, commit_message="Update Excel"):
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"

    with open(local_path, "rb") as f:
        content = f.read()
    encoded = base64.b64encode(content).decode()

    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get("sha", None)

    data = {
        "message": commit_message,
        "content": encoded,
        "sha": sha
    }

    res = requests.put(url, json=data, headers={"Authorization": f"token {token}"})
    return res.status_code in [200, 201]

# ---------------------------------------------------------
# 他のシートを消さずに、指定シートだけ更新する関数
# ---------------------------------------------------------
def save_sheet_without_deleting_others(excel_path, sheet_name, df):
    wb = load_workbook(excel_path)

    if sheet_name in wb.sheetnames

# ---------------------------------------------------------
# 競泳表記 → 秒
# ---------------------------------------------------------
def time_to_seconds(t):
    if t is None:
        return None

    if isinstance(t, pd.Timestamp):
        return t.hour * 3600 + t.minute * 60 + t.second + t.microsecond / 1e6

    if isinstance(t, (int, float)) and t > 30000:
        return None

    if isinstance(t, (int, float)):
        if 0 < t < 1:
            return t * 86400
        else:
            return float(t)

    s = str(t).strip()
    s = s.replace("：", ":")

    m = re.match(r"(\d+)'(\d+)[\"”]?(\d+)", s)
    if m:
        minutes = int(m.group(1))
        seconds = int(m.group(2))
        ms = int(m.group(3))
        return minutes * 60 + seconds + ms / 100

    if ":" in s:
        try:
            m, sec = s.split(":")
            return int(m) * 60 + float(sec)
        except:
            pass

    try:
        return float(s)
    except:
        return None


# ---------------------------------------------------------
# 秒 → 競泳表記
# ---------------------------------------------------------
def seconds_to_swim_format(sec):
    if sec is None or (isinstance(sec, float) and math.isnan(sec)):
        return "―"
    m = int(sec // 60)
    s = sec % 60
    return f"{m}'{s:05.2f}"

# ---------------------------------------------------------
# GitHub から最新 Excel を取得
# ---------------------------------------------------------
local_excel = download_excel_from_github(GITHUB_REPO, GITHUB_FILE_PATH, GITHUB_TOKEN)

if local_excel is None:
    st.stop()

# ---------------------------------------------------------
# Excel 読み込み
# ---------------------------------------------------------
events = ["フリー", "バッタ", "ブレ", "バック", "メドレー"]
event = st.selectbox("種目を選択してください", events)

sheet_name = event

data = pd.read_excel(local_excel, sheet_name=sheet_name)
data = data.iloc[:, :6]
data.columns = ["日付", "学年", "距離", "長水路or短水路", "タイム", "会場"]
data = normalize_columns(data)

# タイム変換
data["タイム"] = data["タイム"].apply(time_to_seconds)

# 距離を数値化
data["距離"] = pd.to_numeric(data["距離"], errors="coerce")
data = data.dropna(subset=["距離"])
data["距離"] = data["距離"].astype(int)

# ---------------------------------------------------------
# 距離選択
# ---------------------------------------------------------
if event == "メドレー":
    distance_list = [200, 400]
elif event == "ブレ":
    distance_list = [50, 100]
else:
    distance_list = sorted(data["距離"].unique())

distance = st.selectbox("距離を選択してください", distance_list)

# ---------------------------------------------------------
# 長水路／短水路
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

filtered = filtered[filtered["タイム"].notna()]

if filtered.empty:
    st.error(f"{event} の {distance}m（{course}）のデータがありません")
    st.stop()

# ---------------------------------------------------------
# グラフ
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

yticks = ax.get_yticks()
ax.set_yticklabels([seconds_to_swim_format(t) for t in yticks])

st.pyplot(fig)

# ---------------------------------------------------------
# 最新記録
# ---------------------------------------------------------
latest = filtered.iloc[-1]

st.subheader("最新の記録")
st.write(f"日付：{latest['日付']}")
st.write(f"タイム：{seconds_to_swim_format(latest['タイム'])}")
st.write(f"会場：{latest['会場']}")

# ---------------------------------------------------------
# ベストタイム
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
