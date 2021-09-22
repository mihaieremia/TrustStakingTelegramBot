import threading
import time
import datetime

from telegram import *
from telegram.ext import *
import sys
from agency_info import Agency, agency_info_handle, agency_info_handle_extra, \
    update_agencies_info, agencies_search, show_agency, change_agency, update_user_agency, get_all_contracts, \
    AllAgencies, update_agency
from redelegation_period import redelegation_period, send_result
from subscriptions import subscriptions, unsubscribe, callback_subscription, subscribeAvailableSpace, subscribe, \
    set_threshold
from utils import *
from database import telegramDb
from wallets import wallets, wallet_configuration, wallet_info, rename_wallet, delete_wallet, mex_calculator, \
    update_price
from threading import Thread

import prettytable as pt

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
    message, chat = messages_to_be_deleted[user][agency]
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

        if agency in old_available_values:
            oldAvailable = old_available_values[agency]
            if newAvailable == 'unlimited' or newAvailable >= 1:
                if oldAvailable != newAvailable:
                    print("\ttelegram_bot_sendtext available - " + TS.name)
                    background_thread = Thread(target=send_notification,
                                               args=(subscription, newAvailable, agency, TS.name))
                    background_thread.start()
            elif oldAvailable == 'unlimited' or oldAvailable >= 1:
                print("\ttelegram_bot_sendtext full - " + TS.name)
                background_thread = Thread(target=send_full_notification,
                                           args=(subscription, newAvailable, agency, TS.name))
                background_thread.start()
        else:
            print("\ttelegram_bot_sendtext first value - " + TS.name)
            old_available_values[agency] = newAvailable


def send_full_notification(subscription, newAvailable, agency, agency_name):
    print('send_full_notification called')
    subscribed_users = telegramDb.get_subscribed_users(subscription, agency)
    for user in subscribed_users:
        bot_message = '{} is full again!'.format(agency_name) + emoji.sad_face
        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' \
                    + str(user['_id']) + '&parse_mode=Markdown&text=' + bot_message
        response = requests.get(send_text)
        data = response.json()
        if not data['ok']:
            print(user['_id'], ":", data)
        else:
            message_id = data['result']['message_id']
            chat_id = data['result']['chat']['id']
            time.sleep(0.1)
            if user['_id'] not in messages_to_be_deleted.keys():
                messages_to_be_deleted[user['_id']] = {}
            if agency_name in messages_to_be_deleted[user['_id']].keys():
                delete_spam(user['_id'], agency_name)
            messages_to_be_deleted[user['_id']][agency_name] = [message_id, chat_id]
    old_available_values[agency] = newAvailable


def send_notification(subscription, newAvailable, agency, agency_name):
    print('send_notification called')
    global AllAgencies

    requests = 0
    bad_requests = 0
    under_requests = 0
    subscribed_users = telegramDb.get_subscribed_users(subscription, agency)
    for user in subscribed_users:
        requests += 1
        threshold = telegramDb.get_threshold(user['_id'], subscription, agency)
        print(old_available_values[agency], " ", newAvailable)
        if abs(old_available_values[agency] - newAvailable) >= threshold:
            bad_requests += check_and_notify(user['_id'], newAvailable, agency, agency_name)
        else:
            under_requests += 1
    old_available_values[agency] = newAvailable
    if requests >= 1:
        print('\t\t notifications sent for agency:', agency_name, 'free space: ', newAvailable, 'eGLD')
        updating = Thread(target=update_agency, args=(list(AllAgencies.keys()).index(agency),))
        updating.start()
        if bad_requests > 0:
            print("\t\tbad requests", str(bad_requests) + "/" + str(requests))
        if under_requests > 0:
            print("\t\tunder threshold requests", str(under_requests) + "/" + str(requests))


def check_and_notify(user_id, newAvailable, agency, name):
    global messages_to_be_deleted

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
        if data['description'] == 'Forbidden: bot was blocked by the user':
            telegramDb.unsubscribe(user_id, 'availableSpace', agency)
        print(user_id, ":", data)
        return 1
    message_id = data['result']['message_id']
    chat_id = data['result']['chat']['id']
    time.sleep(0.1)
    if user_id not in messages_to_be_deleted.keys():
        messages_to_be_deleted[user_id] = {}
    if name in messages_to_be_deleted[user_id].keys():
        delete_spam(user_id, name)
    messages_to_be_deleted[user_id][name] = [message_id, chat_id]

    return 0


antispam_to_delete = []


def delete_antiscam():
    global bot
    global antispam_to_delete
    for message, chat in antispam_to_delete:
        bot.deleteMessage(chat, message)
        time.sleep(0.1)
    antispam_to_delete = []


def antiscam(job):
    delete_antiscam()
    send_antiscam(job)
    send_antiscamRO(job)


