import streamlit as st
import sys
import traceback

# ===== 强制错误输出 =====
def global_exception_handler(exc_type, exc_value, exc_tb):
    print("=" * 50)
    print("🚨 捕获到未处理的异常：")
    traceback.print_exception(exc_type, exc_value, exc_tb)
    print("=" * 50)

sys.excepthook = global_exception_handler

st.set_page_config(page_title="关键词筛选工具", layout="wide")
st.title("🔧 关键词筛选工具")

# ============================================================
# 第一步：导入所有库
# ============================================================
st.write("📦 **第一步：导入库**")

try:
    import pandas as pd
    st.success("✅ pandas")
except Exception as e:
    st.error(f"❌ pandas 导入失败: {e}")

try:
    import re
    st.success("✅ re")
except Exception as e:
    st.error(f"❌ re 导入失败: {e}")

try:
    import requests
    st.success("✅ requests")
except Exception as e:
    st.error(f"❌ requests 导入失败: {e}")

# ============================================================
# 第二步：定义所有函数（但不执行）
# ============================================================
st.write("📦 **第二步：定义函数**")

try:
    # 语言选项
    language_options = {
        "en": "英语",
        "pt": "葡萄牙语",
        "es": "西班牙语",
        "de": "德语",
        "fr": "法语",
        "it": "意大利语",
        "ja": "日语",
        "ko": "韩语",
        "zh": "中文",
        "ru": "俄语",
        "ar": "阿拉伯语"
    }
    st.success("✅ language_options 定义成功")
except Exception as e:
    st.error(f"❌ language_options 定义失败: {e}")

try:
    def parse_brands(raw_text: str):
        if not raw_text:
            return []
        lines = raw_text.splitlines()
        brands = []
        for line in lines:
            line = line.replace(',', ' ')
            parts = line.split()
            brands.extend(parts)
        brands = [b.strip().lower() for b in brands if b.strip()]
        seen = set()
        unique = []
        for b in brands:
            if b not in seen:
                seen.add(b)
                unique.append(b)
        return unique
    st.success("✅ parse_brands 函数定义成功")
except Exception as e:
    st.error(f"❌ parse_brands 定义失败: {e}")

try:
    def is_english(text: str) -> bool:
        if not text or len(text.strip()) < 2:
            return True
        s = text.strip()
        # 快速字符集检测
        non_latin_pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0600-\u06ff\u0400-\u04ff]')
        if non_latin_pattern.search(s):
            return False
        accent_pattern = re.compile(r'[áéíóúñüçãõàèìòù]', re.IGNORECASE)
        if accent_pattern.search(s):
            return False
        try:
            response = requests.post("https://libretranslate.com/detect", json={"q": s}, timeout=3)
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0:
                    best = result[0]
                    return best.get("language") == "en" and best.get("confidence", 0) > 0.7
        except:
            pass
        english_letters = len(re.findall(r'[a-zA-Z]', s))
        total_chars = len(re.sub(r'[0-9\s\W_]', '', s))
        if total_chars == 0:
            return True
        ratio = english_letters / total_chars
        return ratio > 0.7
    st.success("✅ is_english 函数定义成功")
except Exception as e:
    st.error(f"❌ is_english 定义失败: {e}")

try:
    def batch_language_detection(texts, target_lang, progress_bar, status_text):
        results = []
        total = len(texts)
        for i, val in enumerate(texts):
            if pd.isna(val):
                s = ""
            else:
                s = str(val).strip()
            results.append(is_english(s) if target_lang == "en" else True)
            if (i+1) % 200 == 0 or i+1 == total:
                progress_bar.progress((i+1)/total)
                status_text.text(f"🔍 语言检测中... {i+1}/{total} ({int((i+1)/total*100)}%)")
        return results
    st.success("✅ batch_language_detection 函数定义成功")
except Exception as e:
    st.error(f"❌ batch_language_detection 定义失败: {e}")

