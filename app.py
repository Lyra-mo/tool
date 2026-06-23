import requests

def is_english(text: str) -> bool:
    """
    使用 LibreTranslate 公共 API 检测文本是否为英语
    """
    if not text or len(text.strip()) < 2:
        return True
    
    s = text.strip()
    
    # ===== 第一关：快速字符集检测 =====
    # 检查非拉丁字符（中文、日文、韩文、阿拉伯文、俄文等）
    non_latin_pattern = re.compile(
        r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0600-\u06ff\u0400-\u04ff]'
    )
    if non_latin_pattern.search(s):
        return False
    
    # 检查变音符号（西班牙语、法语、葡萄牙语等）
    accent_pattern = re.compile(r'[áéíóúñüçãõàèìòù]', re.IGNORECASE)
    if accent_pattern.search(s):
        return False
    
    # ===== 第二关：LibreTranslate API 检测 =====
    try:
        response = requests.post(
            "https://libretranslate.com/detect",
            json={"q": s},
            timeout=3  # 3秒超时
        )
        if response.status_code == 200:
            result = response.json()
            if result and len(result) > 0:
                # 取置信度最高的语言
                best = result[0]
                return best.get("language") == "en" and best.get("confidence", 0) > 0.7
    except Exception as e:
        # API 调用失败，走兜底
        pass
    
    # ===== 第三关：字符集兜底 =====
    # 统计英文字母占比
    english_letters = len(re.findall(r'[a-zA-Z]', s))
    total_chars = len(re.sub(r'[0-9\s\W_]', '', s))
    if total_chars == 0:
        return True
    ratio = english_letters / total_chars
    return ratio > 0.7