def send_antiscam(job):
    global antispam_to_delete
    file_ids = ["CAACAgQAAxkBAAIhXGCW8IfTuyru08JKCdbPjJWnnmBIAAIUAAMu8zoS0u3oU_aQqIMfBA",
                "CAACAgQAAxkBAAIhXWCW8InPkPkkxqhJXfzaFe8EkHEfAAJdCAACM6thUAGqayRCrbszHwQ",
                "CAACAgQAAxkBAAIhW2CW8IX16Jlt-doUqHzuLfDGuOKLAAISAAMu8zoSeb51JZauMoIfBA"
                ]
    for file_id in file_ids:
        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendSticker?chat_id=' \
                    + str(-1001370506176) + '&sticker=' + file_id
        response = requests.get(send_text)
        time.sleep(0.01)
        data = response.json()
        message_id = data['result']['message_id']
        chat_id = data['result']['chat']['id']
        antispam_to_delete.append((message_id, chat_id))

    message = '''
    ⚠️⚠️⚠️ SECURITY ALERT ⚠️⚠️⚠️

    - Elrond admins will never give you the first private message!

    "Elrond's admins will never call you first!"

    - Elrond admins will not send you an EGLD / ETH / BTC address by Telegram / Email!

    - Elrond Official, Elrond Official Support and other names like SCAM, any questions are solved on the official groups!

    - Please beware of scammers and do not trust anyone who asks you for $eGLD, staking space, passwords or the 24 words!

    -There will never be a need for a representative of the Elrond team or an admin to approach you personally.

    If you are unsure of something, ask.

    Report the scams to @notoscam & join @ElrondScambusters

    Stay alert!
    '''
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' \
                + str(-1001370506176) + '&parse_mode=Markdown&text=' + message
    response = requests.get(send_text)
    data = response.json()
    message_id = data['result']['message_id']
    chat_id = data['result']['chat']['id']
    antispam_to_delete.append((message_id, chat_id))


def send_antiscamRO(job):
    global antispam_to_delete
    print('send_antiscamRO called')
    file_ids = ["CAACAgQAAxkBAAIhXGCW8IfTuyru08JKCdbPjJWnnmBIAAIUAAMu8zoS0u3oU_aQqIMfBA",
                "CAACAgQAAxkBAAIhXWCW8InPkPkkxqhJXfzaFe8EkHEfAAJdCAACM6thUAGqayRCrbszHwQ",
                "CAACAgQAAxkBAAIhW2CW8IX16Jlt-doUqHzuLfDGuOKLAAISAAMu8zoSeb51JZauMoIfBA"
                ]
    for file_id in file_ids:
        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendSticker?chat_id=' \
                    + str(-1001416314327) + '&sticker=' + file_id
        response = requests.get(send_text)
        print('\t', response.status_code)
        data = response.json()
        message_id = data['result']['message_id']
        chat_id = data['result']['chat']['id']
        antispam_to_delete.append((message_id, chat_id))
        time.sleep(0.01)
    message = '''
    \u26a0\ufe0f\u26a0\ufe0f\u26a0\ufe0f ALERTA DE SECURITATE \u26a0\ufe0f\u26a0\ufe0f\u26a0\ufe0f
    
    - Adminii Elrond nu v\u0103 vor da niciodata primii mesaj privat!
    
    - Adminii Elrond nu v\u0103 vor suna niciodata primii!
    
    - Adminii Elrond nu v\u0103 vor trimite o adresa de EGLD/ETH/BTC prin Telegram/Email!
    
    - Elrond Official, Elrond Official Support si alte denumiri de genul sunt SCAM, orice nelamurire se rezolva pe grupurile oficiale!
    
    - Va rog sa fi\u021bi atenti la \u00een\u0219el\u0103torii \u0219i s\u0103 nu ave\u021bi incredere in nimeni care v\u0103 cere $EGLD, loc la staking, parole sau cele 24 de cuvinte!
    
    -Nu va exista vreodata nevoia ca un reprezentant al echipei Elrond sau un admin sa va abordeze personal.
    
    Daca sunteti nesiguri de ceva intrebati. 
    
    Raportati scamurile la @notoscam & alaturati-va pe @ElrondScambusters
    
    - R\u0103m\u00e2ne\u021bi vigilen\u021bi!
    '''
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' \
                + str(-1001416314327) + '&parse_mode=Markdown&text=' + message
    response = requests.get(send_text)
    data = response.json()
    message_id = data['result']['message_id']
    chat_id = data['result']['chat']['id']
    antispam_to_delete.append((message_id, chat_id))
    print('RO:', antispam_to_delete)


