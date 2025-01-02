import requests
import asyncio
from datetime import datetime, time, timedelta, timezone
from telegram import Bot
from itertools import groupby
from operator import itemgetter
from dotenv import load_dotenv
import os
import json
import logging

# Ortam değişkenlerini yükleyin
load_dotenv(dotenv_path="config.env")

# Yapılandırma
config = {
    "telegram_bot_token": os.getenv('TELEGRAM_BOT_TOKEN'),
    "telegram_group_chat_id": os.getenv('TELEGRAM_GROUP_CHAT_ID'),
    "telegram_personal_chat_id": os.getenv('TELEGRAM_PERSONAL_CHAT_ID'),
    "telegram_czech_chat_id": os.getenv('TELEGRAM_CZECH_CHAT_ID'),
    "telegram_belgium_chat_id": os.getenv('TELEGRAM_BELGIUM_CHAT_ID'),
    "telegram_france_chat_id": os.getenv('TELEGRAM_FRANCE_CHAT_ID'),
    "telegram_netherlands_chat_id": os.getenv('TELEGRAM_NETHERLANDS_CHAT_ID'),
    "telegram_slovenia_chat_id": os.getenv('TELEGRAM_SLOVENIA_CHAT_ID'),
    "telegram_fransa_sener_chat_id": os.getenv('TELEGRAM_FRANSA_SENER_CHAT_ID'),
    "telegram_dumbs_chat_id": os.getenv('TELEGRAM_DUMBS_CHAT_ID'),
    "visa_api_url": os.getenv('VISA_API_URL'),
    "chat_names": {
        os.getenv('TELEGRAM_GROUP_CHAT_ID'): "Genel Grup",
        os.getenv('TELEGRAM_PERSONAL_CHAT_ID'): "Kişisel Chat",
        os.getenv('TELEGRAM_CZECH_CHAT_ID'): "Çek Cumhuriyeti",
        os.getenv('TELEGRAM_BELGIUM_CHAT_ID'): "Belçika",
        os.getenv('TELEGRAM_FRANCE_CHAT_ID'): "Fransa",
        os.getenv('TELEGRAM_NETHERLANDS_CHAT_ID'): "Hollanda",
        os.getenv('TELEGRAM_SLOVENIA_CHAT_ID'): "Slovenya",
        os.getenv('TELEGRAM_FRANSA_SENER_CHAT_ID'): "Fransa Şener",
        os.getenv('TELEGRAM_DUMBS_CHAT_ID'): "Dumbs"
    },
    "utc_plus_3": timezone(timedelta(hours=3))
}

# Global last_message_files tanımı
last_message_files = {
    config["telegram_dumbs_chat_id"]: "last_dumbs_message.json",
    config["telegram_group_chat_id"]: "last_general_message.json"
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
bot = Bot(token=config["telegram_bot_token"])

def reset_lists():
    global czechia_list, belgium_list, france_list, netherlands_list, slovenia_list, france_sener_list, dumbs_list, general_list
    czechia_list = []
    belgium_list = []
    france_list = []
    france_sener_list = []
    netherlands_list = []
    slovenia_list = []
    dumbs_list = []
    general_list = []

def load_json(filename):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None

def save_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file)

def get_chat_name(chat_id):
    return config["chat_names"].get(chat_id, "Bilinmeyen Grup")

