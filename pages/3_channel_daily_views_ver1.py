import streamlit as st
import pandas as pd
from io import BytesIO
from myfun.sql_connection import SQL_connection
from myfun.config_read import ConfigRead
from datetime import datetime, timedelta, date
import os, time
from myfun.discord import Discord

today = datetime.today()
yesterday = (datetime.today() - timedelta(days=1)).date()
fun_name = os.path.basename(__file__)
config = ConfigRead("id.config")
discord = Discord(config)
SQL = SQL_connection(config, discord)
today_str = today.strftime('%Y-%m-%d')
last30days = (datetime.today() - timedelta(days=29)).date()
last30days_str = last30days.strftime('%Y-%m-%d')
yesterday_str = (today- timedelta(days=1)).strftime('%Y-%m-%d')
min_date = datetime(2025, 1, 1).date()

start_time = time.time()

# Initialization
# 初次執行時，設定 session_state 的日期預設值
if "P3_custom_date_range" not in st.session_state:
    st.session_state['P3_custom_date_range'] = (yesterday - timedelta(days=6), yesterday)

# if 'P3_custom_date_range_input' not in st.session_state:
#     st.session_state['P3_custom_date_range_input'] = st.session_state['P3_custom_date_range']

# Radio 選擇日期範圍
option = st.radio(
    "選擇日期區間：",
    [ "自訂", "近30天"],
    horizontal=True
)

# 根據選擇更新日期
if option == "近30天":
    current_start = yesterday - timedelta(days=29)
    current_end = yesterday
    st.session_state['P3_default_date_range'] = (yesterday - timedelta(days=29), yesterday)

# 如果是自訂，顯示 date_input
elif option == "自訂":
    st.session_state['P3_default_date_range'] = None
    current_start, current_end = st.session_state['P3_custom_date_range']

    # date_input
    date_query = st.date_input(
        "請選擇日期：",
        value=(current_start, current_end),
        min_value=min_date,
        max_value=yesterday,
        format="YYYY-MM-DD",
        key="P3_custom_date_range_input"
    )

    # 除錯處理: 日期少 and 順序錯誤
    if isinstance(date_query, tuple) and len(date_query) == 2:
        start_date, end_date = date_query
        if start_date > end_date:
            st.error("開始日期不能晚於結束日期！")
            start_date, end_date = end_date, start_date
    else:
        st.error("請選擇兩個日期。")
        st.stop()

    st.session_state['P3_custom_date_range'] = (start_date, end_date)

# 寫出選擇的日期
if st.session_state['P3_default_date_range'] == None:
    start_date, end_date = st.session_state['P3_custom_date_range']
else:
    start_date, end_date = st.session_state['P3_default_date_range']

P3date_range_str = f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
st.write("您選擇的日期區間是：", P3date_range_str, f", 共 {(end_date - start_date).days + 1} 天")

st.markdown("<br>", unsafe_allow_html=True)

# 資料庫查詢query (頻道名稱)
query = f"""
SELECT DISTINCT `channel_id`, `channel_name` 
FROM `yt_channel_statistics`.`channel_data` 
WHERE `date` = "{end_date.strftime('%Y-%m-%d')}" 
AND `category` <> "Unknown category";
"""

channel_df = SQL.query_data('yt_channel_statistics', query)
channel_option = channel_df['channel_name'].tolist()

default_index = 0

if 'P3_channel_select' not in st.session_state:
    st.session_state['P3_channel_select'] = None

if 'P3_channel_select' in st.session_state and st.session_state.P3_channel_select in channel_option:
    default_index = channel_option.index(st.session_state.P3_channel_select)

else: 
    default_index = channel_option.index('中天新聞')

P3_channel_select = st.selectbox("請選擇頻道：", channel_option, index=default_index, key="P3_channel_select_input")

st.session_state['P3_channel_select'] = P3_channel_select

# st.session_state['P3_channel_select'] = P3_channel_select

# 資料庫查詢query
query = f"""
SELECT 
    a.*,
    (b.views_count - a.views_count) AS 'views',
    (b.videos_count - a.videos_count) AS 'videos'

FROM 
    `yt_channel_statistics`.`channel_data` a
JOIN 
    `yt_channel_statistics`.`channel_data` b
    ON a.channel_id = b.channel_id
    AND b.date = DATE_ADD(a.date, INTERVAL 1 DAY)
WHERE 
    a.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
    AND a.channel_name  = '{P3_channel_select}'
    AND HOUR(a.time) = 5
    AND HOUR(b.time) = 5
ORDER BY 'views' DESC;
"""

df = SQL.query_data('yt_channel_statistics', query)

# st.dataframe(df)
df = df.drop(columns=['iD', 'channel_id', 'time', 'views_count', 'videos_count'])
df = df.rename(columns={'subscribers_count': 'subscribers'})
df['videos'] = pd.to_numeric(df['videos'], errors='coerce')
df['views'] = pd.to_numeric(df['views'], errors='coerce')
df['subscribers'] = pd.to_numeric(df['subscribers'], errors='coerce')
df.sort_values('date', ascending=True, inplace=True)

# 下載按鈕
@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

csv = convert_df(df)
if st.download_button("下載完整數據", csv, f"頻道流量排行_{P3_channel_select}_{today_str}.csv", mime='text/csv'):
    st.toast("✔️ 已完成下載!")

# 轉換成千分位數
def format_num(num):
    if pd.isna(num):
        return "0"
    return f"{int(num):,}"  

# st.dataframe(df)

# 呈現結果
st.markdown(
    """
    <style>
    [data-theme="dark"] div {
        color: white !important;
    }
    /* light mode 下用黑色字 */
    [data-theme="light"] div {
        color: black !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 標題列，不指定color，讓css控制
st.markdown("""
<div style="display: flex; font-weight: bold; font-size: 18px; padding: 10px 0; border-bottom: 2px solid #ADD8E6; margin-right: -70px; padding-right: 50px;">
    <div style="flex-basis: 150px; flex-shrink: 0; text-align: left;">日期</div>
    <div style="flex-basis: 150px; flex-shrink: 0; text-align: right;">訂閱數</div>
    <div style="flex-basis: 150px; flex-shrink: 0; text-align: right;">觀看數</div>
    <div style="flex-basis: 150px; flex-shrink: 0; text-align: right;">影片數</div>
</div>
""", unsafe_allow_html=True)

# 顯示每一筆資料，也不寫color inline
for index, row in df.iterrows():
    subs_formatted = format_num(row['subscribers'])
    viewers_formatted = format_num(row['views'])
    videos_formatted = format_num(row['videos'])

    viewers_color = "red" if row['views'] < 0 else "inherit"
    videos_color  = "red" if row['videos'] < 0 else "inherit"

    st.markdown(
        f"""
        <div style="display: flex; align-items: center; min-height: 60px; padding: 10px 0; border-bottom: 1px solid #eee; margin-right: -70px; padding-right: 50px;">
            <div style="flex-basis: 150px; flex-shrink: 0; text-align: left;">{row['date']}</div>
            <div style="flex-basis: 150px; flex-shrink: 0; text-align: right;">{subs_formatted}</div>
            <div style="flex-basis: 150px; flex-shrink: 0; text-align: right; color:{viewers_color};">{viewers_formatted}</div>
            <div style="flex-basis: 150px; flex-shrink: 0; text-align: right; color:{videos_color};">{videos_formatted}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


end_time = time.time()  # 记录结束时间
elapsed_time = end_time - start_time
st.session_state['elapsed_time'] = round(elapsed_time, 2)
st.text(f"\n運行時間: {st.session_state['elapsed_time']} 秒")