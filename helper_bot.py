
import logging
# from systemd.journal import JournaldLogHandler

import time

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

import re
import requests
import json


api_url = "http://localhost:4444"


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# instantiate the JournaldLogHandler to hook into systemd
# journald_handler = JournaldLogHandler()

# set a formatter to include the level name
# journald_handler.setFormatter(logging.Formatter(
#     '[%(levelname)s] %(message)s'
# ))

# logger.addHandler(journald_handler)

# optionally set the logging level
logger.setLevel(logging.DEBUG)

START = 1
END = 2
PHOTO = 3
OPEN_BOOK = 4
ACTION = 5
JALOBA = 6
PREDLOJ = 7
OTZYV = 8
SEND_ID = 9
CANCEL = 10
SELECT_LANG = 11
MAIN = 12
SETTINGS = 13
SHOW_MAIN_MENU = 14

message_from_user = {}

order_type = {
    'Жалоба 😡': 1,
    'Предложение 😎': 2,
    'Отзыв 😊': 3,
    'Shikoyat 😡': 1,
    'Maqtov 😊': 3,
    'Taklif 😎': 2,
}

langs = {
    "uz": 1,
    "ru": 2,
    "en": 3
}

visitor_lang = 'uz'

dialog = {
    'ru': {
        'greeting': 'Здраствуйте уважавемый %s 👋',
        'ask_for_send': 'Хотите написать владельцу предприятия?',
        'select_lang': 'Выберите язык 🌐',
        'set_settings': 'Установите настройки',
        'main_menu': 'Выберите категорию',
        'enter_ID': 'Введите ID предприятия 🏤 :',
        'book': 'Книжка жалоб и предложений 📖',
        'settings': '⚙️ Настройки',
        'uz_lang': '🇺🇿 O\'zbek 🇺🇿',
        'ru_lang': '🇷🇺 Русский 🇷🇺',
        'back': '◀️ Назад',
        'main_menu_opt': 'Главное меню ▶️',
        'contact_opt': '☎️ Контакты',
        'complaint_opt': 'Жалоба 😡',
        'review_opt': 'Отзыв 😊',
        'offer_opt': 'Предложение 😎',
        'choose_action': 'Выберите действие ☝️',
        'complaint_q': '🤧 Введите причину Вашего недовольствия:',
        'review_q': '🤩 Напишите нам Ваши впечатления:',
        'offer_q': '🧐 Напишите нам Ваши предложения:',
        'no_photo': 'Нет фото',
    },
    'uz': {
        'greeting': 'Assalomu alaykum qadrli %s 👋',
        'ask_for_send': 'Tashkilot rahbariga murojaatingiz bormi?',
        'select_lang': 'Tilni tanlang 🌐',
        'set_settings': 'Sozlamalarni o\'rnating',
        'main_menu': 'Kategoriyalardan birini tanlang',
        'enter_ID': '🏤 Tashkilotning ID sini kiriting:',
        'book': 'Ariza va takliflar kitobi 📖',
        'settings': '⚙️ Sozlamalar',
        'uz_lang': '🇺🇿 O\'zbek 🇺🇿',
        'ru_lang': '🇷🇺 Русский 🇷🇺',
        'back': '◀️ Ortga',
        'main_menu_opt': 'Asosiy menyu ▶️',
        'contact_opt': '☎️ Kontaktlar',
        'complaint_opt': 'Shikoyat 😡',
        'review_opt': 'Maqtov 😊',
        'offer_opt': 'Taklif 😎',
        'choose_action': 'Nima yubormoqchisiz ☝️',
        'complaint_q': '🤧 Noroziligingiz sababini yuboring:',
        'review_q': '🤩 O\'z taassurotlaringizni biz bilan ulashing:',
        'offer_q': '🧐 O\'z takliflaringizni bizga yuboring:',
        'no_photo': 'Rasm yo\'q',
    }
}

visitor_info_q = """
            query{
                visitors(where: {username: "%s"}){
                    username
                    id
                    lang
                }
            }
        """

