#%%
import streamlit as st

st.title('📕 使用説明')

tab1, tab2 = st.tabs(["數據來源", "界面介紹"])

with tab1:
    st.markdown(
        """
        <div style='font-size:18px; line-height:1.8'>
        <ol>
            <ol type="a">
                <li>數據來源自中天數據中心資料庫</li>
                <li>資料庫是透過 YouTube 官方 API 定期蒐集並彙整之數據。</li>
                <li>因資料蒐集時間點、統計方式及平台更新機制不同，
                    本資料與其他第三方統計結果，可能略有差異，
                    惟不影響整體趨勢與相對表現之分析。</li>
            </ol>
        </ol>
        </div>
        """,
        unsafe_allow_html=True
    )

with tab2:
    st.subheader("1. 流量排名")
    st.markdown(
        """
        <div style='font-size:18px; line-height:1.8'>
        <ol>
            <ol type="a">
                <li>選擇日期</li>
                <li>選擇頻道類別</li>
                <li>排名僅顯示前100名, 可下載完整數據。下載格式: CSV</li>
                <span>註：選擇頻道類別後, 會自動更新數據</span>
            </ol>
        </ol>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.image("user_guide/channel_ranking.png", width=1000)

    st.divider()

    st.subheader("2. 每日流量")

    st.markdown(
        """
        <div style='font-size:18px; line-height:1.8'>
        <ol>
            <ol type="a">
                <li>選擇日期</li>
                <li>選擇頻道</li>
                <li>可下載完整數據。下載格式: CSV</li>
                <span>註：選擇頻道後, 會自動更新數據</span>
            </ol>
        </ol>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.image("user_guide/daily.png", width=1000)

    st.divider()

    st.subheader("3. 影片流量")

    st.markdown(
        """
        <div style='font-size:18px; line-height:1.8'>
        <ol>
            <ol type="a">
                <li>選擇日期</li>
                <li>選擇頻道類別</li>
                <li>選擇頻道</li>
                <li>選擇影片類型</li>
                <li>點擊查詢</li>
                <li>排名僅顯示前50名, 可下載完整數據。下載格式: CSV</li>
                <span>註：查詢資料量會影響運行速度, 盡可能縮小查詢範圍</span>
            </ol>
        </ol>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.image("user_guide/video_view.png", width=1000)




