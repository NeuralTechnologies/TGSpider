FROM python:3.12
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
WORKDIR /app
COPY src/ /app
ENTRYPOINT ["/usr/local/bin/python", "/app/main.py"]
