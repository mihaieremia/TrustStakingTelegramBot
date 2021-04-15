from telegram import *
from telegram.ext import *

from agency_info import agency_info_handle, agency_info_handle_extra, update_agency_info, GTS
from redelegation_period import redelegation_period, send_result
from subscriptions import subscriptions, unsubscribe, callback_subscription, subscribeAvailableSpace, change
from utils import *
from wallets import wallets, wallet_configuration, wallet_info, rename_wallet, delete_wallet

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
    update.message.reply_text(
        text=emoji.cat + 'Main menu\n'
             'This is the testing bot. \n'
             'Please refer to @TrustStakingBot for the official release.',
        reply_markup=reply_buttons,
    )
    return MainMenu


def main_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    bot = context.bot
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=emoji.cat + 'Main menu\n'
             'This is the testing bot. \n'
             'Please refer to @TrustStakingBot for the official release.',
        reply_markup=reply_buttons,
    )
    return MainMenu

oldAvaiable = 0.0
def telegram_bot_sendtext(job):
    subscription = job.job.context
    global oldAvaiable
    global GTS
    TS = GTS
    subscribed_users = telegramDb.get_subscribed_users(subscription)
    newAvailable = TS.maxDelegationCap - TS.totalActiveStake
    if newAvailable != oldAvaiable:
        print("Old Available: ", oldAvaiable)
        oldAvaiable = newAvailable
        print("Available: ", newAvailable)
        for user in subscribed_users:
            if newAvailable >= user['availableSpace']:
                bot_message = emoji.attention + " {:.2f}".format(newAvailable) + " eGLD available to be staked."
                send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' \
                            + str(user['_id']) + '&parse_mode=Markdown&text=' + bot_message
                response = requests.get(send_text)


def main():
    updater = Updater(bot_token)
    dp = updater.dispatcher

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
                CallbackQueryHandler(main_menu, pattern='back')
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
    updater.job_queue.run_repeating(update_agency_info, 15, context="agency_info")
    updater.job_queue.run_repeating(update_price, 120, context="price_update")
    updater.start_polling()

    updater.idle()


if __name__ == "__main__":
    main()
