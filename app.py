import streamlit as st
import pandas as pd
from langdetect import detect
import time
import re

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

# =========================
# 品牌词输入
# =========================
st.markdown("### 🚫 要删除的品牌词（包含这些词的关键词会被整行删除）")
brand_text = st.text_area(
    "支持空格、逗号、换行分隔",
    height=100,
    placeholder="格力 tcl 创维 松下 海信 美的 海尔"
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
# 🔧 修复后的语言检测函数
# =========================
def batch_language_detection(texts, target_lang, progress_bar, status_text):
    """修复版：不跳过空值，检测失败时用字符集兜底"""
    results = []
    total = len(texts)
    
    for i, val in enumerate(texts):
        # 统一转为字符串，空值也处理
        if pd.isna(val):
            s = ""
        else:
            s = str(val).strip()
        
        # 空字符串或太短（<2个字符）→ 保留，让后续去重处理
        if len(s) < 2:
            results.append(True)
        else:
            try:
                # 用 langdetect 检测
                detected = detect(s)
                results.append(detected == target_lang)
            except:
                # ⚡ 检测失败时，用字符集兜底判断
                # 统计英文字母占比
                letters_only = re.sub(r'[^a-zA-Z]', '', s)
                if len(letters_only) == 0:
                    # 没有英文字母 → 非英语，删除
                    results.append(False)
                else:
                    # 计算英文字母占所有字母的比例
                    all_letters = re.findall(r'[a-zA-ZÀ-ÿ]', s)
                    if len(all_letters) == 0:
                        results.append(False)
                    else:
                        ratio = len(letters_only) / len(all_letters)
                        # 如果目标是英语，英文字母占比 > 70% 就保留
                        results.append(ratio > 0.7 if target_lang == "en" else True)
        
        # 更新进度
        if (i+1) % 200 == 0 or i+1 == total:
            progress_bar.progress((i+1)/total)
            status_text.text(f"🔍 语言检测中... {i+1}/{total} ({int((i+1)/total*100)}%)")
    
    return results

# =========================
# 品牌过滤函数（优化版）
# =========================
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
            s = str(val).lower()
            keep = True
            for brand in brands:
                # 🔧 用完整词匹配，避免误杀短词
                if f" {brand} " in f" {s} " or s == brand or s.startswith(f"{brand} ") or s.endswith(f" {brand}"):
                    keep = False
                    if len(removed_examples) < 10:
                        removed_examples.append(f"「{val}」包含品牌词「{brand}」")
                    break
            results.append(keep)
        
        if (i+1) % 500 == 0 or i+1 == total:
            progress_bar.progress((i+1)/total)
            status_text.text(f"🚫 品牌过滤中... {i+1}/{total} ({int((i+1)/total*100)}%)")
    
    return results, removed_examples

# =========================
# 智能读取 CSV
# =========================
def read_csv_smart(uploaded_file):
    """智能读取 CSV，自动尝试多种分隔符和编码"""
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
        df = pd.read_csv(
            uploaded_file, 
            encoding="utf-8", 
            engine="python", 
            sep=None,
            on_bad_lines="skip"
        )
        if len(df.columns) > 1:
            return df
    except:
        pass
    
    return None

# =========================
# 主逻辑
# =========================
if uploaded_file is not None:
    # 读取文件
    with st.spinner("读取文件中..."):
        if uploaded_file.name.endswith(".csv"):
            df = read_csv_smart(uploaded_file)
            if df is None:
                st.error("❌ 无法读取 CSV 文件，请检查文件格式是否正确")
                st.stop()
        else:
            try:
                df = pd.read_excel(uploaded_file)
            except Exception as e:
                st.error(f"❌ 读取 Excel 文件失败：{e}")
                st.stop()
        
        df.columns = df.columns.astype(str).str.strip().str.replace("\ufeff", "", regex=False)

    st.success(f"✅ 文件读取成功，共 {len(df)} 行，{len(df.columns)} 列")
    st.write("实际列名：", df.columns.tolist())

    keyword_column = st.selectbox("📌 请选择关键词所在的列", df.columns.tolist())
    original_count = len(df)

    brands = parse_brands(brand_text)
    if brands:
        st.success(f"🔍 识别到的品牌词（将删除包含它们的行）：**{', '.join(brands)}**")
    else:
        st.info("未输入品牌词，将跳过品牌过滤")

    with st.expander("📋 点击查看原始数据前20行"):
        st.dataframe(df.head(20))

    st.markdown("---")
    start_btn = st.button("🚀 一键启动筛选", type="primary", use_container_width=True)

    if start_btn:
        working_df = df.copy()
        progress_bar = st.progress(0)
        status_text = st.empty()

        removed_lang = 0
        removed_brand = 0
        removed_dup = 0
        removed_lang_examples = []
        removed_brand_examples = []

        # ---------- 1. 语言过滤 ----------
        if not skip_lang_detect:
            status_text.text("准备语言检测...")
            time.sleep(0.3)
            texts = working_df[keyword_column].tolist()
            keep_mask = batch_language_detection(texts, target_language, progress_bar, status_text)
            
            # 收集被删除的样例
            for i, (val, keep) in enumerate(zip(texts, keep_mask)):
                if not keep and len(removed_lang_examples) < 10:
                    s = str(val) if not pd.isna(val) else ""
                    removed_lang_examples.append(f"「{s}」不是目标语言")
            
            before = len(working_df)
            working_df = working_df[keep_mask].copy()
            removed_lang = before - len(working_df)
            status_text.text(f"✅ 语言过滤完成：删除 {removed_lang} 条，剩余 {len(working_df)} 条")
            time.sleep(0.5)
            progress_bar.empty()
            progress_bar = st.progress(0)
        else:
            status_text.text("⏭️ 跳过语言检测")
            time.sleep(0.5)

        # ---------- 2. 品牌过滤 ----------
        if brands:
            status_text.text("准备品牌过滤...")
            time.sleep(0.3)
            texts = working_df[keyword_column].tolist()
            keep_mask, removed_brand_examples = batch_brand_filter(texts, brands, progress_bar, status_text)
            before = len(working_df)
            working_df = working_df[keep_mask].copy()
            removed_brand = before - len(working_df)
            status_text.text(f"✅ 品牌过滤完成：删除 {removed_brand} 条，剩余 {len(working_df)} 条")
            time.sleep(0.5)
            progress_bar.empty()
            progress_bar = st.progress(0)
        else:
            status_text.text("⏭️ 未输入品牌词，跳过品牌过滤")
            time.sleep(0.5)

        # ---------- 3. 去重 ----------
        status_text.text("准备去重...")
        time.sleep(0.3)
        before = len(working_df)
        for p in range(0, 101, 25):
            progress_bar.progress(p/100)
            status_text.text(f"🔄 去重中... {p}%")
            time.sleep(0.03)
        working_df = working_df.drop_duplicates(subset=[keyword_column]).copy()
        removed_dup = before - len(working_df)
        status_text.text(f"✅ 去重完成：删除 {removed_dup} 条，剩余 {len(working_df)} 条")
        time.sleep(0.5)
        progress_bar.progress(1.0)
        status_text.text("🎉 处理完成！")

        # ---------- 显示被删除样例 ----------
        if removed_lang_examples:
            with st.expander("🔍 被语言检测删除的关键词样例（前10个）"):
                for ex in removed_lang_examples:
                    st.write(f"- {ex}")
        if removed_brand_examples:
            with st.expander("🔍 被品牌过滤删除的关键词样例（前10个）"):
                for ex in removed_brand_examples:
                    st.write(f"- {ex}")

        # ---------- 结果汇总 ----------
        st.markdown("---")
        st.subheader("📈 处理结果汇总")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("原始关键词", original_count)
        c2.metric("删除的非目标语言", removed_lang if not skip_lang_detect else "跳过")
        c3.metric("删除的品牌词", removed_brand)
        c4.metric("删除的重复词", removed_dup)
        st.success(f"✨ 最终剩余关键词：{len(working_df)} 条")

        with st.expander("🔍 点击预览结果（前100行）"):
            st.dataframe(working_df.head(100))

        if len(working_df) > 0:
            csv_data = working_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 下载结果 CSV",
                data=csv_data,
                file_name="filtered_keywords.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("⚠️ 没有剩余关键词，请检查过滤条件是否过严")
    else:
        st.info("👆 点击上方按钮开始处理数据")
else:
    st.info("📁 请先上传 CSV 或 Excel 文件")
