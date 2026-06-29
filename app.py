import streamlit as st
import pandas as pd
import re
import time
import hashlib
import os
import urllib.request

try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False

# =========================
# fastText 语言检测
# =========================
try:
    import fasttext
    FASTTEXT_AVAILABLE = True
    
    MODEL_PATH = "lid.176.ftz"
    
    def download_model():
        if os.path.exists(MODEL_PATH):
            return True
        
        urls = [
            "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz",
            "https://huggingface.co/facebook/fasttext-language-identification/resolve/main/lid.176.ftz",
        ]
        
        for url in urls:
            try:
                st.info(f"📥 下载语言检测模型中...")
                urllib.request.urlretrieve(url, MODEL_PATH)
                st.success("✅ 模型下载完成！")
                return True
            except:
                continue
        return False
    
    if not os.path.exists(MODEL_PATH):
        download_model()
    
    if os.path.exists(MODEL_PATH):
        fasttext_model = fasttext.load_model(MODEL_PATH)
    else:
        FASTTEXT_AVAILABLE = False
        
except ImportError:
    FASTTEXT_AVAILABLE = False
    st.warning("⚠️ fasttext 未安装")

# =========================
# 语言映射
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
    "ar": "阿拉伯语",
    "th": "泰语",
    "id": "印尼语",
    "tr": "土耳其语",
    "pl": "波兰语",
    "vi": "越南语"
}

FASTTEXT_LANG_MAP = {
    "en": "en", "es": "es", "pt": "pt", "de": "de",
    "fr": "fr", "it": "it", "ja": "ja", "ko": "ko",
    "zh": "zh", "ru": "ru", "ar": "ar", "th": "th",
    "id": "id", "tr": "tr", "pl": "pl", "vi": "vi"
}

# =========================
# 通用语言检测函数（优化版）
# =========================
def detect_language_universal(text, target_lang, strict=False):
    """
    通用语言检测 - 引入严格模式，并修复单词检测的高误判率
    """
    if not FASTTEXT_AVAILABLE or pd.isna(text) or not str(text).strip():
        return False
    
    # 替换换行符（fastText对换行符很敏感，容易报错或影响判断）
    s = str(text).strip().replace('\n', ' ')
    
    try:
        if strict:
            # 🎯 严格模式：只看整句的第一预测结果（Top-1）
            predictions = fasttext_model.predict(s, k=1)
            label = predictions[0][0].replace("__label__", "")
            if label in FASTTEXT_LANG_MAP and FASTTEXT_LANG_MAP[label] == target_lang:
                return True
            return False
            
        else:
            # 🌊 宽松模式：整句预测的前3名包含目标语言，且置信度达标 (> 0.15)
            predictions = fasttext_model.predict(s, k=3)
            labels = predictions[0]
            scores = predictions[1]
            
            for label, score in zip(labels, scores):
                lang_code = label.replace("__label__", "")
                if lang_code in FASTTEXT_LANG_MAP:
                    detected = FASTTEXT_LANG_MAP[lang_code]
                    if detected == target_lang and score > 0.15: 
                        return True
            
            # 方法2作为兜底：拆分单词检测，但提高门槛防止全量放行
            words = re.findall(r'[a-zA-ZÀ-ÿ]+', s)
            # 过滤掉长度小于3的词（因为1-2个字母测语言纯属随机扔飞镖）
            valid_words = [w for w in words if len(w) >= 3] 
            
            for word in valid_words:
                word_pred = fasttext_model.predict(word, k=1)
                word_label = word_pred[0][0].replace("__label__", "")
                word_score = word_pred[1][0]
                
                if word_label in FASTTEXT_LANG_MAP:
                    detected = FASTTEXT_LANG_MAP[word_label]
                    # 单词级检测必须非常严格，置信度必须大于 0.6 才能作数
                    if detected == target_lang and word_score > 0.6:
                        return True
    except:
        pass
    
    return False

def is_target_language(text, target_lang, second_lang=None, enable_second=False, strict=False):
    if pd.isna(text):
        return True

    s = str(text).strip()

    if len(s) < 2:
        return True

    # 🚨 关键修复：把 strict 参数传递给底层检测函数
    is_match = detect_language_universal(s, target_lang, strict=strict)
    
    # 如果启用第二语言
    if enable_second and second_lang and not is_match:
        is_match = detect_language_universal(s, second_lang, strict=strict)
    
    return is_match

