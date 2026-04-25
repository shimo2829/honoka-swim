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

    # 既存シートがあれば削除
    if sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        wb.remove(ws)

    # 新しいシートを作成
    ws = wb.create_sheet(sheet_name)

    # DataFrame を書き込み
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)

    wb.save(excel_path)

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
# 種目ごとのヘッダー色設定
# ---------------------------------------------------------
event_colors = {
    "フリー": "#1E90FF",
    "バッタ": "#FF8C00",
    "ブレ":   "#32CD32",
    "バック": "#8A2BE2",
    "メドレー": "#DC143C"
}

header_color = event_colors.get(event, "#000000")

# ---------------------------------------------------------
# 固定ヘッダー
# ---------------------------------------------------------
st.markdown(
    f"""
    <div style="
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        background-color: {header_color};
        padding: 18px 20px;
        font-size: 36px;
        font-weight: bold;
        color: white;
        text-align: center;
        border-bottom: 3px solid #ddd;
        z-index: 9999;
    ">
        {event}
    </div>

    <style>
        .block-container {{
            padding-top: 110px;
        }}
    </style>
    """,
    unsafe_allow_html=True
)

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

# ---------------------------------------------------------
# 新しい記録を追加
# ---------------------------------------------------------
st.subheader("新しい記録を追加")

with st.form("add_record_form"):
    new_date = st.date_input("日付")
    new_grade = st.selectbox("学年", ["小6","中1","中2","中3"])
    new_distance = st.selectbox("距離", distance_list)
    new_course = st.selectbox("長水路 or 短水路", ["長水路", "短水路"])
    new_time_str = st.text_input(
    "タイム（入力方法）\n\n"
    "【60秒未満】例：58秒11 → 58.11\n"
    "【60秒以上】例：1分41秒58 → 1'41\"58\n\n"
    "※ どちらの形式でも自動で変換されます"
)

    new_place = st.text_input("会場", value="菰野スイミング")

    submitted = st.form_submit_button("追加する")

if submitted:
    new_time_sec = time_to_seconds(new_time_str)

    if new_time_sec is None:
        st.error("タイムの形式が正しくありません")
    else:
        new_row = pd.DataFrame([{
            "日付": pd.to_datetime(new_date),
            "学年": new_grade,
            "距離": int(new_distance),
            "長水路or短水路": new_course,
            "タイム": new_time_sec,
            "会場": new_place
        }])

        try:
            book = pd.read_excel(local_excel, sheet_name=sheet_name)
            book = normalize_columns(book)
            book = book.iloc[:, :6]
            book.columns = ["日付", "学年", "距離", "長水路or短水路", "タイム", "会場"]

            updated = pd.concat([book, new_row], ignore_index=True)

            save_sheet_without_deleting_others(local_excel, sheet_name, updated)

            update_excel_to_github(
                local_path=local_excel,
                repo=GITHUB_REPO,
                file_path=GITHUB_FILE_PATH,
                token=GITHUB_TOKEN,
                commit_message=f"Add record: {event} {distance}m"
            )

            st.success("記録を追加しました！（GitHub にも反映済み）")
            st.rerun()

        except Exception as e:
            st.error(f"Excel 書き込みエラー: {e}")

# ---------------------------------------------------------
# 記録の修正・削除
# ---------------------------------------------------------
st.subheader("記録の修正・削除")

edit_df = filtered.copy().reset_index(drop=True)
edit_df["行番号"] = edit_df.index

st.dataframe(edit_df[["行番号", "日付", "学年", "距離", "長水路or短水路", "タイム", "会場"]])

target_index = st.number_input("修正・削除する行番号を入力", min_value=0, max_value=len(edit_df)-1, step=1)

target_row = edit_df.iloc[target_index]

st.write("選択中の記録：")
st.write(target_row)

# -------------------------
# 修正フォーム
# -------------------------
with st.form("edit_form"):
    e_date = st.date_input("日付（修正）", value=target_row["日付"])
    e_grade = st.selectbox("学年（修正）", ["小1","小2","小3","小4","小5","小6","中1","中2","中3"],
                           index=["小1","小2","小3","小4","小5","小6","中1","中2","中3"].index(target_row["学年"]))
    e_distance = st.number_input("距離（修正）", value=int(target_row["距離"]))
    e_course = st.selectbox("長水路 or 短水路（修正）", ["長水路", "短水路"],
                            index=0 if target_row["長水路or短水路"]=="長水路" else 1)
    e_time_str = st.text_input("タイム（修正）", value=seconds_to_swim_format(target_row["タイム"]))
    e_place = st.text_input("会場（修正）", value=target_row["会場"])

    edit_submitted = st.form_submit_button("修正する")

# -------------------------
# 修正処理
# -------------------------
if edit_submitted:
    new_time_sec = time_to_seconds(e_time_str)

    if new_time_sec is None:
        st.error("タイムの形式が正しくありません")
    else:
        book = pd.read_excel(local_excel, sheet_name=sheet_name)
        book = normalize_columns(book)
        book = book.iloc[:, :6]
        book.columns = ["日付", "学年", "距離", "長水路or短水路", "タイム", "会場"]

        book.loc[target_row.name] = [
            pd.to_datetime(e_date),
            e_grade,
            int(e_distance),
            e_course,
            new_time_sec,
            e_place
        ]

        save_sheet_without_deleting_others(local_excel, sheet_name, book)

        update_excel_to_github(
            local_path=local_excel,
            repo=GITHUB_REPO,
            file_path=GITHUB_FILE_PATH,
            token=GITHUB_TOKEN,
            commit_message=f"Edit record: {event} {distance}m"
        )

        st.success("修正しました！（GitHub にも反映済み）")
        st.rerun()

# -------------------------
# 削除ボタン
# -------------------------
if st.button("この行を削除する"):
    book = pd.read_excel(local_excel, sheet_name=sheet_name)
    book = normalize_columns(book)
    book = book.iloc[:, :6]
    book.columns = ["日付", "学年", "距離", "長水路or短水路", "タイム", "会場"]

    book = book.drop(target_row.name)

    save_sheet_without_deleting_others(local_excel, sheet_name, book)

    update_excel_to_github(
        local_path=local_excel,
        repo=GITHUB_REPO,
        file_path=GITHUB_FILE_PATH,
        token=GITHUB_TOKEN,
        commit_message=f"Delete record: {event} {distance}m"
    )

    st.success("削除しました！（GitHub にも反映済み）")
    st.rerun()
