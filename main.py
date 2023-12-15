import requests
import json
import pprint
import time
import pytz 
import sqlite3
from collections import Counter
from datetime import datetime

headers={'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
         'Content-Type':'application/json; charset=utf-8'}

def create_database():
    # Создаем подключение к базе данных (файл my_database.db будет создан)
    db = sqlite3.connect('my_database.db')
    sql = db.cursor()
    
    # Создаем таблицу, если она не существует
    sql.execute('''CREATE TABLE IF NOT EXISTS Users (
        id TEXT
    )''')
    db.commit()
    sql.execute("SELECT COUNT(*) id FROM Users")
    print(sql.fetchall())

def main(db,sql):
    r = requests.get('https://csfloat.com/api/v1/listings?limit=30&sort_by=expires_soon&type=auction', headers=headers)
    res = json.loads(r.text)
    for i in res:
        more_info = i['item']
        if more_info['market_hash_name'].startswith('Souvenir'):
            continue
        else:
            if 'float_value' in more_info:
                
                name = more_info['market_hash_name']
                float_value = more_info['float_value']
                base_price = i['reference']['base_price']/100
                final_price = i['reference']['predicted_price']/100
                auc_price = i['auction_details']['min_next_bid'] / 100
                img = f"https://s.csgofloat.com/{more_info['asset_id']}-front.png"
                timestamp = i['auction_details']['expires_at']
                strickers = None
                total = 0
                current_time = datetime.now(pytz.utc).astimezone(pytz.timezone('Europe/Moscow'))
                target_time = datetime.fromisoformat(timestamp)
                time_diff = target_time - current_time
                if time_diff.total_seconds() <= 1800:
                    if 'stickers' in more_info:
                        stickersfull = [
                            {
                                stick['name']: stick['scm']['price'] / 100,
                                'Wear': stick['wear'] * 100 if 'wear' in stick else 0
                            } if 'scm' in stick and stick['scm']['price'] is not None else
                            {
                                stick['name']: 0,
                                'Wear': stick.get('wear', 0) * 100 if 'wear' in stick else 0
                            } for stick in more_info['stickers'] if stick is not None and more_info['stickers'] is not None
                        ]
                        countpricestickers = [total for x in stickersfull for total in x.values()][::2]
                        total = sum(countpricestickers)
                        c = Counter(countpricestickers)
                        count = [c[x] for x in countpricestickers if c[x] >= 3]

                        r = total
                        if len(count) == 3:
                            r = total * 1.15
                        elif len(count) == 4:
                            r = total * 1.25
                        else:
                            pass
                    else:
                        stickersfull = strickers

                    sql.execute("SELECT id FROM Users WHERE id=?", (more_info['asset_id'],))
                    if sql.fetchone() is None:
                        sql.execute("INSERT INTO Users VALUES (?)", (more_info['asset_id'],))
                        db.commit()
                        if float_value <= 0.009 or type(stickersfull) is list and r >= 8:
                            gun = {
                                'Name': name,
                                'Float': float_value,
                                'steam_price':base_price,
                                'final_price':final_price,
                                'Bit_price': auc_price,
                                'IMG': img,
                                'Stickers': stickersfull,
                                'total_price_stickers': total
                            }
                            pprint.pprint(gun)
                            bot_telegram(item=gun)

def bot_telegram(item):
    TOKEN = "bot_token" # замените на свой token
    channel_id = 'Your chanal_id' # замените на свой chanal_id
    
    Name = item['Name']
    float = item['Float']
    final_price = item['final_price']
    price_steam = item['steam_price']
    bit_price = item['Bit_price']
    total_price_stickers = item['total_price_stickers']
    img = item['IMG']

    message = f"CSGOFLOAT.COM(auction)\n\n<b>Name</b>:<code> {Name}</code>\n<b>Float</b>: {float}\n\n<b>Final_price</b>: <strong>{final_price}$</strong>\n<b>Price_Steam</b>: <strong>{price_steam}$</strong>\n<b>Bit_Price</b>: <strong>{bit_price}$</strong>\n<b>Stickers</b>:\n\n"
    # Добавляем информацию о стикерах
    stickers = item.get('Stickers', [])
    if stickers:
        for i, sticker in enumerate(stickers, 1):
            name = next(iter(sticker.keys()))
            price = next(iter(sticker.values()))
            wear = sticker['Wear']
            message += f"{i}. <code>{name}</code> | {price}$\nWear = {wear}\n"
    else:
        message += "No stickers available\n"
    # Добавляем информацию о общей стоимости стикеров
    message += f"\nℹ️<b>Total_price_stickers</b>: {total_price_stickers}$\n"
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    data2 = {
        "parse_mode": "HTML"
    }
    
    data1 = {
           "chat_id": channel_id,
           "photo": img,
           "caption": message,
           "parse_mode": "HTML"    
        }
    response = requests.post(url,data=data1)
    if response.status_code != 200:
        print(Name,"Ошибка при отправке сообщения")
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={channel_id}&text={message}",data=data2)

if __name__ == '__main__':
    db = sqlite3.connect('my_database.db')
    sql = db.cursor()
    create_database()
    main(db,sql)
    while True:
        try:
            main(db,sql)
            time.sleep(300)
        except Exception as e:
            print(f'Произошла ошибка! {e}')
            time.sleep(65)