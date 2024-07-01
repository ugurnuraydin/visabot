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
    "utc_plus_3": timezone(timedelta(hours=3))
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
bot = Bot(token=config["telegram_bot_token"])

def reset_lists():
    global czechia_list, belgium_list, france_list, netherlands_list, slovenia_list
    czechia_list = []
    belgium_list = []
    france_list = []
    netherlands_list = []
    slovenia_list = []

async def send_message(chat_id, text, now):
    await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
    logging.info(f'Message sent to general group at {now.strftime("%H:%M:%S")}')

        
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

    
async def process_appointments(data,now):
    filter_appointments(data)
    final_message_czechia = "\n\n".join(format_message(item) for item in czechia_list)
    final_message_belgium = "\n\n".join(format_message(item) for item in belgium_list)
    final_message_france = "\n\n".join(format_message(item) for item in france_list)
    final_message_netherlands = "\n\n".join(format_message(item) for item in netherlands_list)
    final_message_slovenia = "\n\n".join(format_message(item) for item in slovenia_list)
    
    await notify_users(final_message_czechia, final_message_belgium, final_message_france, final_message_netherlands, final_message_slovenia, now)

        
        
def filter_appointments(data):
    for item in data:
        if item["source_country"] == "Turkiye" and item["appointment_date"] is not None:
            visa_subcategory = item.get("visa_subcategory") or ""
            if item["mission_country"] == "Czechia" and "tourism" in visa_subcategory.lower():
                czechia_list.append(item)
            elif item["mission_country"] == "Belgium" and "tourism" in visa_subcategory.lower():
                belgium_list.append(item)
            elif item["mission_country"] == "France" and (visa_subcategory == "Short Term Standard" or visa_subcategory == "Tourism/Family visit"):
                france_list.append(item)
            elif item["mission_country"] == "Netherlands" and "tourism" in visa_subcategory.lower():
                netherlands_list.append(item)
            elif item["mission_country"] == "Slovenia" and "tourism" in visa_subcategory.lower():
                slovenia_list.append(item)



def format_message(item):
    appointment_date = datetime.fromisoformat(item['appointment_date']).strftime('%d-%m-%Y')
    return f"<u><b>Ülke:</b></u> {item['mission_country']},\n<u><b>Kategori:</b></u> {item['visa_category']},\n<u><b>Tip:</b></u> {item['visa_subcategory']},\n<u><b>Merkez:</b></u> {item['center_name']},\n<u><b>Date:</b></u> {appointment_date}"

async def notify_users(czechia_message, belgium_message, france_message, netherlands_message, slovenia_message, now):
    chat_messages = {
        config["telegram_czech_chat_id"]: czechia_message,
        config["telegram_belgium_chat_id"]: belgium_message,
        config["telegram_france_chat_id"]: france_message,
        config["telegram_netherlands_chat_id"]: netherlands_message,
        config["telegram_slovenia_chat_id"]: slovenia_message
    }
    for chat_id, message in chat_messages.items():
        if message:  # Eğer mesaj boş değilse gönder
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

