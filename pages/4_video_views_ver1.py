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

# 處理頻道觀看的計算
def video_views(start_date_df, end_date_df):
    if start_date_df.empty:
        print("No data found.")
        exit()

    if end_date_df.empty:
        print("No data found.")
        exit()

     #篩選日期
    start_date_df['insert_date'] = pd.to_datetime(start_date_df['insert_date']).dt.date
    end_date_df['insert_date'] = pd.to_datetime(end_date_df['insert_date']).dt.date
    start_df = start_date_df
    end_df = end_date_df

    # 合并資料
    merged = pd.merge(
    end_df,
    start_df,
    on="video_id",
    how = "left",
    suffixes=("", "_start")
    )

    # 計算觀看數
    merged["video_view_count_start"] = merged["video_view_count_start"].fillna(0)
    merged["views"] = merged["video_view_count"] - merged["video_view_count_start"]

    result = merged[[
    'published_date',
    'channel_id',
    'channel_name',
    'video_id',
    'video_title',
    'kind',
    'video_thumbnails',
    'views'
    ]].sort_values(by="views", ascending=False)

    # # 重命名
    # result = result.rename(columns={
    # 'subscribers_count_end': 'subscribers',
    # 'channel_name_end': 'channel_name',
    # 'category_end': 'category'})

    return(result)

start_time = time.time()

# Initialization
# 初次執行時，設定 session_state 的日期預設值

if "P4_custom_date_range" not in st.session_state:
    st.session_state['P4_custom_date_range'] = (yesterday, yesterday)

if 'P4_custom_date_range_input' not in st.session_state:
    st.session_state['P4_custom_date_range_input'] = st.session_state['P4_custom_date_range']

# Radio 選擇日期範圍
option = st.radio(
    "選擇日期區間：",
    ["自訂", "近7天", "近30天"],
    horizontal=True
)

# 根據選擇更新日期
if option == "近7天":
    current_start = yesterday - timedelta(days=6)
    current_end = yesterday
    st.session_state['P4_default_date_range'] = (yesterday - timedelta(days=6), yesterday)

elif option == "近30天":
    current_start = yesterday - timedelta(days=29)
    current_end = yesterday
    st.session_state['P4_default_date_range'] = (yesterday - timedelta(days=29), yesterday)

# 如果是自訂，顯示 date_input
elif option == "自訂":
    st.session_state['P4_default_date_range'] = None
    current_start, current_end = st.session_state['P4_custom_date_range']

    # date_input
    date_query = st.date_input(
        "請選擇日期：",
        value=(current_start, current_end),
        min_value=min_date,
        max_value=yesterday,
        format="YYYY-MM-DD",
        key="P4_custom_date_range_input"
    )

    # 除錯處理: 日期少 and 順序錯誤
    if isinstance(date_query, tuple) and len(date_query) == 2:
        start_date, end_date = date_query
        if start_date > end_date:
            st.error("開始日期不能晚於結束日期！")
            start_date, end_date = end_date, start_date
        st.session_state['P4_custom_date_range'] = (start_date, end_date)
    else:
        st.error("請選擇兩個日期。")
        st.stop()

# 寫出選擇的日期
if st.session_state['P4_default_date_range'] == None:
    start_date, end_date = st.session_state['P4_custom_date_range']
else:
    start_date, end_date = st.session_state['P4_default_date_range']

P4date_range_str = f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
st.write("你選擇的日期區間是：", P4date_range_str, f", 共 {(end_date - start_date).days + 1} 天")

st.markdown("<br>", unsafe_allow_html=True)

# 資料庫查詢query (頻道名稱)
query = f"""
SELECT DISTINCT `channel_id`, `channel_name` 
FROM `yt_channel_statistics`.`channel_data` 
WHERE `date` = "{end_date.strftime('%Y-%m-%d')}" 
AND `category` <> "Unknown category";
"""
  
channel_df = SQL.query_data('yt_channel_statistics', query)
channel_option = ['全頻道'] + channel_df['channel_name'].tolist()
name_to_id = dict(zip(channel_df['channel_name'], channel_df['channel_id']))
name_to_id['全頻道'] = 'ALL'   # 標記為全部

if 'P4_channel_select' not in st.session_state:
    st.session_state['P4_channel_select'] = channel_option[0]

col1, col2, col3 = st.columns(3)

# 選擇類別  
with col1:
    category_options = ["全部類別", "綜合新聞類", "社會蒐奇類", "生活財經類", "健康類", "娛樂類", "戲劇類"]

    default_index = 0

    if 'P4_category_select' not in st.session_state:
        st.session_state['P4_category_select'] = None

    if 'P4_category_select' in st.session_state and st.session_state.P4_category_select in category_options:
        default_index = category_options.index(st.session_state.P4_category_select)
    else: 
        default_index = 0

    category_select = st.selectbox("請選擇頻道類別：", category_options, index=default_index)

    st.session_state['P4_category_select'] = category_select