try:
    def batch_brand_filter(texts, brands, progress_bar, status_text):
        if not brands:
            return [True] * len(texts), []
        results = []
        total = len(texts)
        removed_examples = []
        for i, val in enumerate(texts):
            if pd.isna(val):
                results.append(True)
            else:
                s = str(val).lower().strip()
                keep = True
                for brand in brands:
                    if s == brand or s.startswith(f"{brand} ") or s.endswith(f" {brand}") or f" {brand} " in f" {s} ":
                        keep = False
                        if len(removed_examples) < 10:
                            removed_examples.append(f"「{val}」包含品牌词「{brand}」")
                        break
                results.append(keep)
            if (i+1) % 500 == 0 or i+1 == total:
                progress_bar.progress((i+1)/total)
                status_text.text(f"🚫 品牌过滤中... {i+1}/{total} ({int((i+1)/total*100)}%)")
        return results, removed_examples
    st.success("✅ batch_brand_filter 函数定义成功")
except Exception as e:
    st.error(f"❌ batch_brand_filter 定义失败: {e}")

try:
    def read_csv_smart(uploaded_file):
        uploaded_file.seek(0)
        try:
            df = pd.read_csv(uploaded_file, encoding="utf-8", engine="python", sep=None)
            if len(df.columns) > 1:
                return df
        except:
            pass
        encodings = ["utf-8", "latin1", "gbk", "gb2312", "cp936", "utf-16"]
        separators = [",", ";", "\t", "|", " "]
        for encoding in encodings:
            for sep in separators:
                try:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, encoding=encoding, sep=sep)
                    if len(df.columns) > 1:
                        return df
                except:
                    continue
        uploaded_file.seek(0)
        try:
            df = pd.read_csv(uploaded_file, encoding="utf-8", engine="python", sep=None, on_bad_lines="skip")
            if len(df.columns) > 1:
                return df
        except:
            pass
        return None
    st.success("✅ read_csv_smart 函数定义成功")
except Exception as e:
    st.error(f"❌ read_csv_smart 定义失败: {e}")

# ============================================================
# 第三步：UI 布局（这是关键！）
# ============================================================
st.write("📦 **第三步：UI 布局**")

try:
    col1, col2 = st.columns(2)
    st.success("✅ 列布局创建成功")
except Exception as e:
    st.error(f"❌ 列布局创建失败: {e}")

try:
    with col1:
        target_language = st.selectbox(
            "🎯 保留哪种语言",
            list(language_options.keys()),
            format_func=lambda x: f"{x} - {language_options[x]}"
        )
    st.success("✅ 语言选择框创建成功")
except Exception as e:
    st.error(f"❌ 语言选择框创建失败: {e}")

try:
    with col2:
        skip_lang_detect = st.checkbox(
            "⚡ 跳过语言检测",
            value=False,
            help="如果你的关键词已经是目标语言（比如全是中文），勾选后可大幅提速"
        )
    st.success("✅ 跳过检测复选框创建成功")
except Exception as e:
    st.error(f"❌ 跳过检测复选框创建失败: {e}")

try:
    st.markdown("### 🚫 要删除的品牌词（包含这些词的关键词会被整行删除）")
    brand_text = st.text_area(
        "支持空格、逗号、换行分隔",
        height=100,
        placeholder="wirecast flexi play mirror iphone"
    )
    st.success("✅ 品牌词输入框创建成功")
except Exception as e:
    st.error(f"❌ 品牌词输入框创建失败: {e}")

try:
    uploaded_file = st.file_uploader("📂 上传 CSV 或 Excel 文件", type=["csv", "xlsx", "xls"])
    st.success("✅ 文件上传组件创建成功")
except Exception as e:
    st.error(f"❌ 文件上传组件创建失败: {e}")

# ============================================================
# 第四步：主逻辑（仅在文件上传后触发）
# ============================================================
st.write("📦 **第四步：等待上传文件**")

if uploaded_file is not None:
    st.info("📄 文件已上传，开始处理...")
    # 这里你可以逐步加回主逻辑

st.success("🎉 **所有组件加载完成！页面应该正常显示。**")
