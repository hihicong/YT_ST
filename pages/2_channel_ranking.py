import streamlit as st
import pandas as pd
from io import BytesIO
from myfun.sql_connection import SQL_connection
from myfun.config_read import ConfigRead
from datetime import datetime, timedelta, date
import os, time, copy
from myfun.discord import Discord

# --- 更新日志 ---

# 0105：新增跨越 2025-02-06 切換時間點的處理邏輯 (因為 2/6 後改成凌晨5點抓取)

# --- 更新日志結束 ---
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

    # result.insert(0, 'rank', result['views'].rank(ascending=False, method='dense').astype(int))

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

cutoff_date = date(2025, 2, 6)

def build_segment_queries(seg_start, seg_end):
    """
    回傳 (start_query, end_query, hour)
    若 seg_end < cutoff => 使用 hour=23 並且 start date = DATE_SUB(seg_start, INTERVAL 1 DAY), end date = seg_end
    若 seg_start >= cutoff => 使用 hour=5 並且 start date = seg_start, end date = DATE_ADD(seg_end, INTERVAL 1 DAY)
    """
    if seg_end < cutoff_date:
        # 全部在 cutoff 之前（含 5號）
        hour = 23
        start_q = f"""
        SELECT *
        FROM `yt_channel_statistics`.`channel_data`
        WHERE date = DATE_SUB('{seg_start.strftime('%Y-%m-%d')}', INTERVAL 1 DAY)
          AND HOUR(time) = {hour}
          AND category <> 'Unknown category';
        """
        end_q = f"""
        SELECT *
        FROM `yt_channel_statistics`.`channel_data`
        WHERE date = '{seg_end.strftime('%Y-%m-%d')}'
          AND HOUR(time) = {hour}
          AND category <> 'Unknown category';
        """
    else:
        # 全部在 cutoff 之後（含 6號）
        hour = 5
        start_q = f"""
        SELECT *
        FROM `yt_channel_statistics`.`channel_data`
        WHERE date = '{seg_start.strftime('%Y-%m-%d')}'
          AND HOUR(time) = {hour}
          AND category <> 'Unknown category';
        """
        end_q = f"""
        SELECT *
        FROM `yt_channel_statistics`.`channel_data`
        WHERE date = DATE_ADD('{seg_end.strftime('%Y-%m-%d')}', INTERVAL 1 DAY)
          AND HOUR(time) = {hour}
          AND category <> 'Unknown category';
        """
    return start_q, end_q, hour

with st.spinner("請稍等..."):
    # 切割範圍（可能只有一段，也可能兩段）
    segments = []
    if end_date < cutoff_date:
        segments.append((start_date, end_date))
    elif start_date >= cutoff_date:
        segments.append((start_date, end_date))
    else:
        # 跨越 cutoff：先處理 start_date .. cutoff_date-1，再處理 cutoff_date .. end_date
        segments.append((start_date, cutoff_date - timedelta(days=1)))
        segments.append((cutoff_date, end_date))

    segment_dfs = []      # 每段計算後的 df (channel_views 的輸出格式)
    segment_end_snapshots = []  # 每段的 end snapshot dataframe，用來取最近 metadata
    segment_infos = []    # 每段的 meta 資訊: {'seg_start','seg_end','hour'}

    for seg_start, seg_end in segments:
        start_query, end_query, hour = build_segment_queries(seg_start, seg_end)

        start_df_seg = SQL.query_data('yt_channel_statistics', start_query)
        query_save_to_db(start_query, start_time, len(start_df_seg))

        end_df_seg = SQL.query_data('yt_channel_statistics', end_query)
        query_save_to_db(end_query, start_time, len(end_df_seg))

        # 若任一段沒有資料則跳過（避免整體中斷）
        if start_df_seg.empty or end_df_seg.empty:
            continue

        df_seg = channel_views(start_df_seg, end_df_seg)
        segment_dfs.append(df_seg)
        segment_end_snapshots.append(end_df_seg)
        segment_infos.append({'seg_start': seg_start, 'seg_end': seg_end, 'hour': hour})

    if not segment_dfs:
        st.write("查無資料，請縮小或更改日期範圍。")
        st.stop()

    # 若只有一段，直接使用該段結果；若多段，合併 views/videos 並以最近 snapshot 拿 metadata
    if len(segment_dfs) == 1:
        df = segment_dfs[0]
    else:
        # 合計 views & videos
        combined = pd.concat([sdf[['channel_id', 'views', 'videos']] for sdf in segment_dfs])
        combined = combined.groupby('channel_id', as_index=False).sum()

        # 取得所有段的 end snapshot，選取每 channel 的最新一筆 metadata
        meta_all = pd.concat(segment_end_snapshots, ignore_index=True)
        meta_all['date'] = pd.to_datetime(meta_all['date']).dt.date
        meta_latest = meta_all.sort_values(['channel_id', 'date']).drop_duplicates('channel_id', keep='last')

        # 選取需要的欄位並合併
        meta_latest = meta_latest[['channel_id', 'channel_name', 'category', 'subscribers_count']].rename(
            columns={'subscribers_count': 'subscribers'}
        )

        df = combined.merge(meta_latest, on='channel_id', how='left')

        # 重新整理欄位順序與名稱，並排名
        df = df[['channel_id', 'channel_name', 'category', 'subscribers', 'views', 'videos']]
        df['subscribers'] = pd.to_numeric(df['subscribers'], errors='coerce').fillna(0).astype(int)

