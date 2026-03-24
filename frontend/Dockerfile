# Node 20 tabanlı hafif imaj
FROM node:20-slim

# Çalışma dizini oluştur
WORKDIR /app

# Bağımlılıkları kopyala ve kur
COPY package*.json ./
RUN npm install

# Uygulama kodlarını kopyala
COPY . .

# Portu aç (Vite varsayılanı)
EXPOSE 5173

# Vite sunucusunu başlat (--host ile ağa aç)
CMD ["npm", "run", "dev", "--", "--host"]
