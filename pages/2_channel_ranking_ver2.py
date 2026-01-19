import streamlit as st
import pandas as pd
from io import BytesIO
from myfun.sql_connection import SQL_connection
from myfun.config_read import ConfigRead
from datetime import datetime, timedelta, date
import os, time, copy
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

start_time = time.time()

def query_save_to_db(conditions_list, start_time, data_size):
    """
    把 conditions + params 轉成完整可讀的 SQL 字串並印出來
    """
    query_sec = int(time.time() - start_time)
    Date_Time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 每個 %s 依序換成對應的值，加上單引號（因為都是字串）
    where_clause = conditions_list

    query = [(Date_Time, query_sec, where_clause, data_size, fun_name)]
    df = pd.DataFrame(query, columns=["Date_Time", "query_sec", "where_clause", "data_size", "fun_name"])
    SQL.insert_data(df, 'yt_channel_statistics', 'sp_UI_query', discord=False)

# 處理頻道觀看的計算
def channel_views(start_date_df, end_date_df):
    if start_date_df.empty:
        print("No data found.")
        exit()

    if end_date_df.empty:
        print("No data found.")
        exit()

     #篩選日期
    start_date_df['date'] = pd.to_datetime(start_date_df['date']).dt.date
    end_date_df['date'] = pd.to_datetime(end_date_df['date']).dt.date
    start_df =start_date_df
    end_df = end_date_df

    # 合并資料
    merged = pd.merge(
    end_df,
    start_df,
    on="channel_id",
    suffixes=("_end", "_start")
    )

    # 計算觀看數
    merged["views"] = merged["views_count_end"] - merged["views_count_start"]
    merged["videos"] = merged["videos_count_end"] - merged["videos_count_start"]

    result = merged[[
    "channel_id",
    "channel_name_end",
    "category_end",
    "subscribers_count_end",
    "views",
    "videos"
    ]].sort_values(by="views", ascending=False)

    # 重命名
    result = result.rename(columns={
    'subscribers_count_end': 'subscribers',
    'channel_name_end': 'channel_name',
    'category_end': 'category'})

    result.insert(0, 'rank', result['views'].rank(ascending=False, method='dense').astype(int))

    return(result)

# Initialization
# 初次執行時，設定 session_state 的日期預設值

if "P2_custom_date_range" not in st.session_state:
    st.session_state['P2_custom_date_range'] = (yesterday, yesterday)

if 'P2_custom_date_range_input' not in st.session_state:
    st.session_state['P2_custom_date_range_input'] = st.session_state['P2_custom_date_range']

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
    st.session_state['P2_default_date_range'] = (yesterday - timedelta(days=6), yesterday)

elif option == "近30天":
    current_start = yesterday - timedelta(days=29)
    current_end = yesterday
    st.session_state['P2_default_date_range'] = (yesterday - timedelta(days=29), yesterday)

# 如果是自訂，顯示 date_input
elif option == "自訂":
    st.session_state['P2_default_date_range'] = None
    current_start, current_end = st.session_state['P2_custom_date_range']

    # date_input
    date_query = st.date_input(
        "請選擇日期：",
        value=(current_start, current_end),
        min_value=min_date,
        max_value=yesterday,
        format="YYYY-MM-DD",
        key="P2_custom_date_range_input"
    )

    # 除錯處理: 日期少 and 順序錯誤
    if isinstance(date_query, tuple) and len(date_query) == 2:
        start_date, end_date = date_query
        if start_date > end_date:
            st.error("開始日期不能晚於結束日期！")
            start_date, end_date = end_date, start_date
        st.session_state['P2_custom_date_range'] = (start_date, end_date)
    else:
        st.error("請選擇兩個日期。")
        st.stop()

# 寫出選擇的日期
if st.session_state['P2_default_date_range'] == None:
    start_date, end_date = st.session_state['P2_custom_date_range']
else:
    start_date, end_date = st.session_state['P2_default_date_range']

P2date_range_str = f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
st.write("您選擇的日期區間是：", P2date_range_str, f", 共 {(end_date - start_date).days + 1} 天")

st.markdown("<br>", unsafe_allow_html=True)

# 資料庫查詢query
start_date_query = f"""
SELECT 
    *
FROM 
    `yt_channel_statistics`.`channel_data`
WHERE 
    date = '{start_date.strftime('%Y-%m-%d')}' 
    AND HOUR(time) = 5
    AND category <> 'Unknown category';
"""

