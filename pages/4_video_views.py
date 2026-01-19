import streamlit as st
import pandas as pd
from io import BytesIO
from myfun.sql_connection import SQL_connection
from myfun.config_read import ConfigRead
from datetime import datetime, timedelta, date
import os, time, html, copy
from myfun.discord import Discord

# --- 更新日志
# 2025/12/23：查詢中時禁用按鈕，避免重複查詢



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
min_date = datetime(2025, 11, 1).date()


# if 'df' not in st.session_state:
#     st.session_state['df'] = None

if "is_querying" not in st.session_state:
    st.session_state.is_querying = False
    
category_mapping = {
    "綜合新聞類": ['綜合新聞類', '政論類', '國際新聞類'],
    "社會蒐奇類": ['社會蒐奇類'],
    "生活財經類": ['生活財經類'],
    "健康類": ['健康類'],
    "娛樂類": ['娛樂節目', '娛樂新聞類'],
    "戲劇類": ['戲劇類'],
}

def print_real_query(conditions_list, params_list, query_name="SQL"):
    """
    把 conditions + params 轉成完整可讀的 SQL 字串並印出來
    """
    # 先複製一份，避免影響原本的 params
    import copy
    params = copy.deepcopy(params_list)
    
    # 每個 %s 依序換成對應的值，加上單引號（因為都是字串）
    where_clause = " AND ".join(conditions_list)
    for i, param in enumerate(params):
        # 日期或字串都要加單引號
        escaped_value = f"'{param}'"
        where_clause = where_clause.replace("%s", escaped_value, 1)  # 只替換第一個
    
    st.write(f"\n=== {query_name} 實際執行的 WHERE 條件 ===")
    st.write(where_clause)
    st.write("=" * 50)

def query_save_to_db(conditions_list, params_list, start_time, data_size):
    """
    把 conditions + params 轉成完整可讀的 SQL 字串並印出來
    """
    params = copy.deepcopy(params_list)
    query_sec = int(time.time() - start_time)
    Date_Time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 每個 %s 依序換成對應的值，加上單引號（因為都是字串）
    where_clause = " AND ".join(conditions_list)
    for i, param in enumerate(params):
        # 日期或字串都要加單引號
        escaped_value = f"'{param}'"
        where_clause = where_clause.replace("%s", escaped_value, 1)  # 只替換第一個
    query = [(Date_Time, query_sec, where_clause, data_size, fun_name)]
    df = pd.DataFrame(query, columns=["Date_Time", "query_sec", "where_clause", "data_size", "fun_name"])
    SQL.insert_data(df, 'yt_channel_statistics', 'sp_UI_query', discord=False)


# 處理頻道觀看的計算
def video_views(start_date_df, end_date_df, start_date):
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

    merged = merged[
        ~((merged["video_view_count_start"] == 0) & (merged["published_date"] < start_date))
    ]

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

    # # 檢查用，顯示所有column
    # result = merged

    return(result)

# ----- 日期option
# 初次執行時，設定 session_state 的日期預設值

if "P4_custom_date_range" not in st.session_state:
    st.session_state['P4_custom_date_range'] = (yesterday, yesterday)

if 'P4_custom_date_range_input' not in st.session_state:
    st.session_state['P4_custom_date_range_input'] = st.session_state['P4_custom_date_range']

