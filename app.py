import streamlit as st
import pandas as pd
import re
import requests

# =========================
# 页面配置
# =========================
st.set_page_config(page_title="关键词筛选工具", layout="wide")
st.title("🔧 关键词筛选工具")

# =========================
# 语言选项
# =========================
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

col1, col2 = st.columns(2)
with col1:
    target_language = st.selectbox(
        "🎯 保留哪种语言",
        list(language_options.keys()),
        format_func=lambda x: f"{x} - {language_options[x]}"
    )
with col2:
    skip_lang_detect = st.checkbox(
        "⚡ 跳过语言检测",
        value=False,
        help="如果你的关键词已经是目标语言（比如全是中文），勾选后可大幅提速"
    )

st.markdown("### 🚫 要删除的品牌词")
brand_text = st.text_area(
    "支持空格、逗号、换行分隔",
    height=100,
    placeholder="wirecast flexi play mirror iphone"
)

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

# =========================
# 文件上传
# =========================
uploaded_file = st.file_uploader("📂 上传 CSV 或 Excel 文件", type=["csv", "xlsx", "xls"])

# =========================
# 语言检测函数
# =========================
def is_english(text: str) -> bool:
    if not text or len(text.strip()) < 2:
        return True
    s = text.strip()
    
    # 检查非拉丁字符
    non_latin_pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0600-\u06ff\u0400-\u04ff]')
    if non_latin_pattern.search(s):
        return False
    
    # 检查变音符号
    accent_pattern = re.compile(r'[áéíóúñüçãõàèìòù]', re.IGNORECASE)
    if accent_pattern.search(s):
        return False
    
    # LibreTranslate API
    try:
        response = requests.post("https://libretranslate.com/detect", json={"q": s}, timeout=3)
        if response.status_code == 200:
            result = response.json()
            if result and len(result) > 0:
                best = result[0]
                return best.get("language") == "en" and best.get("confidence", 0) > 0.7
    except:
        pass
    
    # 字符集兜底
    english_letters = len(re.findall(r'[a-zA-Z]', s))
    total_chars = len(re.sub(r'[0-9\s\W_]', '', s))
    if total_chars == 0:
        return True
    return english_letters / total_chars > 0.7

# =========================
# 智能读取文件
# =========================
def read_file_smart(uploaded_file):
    """自动检测编码并读取文件"""
    if uploaded_file.name.endswith(('.xlsx', '.xls')):
        return pd.read_excel(uploaded_file)
    
    # CSV 文件：尝试多种编码
    encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin1', 'cp1252']
    
    for encoding in encodings:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding=encoding)
            return df
        except UnicodeDecodeError:
            continue
        except Exception:
            continue
    
    # 所有编码都失败
    st.error("❌ 无法识别文件编码，请确保文件为 UTF-8 或 UTF-16 编码")
    return None

# =========================
# 主逻辑
# =========================
st.markdown("---")
st.subheader("📊 处理结果")

if uploaded_file is None:
    st.info("📁 请先上传 CSV 或 Excel 文件，然后点击下方按钮开始处理")
    st.stop()

# ===== 读取文件 =====
df = read_file_smart(uploaded_file)
if df is None:
    st.stop()

st.success(f"✅ 文件读取成功，共 {len(df)} 行")
st.write("列名：", df.columns.tolist())

keyword_column = st.selectbox("📌 请选择关键词所在的列", df.columns.tolist())

brands = parse_brands(brand_text)
if brands:
    st.success(f"🔍 识别到的品牌词：**{', '.join(brands)}**")

start_btn = st.button("🚀 一键启动筛选", type="primary", use_container_width=True)

if start_btn:
    with st.spinner("正在筛选..."):
        texts = df[keyword_column].tolist()
        results = []
        for text in texts:
            results.append(is_english(str(text)) if target_language == "en" else True)
        
        df_filtered = df[results].copy()
        
        # 品牌过滤
        if brands:
            keep_mask = []
            for val in df_filtered[keyword_column].tolist():
                s = str(val).lower().strip()
                keep = True
                for brand in brands:
                    if s == brand or s.startswith(f"{brand} ") or s.endswith(f" {brand}") or f" {brand} " in f" {s} ":
                        keep = False
                        break
                keep_mask.append(keep)
            df_filtered = df_filtered[keep_mask].copy()
        
        # 去重
        df_filtered = df_filtered.drop_duplicates(subset=[keyword_column]).copy()
        
        st.success(f"✨ 筛选完成！剩余 {len(df_filtered)} 条关键词")
        st.dataframe(df_filtered.head(100))
        
        csv_data = df_filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 下载结果 CSV",
            data=csv_data,
            file_name="filtered_keywords.csv",
            mime="text/csv",
            use_container_width=True
        )
