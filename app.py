import streamlit as st
import pandas as pd
import re
import time
import hashlib
from collections import Counter

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
# 各语言常见词库（用于辅助判断）
# =========================
LANGUAGE_COMMON_WORDS = {
    "es": {
        'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
        'y', 'o', 'pero', 'por', 'para', 'con', 'sin', 'sobre',
        'de', 'del', 'al', 'a', 'en', 'entre', 'hasta', 'desde',
        'que', 'quien', 'cual', 'cuando', 'donde', 'como', 'porque',
        'es', 'son', 'está', 'están', 'era', 'eran', 'fue', 'fueron',
        'tiene', 'tienen', 'tenía', 'tenían', 'tuvo', 'tuvieron',
        'puede', 'pueden', 'podía', 'podían', 'pudo', 'pudieron',
        'hace', 'hacen', 'hacía', 'hacían', 'hizo', 'hicieron',
        'dice', 'dicen', 'decía', 'decían', 'dijo', 'dijeron',
        'se', 'me', 'te', 'nos', 'os', 'lo', 'le', 'les', 'la', 'las',
        'mi', 'tu', 'su', 'nuestro', 'vuestro', 'sus',
        'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
        'aquel', 'aquella', 'aquellos', 'aquellas',
        'muy', 'mucho', 'poco', 'más', 'menos', 'tan', 'tanto',
        'bien', 'mal', 'si', 'no', 'también', 'tampoco',
        'ser', 'estar', 'tener', 'hacer', 'decir', 'ir', 'ver',
        'poder', 'saber', 'querer', 'llegar', 'llevar', 'dejar',
        'mirar', 'escuchar', 'hablar', 'comer', 'beber', 'vivir',
        'proyector', 'movil', 'telefono', 'pantalla', 'gratis',
        'tv', 'television', 'video', 'audio', 'musica', 'cine',
        'precio', 'producto', 'servicio', 'empresa', 'tienda',
        'conectar', 'configurar', 'descargar', 'instalar',
        'aplicacion', 'juego', 'musica', 'pelicula', 'serie'
    },
    "en": {
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all',
        'can', 'had', 'her', 'was', 'one', 'our', 'out', 'she',
        'who', 'with', 'from', 'have', 'this', 'they', 'will',
        'your', 'about', 'been', 'that', 'what', 'when', 'where',
        'which', 'while', 'would', 'could', 'should', 'might',
        'free', 'mobile', 'tv', 'projector', 'screen', 'video'
    }
}

# 西语特殊字符
SPANISH_SPECIAL_CHARS = {'ñ', 'á', 'é', 'í', 'ó', 'ú', 'ü'}

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
    """翻译文本到英语"""
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

def batch_translate(texts, progress_bar, status_text, delay=0.2):
    """批量翻译"""
    if not TRANSLATOR_AVAILABLE:
        return [""] * len(texts)
    
    results = []
    total = len(texts)
    failed_count = 0
    
    for i, text in enumerate(texts):
        try:
            translated = translate_to_english(text)
            results.append(translated)
            if not translated or len(translated.strip()) == 0:
                failed_count += 1
        except:
            results.append("")
            failed_count += 1
        
        if i % 5 == 0:
            time.sleep(delay)
        
        if (i + 1) % 50 == 0 or i + 1 == total:
            pct = (i + 1) / total
            progress_bar.progress(pct)
            status_text.text(
                f"🌐 翻译中... {i+1}/{total} ({int(pct*100)}%)"
            )
    
    return results

