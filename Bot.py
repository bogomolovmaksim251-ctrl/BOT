import telebot
import time
import random
import os
from telebot import types
from flask import Flask
from threading import Thread

# --- НАСТРОЙКИ ---
# ВСТАВЛЕН ТВОЙ ТОКЕН (НИКОМУ ЕГО НЕ ПОКАЗЫВАЙ!)
BOT_TOKEN = "9041855905:AAGufnTDR88RHY2qxtCmi8fzumHowzNTu9I" 

CHANNEL_ID = "@твой_канал" # Сюда вставь юзернейм канала (бот должен быть админом!)
PRIZE_ACCOUNT = "@аккаунт_выдачи" # Сюда вставь юзернейм аккаунта выдачи
TARGET_POINTS = 100 # Сколько баллов нужно для приза

bot = telebot.TeleBot(BOT_TOKEN)
users = {} # База данных (пока в памяти)

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# --- ФУНКЦИИ БОТА ---
def get_user(user_id):
    if user_id not in users:
        users[user_id] = {'points': 0, 'last_claim': 0, 'ref_id': 0}
    return users[user_id]

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['creator', 'administrator', 'member']
    except:
        return False

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("🎁 Получить баллы")
    btn2 = types.KeyboardButton("🏆 Мои баллы")
    btn3 = types.KeyboardButton("👥 Пригласить друга")
    markup.add(btn1, btn2, btn3)
    return markup

# --- ОБРАБОТЧИКИ КОМАНД И КНОПОК ---

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    args = message.text.split()
    
    if len(args) > 1 and user['ref_id'] == 0:
        referrer_id = int(args[1])
        if referrer_id != user_id:
            user['ref_id'] = referrer_id 
            ref_user = get_user(referrer_id)
            ref_user['points'] += 10 
            try:
                bot.send_message(referrer_id, "🎉 По вашей ссылке зашел новый человек! Вам начислено 10 баллов.")
            except:
                pass
                
    bot.send_message(
        user_id, 
        f"Привет, {message.from_user.first_name}!\nНабери {TARGET_POINTS} баллов и получи приз!", 
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "🏆 Мои баллы")
def show_points(message):
    user = get_user(message.from_user.id)
    bot.send_message(message.chat.id, f"У вас {user['points']} баллов из {TARGET_POINTS}.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "👥 Пригласить друга")
def invite(message):
    user_id = message.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.send_message(message.chat.id, f"Пригласите друга и получите 10 баллов!\n{link}", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "🎁 Получить баллы")
def claim_points(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("Подписаться на канал", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")
        markup.add(btn)
        bot.send_message(message.chat.id, "Чтобы получать баллы, вы должны быть подписаны на наш канал!", reply_markup=markup)
        return
        
    current_time = time.time()
    cooldown = 5 * 60 * 60 
    
    if current_time - user['last_claim'] < cooldown:
        time_left = cooldown - (current_time - user['last_claim'])
        hours = int(time_left // 3600)
        minutes = int((time_left % 3600) // 60)
        bot.send_message(message.chat.id, f"Приходите через {hours} ч. {minutes} мин.", reply_markup=get_main_keyboard())
        return
        
    points_earned = random.randint(1, 10)
    user['points'] += points_earned
    user['last_claim'] = current_time
    
    bot.send_message(message.chat.id, f"🎉 Вы получили {points_earned} баллов!\nТеперь у вас {user['points']} баллов.", reply_markup=get_main_keyboard())
    
    if user['points'] >= TARGET_POINTS:
        prize_text = (
            f"Время: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Юзернейм: @{message.from_user.username}\n"
            f"Вы набрали достаточное количество баллов, чтобы получить приз. "
            f"Перешлите это сообщение нашему аккаунту {PRIZE_ACCOUNT} для выдачи призов.\n\n"
            f"(За поддельное сообщение или доказательство предусмотрено обнуление ваших баллов.)"
        )
        bot.send_message(message.chat.id, prize_text)

# --- ЭХО-ОБРАБОТЧИК (В САМОМ КОНЦЕ!) ---
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(
        message, 
        "Я тебя услышал! 👋\nНо лучше пользуйся кнопками меню ниже, чтобы играть.",
        reply_markup=get_main_keyboard()
    )

# --- ЗАПУСК ---
if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    print("Бот запущен в фоне...")
    bot.infinity_polling()