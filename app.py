import streamlit as st
import pandas as pd
import re
import time
import hashlib
import os
import urllib.request

# 尝试导入翻译库
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
    
    # 使用轻量模型（7MB），如果下载失败则使用完整版（130MB）
    MODEL_PATH = "lid.176.ftz"  # 优先使用轻量版
    FALLBACK_MODEL = "lid.176.bin"
    
    def download_model():
        """下载 fastText 模型（自动选择轻量版）"""
        if os.path.exists(MODEL_PATH):
            return True
        
        # 尝试下载轻量版（7MB）
        urls = [
            "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz",
            "https://huggingface.co/facebook/fasttext-language-identification/resolve/main/lid.176.ftz",
        ]
        
        for url in urls:
            try:
                st.info(f"📥 下载语言检测模型（7MB）...")
                urllib.request.urlretrieve(url, MODEL_PATH)
                st.success("✅ 模型下载完成！")
                return True
            except:
                continue
        
        # 如果轻量版下载失败，尝试完整版
        try:
            st.info("📥 下载完整模型（130MB），请耐心等待...")
            url = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"
            urllib.request.urlretrieve(url, FALLBACK_MODEL)
            st.success("✅ 完整模型下载完成！")
            return True
        except Exception as e:
            st.error(f"❌ 模型下载失败: {e}")
            return False
    
    # 下载模型
    if not os.path.exists(MODEL_PATH) and not os.path.exists(FALLBACK_MODEL):
        if not download_model():
            FASTTEXT_AVAILABLE = False
    
    # 加载模型
    if FASTTEXT_AVAILABLE:
        try:
            model_path = MODEL_PATH if os.path.exists(MODEL_PATH) else FALLBACK_MODEL
            fasttext_model = fasttext.load_model(model_path)
        except:
            FASTTEXT_AVAILABLE = False
            
except ImportError:
    FASTTEXT_AVAILABLE = False
    st.warning("⚠️ fasttext 未安装，将使用备用检测方案")

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

# fastText 语言代码映射
FASTTEXT_LANG_MAP = {
    "en": "en",
    "es": "es",
    "pt": "pt",
    "de": "de",
    "fr": "fr",
    "it": "it",
    "ja": "ja",
    "ko": "ko",
    "zh": "zh",
    "ru": "ru",
    "ar": "ar",
    "th": "th",
    "id": "id",
    "tr": "tr",
    "pl": "pl",
    "vi": "vi"
}

# =========================
# 语言检测函数（使用 fastText）
# =========================
def detect_language_fasttext(text):
    """
    使用 fastText 检测语言
    返回: (语言代码, 置信度)
    """
    if not FASTTEXT_AVAILABLE or pd.isna(text) or not str(text).strip():
        return None, 0
    
    s = str(text).strip()
    
    # 太短的文本，fastText 可能不准确，但仍尝试检测
    if len(s) < 2:
        return None, 0
    
    try:
        # fastText 预测
        predictions = fasttext_model.predict(s, k=3)  # 返回前3个预测结果
        
        # 解析结果
        labels = predictions[0]
        scores = predictions[1]
        
        for label, score in zip(labels, scores):
            # 提取语言代码（格式: __label__en）
            lang_code = label.replace("__label__", "")
            if lang_code in FASTTEXT_LANG_MAP:
                return FASTTEXT_LANG_MAP[lang_code], score
        
        return None, 0
        
    except Exception as e:
        return None, 0

def is_target_language(text, target_lang, second_lang=None, enable_second=False, strict=False):
    """
    语言检测主函数
    """
    if pd.isna(text):
        return True

    s = str(text).strip()

    if len(s) < 2:
        return True

    # 使用 fastText 检测
    detected_lang, confidence = detect_language_fasttext(s)
    
    if detected_lang is None:
        # 如果 fastText 无法检测，使用备用方案：检查字符集
        return fallback_detection(s, target_lang, second_lang, enable_second)
    
    # 检查是否匹配主要语言
    is_match = (detected_lang == target_lang)
    
    # 如果启用第二语言
    if enable_second and second_lang:
        is_match = is_match or (detected_lang == second_lang)
    
    # 严格模式：置信度低于阈值则拒绝
    if strict and confidence < 0.5:
        return False
    
    return is_match

