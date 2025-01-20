alembic -c /app/alembic.ini revision --autogenerate -m "Initial migration"
alembic -c /app/alembic.ini upgrade head
gunicorn main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind "$SERVER_ADDRESS:$SERVER_PORT" \
  --access-logfile -