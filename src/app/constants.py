# 站点URL、选择器、默认等待/超时、错误码枚举
# constants.py
DOUDIAN = {
    "login_url": "https://fxg.jinritemai.com/login/common?channel=zhaoshang",
    "qr_container": "div.account-center-image-content",
    "qr_img": "div.account-center-image-content img",
    "qr_refresh_button": "button.account-center-code-expired-refresh",
    "shop_name_selector": "div.index_userName__16Isl[data-bytereplay-mask='true']",
    "qr_ttl_seconds": 60,
}
ERRORS = {
    "OTP_REQUIRED": "otp_required",
    "QR_EXPIRED": "qr_expired",
    "NOT_OWNER": "not_owner",
    "NOT_FOUND": "not_found",
    "BROWSER_DOWN": "browser_down",
}
