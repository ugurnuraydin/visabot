import requests
import asyncio
from datetime import datetime, time, timedelta, timezone
from telegram import Bot
from itertools import groupby
from operator import itemgetter
import json
import logging


# Yapılandırma
config = {
    "telegram_bot_token": '6829298339:AAEJjoijTUf8DyaERraNevg9S9jHIRosMhg',
    
    "telegram_group_chat_id": '-1002051631354',
    "telegram_personal_chat_id": '1418776096',
    
    "telegram_czech_chat_id": '-4253313815',
    "telegram_belgium_chat_id": '-4238889616',
    "telegram_france_chat_id": '-4267407232',
    "telegram_netherlands_chat_id": '-4277752437',
    "telegram_slovenia_chat_id": '-1002218773507',
    "telegram_fransa_sener_chat_id": '-1002186778213',
    "telegram_dumbs_chat_id": '-1002242628854',
    "chat_names": {
        '-1002051631354': "Genel Grup",
        '1418776096': "Kişisel Chat",
        '-4253313815': "Çek Cumhuriyeti",
        '-4238889616': "Belçika",
        '-4267407232': "Fransa",
        '-4277752437': "Hollanda",
        '-1002218773507': "Slovenya",
        '-1002186778213': "Fransa Şener",
        '-1002242628854': "Dumbs"
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

async def send_message(chat_id, text, now):
    await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
    chat_name = config["chat_names"].get(chat_id, "bilinmeyen grup")  # Chat adını al, eğer bulunamazsa "bilinmeyen grup" yaz
    logging.info(f'Message sent to {chat_name} at {now.strftime("%H:%M:%S")}')


def load_json(filename):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None

def save_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file)
            
            
async def send_message(chat_id, text, now):
    chat_name = config["chat_names"].get(chat_id, chat_id)  # chat_id için grup ismini al, bulunamazsa chat_id'yi kullan

    if chat_id in last_message_files:
        # last_message_files içindeki id'ler için sadece 08:00-23:00 arasında mesaj gönder
        if time(8, 0) <= now.time() <= time(23, 0):
            await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
            logging.info(f'Message sent to {chat_name} at {now.strftime("%H:%M:%S")}')
        else:
            logging.info(f'Message to {chat_name} not sent due to time restrictions.')
    else:
        # Diğer id'ler için saat kısıtlaması olmadan mesaj gönder
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
        logging.info(f'Message sent to {chat_name} at {now.strftime("%H:%M:%S")}')
        
async def fetch_and_notify(now):
    logging.info('Checking appointments --' + now.strftime("%H:%M:%S"))
    url = "https://api.schengenvisaappointments.com/api/visa-list/"
    
    reset_lists()
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        logging.info('Appointment data retrieved')
    except requests.RequestException as e:
        logging.error(f"Error fetching data: {e}")
        await send_message(config["telegram_personal_chat_id"], f"Error fetching data: {e}", now)
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
    
    
    await notify_users(final_message_czechia, final_message_belgium, final_message_france, final_message_netherlands, final_message_slovenia, final_message_france_sener,final_message_dumbs, final_message_general, now)

        
        
def filter_appointments(data):
    for item in data:
        if item["source_country"] == "Turkiye" and item["appointment_date"] is not None:
            visa_subcategory = item.get("visa_subcategory") or ""
            
            if item["mission_country"] == "Czechia" and "tourism" in visa_subcategory.lower():
                czechia_list.append(item)
                
            if item["mission_country"] == "Belgium" and "tourism" in visa_subcategory.lower():
                belgium_list.append(item)
                
            if item["mission_country"] == "France" and (visa_subcategory == "Short Term Standard" or visa_subcategory == "Tourism/Family visit"):
                france_list.append(item)
                france_sener_list.append(item)
                
            if item["mission_country"] == "Netherlands" and "tourism" in visa_subcategory.lower():
                netherlands_list.append(item)
                
            if item["mission_country"] == "Slovenia" and "tourism" in visa_subcategory.lower():
                slovenia_list.append(item)
                
            if (item["mission_country"] in ["Netherlands", "Belgium"]) and ("ankara" in item["center_name"].lower() or "istanbul" in item["center_name"].lower()) and "tourism" in visa_subcategory.lower():
                dumbs_list.append(item)
                
            if ("ankara" in item["center_name"].lower() or "istanbul" in item["center_name"].lower() or "izmir" in item["center_name"].lower()) and "tourism" in visa_subcategory.lower() or "short term standard" in visa_subcategory.lower():
                general_list.append(item)
    
    # general_list'i item["mission_country"]'ye göre alfabetik olarak sıralayın
    general_list.sort(key=lambda x: x["mission_country"])

        
        

            



def format_message(item):
    appointment_date = datetime.fromisoformat(item['appointment_date']).strftime('%d-%m-%Y')
    return f"<u><b>Ülke:</b></u> {item['mission_country']},\n<u><b>Kategori:</b></u> {item['visa_category']},\n<u><b>Tip:</b></u> {item['visa_subcategory']},\n<u><b>Merkez:</b></u> {item['center_name']},\n<u><b>Date:</b></u> {appointment_date}"

async def notify_users(czechia_message, belgium_message, france_message, netherlands_message, slovenia_message, france_sener_message, dumbs_message, general_message, now):
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
        if chat_id in last_message_files:
            last_message = load_json(last_message_files[chat_id])
            if last_message != message:
                await send_message(chat_id, message, now)
                save_json(last_message_files[chat_id], message)
        elif message:  # Eğer mesaj boş değilse gönder
            await send_message(chat_id, message, now)



async def scheduler():
    while True:
        now = datetime.now(config["utc_plus_3"])
        await fetch_and_notify(now)
        next_run = now + timedelta(minutes=5)
        sleep_seconds = (next_run - datetime.now(config["utc_plus_3"])).total_seconds()
        logging.info("Sonraki Çalışma: " + next_run.strftime("%H:%M:%S"))
        logging.info('___________________________________________________________________\n')

        await asyncio.sleep(sleep_seconds)  # Belirlenen süre kadar bekle
        
async def main():
    logging.info('VisaBot Aktif')
    await scheduler()

if __name__ == "__main__":
    asyncio.run(main())

