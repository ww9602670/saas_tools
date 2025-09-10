# Prometheus 指标 & 中间件  

# metrics.py
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app


active_contexts = Gauge("active_contexts","Current active Playwright contexts")
login_seconds = Histogram("login_duration_seconds","Login duration")
browser_restart = Counter("browser_restart_total","Browser restarts")

def setup_metrics(app):
    app.mount("/metrics", make_asgi_app())
    # 可选：请求日志/trace中间件