# Radio 選擇日期範圍
option = st.radio(
    "選擇日期區間：",
    ["自訂", "近7天", "近30天"],
    horizontal=True,
    disabled=st.session_state.is_querying
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
        key="P4_custom_date_range_input",
        disabled=st.session_state.is_querying
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
        # st.stop()

# 寫出選擇的日期
if st.session_state['P4_default_date_range'] == None:
    start_date, end_date = st.session_state['P4_custom_date_range']
else:
    start_date, end_date = st.session_state['P4_default_date_range']

P4date_range_str = f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
st.write("您選擇的日期區間是：", P4date_range_str, f", 共 {(end_date - start_date).days + 1} 天")

st.markdown("<br>", unsafe_allow_html=True)

# ----- 
col1, col2, col3 = st.columns(3)

# ----- 類別option  
with col1:
    category_options = ["全部類別", "綜合新聞類", "社會蒐奇類", "生活財經類", "健康類", "娛樂類", "戲劇類"]

    default_index = 0

    if 'P4_category_select' not in st.session_state:
        st.session_state['P4_category_select'] = None

    if 'P4_category_select' in st.session_state and st.session_state.P4_category_select in category_options:
        default_index = category_options.index(st.session_state.P4_category_select)
    else: 
        default_index = 0

    P4_category_select = st.selectbox("請選擇頻道類別：", category_options, index=default_index, key="P4_category_select_input", disabled=st.session_state.is_querying)

    st.session_state['P4_category_select'] = P4_category_select

# ----- 頻道option
with col2:

    # 資料庫查詢query (頻道名稱)
    query = f"""
    SELECT DISTINCT `channel_id`, `channel_name`, `category`
    FROM `yt_channel_statistics`.`channel_data` 
    WHERE `date` = "{end_date.strftime('%Y-%m-%d')}" 
    AND `category` <> "Unknown category";
    """
    
    # 轉成list
    channel_df = SQL.query_data('yt_channel_statistics', query)
    channel_option = ['全頻道'] + channel_df['channel_name'].tolist()

    # 類別處理
    if P4_category_select == "全部類別":
        channel_df = channel_df
    elif P4_category_select == "綜合新聞類":
        channel_df = channel_df[channel_df['category'].isin(['綜合新聞類', '政論類', '國際新聞類'])]
    elif P4_category_select == "社會蒐奇類":
        channel_df = channel_df[channel_df['category'] == '社會蒐奇類']
    elif P4_category_select == "生活財經類":
        channel_df = channel_df[channel_df['category'] == '生活財經類']
    elif P4_category_select == "健康類":
        channel_df = channel_df[channel_df['category'] == '健康類']
    elif P4_category_select == "娛樂類":
        channel_df = channel_df[channel_df['category'].isin(['娛樂節目', '娛樂新聞類'])]
    elif P4_category_select == "戲劇類":
        channel_df = channel_df[channel_df['category'] == '戲劇類']

    channel_option = ['全頻道'] + channel_df['channel_name'].tolist()

    # 類別 session
    if 'P4_channel_select' not in st.session_state:
        st.session_state['P4_channel_select'] = channel_option[0]

    if 'P4_channel_select' in st.session_state and st.session_state.P4_channel_select in channel_option:
        default_index = channel_option.index(st.session_state.P4_channel_select)

    # 類別選擇
    P4_channel_select = st.selectbox("請選擇頻道：", channel_option, index=default_index, key="P4_channel_select_input", disabled=st.session_state.is_querying)

    # 類別 session
    st.session_state['P4_channel_select'] = P4_channel_select

# 選擇影片類別
with col3:

    kind_options = ["全部影片類型", "shorts", "videos", "streams"]

    if 'P4_kind_select' not in st.session_state:
        st.session_state['P4_kind_select'] = kind_options[0]

    if 'P4_kind_select' in st.session_state and st.session_state.P4_kind_select in kind_options:
        default_index = kind_options.index(st.session_state.P4_kind_select)
    else:
        default_index = 0

    P4_kind_select = st.selectbox("請選擇影片類型：", kind_options, index=default_index, key="P4_kind_select_input", disabled=st.session_state.is_querying)

    st.session_state['P4_kind_select'] = P4_kind_select


#---------------------------
end_date_conditions = []
end_date_params = []
start_date_conditions = []
start_date_params = []

start_date_conditions.append("DATE(`insert_datetime`) = %s")
start_date_conditions.append("member_video = 0")
start_date_params.append(start_date.strftime("%Y-%m-%d"))

end_date_conditions.append("DATE(`insert_datetime`) = DATE_ADD(%s, INTERVAL 1 DAY)")
end_date_conditions.append("member_video = 0")
end_date_params.append(end_date.strftime("%Y-%m-%d"))

# 動態條件：根據 selectbox 決定要不要加
if P4_category_select != "全部類別":
    real_categories = category_mapping[P4_category_select]
    if len(real_categories) == 1:
        # 只有一個，直接用 =
        end_date_conditions.append("category = %s")
        end_date_params.append(real_categories[0])
        
        start_date_conditions.append("category = %s")
        start_date_params.append(real_categories[0])
    else:
        # 多個，用 IN
        placeholders = ", ".join(["%s"] * len(real_categories))
        end_date_conditions.append(f"category IN ({placeholders})")
        end_date_params.extend(real_categories)
        
        start_date_conditions.append(f"category IN ({placeholders})")
        start_date_params.extend(real_categories)

if P4_channel_select != "全頻道":
    end_date_conditions.append("channel_name = %s")
    end_date_params.append(P4_channel_select)
    start_date_conditions.append("channel_name = %s")
    start_date_params.append(P4_channel_select)

if P4_kind_select != "全部影片類型":
    end_date_conditions.append("kind = %s")
    end_date_params.append(P4_kind_select)
    start_date_conditions.append("kind = %s")
    start_date_params.append(P4_kind_select)

# 把所有條件用 AND 接起來
end_date_where_clause = " AND ".join(end_date_conditions)
start_date_where_clause = " AND ".join(start_date_conditions)

# # st.write 出實際查詢的 SQL
# print_real_query(start_date_conditions, start_date_params, "起始日查詢")
# print_real_query(end_date_conditions,   end_date_params,   "結束日查詢")

# 資料庫查詢query
start_date_query = f"""
SELECT 
    DATE(`insert_datetime`) AS insert_date,
    video_id,
    video_view_count

FROM 
    `yt_channel_statistics`.`video_data`
WHERE 
    {start_date_where_clause};
"""

end_date_query = f"""
SELECT 
    DATE(`insert_datetime`) AS insert_date,
    DATE(`taiwan_published_datetime`) AS published_date,
    channel_id,
    channel_name,
    category,
    video_id,
    video_title,
    kind,
    video_thumbnails,
    video_view_count

FROM 
    `yt_channel_statistics`.`video_data`
WHERE 
    {end_date_where_clause};
"""

st.markdown("""
<style>
    .myform {
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    div[data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

with st.form("query_form", clear_on_submit=False):
    st.markdown('<div class="myform">', unsafe_allow_html=True)
    submitted = st.form_submit_button("查詢", disabled=st.session_state.is_querying)
    st.markdown('</div>', unsafe_allow_html=True)

if submitted and not st.session_state.is_querying:
    st.session_state.is_querying = True
    st.rerun()

if st.session_state.is_querying:
    with st.spinner("查詢與彙整中, 請稍等..."):
        try:
            P4_start_time = time.time()
            start_date_df = SQL.query_data('yt_channel_statistics', start_date_query, params=start_date_params)
            query_save_to_db(start_date_conditions, start_date_params, P4_start_time, len(start_date_df))
            end_date_df = SQL.query_data('yt_channel_statistics', end_date_query, params=end_date_params)
            query_save_to_db(end_date_conditions, end_date_params, P4_start_time, len(end_date_df))
            df = video_views(start_date_df, end_date_df, start_date)
            if df.empty:
                st.warning("⚠️ 查無資料，請調整篩選條件後重新查詢。")

            if df is not None and not df.empty:
                name_to_id = dict(zip(channel_df['channel_name'], channel_df['channel_id']))
                name_to_id['全頻道'] = 'ALL'   # 標記為全部
                if P4_channel_select == '全頻道':
                    df = df.copy()  # 全選
                else:
                    target_id = name_to_id[P4_channel_select]           # 拿到對應的 channel_id
                    df = df[df['channel_id'] == target_id]

                df.insert(0, 'rank', df['views'].rank(ascending=False, method='dense').astype(int))

                st.session_state['df'] = df
                P4_end_time = time.time()  # 记录结束时间
                P4_elapsed_time = P4_end_time - P4_start_time
                st.session_state['P4_elapsed_time'] = round(P4_elapsed_time, 2)

        finally:
            st.session_state.is_querying = False
            st.rerun()

# # 檢查用，以datadrame 顯示
# if 'df' in st.session_state:
#     st.dataframe(st.session_state['df'], use_container_width=True)

if 'df' in st.session_state and st.session_state['df'] is not None:
    # 下載按鈕
    def convert_df(df):
        # IMPORTANT: Cache the conversion to prevent computation on every rerun
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    csv = convert_df(st.session_state['df'])
    if st.download_button("下載完整數據", csv, f"影片流量排行_{P4_category_select}_{P4_channel_select}_{P4_kind_select}_{today_str}.csv", mime='text/csv'):
        st.toast("✔️ 已完成下載!")

    # 轉換成千分位數
    def format_num(num):
        if pd.isna(num):
            return "0"
        num = float(num)
        if num >= 10000:
            return f"{num / 10000:,.2f} 萬"

        # 小於一萬 → 原值千分位
        return f"{num:,.0f}"

    # st.dataframe(df)

    # 顯示每一筆資料，也不寫color inline
    for index, row in st.session_state['df'].head(50).iterrows():
        viewers_formatted = format_num(row['views'])
        full_title = html.escape(row['video_title'], quote=True)

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
                    style="text-decoration: none; color: inherit;"
                >
                    <h4 
                        style="margin:0 0 6px 0; font-size:18px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"
                        title="{full_title}"
                    >
                        {full_title}
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


if 'P4_elapsed_time' in st.session_state:
    st.text(f"\n運行時間: {st.session_state['P4_elapsed_time']} 秒")
    