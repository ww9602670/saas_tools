# Playwright 1.55 对应的 Python 基础镜像（含Chromium/Firefox/WebKit与依赖）
FROM mcr.microsoft.com/playwright/python:v1.55.0-jammy

WORKDIR /app

# 先装依赖再拷贝代码，可利用缓存
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "src/app/doudian.py"]