def log_message(message, chat_id):
    chat_name = get_chat_name(chat_id)
    logging.info(f"{message} - Grup: {chat_name}, Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def send_message(chat_id, text, now):
    chat_name = get_chat_name(chat_id)

    if not text.strip():  # Mesaj boşsa logla ve gönderme
        log_message("Mesaj boş olduğu için gönderilmiyor", chat_id)
        return

    if chat_id in last_message_files:
        # last_message_files içindeki id'ler için sadece 08:00-23:00 arasında mesaj gönder
        if time(8, 0) <= now.time() <= time(23, 0):
            await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
            log_message("Mesaj gönderildi", chat_id)
        else:
            log_message("Mesaj zaman kısıtlaması nedeniyle gönderilmiyor", chat_id)
    else:
        # Diğer id'ler için saat kısıtlaması olmadan mesaj gönder
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
        log_message("Mesaj gönderildi", chat_id)

async def fetch_and_notify(now):
    log_message("Randevular kontrol ediliyor", config["telegram_personal_chat_id"])
    url = config["visa_api_url"]

    reset_lists()

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Boş veri kontrolü
        if not data:  # Eğer data None, boş liste veya boş dictionary ise
            log_message("API yanıtı boş veya null", config["telegram_personal_chat_id"])
            await send_message(config["telegram_personal_chat_id"], f"API'den dönen veri boş veya null: {url}", now)
            return  # Eğer veri boşsa, devam etmeyi durdur

        log_message("Randevu verileri alındı", config["telegram_personal_chat_id"])
    except requests.RequestException as e:
        log_message(f"Veri çekme hatası: {e}", config["telegram_personal_chat_id"])
        await send_message(config["telegram_personal_chat_id"], f"Veri çekme hatası: {e}", now)
        return

    await process_appointments(data, now)

async def process_appointments(data, now):
    filter_appointments(data)
    final_message_czechia = "\n\n".join(format_message(item) for item in czechia_list)
    final_message_belgium = "\n\n".join(format_message(item) for item in belgium_list)
    final_message_france = "\n\n".join(format_message(item) for item in france_list)
    final_message_france_sener = "\n\n".join(format_message(item) for item in france_sener_list)
    final_message_netherlands = "\n\n".join(format_message(item) for item in netherlands_list)
    final_message_slovenia = "\n\n".join(format_message(item) for item in slovenia_list)
    final_message_dumbs = "\n\n".join(format_message(item) for item in dumbs_list)
    final_message_general = "\n\n".join(format_message(item) for item in general_list)

    await notify_users(
        final_message_czechia, 
        final_message_belgium, 
        final_message_france, 
        final_message_netherlands, 
        final_message_slovenia, 
        final_message_france_sener, 
        final_message_dumbs, 
        final_message_general, 
        now
    )

def filter_appointments(data):
    
    dataForTurkey = [
        item for item in data
        if item.get("source_country") == "Turkiye"
        and item.get("appointment_date") is not None
        and "tourism" in (item.get("visa_subcategory") or "").lower()
    ]

    for item in dataForTurkey:
    
        center_name = item["center_name"].lower()  # Küçük harfe çevir
        mission_country = item["mission_country"].lower()  # Küçük harfe çevir

        # Czechia
        if mission_country == "czechia":
            czechia_list.append(item)

        # Belgium
        if mission_country == "belgium":
            belgium_list.append(item)

        # France
        if mission_country == "france":
            france_list.append(item)
            france_sener_list.append(item)

        # Netherlands
        if mission_country == "netherlands":
            netherlands_list.append(item)

        # Slovenia
        if mission_country == "slovenia":
            slovenia_list.append(item)

        # Dumbs List
        if mission_country in {"netherlands", "belgium", "france"} and (
            "ankara" in center_name or "istanbul" in center_name
        ):
            dumbs_list.append(item)

        # General List
        if (
            "ankara" in center_name
            or "istanbul" in center_name
        ):
            general_list.append(item)


    # general_list'i item["mission_country"]'ye göre alfabetik olarak sıralayın
    general_list.sort(key=lambda x: x["mission_country"])

def format_message(item):
    appointment_date = datetime.fromisoformat(item['appointment_date']).strftime('%d-%m-%Y')
    return f"<u><b>Ülke:</b></u> {item['mission_country']},\n<u><b>Kategori:</b></u> {item['visa_category']},\n<u><b>Tip:</b></u> {item['visa_subcategory']},\n<u><b>Merkez:</b></u> {item['center_name']},\n<u><b>Date:</b></u> {appointment_date}"

async def notify_users(
    czechia_message, 
    belgium_message, 
    france_message, 
    netherlands_message, 
    slovenia_message, 
    france_sener_message, 
    dumbs_message, 
    general_message, 
    now
):
    chat_messages = {
        config["telegram_czech_chat_id"]: czechia_message,
        config["telegram_belgium_chat_id"]: belgium_message,
        config["telegram_france_chat_id"]: france_message,
        config["telegram_netherlands_chat_id"]: netherlands_message,
        config["telegram_slovenia_chat_id"]: slovenia_message,
        config["telegram_fransa_sener_chat_id"]: france_sener_message,
        config["telegram_dumbs_chat_id"]: dumbs_message,
        config["telegram_group_chat_id"]: general_message
    }

    for chat_id, message in chat_messages.items():
        if not message or not message.strip():  # Mesaj boşsa atla ve logla
            log_message("Mesaj boş. Gönderim atlandı.", chat_id)
            continue

        if chat_id in last_message_files:
            last_message = load_json(last_message_files[chat_id])
            if last_message != message:
                await send_message(chat_id, message, now)
                save_json(last_message_files[chat_id], message)
            else:
                log_message("Mesajda değişiklik yok. Gönderim atlandı.", chat_id)
        else:  # Eğer chat_id `last_message_files`'ta değilse ve mesaj boş değilse gönder
            await send_message(chat_id, message, now)

async def scheduler():
    while True:
        now = datetime.now(config["utc_plus_3"])
        await fetch_and_notify(now)
        next_run = now + timedelta(minutes=5)
        sleep_seconds = (next_run - datetime.now(config["utc_plus_3"])).total_seconds()
        log_message("Sonraki Çalışma Planlandı", config["telegram_personal_chat_id"])
        logging.info("_______________________________________________________________")
        await asyncio.sleep(sleep_seconds)  # Belirlenen süre kadar bekle

async def main():
    log_message("VisaBot Aktif", config["telegram_personal_chat_id"])
    await scheduler()

if __name__ == "__main__":
    asyncio.run(main())
