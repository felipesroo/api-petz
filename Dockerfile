# Usa uma imagem Python leve (sem navegadores pesados)
FROM python:3.9-slim

# Define pasta de trabalho
WORKDIR /app

# Copia os arquivos
COPY . .

# Instala apenas requests, beautifulsoup e fastapi
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta 80
EXPOSE 80

# Inicia o servidor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