# 選擇頻道
with col2:
    P4_channel_select = st.selectbox("請選擇頻道：", channel_option, key="P4_channel_select")

with col3:
    kind_options = ["全部影片類型", "shorts", "videos", "streams"]
    if 'P4_kind_select' not in st.session_state:
        st.session_state['P4_kind_select'] = kind_options[0]
    P4_kind_select = st.selectbox("請選擇影片類型：", kind_options, key="P4_kind_select")

# 資料庫查詢query
start_date_query = f"""
SELECT 
    DATE(`insert_datetime`) AS insert_date,
    video_id,
    video_view_count

FROM 
    `yt_channel_statistics`.`video_data`
WHERE 
    DATE(`insert_datetime`) = '{start_date.strftime('%Y-%m-%d')}' 
AND member_video = 0;
"""

end_date_query = f"""
SELECT 
    DATE(`insert_datetime`) AS insert_date,
    DATE(`taiwan_published_datetime`) AS published_date,
    channel_id,
    channel_name,
    video_id,
    video_title,
    kind,
    video_thumbnails,
    video_view_count

FROM 
    `yt_channel_statistics`.`video_data`
WHERE 
    DATE(`insert_datetime`) = DATE_ADD('{end_date.strftime('%Y-%m-%d')}', INTERVAL 1 DAY)
AND member_video = 0;
"""

with st.spinner("請稍等..."):
    start_date_df = SQL.query_data('yt_channel_statistics', start_date_query)
    end_date_df = SQL.query_data('yt_channel_statistics', end_date_query)
    df = video_views(start_date_df, end_date_df)

if P4_channel_select == '全頻道':
    df = df.copy()  # 全選
else:
    target_id = name_to_id[P4_channel_select]           # 拿到對應的 channel_id
    df = df[df['channel_id'] == target_id]

df.insert(0, 'rank', df['views'].rank(ascending=False, method='dense').astype(int))

@st.cache_data
# 下載按鈕
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

csv = convert_df(df)
if st.download_button("下載完整數據", csv, f"影片流量排行_{today_str}.csv", mime='text/csv'):
    st.toast("✔️ 已完成下載!")

# 轉換成千分位數
def format_num(num):
    if pd.isna(num):
        return "0"
    num = float(num)
    return f"{num / 10000:,.2f} 萬"

# st.dataframe(df)

# 顯示每一筆資料，也不寫color inline
for index, row in df.head(10).iterrows():
    viewers_formatted = format_num(row['views'])

    st.markdown(
    f"""
    <div style="
        border: 2px solid #ADD8E6;
        border-radius: 8px;
        padding: 12px 10px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;           /* 關鍵改這行 */
        min-height: 88px;
        background-color: #121212;
        color: white;
        gap: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    ">
        <!-- Rank --）-->
        <div style="
            width: 40px;
            flex-shrink: 0;
            display: grid;
            place-items: center;
            height: 100%;                  /* 強制跟整行一樣高 */
        ">
            <div style="
                font-size: 20px;
                font-weight: 900;
                line-height: 1;            /* 關鍵1：行高鎖死為 1 */
                margin: 0;
                padding: 0;
                text-align: center;
            ">
                {row['rank']}
            </div>
        </div>
        <!-- Thumbnail -->
        <div style="display: grid; place-items: center; flex-shrink: 0;">
            <img src="{row['video_thumbnails']}" style="width:128px; height:72px; object-fit:cover; object-position:center; border-radius:6px;">
        </div>
        <!-- 垂直線1 -->
        <div style="width:2px; background:#ADD8E6; align-self: stretch;"></div>
        <!-- 標題資訊區 -->
        <div style="flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: center;">
            <a href="https://www.youtube.com/watch?v={row['video_id']}" 
                target="_blank" 
                style="text-decoration: none; color: inherit;">
                <h4 style="margin:0 0 6px 0; font-size:18px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                    {row['video_title']}
                </h4>
            </a>
            <a href="https://www.youtube.com/channel/{row['channel_id']}" 
                target="_blank" 
                style="text-decoration: none; color: inherit;">
                <p style="margin:0; font-size:15px; opacity:0.9;"><strong>頻道：</strong>{row['channel_name']}</p>
            </a>
            <p style="margin:0; font-size:15px; opacity:0.9;"><strong>發佈日期：</strong>{row['published_date']}</p>
        </div>
        <!-- 垂直線2 -->
        <div style="width:2px; background:#ADD8E6; align-self: stretch;"></div>
        <!-- 觀看數 -->
        <div style="display: grid; place-items: center; width: 126px; flex-shrink: 0;">
            <h4 style="margin:0; font-size:24px; font-weight:bold;">{viewers_formatted}</h4>
        </div>
    </div>
    """,
    unsafe_allow_html=True
    )





end_time = time.time()  # 记录结束时间
elapsed_time = end_time - start_time
st.session_state['elapsed_time'] = round(elapsed_time, 2)
st.text(f"\n運行時間: {st.session_state['elapsed_time']} 秒")