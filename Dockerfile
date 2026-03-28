FROM ubuntu:22.04

RUN apt-get update && apt-get install -y curl python3 python3-pip

RUN curl -fsSL https://ollama.com/install.sh | sh

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ollama serve & sleep 5 && \
    ollama pull mistral && \
    ollama create my-sql-model -f Modelfile && \
    gunicorn sqlai.wsgi --bind 0.0.0.0:8000