# =========================
# 批量检测
# =========================
def batch_language_detection(
    texts,
    target_lang,
    progress_bar,
    status_text,
    second_lang=None,
    enable_second=False,
    strict=False
):
    results = []
    total = len(texts)
    rejected_count = 0
    kept_count = 0

    batch_size = 100
    
    for i, text in enumerate(texts):
        is_match = is_target_language(text, target_lang, second_lang, enable_second, strict)
        results.append(is_match)
        
        if is_match:
            kept_count += 1
        else:
            rejected_count += 1

        if (i + 1) % batch_size == 0 or i + 1 == total:
            pct = (i + 1) / total
            progress_bar.progress(pct)

            lang_info = f" + {language_options[second_lang]}" if enable_second and second_lang else ""
            status_text.text(
                f"🔍 检测中... {i+1}/{total} ({int(pct*100)}%) | 保留: {kept_count} | 排除: {rejected_count}"
            )

    return results

# =========================
# 其他函数
# =========================
def parse_brands(raw_text):
    if not raw_text:
        return []
    lines = raw_text.splitlines()
    brands = []
    for line in lines:
        line = line.replace(",", " ")
        brands.extend(line.split())
    brands = [x.strip().lower() for x in brands if x.strip()]
    seen = set()
    unique = []
    for b in brands:
        if b not in seen:
            seen.add(b)
            unique.append(b)
    return unique

def batch_brand_filter(texts, brands, progress_bar, status_text):
    if not brands:
        return [True] * len(texts), []
    results = []
    removed_examples = []
    total = len(texts)
    batch_size = 500
    for i, val in enumerate(texts):
        if pd.isna(val):
            results.append(True)
        else:
            s = str(val).lower().strip()
            keep = True
            for brand in brands:
                if (s == brand or 
                    s.startswith(f"{brand} ") or 
                    s.endswith(f" {brand}") or 
                    f" {brand} " in f" {s} "):
                    keep = False
                    if len(removed_examples) < 10:
                        removed_examples.append(f"「{val}」包含品牌词「{brand}」")
                    break
            results.append(keep)
        if (i + 1) % batch_size == 0 or i + 1 == total:
            pct = (i + 1) / total
            progress_bar.progress(pct)
            status_text.text(f"🚫 品牌过滤中... {i+1}/{total} ({int(pct*100)}%)")
    return results, removed_examples

def read_file_smart(uploaded_file):
    if uploaded_file.name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    encodings = ["utf-8", "utf-8-sig", "utf-16", "latin1", "cp1252"]
    separators = [",", "\t", ";", "|"]
    for encoding in encodings:
        for sep in separators:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding=encoding, sep=sep, engine="python")
                if len(df.columns) > 1:
                    return df
            except Exception:
                pass
    try:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, sep=None, engine="python")
    except Exception:
        st.error("❌ 文件解析失败")
        return None

# =========================
# Streamlit UI
# =========================

# 显示状态
if FASTTEXT_AVAILABLE:
    st.sidebar.success("✅ fastText 已就绪")
else:
    st.sidebar.warning("⚠️ fastText 未就绪")

col1, col2 = st.columns(2)
with col1:
    target_language = st.selectbox(
        "🎯 保留哪种主要语言",
        list(language_options.keys()),
        format_func=lambda x: f"{x} - {language_options[x]}"
    )
with col2:
    enable_second_lang = st.checkbox("➕ 启用第二种语言筛选", value=False)

if enable_second_lang:
    col3, col4 = st.columns(2)
    with col3:
        second_language = st.selectbox(
            "🎯 保留第二种语言",
            list(language_options.keys()),
            format_func=lambda x: f"{x} - {language_options[x]}",
            key="second_lang_select"
        )
        if second_language == target_language:
            st.warning("⚠️ 两种语言不能相同")
    with col4:
        skip_lang_detect = st.checkbox("⚡ 跳过语言检测", value=False)
        strict_mode = st.checkbox("🎯 严格模式", value=False)
