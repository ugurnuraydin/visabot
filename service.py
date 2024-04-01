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
TELEGRAM_BERKCAN_CHAT_ID = '-4188174746' #Berkcan Chat
bot = Bot(token=TELEGRAM_BOT_TOKEN)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
UTC_PLUS_3 = timezone(timedelta(hours=3))


def save_last_message(data):
    with open("lastMessage.json", "w") as file:
        json.dump(data, file)
        
def load_last_message():
    try:
        with open("lastMessage.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None

def save_last_message_berkcan(data):
    with open("lastMessageBerkcan.json", "w") as file:
        json.dump(data, file)
        
def load_last_message_berkcan():
    try:
        with open("lastMessageBerkcan.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None

async def send_telegram_message_general(text, now):
    if time(9, 0) <= now.time() <= time(21, 0):
        await bot.send_message(chat_id=TELEGRAM_GROUP_CHAT_ID, text=text, parse_mode='Markdown')
        logging.info('Gruba Mesaj Gönderildi.' )
            
async def send_telegram_message_berkcan(text):
    await bot.send_message(chat_id=TELEGRAM_BERKCAN_CHAT_ID, text=text, parse_mode='Markdown') 
    logging.info('Berkcana Mesaj Gönderildi.')
        
            
async def send_telegram_message_personal(text):
    await bot.send_message(chat_id=TELEGRAM_KISISEL_CHAT_ID, text=text, parse_mode='Markdown')
    logging.info('Kişisel Mesaj Gönderildi.')
        
        
async def fetch_visa_appointments(now):
    logging.info('Randevu Kontrol Akışı Başladı --' + now.strftime("%H:%M:%S"))
    global lastMessage
    global lastMessageBerkcan
    url = "https://api.schengenvisaappointments.com/api/visa-list/"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            logging.info('Randevu Bilgileri Alındı')
        else:
            logging.error(f"API'den beklenen yanıt alınamadı, durum kodu: {response.status_code}")
            await send_telegram_message_personal(f"API'den beklenen yanıt alınamadı, durum kodu:\n {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API'den hata alındı, durum kodu: {response.status_code}")
        await send_telegram_message_personal(f"API isteği sırasında bir hata oluştu:\n {e}")
        return None

    genel_sonucListe = [
        item for item in data if item["source_country"] == "Turkiye" and 
        # (item["mission_country"] == "Belgium" or item["mission_country"] == "Netherlands") and
        # item["visa_category"] == "KISA DONEM BASVURU / SHORT TERM APPLICATION" and 
        "tourism" in item["visa_subcategory"].lower() and
        item["appointment_date"] is not None
    ]
    
    berkcan_genel_sonucListe = [
    item for item in data if item["source_country"] == "Turkiye" and 
    item["mission_country"] in ["France", "Czechia", "Austria", "Poland","Belgium","Netherlands"] and
    item["appointment_date"] is not None
]

    

        
    berkcan_sorted_list = sorted(berkcan_genel_sonucListe, key=lambda x: x["mission_country"])
    general_sorted_list = sorted(genel_sonucListe, key=lambda x: x["mission_country"])
    
    
    for item in general_sorted_list:
        if item["mission_country"] == "Belgium" and item["appointment_date"] is not None:
            message_content = f"Belgium için randevu bulundu!! \nRandevu Merkezi: {item['center_name']}, \nRandevu Tarihi: {item['appointment_date']}"
            logging.info('Belgium için randevu bulundu:')
            await send_telegram_message_personal(message_content)
            break
    

    general_messages = []
    berkcan_messages = []
    lastMessage = load_last_message()
    lastMessageBerkcan = load_last_message_berkcan()


    for mission_country, items in groupby(general_sorted_list, key=lambda x: x["mission_country"]):
        for item in items:
            if item['appointment_date'] is not None:
                appointment_date = datetime.fromisoformat(item['appointment_date']).strftime('%d-%m-%Y')
            else:
                appointment_date = "Uyumsuz Format"        
            message = f"**Ülke:** {mission_country}, \n**Randevu Merkezi:** {item['center_name']}, \n**Randevu Tarihi:** {appointment_date}"
        
            general_messages.append(message)
            

    for mission_country, items in groupby(berkcan_sorted_list, key=lambda x: x["mission_country"]):
        for item in items:
            if item['appointment_date'] is not None:
                appointment_date = datetime.fromisoformat(item['appointment_date']).strftime('%d-%m-%Y')
            else:
                appointment_date = "Uyumsuz Format"        
            message = f"**Ülke:** {mission_country}, \n**Randevu Merkezi:** {item['center_name']}, \n**Vize Türü:** {item['visa_category']}, \n**Randevu Tarihi:** {appointment_date}"
        
            berkcan_messages.append(message)
            
        
    
    if  general_messages != lastMessage:
        lastMessage = general_messages
        save_last_message(general_messages)
        final_message = "\n\n".join(general_messages)
        # logging.info('Mesaj Farkı Bulundu, Son Mesaj:\n' + final_message)
        await send_telegram_message_general(final_message, now)
        
    else:
        logging.info('Randevularda Değişiklik yok, mesaj gönderilmedi')

    if  berkcan_messages != lastMessageBerkcan:
        lastMessageBerkcan = berkcan_messages
        save_last_message_berkcan(general_messages)
        final_message = "\n\n".join(berkcan_messages)
        # logging.info('Mesaj Farkı Bulundu, Son Mesaj:\n' + final_message)
        await send_telegram_message_berkcan(final_message)
        
    else:
        logging.info('Randevularda Değişiklik yok, mesaj gönderilmedi')
    

async def scheduler():
     while True:
        now = datetime.now(UTC_PLUS_3)  # Şu anki zamanı UTC+3 olarak al
        await fetch_visa_appointments(now)  # Şu anki zamanı fonksiyona argüman olarak gönder
        next_run = now + timedelta(minutes=10)  # Bir sonraki çalışma için 10 dakika sonrasını hesapla
        sleep_seconds = (next_run - datetime.now(UTC_PLUS_3)).total_seconds()  # Bekleme süresini hesapla

        logging.info("Sonraki Çalışma: " + next_run.strftime("%H:%M:%S"))
        logging.info('___________________________________________________________________\n')

        await asyncio.sleep(sleep_seconds)  # Belirlenen süre kadar bekle
        



async def main():
    logging.info('VisaBot Aktif')
    await scheduler()

if __name__ == "__main__":
    asyncio.run(main())

