D:
cd D:\python\YT_ST
call .venv\Scripts\activate
streamlit run YT_ST.py --server.headless true --server.port 8502 --server.baseUrlPath YTDashboard --server.maxUploadSize 2048 --server.maxMessageSize=4096
