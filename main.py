import threading
import time

from telegram import *
from telegram.ext import *

from agency_info import Agency, agency_info_handle, agency_info_handle_extra, \
    update_agencies_info, agencies_search, show_agency, change_agency, update_user_agency, get_all_contracts, \
    AllAgencies, update_agency
from redelegation_period import redelegation_period, send_result
from subscriptions import subscriptions, unsubscribe, callback_subscription, subscribeAvailableSpace, subscribe
from utils import *
from database import telegramDb
from wallets import wallets, wallet_configuration, wallet_info, rename_wallet, delete_wallet, mex_calculator
from threading import Thread

reply_buttons = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(emoji.info + " Agency info", callback_data='agency_info')
    ],
    [
        InlineKeyboardButton(emoji.credit_card + " My wallets", callback_data='wallets')
    ],
    [
        InlineKeyboardButton(emoji.pencil + "Find optimal redelegation period", callback_data='redelegation_period')
    ],
    [
        InlineKeyboardButton(emoji.mail + "Subscriptions", callback_data='subscriptions')
    ]
])


def start(update: Update, context: CallbackContext):
    user_id = update.effective_chat['id']
    print("start called by: ", user_id)
    message_id = update.effective_message['message_id']
    if user_id < 0:
        try:
            context.bot.deleteMessage(user_id, message_id)
        except Exception as e:
            print("\t Delete message failed:", e)
        return
    background_thread = Thread(target=update_price, args=(None,))
    background_thread.start()
    background_thread = Thread(target=update_user_agency, args=(user_id,))
    background_thread.start()

    update.message.reply_text(
        text=main_menu_message,
        reply_markup=reply_buttons,
    )
    return MainMenu


def main_menu(update: Update, context: CallbackContext):
    user_id = update.effective_chat['id']
    background_thread = Thread(target=update_user_agency, args=(user_id,))
    background_thread.start()

    query = update.callback_query
    bot = context.bot
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=main_menu_message,
        reply_markup=reply_buttons,
    )
    return MainMenu


old_available_values = {}
messages_to_be_deleted = {}
bot = None

def delete_spam(user, agency):
    global messages_to_be_deleted
    global bot
    if user not in messages_to_be_deleted and \
        agency not in messages_to_be_deleted[user] and \
        len(messages_to_be_deleted[user][agency]) < 2:
        return
    for message, chat in messages_to_be_deleted[user][agency][1:]:
        bot.deleteMessage(chat, message)
    messages_to_be_deleted[user][agency] = []


def telegram_bot_sendtext(job):
    print('telegram_bot_sendtext called')
    subscription = job.job.context
    global AllAgencies
    for agency in AllAgencies:
        TS = AllAgencies[agency]
        if TS.maxDelegationCap == 'unlimited':
            newAvailable = TS.maxDelegationCap
        else:
            newAvailable = TS.maxDelegationCap - TS.totalActiveStake
        if newAvailable == 'unlimited' or newAvailable >= 1 \
            or (agency in old_available_values
                and (old_available_values[agency] == 'unlimited'
                     or old_available_values[agency] >= 1)):
            background_thread = Thread(target=send_notification, args=(subscription, newAvailable, agency, TS.name))
            background_thread.start()



def send_notification(subscription, newAvailable, agency, agency_name):
    global oldAvailable
    global AllAgencies

    requests = 0
    bad_requests = 0

    if not agency in old_available_values:
        old_available_values[agency] = 0
    if newAvailable != old_available_values[agency]:
        subscribed_users = telegramDb.get_subscribed_users(subscription, agency)
        for user in subscribed_users:
            requests += 1
            bad_requests += check_and_notify(user['_id'], newAvailable, old_available_values[agency], agency_name)
            old_available_values[agency] = newAvailable
        if requests >= 1:
            print('\t\t notifications sent for agency:', agency_name, 'free space: ', newAvailable, 'eGLD')
            print('\t\t force update agency:', agency_name)
            updating = Thread(target=update_agency, args=(list(AllAgencies.keys()).index(agency),))
            updating.start()
            print("\t\tbad requests", str(bad_requests) + "/" + str(requests))


