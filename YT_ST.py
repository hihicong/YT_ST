#%%
import streamlit as st
#from ST_menu import menu
from io import StringIO
import pandas as pd
import toml
import importlib.util
from st_pages import add_page_title, get_nav_from_toml




def main():
    st.set_page_config(
        page_title="YT流量數據",
        page_icon="🔴")

    # # 讀取整個 config
    # nav = get_nav_from_toml(".streamlit/pages.toml")
    # pg = st.navigation(nav)
    # # add_page_title(nav)
    # pg.run()

    config = toml.load(".streamlit/pages.toml")
    pages = {}
    for section, items in config.items():
        pages[section.capitalize()] = [
            st.Page(i["path"], title=i["name"], icon=i["icon"]) for i in items
        ]

    pg = st.navigation(pages)
    pg.run()



if __name__ == '__main__':
    # menu()
    main()