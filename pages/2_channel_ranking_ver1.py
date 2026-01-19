import streamlit as st
import pandas as pd
from io import BytesIO
from myfun.sql_connection import SQL_connection
from myfun.config_read import ConfigRead
from datetime import datetime, timedelta, date
import os
from myfun.discord import Discord

today = datetime.today()
yesterday = (datetime.today() - timedelta(days=1)).date()
fun_name = os.path.basename(__file__)
config = ConfigRead("id.config")
discord = Discord(config)
SQL = SQL_connection(config, discord)
today_str = today.strftime('%Y-%m-%d')
last30days = (today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=29)).strftime('%Y-%m-%d %H:%M:%S')
yesterday_str = (today- timedelta(days=1)).strftime('%Y-%m-%d')
min_date = datetime(2025, 1, 1).date()

# Initialization
# 初次執行時，設定 session_state 的日期預設值

if "date_range" not in st.session_state:
    st.session_state.date_range = (yesterday, yesterday)

if 'custom_date_range_input' not in st.session_state:
    st.session_state['custom_date_range_input'] = (yesterday, yesterday)



# Radio 選擇日期範圍
option = st.radio(
    "選擇日期區間：",
    ["自訂", "近7天", "近30天"],
    horizontal=True
)

# 根據選擇更新日期
if option == "近7天":
    st.session_state.date_range = (yesterday - timedelta(days=6), yesterday)
elif option == "近30天":
    st.session_state.date_range = (yesterday - timedelta(days=29), yesterday)

# 如果是自訂，顯示 date_input
elif option == "自訂":
    current_start, current_end = st.session_state.date_range
    date_query = st.date_input(
        "請選擇日期：",
        value=(current_start, current_end),
        min_value=min_date,
        max_value=yesterday,
        format="YYYY-MM-DD",
        key="custom_date_range_input"
    )

    if isinstance(date_query, tuple) and len(date_query) == 2:
        start_date, end_date = date_query
        if start_date > end_date:
            st.error("開始日期不能晚於結束日期！")
            start_date, end_date = end_date, start_date
        st.session_state.date_range = (start_date, end_date)
    else:
        st.error("請選擇兩個日期。")
        st.stop()


start_date, end_date = st.session_state.date_range
date_range_str = f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
st.write("你選擇的日期區間是：", date_range_str, f", 共 {(end_date - start_date).days + 1} 天")

st.markdown("<br>", unsafe_allow_html=True)


# 選擇類別
category_options = ["全部類別", "綜合新聞類", "社會蒐奇類", "生活財經類", "健康類", "娛樂類", "戲劇類"]

default_index = 0

if 'category_select' not in st.session_state:
    st.session_state['category_select'] = None

if 'category_select' in st.session_state and st.session_state.category_select in category_options:
    default_index = category_options.index(st.session_state.category_select)
else: 
    default_index = 0

category_select = st.selectbox("請選擇頻道類別：", category_options, index=default_index)

st.session_state['category_select'] = category_select

# 資料庫查詢query
query = f"""
SELECT 
    a.*,
    (a.views_count - b.views_count) AS 'views',
    (a.videos_count - b.videos_count) AS 'videos'

FROM 
    `yt_channel_statistics`.`views_and_subscribers` a
JOIN 
    `yt_channel_statistics`.`views_and_subscribers` b
    ON a.channel_id = b.channel_id
WHERE 
    a.date = '{end_date.strftime('%Y-%m-%d')}'   
    AND b.date = '{start_date.strftime('%Y-%m-%d')}' - INTERVAL 1 DAY 
    AND a.category <> 'Unknown category'
ORDER BY 'views' DESC;
"""
  
df = SQL.query_data('yt_channel_statistics', query)

