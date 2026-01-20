# myfun/settings.py
from __future__ import annotations
from typing import Optional

def _safe_get_secrets():
    """
    st.secrets 只能在 streamlit 執行環境下可用。
    這個函式的目的：就算在純 python / 測試環境 import，也不要炸。
    """
    try:
        import streamlit as st  # lazy import
        return st.secrets
    except Exception:
        return None


def get_discord_webhook_url(config=None) -> Optional[str]:
    """
    讀取 Discord webhook URL：
    1) 先從 Streamlit Cloud secrets
    2) 再從本機 config（你原本的 config.config_read）
    3) 都沒有就回 None（不要 raise）
    """
    secrets = _safe_get_secrets()
    if secrets is not None:
        url = secrets.get("discord_webhook", {}).get("url")
        if url:
            return str(url).strip()

    if config is not None:
        try:
            url = config.config_read("discord_webhook", "url")
            if url:
                return str(url).strip()
        except Exception:
            pass

    return None


def get_sql_db_url(config=None) -> Optional[str]:
    """
    讀取 SQL DB_URL：
    1) secrets
    2) 本機 config
    3) 都沒有回 None
    """
    secrets = _safe_get_secrets()
    if secrets is not None:
        db_url = secrets.get("SQL_DB", {}).get("DB_URL")
        if db_url:
            return str(db_url).strip()

    if config is not None:
        try:
            db_url = config.config_read("SQL_DB", "DB_URL")
            if db_url:
                return str(db_url).strip()
        except Exception:
            pass

    return None