nav_rk = {
    'uz': [dialog['uz']['back'], dialog['uz']['main_menu_opt']],
    'ru': [dialog['ru']['back'], dialog['ru']['main_menu_opt']],
}

main_rk = {
    'uz': [[dialog['uz']['book']], [dialog['uz']['settings']]],
    'ru': [[dialog['ru']['book']], [dialog['ru']['settings']]],
}

lang_rk = {
    'uz': [[dialog['uz']['uz_lang']], [dialog['uz']['ru_lang']],
           nav_rk['uz']],
    'ru': [[dialog['ru']['uz_lang']], [dialog['ru']['ru_lang']],
           nav_rk['ru']]
}

settings_rk = {
    'uz':  [[dialog['uz']['select_lang']], [dialog['uz']['contact_opt']], [dialog['uz']['main_menu_opt']]],
    'ru':  [[dialog['ru']['select_lang']], [dialog['ru']['contact_opt']], [dialog['ru']['main_menu_opt']]],
}

action_rk = {
    'uz': [[dialog['uz']['complaint_opt'], dialog['uz']['review_opt']], [dialog['uz']['offer_opt']], nav_rk['uz']],
    'ru': [[dialog['ru']['complaint_opt'], dialog['ru']['review_opt']], [dialog['ru']['offer_opt']], nav_rk['ru']],
}

photo_rk = {
    'uz': [[dialog['uz']['no_photo']], nav_rk['uz']],
    'ru': [[dialog['uz']['no_photo']], nav_rk['ru']],
}

temp = {

}


def start(update, context):
    lang = context.user_data['lang'] = visitor_lang
    user = update.effective_user

    res = requests.post(f'{api_url}/graphql', data={
        "query": visitor_info_q % (user.username)
    }).json()

    if res["data"]["visitors"][0]:
        visitor = res["data"]["visitors"][0]
        if visitor["lang"]:
            lang = context.user_data['lang'] = visitor["lang"]
        else:
            return show_lang(update, context)

    name = user.first_name + " " + user.last_name

    update.message.reply_text(
        "%s" % (dialog[lang]["greeting"] % (name)))

    update.message.reply_text(dialog[lang]['ask_for_send'],
                              reply_markup=ReplyKeyboardMarkup(main_rk[lang], resize_keyboard=True),)

    return OPEN_BOOK


def show_settings(update, context):
    lang = context.user_data.get('lang', visitor_lang)
    update.message.reply_text(dialog[lang]['set_settings'],
                              reply_markup=ReplyKeyboardMarkup(settings_rk[lang], resize_keyboard=True),)
    return SETTINGS


def settings(update, context):
    lang = context.user_data.get('lang', visitor_lang)

    if re.search(dialog[lang]['contact_opt'], update.message.text):
        return show_main_menu(update, context)
    elif re.search(dialog[lang]['select_lang'], update.message.text):
        return show_lang(update, context)
    elif re.search(dialog[lang]['main_menu_opt'], update.message.text):
        return show_main_menu(update, context)


def show_lang(update, context):
    lang = context.user_data.get('lang', visitor_lang)
    update.message.reply_text(dialog[lang]["select_lang"],
                              reply_markup=ReplyKeyboardMarkup(lang_rk[lang], resize_keyboard=True))
    return SELECT_LANG


def select_lang(update, context):
    lang = context.user_data.get('lang', visitor_lang)
    if re.search(dialog[lang]['uz_lang'], update.message.text):
        context.user_data['lang'] = 'uz'
    elif re.search(dialog[lang]['ru_lang'], update.message.text):
        context.user_data['lang'] = 'ru'
    elif re.search(dialog[lang]['main_menu_opt'], update.message.text):
        return show_main_menu(update, context)
    elif re.search(dialog[lang]['back'], update.message.text):
        return show_settings(update, context)

    print(context.user_data['lang'])
    return show_settings(update, context)


