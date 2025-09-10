# OTP 流程封装：识别、提交、重试策略

# otp_flow.py
class OTPFlow:
    async def is_otp_page(self, page) -> bool:
        # 粗略识别：存在“验证码”输入框或含“发送验证码”的按钮
        return bool(await page.query_selector("input[type='text'][placeholder*='验证码'], input[aria-label*='验证码']"))

    async def submit(self, page, kind:str, code:str) -> bool:
        inp = await page.query_selector("input[type='text'][placeholder*='验证码'], input[aria-label*='验证码']")
        if not inp: return False
        await inp.fill(code)
        # 提交按钮：根据页面实际 class 再补充；先用含“确认/提交”的按钮兜底
        submit_btn = await page.query_selector("button:has-text('确认'), button:has-text('提交')")
        if submit_btn:
            await submit_btn.click()
            await page.wait_for_timeout(800)  # 等待后续跳转
        return True
