import re
import time
from datetime import datetime, timedelta

from erdpy import errors
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from threading import Thread
from agency_info import AllAgencies, get_user_staking_agencies
from database import telegramDb
from utils import *


def get_keyboard(user_id, user_wallets):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(emoji.plus + " Add wallet", callback_data='add_wallet')
        ],
        [
            InlineKeyboardButton(emoji.back + " Back", callback_data='back')
        ]
    ])
    for i, wallet in enumerate(user_wallets):
        if wallet['label'] is None:
            telegramDb.delete_wallet(user_id, wallet['address'])
            continue
        keyboard.inline_keyboard.insert(i, [
            InlineKeyboardButton("#" + str(i + 1) + ". " + wallet['label'] + " - " + wallet['address'],
                                 callback_data=wallet['address'])
        ])
    return keyboard


def update_wallets(user_id, user_wallets):
    print("update_wallets called")
    global AllAgencies
    for wallet in user_wallets:
        print("\t wallet updating: ", wallet)
        now = datetime.now()
        if now - wallet['last_update'] > timedelta(seconds=30):
            available = get_active_balance(wallet['address'])
            delegated_agencies = {}
            for agency in get_user_staking_agencies(wallet['address']):
                active, claimable, totalRewards = AllAgencies[agency].get_address_info(wallet['address'])
                if active >= 1:
                    delegated_agencies[AllAgencies[agency].name] = {'active': active,
                                                                    'claimable': claimable,
                                                                    'totalRewards': totalRewards}

            telegramDb.update_wallet(user_id, wallet['address'], available, delegated_agencies)


def wallet_configuration(update, context):
    print("wallet_configuration called")
    try:
        msg = update.message.text
    except:
        print("\tphase 1 enter wallet")
        query = update.callback_query
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(emoji.back + " Back", callback_data='back')
            ]
        ])
        context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text='Please enter a wallet addres:',
            reply_markup=keyboard
        )
        return WalletConfiguration
    wallet_pattern = re.compile("erd.*")
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(emoji.back + " Back", callback_data='back')
        ]
    ])
    user_id = update.effective_chat['id']
    user = telegramDb.get_user(user_id)
    if wallet_pattern.match(msg):
        print("\tphase 2 enter label")
        try:
            Address(msg)._assert_validity()
            if user is None:
                telegramDb.add_user(user_id)
            text = "Please enter a label for wallet address:\n<code>" + msg + "</code>"
            if not telegramDb.add_wallet(user_id, msg, None):
                text = "You already have this address saved!\nPlease enter another one!"
        except errors.EmptyAddressError():
            text = 'Address invalid!'
        except Exception as e:
            print(f"\t\t {e}")
            text = 'Error when entering the addres. Please try again.'
        update.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
        print("\tphase 3 finish")
        wallet = telegramDb.get_wallet(user_id, None)
        text = "Wallet saved"
        if wallet['label'] is None:
            telegramDb.set_label(user_id, wallet['address'], msg)
        else:
            text = "Wallet has not been saved due to an error\nPlease try again!"

        update.message.reply_text(
            text=text,
            reply_markup=reply_markup
        )
    return WalletConfiguration


def rename_wallet(update, context):
    print("rename_wallet called")

    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(emoji.back + " Back", callback_data='back')
        ]
    ])
    user_id = update.effective_chat['id']
    try:
        new_label = update.message.text
        wallet = telegramDb.get_wallet(user_id, "^toberenamed")
        text = "Wallet renamed."
        if wallet is not None:
            telegramDb.set_label(user_id, wallet['address'], new_label)
        else:
            text = "Wallet has not been renamed due to an error\nPlease try again!"

        update.message.reply_text(
            text=text,
            reply_markup=reply_markup
        )
    except AttributeError:
        query = update.callback_query
        bot = context.bot
        label = query.data.split("^_^")[1]
        wallet = telegramDb.get_wallet(user_id, '^' + label + '$')
        telegramDb.set_label(user_id, wallet['address'], "toberenamed_" + label)
        bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text="Please enter a label for wallet address:\n<code>" + wallet['address'] + "</code>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    return WalletStatus


