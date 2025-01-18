alembic -с solution/alembic.ini upgrade head
gunicorn main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind "$SERVER_ADDRESS:$SERVER_PORT" \
  --access-logfile -