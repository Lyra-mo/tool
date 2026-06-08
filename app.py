import streamlit as st
import pandas as pd
import re

# =========================
# 基础配置
# =========================
st.set_page_config(page_title="关键词清洗工具", layout="wide")

# =========================
# 参数（避免 NameError）
# =========================
target_language = st.selectbox("目标语言", ["zh", "en", "ja", "ko"], index=0)
brand_text = st.text_area("品牌词（每行一个，可选）")


# =========================
# 工具函数
# =========================
def match_language(text, target_language):
    if pd.isna(text):
        return False

    text = str(text)

    if target_language == "zh":
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    if target_language == "en":
        return bool(re.search(r'[a-zA-Z]', text))

    if target_language == "ja":
        return bool(re.search(r'[\u3040-\u30ff\u31f0-\u31ff]', text))

    if target_language == "ko":
        return bool(re.search(r'[\uac00-\ud7af]', text))

    return True


def contains_brand(text, brands):
    if pd.isna(text):
        return False
    text = str(text).lower()
    return any(b in text for b in brands)


# =========================
# 文件上传
# =========================
uploaded_file = st.file_uploader("上传文件（CSV / Excel）", type=["csv", "xlsx"])

if uploaded_file is not None:

    # =========================
    # 读取文件
    # =========================
    if uploaded_file.name.endswith(".csv"):
        try:
            df = pd.read_csv(uploaded_file)
        except Exception:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding="latin1")
    else:
        df = pd.read_excel(uploaded_file)

    # =========================
    # 清理列名
    # =========================
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace("\ufeff", "", regex=False)
    )

    st.write("📌 实际列名：")
    st.write(df.columns.tolist())

    # =========================
    # 必要列
    # =========================
    keep_columns = [
        "原搜索词",
        "英文语义",
        "检测语言",
        "访问用户",
        "安装用户",
        "转化率"
    ]

    missing = [c for c in keep_columns if c not in df.columns]

    if missing:
        st.error(f"缺少列: {missing}")
        st.stop()

    df = df[keep_columns].copy()

    original_count = len(df)

    # =========================
    # 语言过滤
    # =========================
    lang_filtered = df[
        df["原搜索词"].apply(
            lambda x: match_language(x, target_language)
        )
    ].copy()

    removed_language = original_count - len(lang_filtered)

    # =========================
    # 品牌词过滤
    # =========================
    brands = [
        x.strip().lower()
        for x in brand_text.splitlines()
        if x.strip()
    ]

    before_brand = len(lang_filtered)

    if brands:
        lang_filtered = lang_filtered[
            ~lang_filtered["原搜索词"].apply(
                lambda x: contains_brand(x, brands)
            )
        ]

    removed_brand = before_brand - len(lang_filtered)

    # =========================
    # 去重
    # =========================
    before_dedup = len(lang_filtered)

    lang_filtered = lang_filtered.drop_duplicates(subset=["原搜索词"])

    removed_dup = before_dedup - len(lang_filtered)

    # =========================
    # 输出结果
    # =========================
    st.subheader("处理结果")

    st.write(f"原始关键词：{original_count}")
    st.write(f"删除非目标语言：{removed_language}")
    st.write(f"删除品牌词：{removed_brand}")
    st.write(f"删除重复词：{removed_dup}")
    st.write(f"剩余关键词：{len(lang_filtered)}")

    st.dataframe(lang_filtered.head(50))

    # =========================
    # 下载
    # =========================
    csv_data = lang_filtered.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "下载结果 CSV",
        csv_data,
        file_name="filtered_keywords.csv",
        mime="text/csv"
    )