# 篩選負數資料
if (df['views'] < 0).any():
    negative = df[df['views'] < 0]
    channel_ids = negative["channel_id"].tolist()
    channel_ids_str = ', '.join([f"'{name}'" for name in channel_ids])

    query_negative_view = f"""
    SELECT 
        a.*,
        (a.views_count - b.views_count) AS 'negative_views'

    FROM 
        `yt_channel_statistics`.`views_and_subscribers` a
    JOIN 
        `yt_channel_statistics`.`views_and_subscribers` b
        ON a.channel_id = b.channel_id
        AND a.date = DATE_ADD(b.date, INTERVAL 1 DAY)
    WHERE 
        a.channel_id IN ({channel_ids_str})
        AND a.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND'{end_date.strftime('%Y-%m-%d')}' 
        AND (a.views_count - b.views_count) < 0
    ORDER BY 'negative_views' DESC;
    """

    df_update = SQL.query_data('yt_channel_statistics', query_negative_view)

    # 計算調整後的views
    negative_sums = df_update.groupby("channel_id")["negative_views"].sum().reset_index()
    negative_updated = negative.merge(negative_sums, on="channel_id", how="left")
    negative_updated["negative_views"] = negative_updated["negative_views"].fillna(0)
    negative_updated["adjusted_views"] = abs(negative_updated["negative_views"]) + negative_updated["views"]

    # 調整後的views插入原本的df
    target_col = "views"
    update_map = negative_updated.set_index("channel_id")["adjusted_views"]
    df[target_col] = df["channel_id"].map(update_map).combine_first(df[target_col])

# 根據類別篩選
if category_select == "全部類別":
    df = df
elif category_select == "綜合新聞類":
    df = df[df['category'].isin(['綜合新聞類', '政論類', '國際新聞類'])]
elif category_select == "社會蒐奇類":
    df = df[df['category'] == '社會蒐奇類']
elif category_select == "生活財經類":
    df = df[df['category'] == '生活財經類']
elif category_select == "健康類":
    df = df[df['category'] == '健康類']
elif category_select == "娛樂類":
    df = df[df['category'].isin(['娛樂節目', '娛樂新聞類'])]
elif category_select == "戲劇類":
    df = df[df['category'] == '戲劇類']

df = df.drop(columns=['iD', 'channel_id', 'date', 'time', 'views_count', 'videos_count'])
df = df.rename(columns={'subscribers_count': 'subscribers'})
df['videos'] = pd.to_numeric(df['videos'], errors='coerce')
df['views'] = pd.to_numeric(df['views'], errors='coerce')
df['subscribers'] = pd.to_numeric(df['subscribers'], errors='coerce')
df.sort_values('views', ascending=False, inplace=True)
df.insert(0, 'rank', df['views'].rank(ascending=False, method='dense').astype(int))


# 下載按鈕
@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

csv = convert_df(df)
if st.download_button("下載完整排行", csv, f"頻道流量排行_{st.session_state['category_select']}_{today_str}.csv", mime='text/csv'):
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
    <div style="flex-basis: 60px; flex-shrink: 0; text-align: center;">排名</div>
    <div style="flex-basis: 250px; flex-shrink: 0;">頻道名稱</div>
    <div style="flex-basis: 150px; flex-shrink: 0; text-align: right;">訂閱數</div>
    <div style="flex-basis: 150px; flex-shrink: 0; text-align: right;">觀看數</div>
    <div style="flex-basis: 150px; flex-shrink: 0; text-align: right;">影片數</div>
</div>
""", unsafe_allow_html=True)

# 顯示每一筆資料，也不寫color inline
for index, row in df.head(100).iterrows():
    subs_formatted = format_num(row['subscribers'])
    viewers_formatted = format_num(row['views'])
    videos_formatted = format_num(row['videos'])

    st.markdown(
        f"""
        <div style="display: flex; align-items: center; min-height: 60px; padding: 10px 0; border-bottom: 1px solid #eee; margin-right: -70px; padding-right: 50px;">
            <div style="flex-basis: 60px; flex-shrink: 0; text-align: center;">{row['rank']}</div>
            <div style="flex-basis: 250px; flex-shrink: 0;">{row['channel_name']}</div>
            <div style="flex-basis: 150px; flex-shrink: 0; text-align: right;">{subs_formatted}</div>
            <div style="flex-basis: 150px; flex-shrink: 0; text-align: right;">{viewers_formatted}</div>
            <div style="flex-basis: 150px; flex-shrink: 0; text-align: right;">{videos_formatted}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
