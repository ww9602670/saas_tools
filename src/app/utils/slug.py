# 店铺名→文件名 slugify 规则（保留中英文/数/-/_，其他→_）

# slug.py
import re, unicodedata
def slugify(name:str, max_len=64):
    s = unicodedata.normalize("NFKC", name.strip())
    s = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", s)  # 保留中英文、数字、下划线、连字符
    s = re.sub(r"_+", "_", s).strip("_.-")
    return s[:max_len] or "shop"