def show_main_menu(update, context):
    lang = context.user_data.get('lang', visitor_lang)
    update.message.reply_text(dialog[lang]["main_menu"],
                              reply_markup=ReplyKeyboardMarkup(main_rk[lang], resize_keyboard=True))
    return MAIN


def main_menu(update, context):
    lang = context.user_data.get('lang', visitor_lang)
    if re.search(dialog[lang]['book'], update.message.text):
        return openBook(update, context)
    elif re.search(dialog[lang]['settings'], update.message.text):
        return show_settings(update, context)


def openBook(update, context):

    # print(update)
    # logger.info(update)
    lang = context.user_data.get('lang', visitor_lang)

    update.message.reply_text(dialog[lang]['enter_ID'],
                              reply_markup=ReplyKeyboardMarkup(
        [nav_rk[lang]], resize_keyboard=True))

    res = requests.post(f'{api_url}/visitors/{update.message.from_user.username}', data={
        "username": update.message.from_user.username,
        "phone": None,
        "chat_id": update.message.chat.id
    })

    # print(f'http://localhost:4444/visitors/{update.message.from_user.username}')

    # print(res.text)

    return SEND_ID


def sendID(update, context):
    lang = context.user_data.get('lang', visitor_lang)

    if re.search(dialog[lang]['main_menu_opt'], update.message.text):
        return show_main_menu(update, context)
    elif re.search(dialog[lang]['back'], update.message.text):
        return show_main_menu(update, context)

    try:
        message_from_user['ID'] = int(update.message.text)
    except:
        return openBook(update, context)

    return show_action(update, context)

    # update.message.reply_text('Ждраствуйте уважаемый ', update.effective_user)


def show_action(update, context):
    lang = context.user_data.get('lang', visitor_lang)
    update.message.reply_text(dialog[lang]['choose_action'],
                              reply_markup=ReplyKeyboardMarkup(action_rk[lang], resize_keyboard=True))

    return ACTION


def action(update, context):
    lang = context.user_data.get('lang', visitor_lang)
    if re.search(dialog[lang]['main_menu_opt'], update.message.text):
        return show_main_menu(update, context)
    elif re.search(dialog[lang]['back'], update.message.text):
        return openBook(update, context)
    message = update.message.text

    if re.search(dialog[lang]['complaint_opt'], message):
        message_from_user['type'] = dialog[lang]['complaint_opt']
        update.message.reply_text(
            dialog[lang]['complaint_q'], reply_markup=ReplyKeyboardMarkup(
                [nav_rk[lang]], resize_keyboard=True))
        return JALOBA
    elif re.search(dialog[lang]['review_opt'], message):
        message_from_user['type'] = dialog[lang]['review_opt']
        update.message.reply_text(
            dialog[lang]['review_q'], reply_markup=ReplyKeyboardMarkup(
                [nav_rk[lang]], resize_keyboard=True))
        return OTZYV
    elif re.search(dialog[lang]['offer_opt'], message):
        message_from_user['type'] = dialog[lang]['offer_opt']
        update.message.reply_text(
            dialog[lang]['offer_q'], reply_markup=ReplyKeyboardMarkup(
                [nav_rk[lang]], resize_keyboard=True))
        return OTZYV
    else:
        return show_action(update, context)

    return CANCEL


def jaloba(update, context):
    lang = context.user_data.get('lang', visitor_lang)
    if re.search(dialog[lang]['main_menu_opt'], update.message.text):
        return show_main_menu(update, context)
    elif re.search(dialog[lang]['back'], update.message.text):
        return show_action(update, context)

    message = update.message.text
    message_from_user['text'] = message
    update.message.reply_text('Отправьте фото если имеется 🏞', reply_markup=ReplyKeyboardMarkup(
        photo_rk[lang], resize_keyboard=True))
    return PHOTO


def otzyv(update, context):
    lang = context.user_data.get('lang', visitor_lang)
    if re.search(dialog[lang]['main_menu_opt'], update.message.text):
        return show_main_menu(update, context)
    elif re.search(dialog[lang]['back'], update.message.text):
        return ACTION
    message = update.message.text
    message_from_user['text'] = message
    update.message.reply_text(
        'Спасибо за вклад для внесенный для продвижения сервиса! 👍')
    return end(update, context)