def fallback_detection(text, target_lang, second_lang=None, enable_second=False):
    """
    备用检测方案（当 fastText 无法检测时使用）
    基于字符集和常见词汇
    """
    s = str(text).lower()
    
    # 西语特征
    spanish_chars = {'ñ', 'á', 'é', 'í', 'ó', 'ú', 'ü'}
    spanish_words = {'el', 'la', 'los', 'las', 'de', 'en', 'que', 'y', 'o', 'por', 'para', 'con', 'sin', 'sobre', 'del', 'al', 'es', 'son', 'fue', 'fueron', 'tiene', 'puede', 'hace', 'se', 'me', 'te', 'nos', 'lo', 'le', 'les', 'mi', 'tu', 'su', 'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'muy', 'mucho', 'poco', 'mas', 'menos', 'bien', 'mal', 'si', 'no'}
    
    # 检查西语特殊字符
    has_spanish_char = any(char in s for char in spanish_chars)
    
    # 检查西语常见词
    words = re.findall(r'[a-záéíóúüñ]+', s)
    spanish_word_count = sum(1 for word in words if word in spanish_words)
    
    # 判断是否为西语
    is_spanish = has_spanish_char or spanish_word_count >= 1
    
    # 英语特征：纯 ASCII + 常见英语词
    english_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'with', 'from', 'have', 'this', 'they', 'will', 'your', 'about', 'been', 'that', 'what', 'when', 'where', 'which'}
    is_ascii = all(ord(c) < 128 for c in s)
    english_word_count = sum(1 for word in words if word in english_words)
    is_english = is_ascii and (english_word_count >= 1 or len(words) > 0)
    
    # 根据目标语言返回结果
    if target_lang == "es":
        return is_spanish
    elif target_lang == "en":
        return is_english
    elif enable_second and second_lang:
        if target_lang == "es" and second_lang == "en":
            return is_spanish or is_english
        elif target_lang == "en" and second_lang == "es":
            return is_english or is_spanish
    
    # 默认返回 True（保留）
    return True

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

# 显示 fastText 状态
if FASTTEXT_AVAILABLE:
    st.sidebar.success("✅ fastText 已就绪")
else:
    st.sidebar.warning("⚠️ fastText 未就绪，将使用备用检测")

# 语言选择
col1, col2 = st.columns(2)

with col1:
    target_language = st.selectbox(
        "🎯 保留哪种主要语言",
        list(language_options.keys()),
        format_func=lambda x: f"{x} - {language_options[x]}"
    )

with col2:
    enable_second_lang = st.checkbox(
        "➕ 启用第二种语言筛选",
        value=False
    )

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
        strict_mode = st.checkbox(
            "🎯 严格模式", 
            value=False,
            help="开启后更严格地过滤语言（置信度低于50%将被拒绝）"
        )
else:
    with col2:
        skip_lang_detect = st.checkbox("⚡ 跳过语言检测", value=False)
        strict_mode = st.checkbox(
            "🎯 严格模式", 
            value=False,
            help="开启后更严格地过滤语言（置信度低于50%将被拒绝）"
        )

# 翻译选项
st.markdown("### 🌐 翻译设置")
col_trans1, col_trans2 = st.columns([1, 2])
with col_trans1:
    enable_translation = st.checkbox("📝 添加英语翻译列", value=False)
with col_trans2:
    if enable_translation:
        st.info("💡 翻译使用 Google Translate API，需要联网")

# 品牌词
st.markdown("### 🚫 要删除的品牌词")
brand_text = st.text_area(
    "支持空格、逗号、换行分隔",
    height=100,
    placeholder="wirecast flexi play mirror iphone"
)

# 文件上传
uploaded_file = st.file_uploader(
    "📂 上传 CSV 或 Excel 文件",
    type=["csv", "xlsx", "xls"]
)

# =========================
# 主流程
# =========================
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

        # 语言过滤
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

        # 显示语言分布
        if not skip_lang_detect and len(df_filtered) > 0:
            with st.expander("📊 筛选后的语言分布"):
                sample_texts = df_filtered[keyword_column].head(500).tolist()
                lang_counts = {}
                for text in sample_texts:
                    if pd.isna(text):
                        continue
                    detected_lang, _ = detect_language_fasttext(str(text).strip()[:100])
                    if detected_lang:
                        lang_counts[detected_lang] = lang_counts.get(detected_lang, 0) + 1
                
                if lang_counts:
                    lang_df = pd.DataFrame(
                        list(lang_counts.items()),
                        columns=["语言", "数量"]
                    ).sort_values("数量", ascending=False)
                    st.dataframe(lang_df)

        # 品牌过滤
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

        # 去重
        before_dedup = len(df_filtered)
        df_filtered = df_filtered.drop_duplicates(subset=[keyword_column])
        if before_dedup > len(df_filtered):
            st.info(f"🔄 去重: 移除 {before_dedup - len(df_filtered)} 条")

        # 翻译
        if enable_translation and TRANSLATOR_AVAILABLE and len(df_filtered) > 0:
            status_text.text("🌐 准备翻译...")
            keywords = df_filtered[keyword_column].tolist()
            translations = batch_translate(keywords, progress_bar, status_text)
            
            col_index = df_filtered.columns.get_loc(keyword_column)
            df_filtered.insert(col_index + 1, 'english_translation', translations)
            
            translated_count = sum(1 for t in translations if t and t.strip())
            st.info(f"✅ 成功翻译 {translated_count}/{len(keywords)} 条")

        progress_bar.progress(1.0)
        
        lang_info = f" + {language_options[second_language]}" if enable_second_lang and second_language else ""
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