# ...existing code...
    # 精準負數調整：針對每個 segment 用該段實際的 hour 與 a.date 範圍查負數，最後合併再 groupby
    if (df['views'] < 0).any():
        negative = df[df['views'] < 0].copy()
        channel_ids = negative["channel_id"].tolist()
        channel_ids_str = ', '.join([f"'{name}'" for name in channel_ids])

        per_segment_updates = []
        for info in segment_infos:
            seg_start = info['seg_start']
            seg_end = info['seg_end']
            hr = info['hour']

            if hr == 23:
                a_start = seg_start
                a_end = seg_end
            else:  # hr == 5
                a_start = seg_start + timedelta(days=1)
                a_end = seg_end + timedelta(days=1)

            if a_start > a_end:
                continue

            query_negative_view = f"""
            SELECT
                a.channel_id,
                (a.views_count - b.views_count) AS negative_views,
                a.date AS a_date
            FROM `yt_channel_statistics`.`channel_data` a
            JOIN `yt_channel_statistics`.`channel_data` b
                ON a.channel_id = b.channel_id
                AND a.date = DATE_ADD(b.date, INTERVAL 1 DAY)
            WHERE a.channel_id IN ({channel_ids_str})
              AND HOUR(a.time) = {hr}
              AND HOUR(b.time) = {hr}
              AND a.date BETWEEN DATE('{a_start.strftime('%Y-%m-%d')}') AND DATE('{a_end.strftime('%Y-%m-%d')}')
              AND (a.views_count - b.views_count) < 0
            ;
            """
            df_up = SQL.query_data('yt_channel_statistics', query_negative_view)
            query_save_to_db(query_negative_view, start_time, len(df_up))
            if not df_up.empty and 'channel_id' in df_up.columns and 'negative_views' in df_up.columns:
                # 強制型別，確保後續處理正確
                df_up['negative_views'] = pd.to_numeric(df_up['negative_views'], errors='coerce').fillna(0).astype(int)
                # 保證 a_date 為字串
                if 'a_date' in df_up.columns:
                    df_up['a_date'] = pd.to_datetime(df_up['a_date'], errors='coerce').dt.date.astype(str)
                per_segment_updates.append(df_up)

        if per_segment_updates:
            df_update_all = pd.concat(per_segment_updates, ignore_index=True)

            # 每 channel 的負數日期與該日負數值合併成字串，方便檢視
            if 'a_date' in df_update_all.columns:
                neg_details = (
                    df_update_all
                    .assign(pair=lambda d: d['a_date'] + ':' + d['negative_views'].astype(str))
                    .groupby('channel_id')['pair']
                    .apply(lambda s: '; '.join(s))
                    .reset_index(name='neg_dates_views')
                )
            else:
                neg_details = df_update_all.groupby('channel_id')['negative_views'].apply(lambda s: '; '.join(s.astype(str))).reset_index(name='neg_dates_views')

            negative_sums = df_update_all.groupby("channel_id", as_index=False)["negative_views"].sum()
            negative_updated = negative.merge(negative_sums, on="channel_id", how="left")
            negative_updated = negative_updated.merge(neg_details, on='channel_id', how='left')
            negative_updated["negative_views"] = negative_updated["negative_views"].fillna(0).astype(int)
            # 調整邏輯：adjusted = abs(sum_negative_views) + original_views
            negative_updated["adjusted_views"] = abs(negative_updated["negative_views"]) + negative_updated["views"]

            update_map = negative_updated.set_index("channel_id")["adjusted_views"]
            df["views"] = df["channel_id"].map(update_map).combine_first(df["views"])

# ...existing code...

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
df.sort_values('views', ascending=False, inplace=True)
df.insert(0, 'rank', df['views'].rank(ascending=False, method='dense').astype(int))


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