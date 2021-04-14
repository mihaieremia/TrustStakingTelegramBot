from telegram import *
from telegram.ext import *

import emoji
from agency_info import agency_info_handle, Agency
from database import Database
from redelegation_period import redelegation_period, send_result
from subscriptions import subscriptions, unsubscribe, callback_subscription, subscribeAvailableSpace, change
import requests
from utils import *

reply_buttons = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(emoji.info + " Agency info", callback_data='agency_info')
    ],
    [
        InlineKeyboardButton(emoji.pencil + "Find optimal redelegation period", callback_data='redelegation_period')
    ],
    [
        InlineKeyboardButton(emoji.mail + "Subscriptions", callback_data='subscriptions')
    ]
])
telegramDb = Database()


def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        text='Main menu',
        reply_markup=reply_buttons,
    )
    return MainMenu


def main_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    bot = context.bot
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text='Main menu',
        reply_markup=reply_buttons,
    )
    return MainMenu

oldAvaiable = 0.0
def telegram_bot_sendtext(job):
    subscription = job.job.context
    global oldAvaiable
    bot_token = '1724076081:AAE0US-BoKRnSdfiF_V7j9zvzNSgPqAjdB4'
    subscribed_users = telegramDb.get_subscribed_users(subscription)
    TS = Agency()
    newAvailable = TS.maxDelegationCap - TS.totalActiveStake
    if newAvailable != oldAvaiable:
        print("Old Available: ", oldAvaiable)
        oldAvaiable = newAvailable
        print("Available: ", newAvailable)
        for user in subscribed_users:
            if newAvailable >= user['availableSpace']:
                bot_message = emoji.attention + " {:.4f}".format(newAvailable) + " eGLD available to be stake"
                send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' \
                            + str(user['_id']) + '&parse_mode=Markdown&text=' + bot_message
                response = requests.get(send_text)


def main():

    updater = Updater(
        '1654360962:AAFNJTAZxdplj1nrgsv9LnfmCntOMR-DdGg')
    dp = updater.dispatcher
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MainMenu: [
                CallbackQueryHandler(agency_info_handle, pattern='agency_info'),
                CallbackQueryHandler(redelegation_period, pattern='redelegation_period'),
                CallbackQueryHandler(subscriptions, pattern='subscriptions')
            ],
            AgencyInfo: [
                CallbackQueryHandler(main_menu, pattern='back')
            ],
            RedelegationPerion: [
                MessageHandler(Filters.text & ~Filters.command, send_result),
                CallbackQueryHandler(main_menu, pattern='back'),
            ],
            SubscriptionsMenu: [
                CallbackQueryHandler(callback_subscription, pattern='availableSpace$'),
                CallbackQueryHandler(unsubscribe, pattern='.*_unsubscribe'),
                CallbackQueryHandler(change, pattern='.*_change'),
                CallbackQueryHandler(subscriptions, pattern='back$'),
                CallbackQueryHandler(main_menu, pattern='back_main_menu'),

            ],
            availableSpace: [
                MessageHandler(Filters.text & ~Filters.command, subscribeAvailableSpace),
                CallbackQueryHandler(subscriptions, pattern='back'),
            ]
        },
        fallbacks=[CommandHandler('start', start)]
    )

    dp.add_handler(conv_handler)
    updater.job_queue.run_repeating(telegram_bot_sendtext, 3, context="availableSpace")
    updater.start_polling()

    updater.idle()

if __name__ == "__main__":
    main()