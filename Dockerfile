# Imagem Python leve e rápida
FROM python:3.9-slim

WORKDIR /app

COPY . .

# Instala apenas o necessário (requests, beautifulsoup)
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