def photo(update, context):
    user = update.message.from_user
    photo_file = update.message.photo[-1].get_file()
    if photo_file != None:
        photo_file.download('user_photo-{}.jpg'.format(time.time()))
        logger.info("Photo of %s: %s", user.first_name, 'user_photo.jpg')
        message_from_user['photo'] = photo_file
    else:
        message_from_user['photo'] = ''
        return skip_photo(update, context)

    return end(update, context)


def skip_photo(update, context):
    user = update.message.from_user
    logger.info("User %s did not send a photo.", user.first_name)

    return end(update, context)


def end(update, context):
    lang = context.user_data.get('lang', visitor_lang)
    gq = """
            query{
                visitors(where: {username: "%s"}){
                    username
                    id
                }
            }
        """ % (update.message.from_user.username)

    res = requests.post(f'http://localhost:4444/graphql', data={
        "query": gq
    })

    resJson = res.json()

    # print(resJson)

    id = resJson["data"]["visitors"][0]["id"]
    data = {
        "text": message_from_user["text"],
        "visitor": id,
        "type": order_type[message_from_user["type"]]
    }

    res = requests.post(f'{api_url}/orders', data=data)

    print(data)

    update.message.reply_text(
        f'Вы оставили следуещее заявление:\n'
        f'🏤 ID предприятия: {message_from_user["ID"]}\n'
        f'📬 Тип запроса: {message_from_user["type"]}\n'
        f'💬 Текст запроса: {message_from_user["text"]}\n'
        f'Уважаемый {update.effective_user.username}, на Ваш запрос ответим в кратчайшие сроки 👌\n',
        reply_markup=ReplyKeyboardMarkup([nav_rk[lang]], resize_keyboard=True)
    )

    return SHOW_MAIN_MENU


def cancel(update, context):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Bye! I hope we can talk again some day.', reply_markup=None
    )

    return ConversationHandler.END


def main():
    updater = Updater(
        "1416576907:AAFlPluGEQTcCJtAVAx2o00GvGiqEMuxIpo", use_context=True)

    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', show_main_menu),
                      MessageHandler(Filters.regex(
                          '^(.*menyu.*|.*меню.*)$'), show_main_menu),
                      MessageHandler(Filters.regex(
                          dialog[visitor_lang]['book']), show_main_menu),
                      MessageHandler(Filters.regex(
                          '^(Sozlamalar|Настройки)$'), show_settings)
                      ],
        states={
            OPEN_BOOK: [MessageHandler(Filters.text, openBook)],
            SEND_ID: [MessageHandler(Filters.text, sendID)],
            ACTION: [MessageHandler(Filters.text, action)],
            JALOBA: [MessageHandler(Filters.text, jaloba)],
            PREDLOJ: [MessageHandler(Filters.text, action)],
            OTZYV: [MessageHandler(Filters.text, otzyv)],
            PHOTO: [
                MessageHandler(Filters.photo, photo),
                CommandHandler('skip', start),
                MessageHandler(Filters.regex(f'^({dialog["uz"]["no_photo"]}|{dialog["ru"]["no_photo"]})$'), end)],
            CANCEL: [CommandHandler('cancel', cancel)],
            START: [MessageHandler(Filters.text, start),
                    CommandHandler('start', start),
                    MessageHandler(Filters.regex("^(Назад)$"), end)],
            END: [MessageHandler(Filters.text, end), CommandHandler('end', end)],
            SELECT_LANG: [MessageHandler(Filters.text, select_lang)],
            MAIN: [MessageHandler(Filters.text, main_menu),
                   MessageHandler(Filters.regex("^(Asosiy menyu)$"), show_main_menu)],
            SETTINGS: [MessageHandler(Filters.text, settings)],
            SHOW_MAIN_MENU: [MessageHandler(Filters.text, show_main_menu)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
