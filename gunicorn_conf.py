# Configuração otimizada do Gunicorn para Render
import multiprocessing
import os

# Bind
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'  # ou 'gevent' para melhor performance
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100

# Timeouts (importante para Railway/Render)
timeout = 120  # 2 minutos
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Restart workers periodically
preload_app = False

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

print(f"🚀 Gunicorn configurado:")
print(f"   - Porta: {bind}")
print(f"   - Workers: {workers}")
print(f"   - Timeout: {timeout}s")