end_date_query = f"""
SELECT 
    *
FROM 
    `yt_channel_statistics`.`channel_data`
WHERE 
    date = DATE_ADD('{end_date.strftime('%Y-%m-%d')}', INTERVAL 1 DAY)
    AND HOUR(time) = 5
    AND category <> 'Unknown category';
"""

with st.spinner("請稍等..."):
    start_date_df = SQL.query_data('yt_channel_statistics', start_date_query)
    query_save_to_db(start_date_query, start_time, len(start_date_df))

    end_date_df = SQL.query_data('yt_channel_statistics', end_date_query)
    query_save_to_db(end_date_query, start_time, len(end_date_df))

    df = channel_views(start_date_df, end_date_df)

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
            `yt_channel_statistics`.`channel_data` a
        JOIN 
            `yt_channel_statistics`.`channel_data` b
            ON a.channel_id = b.channel_id
            AND a.date = DATE_ADD(b.date, INTERVAL 1 DAY)
        WHERE 
            a.channel_id IN ({channel_ids_str})
            AND HOUR(a.time) = "5"
            AND HOUR(b.time) = "5"
            AND a.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND'{end_date.strftime('%Y-%m-%d')}'+ INTERVAL 1 DAY 
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

    # 選擇類別
    category_options = ["全部類別", "綜合新聞類", "社會蒐奇類", "生活財經類", "健康類", "娛樂類", "戲劇類"]

    default_index = 0

    if 'P2_category_select' not in st.session_state:
        st.session_state['P2_category_select'] = None

    if 'P2_category_select' in st.session_state and st.session_state.P2_category_select in category_options:
        default_index = category_options.index(st.session_state.P2_category_select)
    else: 
        default_index = 0

    P2_category_select = st.selectbox("請選擇頻道類別：", category_options, index=default_index, key="P2_category_select_input")

    st.session_state['P2_category_select'] = P2_category_select

    # 根據類別篩選
    if P2_category_select == "全部類別":
        df = df
    elif P2_category_select == "綜合新聞類":
        df = df[df['category'].isin(['綜合新聞類', '政論類', '國際新聞類'])]
    elif P2_category_select == "社會蒐奇類":
        df = df[df['category'] == '社會蒐奇類']
    elif P2_category_select == "生活財經類":
        df = df[df['category'] == '生活財經類']
    elif P2_category_select == "健康類":
        df = df[df['category'] == '健康類']
    elif P2_category_select == "娛樂類":
        df = df[df['category'].isin(['娛樂節目', '娛樂新聞類'])]
    elif P2_category_select == "戲劇類":
        df = df[df['category'] == '戲劇類']


# df = df.drop(columns=['iD', 'channel_id', 'date', 'time', 'views_count', 'videos_count'])
# df = df.rename(columns={'subscribers_count': 'subscribers'})
# df['videos'] = pd.to_numeric(df['videos'], errors='coerce')
# df['views'] = pd.to_numeric(df['views'], errors='coerce')
# df['subscribers'] = pd.to_numeric(df['subscribers'], errors='coerce')
# df.sort_values('views', ascending=False, inplace=True)
# df.insert(0, 'rank', df['views'].rank(ascending=False, method='dense').astype(int))


# 下載按鈕
@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

csv = convert_df(df)
if st.download_button("下載完整排行", csv, f"頻道流量排行_{P2_category_select}_{today_str}.csv", mime='text/csv'):
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

    # 判斷負數 → 套紅色
    viewers_color = "red" if row['views'] < 0 else "inherit"
    videos_color  = "red" if row['videos'] < 0 else "inherit"

    st.markdown(
        f"""
        <div style="display: flex; align-items: center; min-height: 60px; padding: 10px 0; border-bottom: 1px solid #eee; margin-right: -70px; padding-right: 50px;">
            <div style="flex-basis: 60px; flex-shrink: 0; text-align: center;">{row['rank']}</div>
            <div style="flex-basis: 250px; flex-shrink: 0;">{row['channel_name']}</div>
            <div style="flex-basis: 150px; flex-shrink: 0; text-align: right;">{subs_formatted}</div>
            <div style="flex-basis: 150px; flex-shrink: 0; text-align: right; color:{viewers_color};">{viewers_formatted}</div>
            <div style="flex-basis: 150px; flex-shrink: 0; text-align: right; color:{videos_color};">{videos_formatted}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

end_time = time.time()  # 记录结束时间
P2_elapsed_time = end_time - start_time
st.session_state['P2_elapsed_time'] = round(P2_elapsed_time, 2)
st.text(f"\n運行時間: {st.session_state['P2_elapsed_time']} 秒")