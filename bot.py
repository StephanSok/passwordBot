import time
import telebot
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from telebot import types
import sqlite3

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')


class Account(BaseModel):
    login: str
    password: str


def makeCopyKeyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text='Скопировано', callback_data='copy'))
    return markup


def makeKeyboard(chat_id):
    markup = types.InlineKeyboardMarkup()

    for key, value in user_chats[chat_id].items():
        markup.add(
            types.InlineKeyboardButton(
                text=key, callback_data="acc " + str(chat_id) + ' ' + key
            ),
            types.InlineKeyboardButton(text=crossIcon, callback_data="cross " + key),
        )
    return markup


def get_acc(chat_id: int, service: str):
    if chat_id not in user_chats or service not in user_chats[chat_id]:
        return False
    return user_chats[chat_id][service]


def del_acc(chat_id: int, service: str):
    global cursor
    global db
    if chat_id not in user_chats or service not in user_chats[chat_id]:
        return False
    del user_chats[chat_id][service]
    cursor.execute(
        "DELETE FROM users WHERE chat_id=(?) AND service=(?)",
        (chat_id, service),
    )
    db.commit()
    return True


bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_chats = {}
crossIcon = u"\u274C"
db = sqlite3.connect('server.db', check_same_thread=False)
cursor = db.cursor()
cursor.execute(
    "CREATE TABLE IF NOT EXISTS users (chat_id INT, service TEXT, login TEXT, password TEXT)"
)
db.commit()


def read_db():
    global user_chats
    user_chats = {}
    for values in cursor.execute("SELECT * FROM users"):
        if values[0] not in user_chats:
            user_chats[values[0]] = {}
        # if len(user_chats[values[0]]) == 0:
        #     user_chats[values[0]][values[1]] = {}
        user_chats[values[0]][values[1]] = Account(login=values[2], password=values[3])
    print(user_chats)


@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id,
        '1) /set - эту команду можно использовать, чтобы добавить логин и пароль к сервису.\n'
        '\t\t\tПример использования: /set название_сервиса логин пароль.\n'
        '2) /get - эту команду можно применить, чтобы воспользоваться интерактивным меню, с помощью которого\n'
        '\t\t\tможно получить логин и пароль по названию сервиса или удалить соответствующие ему значения.\n' 
        '\t\t\tПример использования: /get.\n'
        '3) /del - эту команду можно использовать, чтобы удалить значения логина и пароля для сервиса.\n' 
        '\t\t\tПример использования: /del название_сервиса.\n'
        '\t\t\tТакже для удаления можно использовать интерактивное меню после команды /get.\n')

@bot.message_handler(commands=['set'])
def set_account(message):
    words = message.text.split()
    if len(words) < 4:
        bot.send_message(message.chat.id, '/set <SERVICE> <LOGIN> <PASSWORD>')
        return
    if message.chat.id not in user_chats:
        user_chats[message.chat.id] = {}
    if words[1] in user_chats[message.chat.id]:
        bot.send_message(message.chat.id, 'У этого сервиса уже есть учетная запись')
        return
    user_chats[message.chat.id][words[1]] = Account(login=words[2], password=words[3])
    cursor.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?)",
        (message.chat.id, words[1], words[2], words[3]),
    )
    db.commit()
    bot.send_message(message.chat.id, 'Готово')


@bot.message_handler(commands=['del'])
def delete_account(message):
    words = message.text.split()
    if len(words) < 2:
        bot.send_message(message.chat.id, '/del <SERVICE>')
        return
    if not del_acc(message.chat.id, words[1]):
        bot.send_message(
            message.chat.id, 'У вас нет учетной записи в сервисе с таким именем'
        )
        return
    bot.send_message(message.chat.id, 'Готово')


@bot.message_handler(commands=['get'])
def get_accounts(message):
    if message.chat.id in user_chats and len(user_chats[message.chat.id]) != 0:
        bot.send_message(
            chat_id=message.chat.id,
            text="Все ваши учетные записи:",
            reply_markup=makeKeyboard(message.chat.id),
            parse_mode='HTML',
        )
    else:
        bot.send_message(
            chat_id=message.chat.id,
            text="У вас пока нет сохраненных паролей",
            parse_mode='HTML',
        )


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data.startswith("acc"):
        account = get_acc(call.message.chat.id, call.data.split()[2])
        if account:
            bot.answer_callback_query(
                callback_query_id=call.id,
                show_alert=True,
                text='login: ' + account.login + '\npassword: ' + account.password,
            )
            bot.send_message(
                chat_id=call.message.chat.id,
                text='login: `' + account.login + '` \npassword: `' + account.password + '`',
                reply_markup=makeCopyKeyboard(),
                parse_mode='MARKDOWN',
            )
        else:
            bot.send_message(
                call.message.chat.id,
                'У вас нет учетной записи в сервисе с таким именем',
            )
            if (
                call.message.chat.id in user_chats
                and len(user_chats[call.message.chat.id]) != 0
            ):
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    text="Все ваши учетные записи:",
                    message_id=call.message.message_id,
                    reply_markup=makeKeyboard(call.message.chat.id),
                    parse_mode='HTML',
                )
            else:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    text="У вас пока нет сохраненных паролей",
                    message_id=call.message.message_id,
                    parse_mode='HTML',
                )

    if call.data.startswith("cross"):
        if del_acc(call.message.chat.id, call.data.split()[1]):
            if (
                call.message.chat.id in user_chats
                and len(user_chats[call.message.chat.id]) != 0
            ):
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    text="Все ваши учетные записи:",
                    message_id=call.message.message_id,
                    reply_markup=makeKeyboard(call.message.chat.id),
                    parse_mode='HTML',
                )
            else:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    text="У вас пока нет сохраненных паролей",
                    message_id=call.message.message_id,
                    parse_mode='HTML',
                )
            bot.send_message(
                call.message.chat.id,
                'Данные учетной записи ' + call.data.split()[1] + ' удалены',
            )
        else:
            bot.send_message(
                call.message.chat.id,
                'У вас нет учетной записи в сервисе с таким именем',
            )
            if (
                call.message.chat.id in user_chats
                and len(user_chats[call.message.chat.id]) != 0
            ):
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    text="Все ваши учетные записи:",
                    message_id=call.message.message_id,
                    reply_markup=makeKeyboard(call.message.chat.id),
                    parse_mode='HTML',
                )
            else:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    text="У вас пока нет сохраненных паролей",
                    message_id=call.message.message_id,
                    parse_mode='HTML',
                )

    if call.data.startswith("copy"):
        bot.delete_message(call.message.chat.id, call.message.message_id)


while True:
    try:
        read_db()
        bot.polling(none_stop=True, interval=0, timeout=0)
    except:
        print('sleep')
        time.sleep(10)