else:
    with col2:
        skip_lang_detect = st.checkbox("⚡ 跳过语言检测", value=False)
        strict_mode = st.checkbox("🎯 严格模式", value=False)

st.markdown("### 🌐 翻译设置")
col_trans1, col_trans2 = st.columns([1, 2])
with col_trans1:
    enable_translation = st.checkbox("📝 添加英语翻译列", value=False)
with col_trans2:
    if enable_translation:
        st.info("💡 翻译使用 Google Translate API，需要联网")

st.markdown("### 🚫 要删除的品牌词")
brand_text = st.text_area(
    "支持空格、逗号、换行分隔",
    height=100,
    placeholder="wirecast flexi play mirror iphone"
)

uploaded_file = st.file_uploader(
    "📂 上传 CSV 或 Excel 文件",
    type=["csv", "xlsx", "xls"]
)

st.markdown("---")
st.subheader("📊 处理结果")

if uploaded_file is None:
    st.info("📁 请上传文件")
    st.stop()

df = read_file_smart(uploaded_file)
if df is None:
    st.stop()

st.success(f"✅ 文件读取成功，共 {len(df)} 行，{len(df.columns)} 列")
st.write("📋 检测到的列名：", df.columns.tolist())

keyword_column = st.selectbox("📌 请选择关键词所在列", df.columns.tolist())

brands = parse_brands(brand_text)
if brands:
    st.success(f"🔍 品牌词：{', '.join(brands)}")

start_btn = st.button("🚀 一键启动筛选", type="primary", use_container_width=True)

if start_btn:
    if enable_second_lang and second_language == target_language:
        st.error("❌ 两种语言不能相同")
        st.stop()

    with st.spinner("处理中..."):
        progress_bar = st.progress(0)
        status_text = st.empty()

        texts = df[keyword_column].tolist()

        if skip_lang_detect:
            keep_mask = [True] * len(texts)
        else:
            keep_mask = batch_language_detection(
                texts,
                target_language,
                progress_bar,
                status_text,
                second_language if enable_second_lang else None,
                enable_second_lang,
                strict_mode
            )

        df_filtered = df[keep_mask].copy()

        if brands:
            keep_mask, removed_examples = batch_brand_filter(
                df_filtered[keyword_column].tolist(),
                brands,
                progress_bar,
                status_text
            )
            df_filtered = df_filtered[keep_mask].copy()
            if removed_examples:
                with st.expander("📝 被过滤的品牌词示例"):
                    for example in removed_examples:
                        st.write(f"- {example}")

        before_dedup = len(df_filtered)
        df_filtered = df_filtered.drop_duplicates(subset=[keyword_column])
        if before_dedup > len(df_filtered):
            st.info(f"🔄 去重: 移除 {before_dedup - len(df_filtered)} 条")

        if enable_translation and TRANSLATOR_AVAILABLE and len(df_filtered) > 0:
            from deep_translator import GoogleTranslator
            status_text.text("🌐 准备翻译...")
            keywords = df_filtered[keyword_column].tolist()
            translations = []
            total = len(keywords)
            for i, kw in enumerate(keywords):
                try:
                    translator = GoogleTranslator(source='auto', target='en')
                    translated = translator.translate(str(kw))
                    translations.append(translated if translated else "")
                except:
                    translations.append("")
                if (i + 1) % 100 == 0 or i + 1 == total:
                    pct = (i + 1) / total
                    progress_bar.progress(pct)
                    status_text.text(f"🌐 翻译中... {i+1}/{total} ({int(pct*100)}%)")
            
            col_index = df_filtered.columns.get_loc(keyword_column)
            df_filtered.insert(col_index + 1, 'english_translation', translations)
            translated_count = sum(1 for t in translations if t and t.strip())
            st.info(f"✅ 成功翻译 {translated_count}/{len(keywords)} 条")

        progress_bar.progress(1.0)
        status_text.text(f"✅ 筛选完成 | 保留: {len(df_filtered)} 条")
        st.success(f"✨ 最终剩余 {len(df_filtered)} 条关键词")
        st.dataframe(df_filtered.head(100))

        csv_data = df_filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 下载结果 CSV",
            csv_data,
            "filtered_keywords.csv",
            "text/csv",
            use_container_width=True
        )
