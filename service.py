import requests
import asyncio
from datetime import datetime, time, timedelta, timezone
from telegram import Bot
from itertools import groupby
from operator import itemgetter
import json
import logging


# Telegram bot token ve grup ID bilgilerinizi buraya girin
TELEGRAM_BOT_TOKEN = '6829298339:AAEJjoijTUf8DyaERraNevg9S9jHIRosMhg'
TELEGRAM_GROUP_CHAT_ID = '-1002051631354' #Canlı Grup
TELEGRAM_KISISEL_CHAT_ID = '1418776096' #Kişisel Chat
bot = Bot(token=TELEGRAM_BOT_TOKEN)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
UTC_PLUS_3 = timezone(timedelta(hours=3))
now = datetime.now(UTC_PLUS_3)
GROUP = "GROUP"
PERSONAL = "PERSONAL"


def save_last_message(data):
    with open("lastMessage.json", "w") as file:
        json.dump(data, file)
        
def load_last_message():
    try:
        with open("lastMessage.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None

async def send_telegram_message(text,chatType):
    if chatType == GROUP:
        await bot.send_message(chat_id=TELEGRAM_GROUP_CHAT_ID, text=text, parse_mode='Markdown')
        logging.info('Gruba Mesaj Gönderildi.')
    else:
       await bot.send_message(chat_id=TELEGRAM_KISISEL_CHAT_ID, text=text, parse_mode='Markdown') 
       logging.info('Kişisel Mesaj Gönderildi.')

async def fetch_visa_appointments():
    logging.info('Randevu Kontrol Akışı Başladı --' + now.strftime("%H:%M:%S"))
    global lastMessage
    lastMessage = load_last_message()
    url = "https://api.schengenvisaappointments.com/api/visa-list/"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            logging.info('Randevu Bilgileri Alındı')
        else:
            logging.error(f"API'den beklenen yanıt alınamadı, durum kodu: {response.status_code}")
            await send_telegram_message(f"API'den beklenen yanıt alınamadı, durum kodu:\n {response.status_code}", PERSONAL)
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API'den hata alındı, durum kodu: {response.status_code}")
        await send_telegram_message(f"API isteği sırasında bir hata oluştu:\n {e}" ,PERSONAL)
        return None

    

    sonucListe = [
        item for item in data if item["source_country"] == "Turkiye" and 
        # (item["mission_country"] == "Belgium" or item["mission_country"] == "Netherlands") and
        # item["visa_category"] == "KISA DONEM BASVURU / SHORT TERM APPLICATION" and 
        "tourism" in item["visa_subcategory"].lower() and
        item["appointment_date"] is not None
    ]
    logging.info('Sonuç Listesi Alındı:')

        
    sorted_list = sorted(sonucListe, key=lambda x: x["mission_country"])
    
    messages = []

    for mission_country, items in groupby(sorted_list, key=lambda x: x["mission_country"]):
        for item in items:
            if item['appointment_date'] is not None:
                appointment_date = datetime.fromisoformat(item['appointment_date']).strftime('%d-%m-%Y')
            else:
                appointment_date = "Uyumsuz Format"        
            message = f"**Ülke:** {mission_country}, \n**Randevu Merkezi:** {item['center_name']}, \n**Randevu Tarihi:** {appointment_date}"
        
            messages.append(message)
    
    if  messages != lastMessage:
        lastMessage = messages
        save_last_message(messages)
        final_message = "\n\n".join(messages)
        logging.info('Mesaj Farkı Bulundu, Son Mesaj:\n' + final_message)
        if sonucListe and messages:
            await send_telegram_message(final_message,PERSONAL)
    else:
        logging.info('Dandevularda Değişiklik yok, mesaj gönderilmedi')


    

async def scheduler():
    while True:
        # Saat şu an 09:00 ile 22:00 arasında mı kontrol et
        if time(9, 0) <= now.time() <= time(22, 0):
            await fetch_visa_appointments()
            # Bir sonraki çalışma için 15 dakika sonrasına ayarla
            next_run = now + timedelta(minutes=5)
            logging.info("Sonraki Çalışma " + next_run.strftime("%H:%M:%S"))
            sleep_seconds = (next_run - datetime.now(UTC_PLUS_3)).total_seconds()
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
        logging.info('___________________________________________________________________')



async def main():
    logging.info('VisaBot Aktif')
    await scheduler()

if __name__ == "__main__":
    asyncio.run(main())

