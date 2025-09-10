# 站点URL、选择器、默认等待/超时、错误码枚举
# constants.py
DOUDIAN = {
    "login_url": "https://fxg.jinritemai.com/ffa/mshop/login",   # 示例入口，按你们现用URL替换
    "qr_selector": "img.qrcode, canvas.qrcode, div.qrcode img",  # 兜底写法，实际以现有为准
    "shop_name_selector": 'div.index_userName__16Isl[data-bytereplay-mask="true"]',
    "qr_refresh_button": "button.account-center-code-expired-refresh",
    "qr_ttl_seconds": 60,
    "logged_in_cookie_whitelist": ["sessionid", "sid", "odin_tt", "passport_csrf_token"],  # 可为空，主要靠DOM判定
}
ERRORS = {
    "OTP_REQUIRED": "otp_required",
    "QR_EXPIRED": "qr_expired",
    "NOT_OWNER": "not_owner",
    "NOT_FOUND": "not_found",
    "BROWSER_DOWN": "browser_down",
}
