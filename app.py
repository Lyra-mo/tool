import streamlit as st
import pandas as pd
import re
import time
import hashlib

from lingua import Language, LanguageDetectorBuilder

# 尝试导入翻译库
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False

# =========================
# 页面配置
# =========================
st.set_page_config(page_title="关键词筛选工具", layout="wide")
st.title("🔧 关键词筛选工具")

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

lingua_map = {
    "en": Language.ENGLISH,
    "pt": Language.PORTUGUESE,
    "es": Language.SPANISH,
    "de": Language.GERMAN,
    "fr": Language.FRENCH,
    "it": Language.ITALIAN,
    "ja": Language.JAPANESE,
    "ko": Language.KOREAN,
    "zh": Language.CHINESE,
    "ru": Language.RUSSIAN,
    "ar": Language.ARABIC,
    "th": Language.THAI,
    "id": Language.INDONESIAN,
    "tr": Language.TURKISH,
    "pl": Language.POLISH,
    "vi": Language.VIETNAMESE
}

# =========================
# 构建检测器
# =========================
detector = LanguageDetectorBuilder.from_languages(
    *lingua_map.values()
).build()

# =========================
# 翻译缓存
# =========================
translation_cache = {}

def get_cache_key(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def translate_to_english(text):
    if not TRANSLATOR_AVAILABLE:
        return ""
    
    if pd.isna(text) or not str(text).strip():
        return ""
    
    text = str(text).strip()
    
    try:
        detected = detector.detect_language_of(text)
        if detected == Language.ENGLISH:
            return text
    except:
        pass
    
    cache_key = get_cache_key(text)
    if cache_key in translation_cache:
        return translation_cache[cache_key]
    
    try:
        translator = GoogleTranslator(source='auto', target='en')
        translated = translator.translate(text)
        if translated and len(translated.strip()) > 0:
            translation_cache[cache_key] = translated
            return translated
    except Exception:
        pass
    
    translation_cache[cache_key] = ""
    return ""

def batch_translate(texts, progress_bar, status_text, delay=0.15):
    if not TRANSLATOR_AVAILABLE:
        return [""] * len(texts)
    
    results = []
    total = len(texts)
    
    for i, text in enumerate(texts):
        try:
            translated = translate_to_english(text)
            results.append(translated)
        except:
            results.append("")
        
        if i % 10 == 0:
            time.sleep(delay)
        
        if (i + 1) % 100 == 0 or i + 1 == total:
            pct = (i + 1) / total
            progress_bar.progress(pct)
            status_text.text(
                f"🌐 翻译中... {i+1}/{total} ({int(pct*100)}%)"
            )
    
    return results

# =========================
# 语言检测函数（稳定版）
# =========================
def detect_language(text, target_lang, second_lang=None, enable_second=False):
    """
    使用 lingua 进行语言检测，并处理特殊情况
    """
    if pd.isna(text) or not str(text).strip():
        return True
    
    s = str(text).strip()
    
    # 太短的文本直接保留（避免误判）
    if len(s) < 3:
        return True
    
    try:
        # 使用 lingua 检测
        detected = detector.detect_language_of(s)
        
        if detected is None:
            # 无法检测时，检查是否包含目标语言特征
            return False
        
        detected_code = detected.name.lower()
        
        # 检查是否匹配主要语言
        is_match = (detected_code == target_lang)
        
        # 如果启用第二语言
        if enable_second and second_lang:
            is_match = is_match or (detected_code == second_lang)
        
        return is_match
        
    except Exception as e:
        # 检测出错时，保守处理：保留文本
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
        is_match = detect_language(text, target_lang, second_lang, enable_second)
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
# 其他函数（保持不变）
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
            help="开启后更严格地过滤语言"
        )
else:
    with col2:
        skip_lang_detect = st.checkbox("⚡ 跳过语言检测", value=False)
        strict_mode = st.checkbox(
            "🎯 严格模式", 
            value=False,
            help="开启后更严格地过滤语言"
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
                    try:
                        detected = detector.detect_language_of(str(text).strip()[:100])
                        if detected:
                            lang_name = detected.name.lower()
                            lang_counts[lang_name] = lang_counts.get(lang_name, 0) + 1
                    except:
                        pass
                
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