def send_new_epoch_status(job):
    print("send_new_epoch_status called")
    msg = f"%23dailystatus {getEpoch(datetime.datetime.today().timestamp())}\n"
    table = pt.PrettyTable(['Daily', 'Nodes', 'Forcast'])
    table.align['Pool'] = 'l'
    table.align['Daily'] = 'l'
    table.align['Tomorrow'] = 'l'
    try:
        with open('trust_agencies.json', 'r') as fp:
            trust_agencies = json.load(fp)
    except Exception as e:
        print(e)
        trust_agencies = trust_agencies_backup
    for agency in trust_agencies:
        agency_name = agency['name']
        update_agency(list(AllAgencies.keys()).index(agency_name), extra_info=True)
        reply = AllAgencies[agency_name].contract.query(mainnet_proxy, 'getContractConfig', [])
        owner_address = Address(json.loads(reply[0].to_json())['hex']).bech32()
        url = 'http://api.elrond.tax/accounts/'
        resp = requests.get(url + owner_address + '/txHistory')
        data = resp.json()
        if 'error' in data:
            print(data['error'] + " " + agency_name, file=sys.stderr)
            send_update_error(data['error'] + " " + agency_name)
            break
        if 'rewards' not in data:
            print('No rewards' + " " + agency_name, file=sys.stderr)
            send_update_error('No rewards' + " " + agency_name)
            break
        data = data['rewards']
        if 'avgAPR_per_provider' in data \
                and AllAgencies[agency_name].contract.address.bech32() in data['avgAPR_per_provider']:
            avg = float(data['avgAPR_per_provider'][AllAgencies[agency_name].contract.address.bech32()])
        else:
            avg = 0.00
        try:
            last = data['rewards_per_epoch'][AllAgencies[agency_name].contract.address.bech32()][0]
        except Exception as e:
            print("error:", e)
            last_apy = {'epoch': '-', "APRDelegator": '0.00'}
        fapy = 0.0
        current_eligible = AllAgencies[agency_name].nodes['eligible']['total']
        last_apy = float(last["APRDelegator"])
        if last_apy:
            if agency['last_eligible'] > 0:
                fapy = round(last_apy * current_eligible / agency['last_eligible'], 2)
            else:
                fapy = '-'
        # msg += provider_daily_statistic.format(AllAgencies[agency_name].name,
        #                                        last_apy,
        #                                        current_eligible,
        #                                        AllAgencies[agency_name].nodes['total']['active'],
        #                                        fapy,
        #                                        avg,
        #                                        )
        name = AllAgencies[agency_name].name.replace('Trust Staking', '')
        if name == '':
            name = '--M--'
        elif 'US' in name:
            name = '-USA-'
        elif 'Swiss' in name:
            name = 'Swiss'
        elif 'Portugal' in name:
            name = '-PRT-'
        elif 'Netherlands' in name:
            name = '-NLD-'
        table.add_row(['-----', '-----', '-------'])
        table.add_row(['-----', name.strip(), '-------'])
        table.add_row(['-----', '-----', '-------'])
        table.add_row([f'{last_apy:.2f}',
                       str(current_eligible) + '/' + str(AllAgencies[agency_name].nodes['total']['active']), fapy])
        agency['last_eligible'] = current_eligible
    table = str(table)\
        .replace(' | --M-- | --', 'Trust Staking')\
        .replace('--- | Swiss | -----', 'Trust Staking Swiss')\
        .replace('- | -USA- | ----', 'Trust Staking US')\
        .replace('----- | -PRT- | -------', 'Trust Staking Portugal ') \
        .replace('---- | -NLD- | ------', 'Trust the Netherlands')
    for user in epoch_status_users:
        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' \
                    + str(user) + '&parse_mode=HTML&text=' + msg + f'<pre>{table}</pre>'

        response = requests.get(send_text)
        data = response.json()
    with open('trust_agencies.json', 'w') as fp:
        json.dump(trust_agencies, fp)


def update_eligible():
    print("update_eligible called")
    try:
        with open('trust_agencies.json', 'r') as fp:
            trust_agencies = json.load(fp)
            print('\texisting values loaded')
    except Exception as e:
        print(e)
        print('\tfile not found, creating new one...')
        trust_agencies = trust_agencies_backup
        for agency in trust_agencies:
            update_agency(list(AllAgencies.keys()).index(agency['name']), extra_info=True)
            agency['last_eligible'] = AllAgencies[agency['name']].nodes['eligible']['total']
    with open('trust_agencies.json', 'w') as fp:
        json.dump(trust_agencies, fp)


def main():
    updater = Updater(bot_token)
    dp = updater.dispatcher
    global bot
    bot = dp.bot
    get_all_contracts()
    update_eligible()
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
                CallbackQueryHandler(set_threshold, pattern='.*_threshold'),
                CallbackQueryHandler(callback_subscription, pattern='availableSpace$'),  # back
                CallbackQueryHandler(main_menu, pattern='back_main_menu'),
            ],
            availableSpace_threshold: [
                MessageHandler(Filters.text & ~Filters.command, set_threshold),
                CallbackQueryHandler(callback_subscription, pattern='availableSpace$')
            ]
        },
        fallbacks=[CommandHandler('start', start)])

    dp.add_handler(conv_handler)

    dp.add_handler(InlineQueryHandler(agencies_search))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, show_agency))

    updater.job_queue.run_repeating(telegram_bot_sendtext, 10, context="availableSpace")
    updater.job_queue.run_repeating(update_agencies_info, 2, context="update_agencies_info")
    # updater.job_queue.run_repeating(antiscam, 43200, first=21600, context="antiscam")
    updater.job_queue.run_repeating(update_price, 120, context="price_update", )

    send_new_epoch_status(None)
    t = datetime.time(14, 50)
    updater.job_queue.run_daily(send_new_epoch_status, t, context="send_new_epoch_status")
    updater.start_polling()

    updater.idle()


if __name__ == "__main__":
    main()
