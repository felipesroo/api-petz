# Usa a imagem oficial do Playwright com Python (já tem navegadores!)
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

# Define pasta de trabalho
WORKDIR /app

# Copia os arquivos
COPY . .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Instala os navegadores do Playwright (garantia extra)
RUN playwright install chromium

# Expõe a porta 80
EXPOSE 80

# Comando para iniciar a API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]