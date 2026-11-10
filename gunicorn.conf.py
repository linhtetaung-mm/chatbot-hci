"""One process owns chat locks; threads allow Stop during an API request."""
import os
bind='0.0.0.0:'+os.getenv('PORT','10000')
workers=1
worker_class='gthread'
threads=16
timeout=90
graceful_timeout=70
# Do not log request URLs, conversation IDs, cookies or submitted text.
accesslog=None
errorlog='-'
capture_output=False

def post_worker_init(worker):
    # Check the settings at start-up, but connect to the database on the first request, so a new deploy
    # can pass its health check while the previous copy still holds the database lock.
    from app.config import configuration
    configuration()

def worker_exit(server, worker):
    # Release the database lock as soon as this copy stops (e.g. when Render replaces it during a deploy).
    from app import server as app_server
    if app_server.bot is not None and hasattr(app_server.bot.storage,'close'):app_server.bot.storage.close()
