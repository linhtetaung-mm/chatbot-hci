"""One process owns chat locks; threads allow Stop during an API request."""
import os
bind='0.0.0.0:'+os.getenv('PORT','10000')
workers=1
worker_class='gthread'
threads=8
timeout=90
graceful_timeout=70
# Do not log request URLs, conversation IDs, cookies or submitted text.
accesslog=None
errorlog='-'
capture_output=False

def post_worker_init(worker):
    from app.server import get_bot
    get_bot()  # Validate configuration and initialize storage before serving.
