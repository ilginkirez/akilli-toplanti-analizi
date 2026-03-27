# Python 3.11 Bookworm
FROM python:3.11-slim-bookworm

# Çalışma dizini oluştur
WORKDIR /app

# Sistem bağımlılıklarını kur (Ses işleme ve FFMPEG için)
# Hata düzeltme: libsoundfile1 -> libsndfile1
RUN apt-get update --fix-missing && apt-get install -yqq \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Gereksinimleri kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodlarını kopyala
COPY . .

# Portu aç
EXPOSE 8000

# Uygulamayı başlat
CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8000"]