def delete_wallet(update, context):
    print("delete_wallet called")

    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(emoji.back + " Back", callback_data='back')
        ]
    ])
    user_id = update.effective_chat['id']

    query = update.callback_query
    bot = context.bot
    label = query.data.split("^_^")[1]
    wallet = telegramDb.get_wallet(user_id, '^' + label + '$')
    text = 'Wallet deleted'
    if not telegramDb.delete_wallet(user_id, wallet['address']):
        text = "Wallet has not been removed due to an error\nPlease try again!"
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=text,
        reply_markup=reply_markup
    )
    return WalletStatus


price = None

def get_current_price():
    print("get_current_price called")
    url = 'https://data.elrond.com/market/quotes/egld/price'
    try:
        resp = requests.get(url)
        data = resp.json()
        print(f'\tget_current_price reply: {data[-1]}')
        return data[-1]['value']
    except KeyError as e:
        print("\tKeyError: %s" % str(e))
        return 0
    except TypeError as e:
        print("\tTypeError: %s" % str(e))
        return 0
    except Exception as e:
        print("\tError: %s" % str(e))
        return 0

def update_price(job):
    global price
    price = get_current_price()


def mex_calculator(update, context):
    print("mex_calculator called")

    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(emoji.back + " Back", callback_data='back')
        ]
    ])
    user_id = update.effective_chat['id']

    query = update.callback_query
    bot = context.bot
    label = query.data.split("^_^")[1]
    wallet = telegramDb.get_wallet(user_id, '^' + label + '$')
    available = wallet['available']
    active = 0
    for agency in wallet['agencies'].keys():
        active += wallet['agencies'][agency]['active']

    mex_available = available ** 0.95
    mex_active = active ** 0.95 * 1.5
    total = mex_active + mex_available
    text = mex_calculator_info.format(total, mex_active, active, mex_available, available)
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML

    )
    return MEXCalc


def wallet_info(update, context):
    print("wallet_info called")
    global price
    query = update.callback_query
    address = query.data
    bot = context.bot
    user_id = query.from_user.id
    wallet = telegramDb.get_wallet_by_address(user_id, address)
    keyboard = InlineKeyboardMarkup([
        # [
        #     InlineKeyboardButton(emoji.sparkles + " Delegate", callback_data='delegate'),
        #     InlineKeyboardButton(emoji.no_entry2 + " Undelegate", callback_data='undelegate')
        # ],
        # [
        #     InlineKeyboardButton(emoji.money + " Claim", url=claimURL.format(GTS.contract.address)),
        #     InlineKeyboardButton(emoji.anticlockwise + " Restake", callback_data='restake')
        # ],
        [
            InlineKeyboardButton(emoji.pocket_calculator + " MEX calculator", callback_data='mex^_^' + wallet['label'])
        ],
        [
            InlineKeyboardButton(emoji.bookmark + " Rename", callback_data='rename^_^' + wallet['label']),
            InlineKeyboardButton(emoji.trash + " Delete", callback_data='delete^_^' + wallet['label'])
        ],
        [
            InlineKeyboardButton(emoji.back + " Back", callback_data='back')
        ]
    ])
    if price is None:
        price = get_current_price()
    available = wallet['available']
    text = ''
    total = available
    for agency in wallet['agencies'].keys():
        active = wallet['agencies'][agency]['active']
        claimable = wallet['agencies'][agency]['claimable']
        totalRewards = wallet['agencies'][agency]['totalRewards']
        total += active + claimable
        text += wallet_for_agency_info.format(agency,
                                              active, active * price,
                                              claimable, claimable * price,
                                              totalRewards, totalRewards * price,
                                              price
                                              )
    text = wallet_information.format(wallet['address'], wallet['label'],
                                     wallet['address'][:10], wallet['address'][-6:],
                                     available, available * price, total, total * price) + text
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )
    return WalletStatus


def wallets(update, context):
    print("wallets called")
    query = update.callback_query
    bot = context.bot
    user_id = query.from_user.id
    user_wallets = telegramDb.get_wallets(user_id)
    background_thread = Thread(target=update_wallets, args=(user_id, user_wallets.clone()))
    background_thread.start()
    keyboard = get_keyboard(user_id, user_wallets)

    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=emoji.credit_card + " My wallets",
        reply_markup=keyboard
    )
    return Wallets
