FROM python:3.12

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt


COPY . .

RUN chmod +x entry.sh

ENTRYPOINT [ "sh", "entry.sh" ]