# =========================
# 增强的语言检测函数
# =========================
def detect_language_with_confidence(text, target_lang):
    """
    检测文本语言并返回置信度评分
    返回: (语言代码, 置信度分数 0-1)
    """
    if pd.isna(text) or not str(text).strip():
        return None, 0
    
    s = str(text).strip().lower()
    words = re.findall(r'\b[a-zA-Záéíóúüñ]+(?:['"\-][a-zA-Z]+)*\b', s)
    
    if not words:
        return None, 0
    
    # 1. 使用 lingua 检测
    lingua_detected = None
    try:
        detected = detector.detect_language_of(s)
        if detected:
            lingua_detected = detected.name.lower()
    except:
        pass
    
    # 2. 统计各语言词频
    lang_scores = {}
    
    for lang_code, common_words in LANGUAGE_COMMON_WORDS.items():
        match_count = sum(1 for word in words if word in common_words)
        if words:
            score = match_count / len(words)
            lang_scores[lang_code] = score
    
    # 3. 西语特殊字符加分
    if target_lang == "es" or "es" in lang_scores:
        special_count = sum(1 for char in s if char in SPANISH_SPECIAL_CHARS)
        if special_count > 0:
            lang_scores["es"] = lang_scores.get("es", 0) + min(special_count * 0.05, 0.3)
    
    # 4. 如果 lingua 检测到了，给予权重
    if lingua_detected and lingua_detected[:2] in lang_scores:
        lang_scores[lingua_detected[:2]] = lang_scores.get(lingua_detected[:2], 0) + 0.3
    
    # 5. 检查是否包含目标语言的关键词特征
    # 例如：西语中的"en español"、"gratis"等
    if target_lang == "es":
        spanish_markers = ['en español', 'gratis', 'proyector', 'movil', 'telefono']
        marker_count = sum(1 for marker in spanish_markers if marker in s)
        if marker_count > 0:
            lang_scores["es"] = lang_scores.get("es", 0) + min(marker_count * 0.1, 0.3)
    
    # 6. 如果文本包含多个语言词，选择得分最高的
    if lang_scores:
        best_lang = max(lang_scores, key=lang_scores.get)
        best_score = lang_scores[best_lang]
        
        # 如果得分超过阈值，返回该语言
        if best_score >= 0.15:  # 降低阈值，让混合语言也能被识别
            return best_lang, min(best_score, 1.0)
    
    return None, 0

def is_target_language(text, target_lang, second_lang=None, enable_second=False, strict=False):
    """
    增强的语言检测，能识别混合语言
    """
    if pd.isna(text):
        return True

    s = str(text).strip()

    # 空文本或太短的文本
    if len(s) < 2:
        return True

    # 使用增强检测
    detected_lang, confidence = detect_language_with_confidence(s, target_lang)
    
    if detected_lang is None:
        # 如果检测失败，在严格模式下返回False
        return not strict
    
    # 检查是否匹配目标语言
    is_match = detected_lang == target_lang
    
    # 如果启用第二语言
    if enable_second and second_lang:
        is_match = is_match or (detected_lang == second_lang)
    
    # 如果匹配，但置信度太低，在严格模式下拒绝
    if is_match and strict and confidence < 0.2:
        return False
    
    return is_match

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

    for i, text in enumerate(texts):
        is_match = is_target_language(text, target_lang, second_lang, enable_second, strict)
        results.append(is_match)
        
        if is_match:
            kept_count += 1
        else:
            rejected_count += 1

        if (i + 1) % 200 == 0 or i + 1 == total:
            pct = (i + 1) / total
            progress_bar.progress(pct)

            lang_info = f" + {language_options[second_lang]}" if enable_second and second_lang else ""
            status_text.text(
                f"🔍 检测中... {i+1}/{total} ({int(pct*100)}%) | 保留: {kept_count} | 排除: {rejected_count} | 目标: {language_options[target_lang]}{lang_info}"
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

        if (i + 1) % 500 == 0 or i + 1 == total:
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
            value=False,  # 默认关闭，让混合语言能被保留
            help="开启后会过滤掉混合语言文本，关闭则保留包含目标语言的混合文本"
        )
else:
    with col2:
        skip_lang_detect = st.checkbox("⚡ 跳过语言检测", value=False)
        strict_mode = st.checkbox(
            "🎯 严格模式", 
            value=False,
            help="开启后会过滤掉混合语言文本，关闭则保留包含目标语言的混合文本"
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
                sample_texts = df_filtered[keyword_column].head(1000).tolist()
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
        status_text.text(f"✅ 筛选完成 | 保留: {len(df_filtered)} 条 | 语言: {language_options[target_language]}{lang_info}")

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
