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
    "telegram_berkcan_chat_id": '-4188174746',
    "utc_plus_3": timezone(timedelta(hours=3))
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
bot = Bot(token=config["telegram_bot_token"])


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
    if chat_id == config["telegram_group_chat_id"] and time(9, 0) <= now.time() <= time(21, 0):
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
        logging.info(f'Message sent to general group at {now.strftime("%H:%M:%S")}')
    elif chat_id == config["telegram_berkcan_chat_id"]:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
        logging.info(f'Message sent to Berkcan at {now.strftime("%H:%M:%S")}')
    elif chat_id == config["telegram_personal_chat_id"]:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
        logging.info(f'Message sent to Uğur at {now.strftime("%H:%M:%S")}')

        
async def fetch_and_notify(now):
    logging.info('Checking appointments --' + now.strftime("%H:%M:%S"))
    url = "https://api.schengenvisaappointments.com/api/visa-list/"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        logging.info('Appointment data retrieved')
    except requests.RequestException as e:
        logging.error(f"Error fetching data: {e}")
        await send_message(config["telegram_personal_chat_id"], f"Error fetching data: {e}", now)
        return

    await process_appointments(data, "general", now)
    await process_appointments(data, "berkcan", now)
    await process_appointments(data, "personal", now)
    
async def process_appointments(data, category, now):
    filtered_data = filter_appointments(data, category)
    last_messages = load_json(f"lastMessage{category.capitalize()}.json")
    final_message = "\n\n".join(format_message(item,category) for item in filtered_data)
    if category != "personal":  
        if not final_message == last_messages:
            save_json(f"lastMessage{category.capitalize()}.json", final_message)
            await notify_users(category, final_message, now)
        else:
            logging.info(f'No changes in appointments for {category}')
    else:
        #Turistik belçika için özel kontrol eklendi.
        if filtered_data: 
            await send_message(config["telegram_personal_chat_id"], final_message, now)
        
        
def filter_appointments(data, category):
    if category == "general":
        return [item for item in data if item["source_country"] == "Turkiye" and "tourism" in item["visa_subcategory"].lower() and item["appointment_date"] is not None]
    elif category == "berkcan":
        return [item for item in data if item["source_country"] == "Turkiye" and item["mission_country"] in ["France", "Czechia", "Austria", "Poland", "Belgium", "Netherlands"] and item["appointment_date"] is not None]
    elif category == "personal":
        return [item for item in data if item["source_country"] == "Turkiye" and item["mission_country"] == "Belgium" and "tourism" in item["visa_subcategory"].lower() and item["appointment_date"] is not None]


def format_message(item, category):
    appointment_date = datetime.fromisoformat(item['appointment_date']).strftime('%d-%m-%Y')
    if category == "general":
        return f"<b><u>Ülke:</u></b> {item['mission_country']},\n<b><u>Merkez:</u></b> {item['center_name']},\n<b><u>Date:</u></b> {appointment_date}"

    elif category == "berkcan":
        return f"<u><b>Ülke:</b></u> {item['mission_country']},\n<u><b>Kategori:</b></u> {item['visa_category']},\n<u><b>Tip:</b></u> {item['visa_subcategory']},\n<u><b>Merkez:</b></u> {item['center_name']},\n<u><b>Date:</b></u> {appointment_date}"
    
    if category == "personal":
        return f"<b><u>BELÇİKA İÇİN RANDEVU BULUNDU!!</u></b>\n<b><u>Ülke:</u></b> {item['mission_country']}, <b><u>Merkez:</u></b> {item['center_name']}, <b><u>Date:</u></b> {appointment_date}"

async def notify_users(category, message, now):
    chat_ids = {
        "general": [config["telegram_group_chat_id"]],
        "berkcan": [config["telegram_berkcan_chat_id"]]
    }
    for chat_id in chat_ids.get(category, []):
        await send_message(chat_id, message, now)


async def scheduler():
    while True:
        now = datetime.now(config["utc_plus_3"])
        await fetch_and_notify(now)
        next_run = now + timedelta(minutes=10)
        sleep_seconds = (next_run - datetime.now(config["utc_plus_3"])).total_seconds()
        logging.info("Sonraki Çalışma: " + next_run.strftime("%H:%M:%S"))
        logging.info('___________________________________________________________________\n')

        await asyncio.sleep(sleep_seconds)  # Belirlenen süre kadar bekle
        
async def main():
    logging.info('VisaBot Aktif')
    await scheduler()

if __name__ == "__main__":
    asyncio.run(main())

