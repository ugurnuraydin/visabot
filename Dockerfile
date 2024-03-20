# Python'un resmi "slim" sürümünü temel alarak başla
FROM python:3.9-slim

# Uygulama dosyalarınızı koyacağınız dizin
WORKDIR /app

# requirements.txt dosyasını mevcut dizinden /app dizinine kopyala
COPY requirements.txt /app/

# requirements.txt'de listelenen bağımlılıkları yükle
RUN pip install --no-cache-dir -r requirements.txt

# Uygulamanızın geri kalan dosyalarını mevcut dizinden /app dizinine kopyala
COPY . /app

# Uygulamanızı çalıştır
CMD ["python", "./service.py"]
