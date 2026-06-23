import streamlit as st
import pandas as pd
import re

from lingua import Language, LanguageDetectorBuilder

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
    "ar": "阿拉伯语"
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
    "ar": Language.ARABIC
}

# 构建检测器（只检测支持的语言，速度更快）
detector = LanguageDetectorBuilder.from_languages(
    *lingua_map.values()
).build()

# =========================
# 语言选择
# =========================
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
        help="如果文件已经全部是目标语言，可以跳过检测"
    )

# =========================
# 品牌词
# =========================
st.markdown("### 🚫 要删除的品牌词")

brand_text = st.text_area(
    "支持空格、逗号、换行分隔",
    height=100,
    placeholder="wirecast flexi play mirror iphone"
)

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

# =========================
# 文件上传
# =========================
uploaded_file = st.file_uploader(
    "📂 上传 CSV 或 Excel 文件",
    type=["csv", "xlsx", "xls"]
)

# =========================
# 语言检测
# =========================
def is_target_language(text, target_lang):

    if pd.isna(text):
        return True

    s = str(text).strip()

    if len(s) < 2:
        return True

    try:
        detected = detector.detect_language_of(s)

        if detected is None:
            return False

        return detected == lingua_map[target_lang]

    except Exception:
        return False

def batch_language_detection(
    texts,
    target_lang,
    progress_bar,
    status_text
):
    results = []

    total = len(texts)

    for i, text in enumerate(texts):

        results.append(
            is_target_language(text, target_lang)
        )

        if (i + 1) % 200 == 0 or i + 1 == total:
            pct = (i + 1) / total

            progress_bar.progress(pct)

            status_text.text(
                f"🔍 语言检测中... {i+1}/{total} ({int(pct*100)}%)"
            )

    return results

# =========================
# 品牌过滤
# =========================
def batch_brand_filter(
    texts,
    brands,
    progress_bar,
    status_text
):

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

                if (
                    s == brand
                    or s.startswith(f"{brand} ")
                    or s.endswith(f" {brand}")
                    or f" {brand} " in f" {s} "
                ):
                    keep = False

                    if len(removed_examples) < 10:
                        removed_examples.append(
                            f"「{val}」包含品牌词「{brand}」"
                        )

                    break

            results.append(keep)

        if (i + 1) % 500 == 0 or i + 1 == total:

            pct = (i + 1) / total

            progress_bar.progress(pct)

            status_text.text(
                f"🚫 品牌过滤中... {i+1}/{total} ({int(pct*100)}%)"
            )

    return results, removed_examples

# =========================
# 智能读取文件
# =========================
def read_file_smart(uploaded_file):

    if uploaded_file.name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)

    encodings = [
        "utf-8",
        "utf-8-sig",
        "utf-16",
        "latin1",
        "cp1252"
    ]

    separators = [
        ",",
        "\t",
        ";",
        "|"
    ]

    for encoding in encodings:
        for sep in separators:

            try:
                uploaded_file.seek(0)

                df = pd.read_csv(
                    uploaded_file,
                    encoding=encoding,
                    sep=sep,
                    engine="python"
                )

                if len(df.columns) > 1:
                    return df

            except Exception:
                pass

    try:
        uploaded_file.seek(0)

        return pd.read_csv(
            uploaded_file,
            sep=None,
            engine="python"
        )

    except Exception:

        st.error("❌ 文件解析失败")

        return None

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

st.success(
    f"✅ 文件读取成功，共 {len(df)} 行，{len(df.columns)} 列"
)

st.write(
    "📋 检测到的列名：",
    df.columns.tolist()
)

keyword_column = st.selectbox(
    "📌 请选择关键词所在列",
    df.columns.tolist()
)

brands = parse_brands(brand_text)

if brands:
    st.success(
        f"🔍 品牌词：{', '.join(brands)}"
    )

start_btn = st.button(
    "🚀 一键启动筛选",
    type="primary",
    use_container_width=True
)

if start_btn:

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
                status_text
            )

        df_filtered = df[keep_mask].copy()

        # 品牌过滤
        if brands:

            keep_mask, removed_examples = batch_brand_filter(
                df_filtered[keyword_column].tolist(),
                brands,
                progress_bar,
                status_text
            )

            df_filtered = df_filtered[keep_mask].copy()

        # 去重
        df_filtered = df_filtered.drop_duplicates(
            subset=[keyword_column]
        )

        progress_bar.progress(1.0)

        status_text.text("✅ 筛选完成")

        st.success(
            f"✨ 剩余 {len(df_filtered)} 条关键词"
        )

        st.dataframe(df_filtered.head(100))

        csv_data = df_filtered.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "📥 下载结果 CSV",
            csv_data,
            "filtered_keywords.csv",
            "text/csv",
            use_container_width=True
        )
