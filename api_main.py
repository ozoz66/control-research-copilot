# -*- coding: utf-8 -*-
"""
AutoControl-Scientist API 入口点

启动:
    python api_main.py
    # 或
    uvicorn api_main:app --host 0.0.0.0 --port 8000 --reload
"""

from api.app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
