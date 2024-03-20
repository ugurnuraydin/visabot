import requests
import asyncio
from datetime import datetime, time, timedelta
from telegram import Bot
from itertools import groupby
from operator import itemgetter
import json


# Telegram bot token ve grup ID bilgilerinizi buraya girin
TELEGRAM_BOT_TOKEN = '6829298339:AAEJjoijTUf8DyaERraNevg9S9jHIRosMhg'
# TELEGRAM_CHAT_ID = '-1002051631354' #Canlı Grup
TELEGRAM_CHAT_ID = '1418776096' #Test Grubu
bot = Bot(token=TELEGRAM_BOT_TOKEN)

def save_last_message(data):
    with open("lastMessage.json", "w") as file:
        json.dump(data, file)
        
def load_last_message():
    try:
        with open("lastMessage.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None

async def send_telegram_message(text):
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode='Markdown')

async def fetch_visa_appointments():
    global lastMessage
    lastMessage = load_last_message()
    url = "https://api.schengenvisaappointments.com/api/visa-list/"
    response = requests.get(url)
    data = response.json()
    

    sonucListe = [
        item for item in data if item["source_country"] == "Turkiye" and 
        # (item["mission_country"] == "Belgium" or item["mission_country"] == "Netherlands") and
        # item["visa_category"] == "KISA DONEM BASVURU / SHORT TERM APPLICATION" and 
        "tourism" in item["visa_subcategory"].lower() and
        item["appointment_date"] is not None
    ]
        
    sorted_list = sorted(sonucListe, key=lambda x: x["mission_country"])
    
    messages = []

    for mission_country, items in groupby(sorted_list, key=lambda x: x["mission_country"]):
        for item in items:
            if item['appointment_date'] is not None:
                appointment_date = datetime.fromisoformat(item['appointment_date']).strftime('%d-%m-%Y')
            else:
                appointment_date = "Uyumsuz Format"        
            # Belirtilen formatta mesajı oluşturalım.
            message = f"**Ülke:** {mission_country}, \n**Randevu Merkezi:** {item['center_name']}, \n**Randevu Tarihi:** {appointment_date}"
        
            # Oluşturulan mesajı messages listesine ekleyelim.
            messages.append(message)
    
    if  messages != lastMessage:
        lastMessage = messages
        save_last_message(messages)  # Güncellenen lastMessage'yı dosyaya kaydet

        # Tüm mesajları birleştirerek tek bir mesaj oluşturalım.
        final_message = "\n\n".join(messages)
        # Eğer listemiz ve mesajlarımız var ise telegrama final_message'ı gönderebiliriz. Eğer yok ise herhangi bir bilgilendirme yapılmayacak!
        if sonucListe and messages:
            await send_telegram_message(final_message)
    else:
        await send_telegram_message("Bilgiler Aynı")


    

async def scheduler():
    while True:
        now = datetime.now()
        # Saat şu an 09:00 ile 22:00 arasında mı kontrol et
        if time(9, 0) <= now.time() <= time(22, 0):
            await fetch_visa_appointments()
            # Bir sonraki çalışma için 10 dakika sonrasına ayarla
            next_run = now + timedelta(minutes=15)
            await send_telegram_message("Sonraki Çalışma " + next_run.strftime("%H:%M:%S"))
            sleep_seconds = (next_run - datetime.now()).total_seconds()
        else:
            # 22:00'dan sonra bir sonraki günün 9:00'una kadar bekle
            if now.time() > time(22, 0):
                tomorrow = now + timedelta(days=1)
                next_run = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            # 00:00'dan önce 9:00'a kadar bekle
            else:
                next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
            sleep_seconds = (next_run - now).total_seconds()

        await asyncio.sleep(sleep_seconds)



async def main():
    await send_telegram_message("Service Started")
    await scheduler()

if __name__ == "__main__":
    asyncio.run(main())

