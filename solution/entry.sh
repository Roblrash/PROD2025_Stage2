alembic -c solution/alembic.ini upgrade head
exec gunicorn main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind "$SERVER_ADDRESS:$SERVER_PORT" \
  --access-logfile -