def check_and_notify(user_id, newAvailable, oldAvailable, name):
    print('\tcheck_and_notify called')
    global messages_to_be_deleted
    if newAvailable == 'unlimited' or newAvailable >= 1:
        bot_message = emoji.attention
        if isinstance(newAvailable, float):
            bot_message += " {:.2f}".format(newAvailable)
        else:
            bot_message += newAvailable
        bot_message += " eGLD available to be staked for {}".format(name)

        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' \
                    + str(user_id) + '&parse_mode=Markdown&text=' + bot_message
        response = requests.get(send_text)
        data = response.json()
        if not data['ok']:
            print(user_id, ":", data)
            return 0
        message_id = data['result']['message_id']
        chat_id = data['result']['chat']['id']
        time.sleep(0.1)
        if user_id not in messages_to_be_deleted.keys():
            messages_to_be_deleted[user_id] = {}
        if name not in messages_to_be_deleted[user_id].keys():
            messages_to_be_deleted[user_id][name] = []
        messages_to_be_deleted[user_id][name].append([message_id, chat_id])
    elif oldAvailable == 'unlimited' or oldAvailable >= 1:
        bot_message = '{} is full again!'.format(name) + emoji.sad_face
        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' \
                    + str(user_id) + '&parse_mode=Markdown&text=' + bot_message
        response = requests.get(send_text)
        data = response.json()
        if not data['ok']:
            print(user_id, ":", data)
            return 0
        delete_spam(user_id, name)
        time.sleep(0.1)
    else:
        print("\t error: user_id", user_id, "agency", name, "newAvailable", newAvailable, 'oldAvailable', oldAvailable)
        return 0
    return 1


def main():
    updater = Updater(bot_token)
    dp = updater.dispatcher
    global bot
    bot = dp.bot
    get_all_contracts()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MainMenu: [
                CallbackQueryHandler(agency_info_handle, pattern='agency_info'),
                CallbackQueryHandler(redelegation_period, pattern='redelegation_period'),
                CallbackQueryHandler(subscriptions, pattern='subscriptions'),
                CallbackQueryHandler(wallets, pattern='wallets')
            ],
            AgencyInfo: [
                CallbackQueryHandler(agency_info_handle_extra, pattern='more_info'),
                CallbackQueryHandler(agency_info_handle, pattern='less_info'),
                CallbackQueryHandler(change_agency, pattern='change_agency'),
                CallbackQueryHandler(main_menu, pattern='back')
            ],
            ChangeAgency: [
                MessageHandler(Filters.text & ~Filters.command, change_agency),
                CallbackQueryHandler(agency_info_handle, pattern='back')
            ],
            Wallets: [
                CallbackQueryHandler(wallet_configuration, pattern='add_wallet'),
                CallbackQueryHandler(wallet_info, pattern='^erd.*'),
                CallbackQueryHandler(main_menu, pattern='back')
            ],
            WalletStatus: [
                CallbackQueryHandler(rename_wallet, pattern='rename'),
                MessageHandler(Filters.text & ~Filters.command, rename_wallet),
                CallbackQueryHandler(delete_wallet, pattern='delete'),
                CallbackQueryHandler(mex_calculator, pattern='mex'),
                CallbackQueryHandler(wallets, pattern='back')

            ],
            MEXCalc: [
                CallbackQueryHandler(wallets, pattern='back')
            ],
            WalletConfiguration: [
                MessageHandler(Filters.text & ~Filters.command, wallet_configuration),
                CallbackQueryHandler(wallets, pattern='back')
            ],
            RedelegationPerion: [
                MessageHandler(Filters.text & ~Filters.command, send_result),
                CallbackQueryHandler(main_menu, pattern='back'),
            ],
            SubscriptionsMenu: [
                CallbackQueryHandler(callback_subscription, pattern='availableSpace$'),
                CallbackQueryHandler(main_menu, pattern='back_main_menu'),

            ],
            availableSpace: [
                CallbackQueryHandler(subscribe, pattern='new_agency'),
                CallbackQueryHandler(unsubscribe, pattern='.*_unsubscribe$'),
                MessageHandler(Filters.text & ~Filters.command, subscribeAvailableSpace),
                CallbackQueryHandler(callback_subscription, pattern='availableSpace$'),  # back
                CallbackQueryHandler(main_menu, pattern='back_main_menu'),
            ]
        },
        fallbacks=[CommandHandler('start', start)])

    dp.add_handler(conv_handler)

    dp.add_handler(InlineQueryHandler(agencies_search))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, show_agency))

    updater.job_queue.run_repeating(telegram_bot_sendtext, 10, context="availableSpace")
    updater.job_queue.run_repeating(update_agencies_info, 2, context="update_agencies_info")
    updater.job_queue.run_repeating(update_price, 120, context="price_update", )
    updater.start_polling()

    updater.idle()


if __name__ == "__main__":
    main()
