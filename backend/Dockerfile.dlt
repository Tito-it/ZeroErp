FROM python:3.11-slim
WORKDIR /app

# ora il contesto è la root, trova requirements.txt
COPY requirements.txt .       

RUN pip install --no-cache-dir -r requirements.txt

# poi copi il codice Django dentro /app
COPY backend/ .                

CMD ["gunicorn","backend.wsgi:application","--bind","0.0.0.0:8000"]
