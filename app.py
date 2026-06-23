import sys
import traceback
import streamlit as st

# ===== 强制错误输出 =====
def global_exception_handler(exc_type, exc_value, exc_tb):
    print("=" * 50)
    print("🚨 捕获到未处理的异常：")
    traceback.print_exception(exc_type, exc_value, exc_tb)
    print("=" * 50)

sys.excepthook = global_exception_handler

# ===== 页面 =====
st.set_page_config(page_title="测试", layout="wide")
st.title("✅ 测试页面")

try:
    st.write("1. 导入模块...")
    import pandas as pd
    st.write("✅ pandas 导入成功")
    
    import requests
    st.write("✅ requests 导入成功")
    
    import re
    st.write("✅ re 导入成功")
    
    st.write("2. 所有模块导入完成！")
    st.success("🎉 应用运行正常")
    
except Exception as e:
    st.error(f"❌ 发生错误：{e}")
    print("=" * 50)
    print("🚨 页面渲染时发生错误：")
    traceback.print_exc()
    print("=" * 50)
