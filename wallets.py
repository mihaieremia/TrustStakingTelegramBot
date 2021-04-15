import re
import time
from datetime import datetime, timedelta
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from threading import Thread
from agency_info import Agency, GTS
from utils import *


def get_keyboard(user_id, user_wallets):
    global GTS
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
    for wallet in user_wallets:
        now = datetime.now()
        if now - wallet['last_update'] > timedelta(seconds=30):
            available, active, claimable, totalRewards = GTS.get_address_info(wallet['address'])
            telegramDb.update_wallet(user_id, wallet['address'], available, active, claimable, totalRewards)

def wallet_configuration(update, context):
    print("wallet_configuration called")
    try:
        msg = update.message.text
    except:
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
        try:
            Address(msg)._assert_validity()
            if user is None:
                telegramDb.add_user(user_id)
            text = "Please enter a label for wallet address:\n<code>" + msg + "</code>"
            if not telegramDb.add_wallet(user_id, msg, None):
                text = "You already have this address saved!\nPlease enter another one!"
        except:
            text = 'Address invalid!'
        update.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
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
        label = query.data.split("_")[1]
        wallet = telegramDb.get_wallet(user_id, '^' + label +'$')
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
    label = query.data.split("_")[1]
    wallet = telegramDb.get_wallet(user_id, '^' + label +'$')
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

def wallet_info(update, context):
    print("wallet_info called")
    global GTS
    global price
    query = update.callback_query
    address = query.data
    bot = context.bot
    user_id = query.from_user.id
    wallet = telegramDb.get_wallet_byAddress(user_id, address)
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
            InlineKeyboardButton(emoji.bookmark + " Rename", callback_data='rename_' + wallet['label']),
            InlineKeyboardButton(emoji.trash + " Delete", callback_data='delete_' + wallet['label'])
        ],
        [
            InlineKeyboardButton(emoji.back + " Back", callback_data='back')
        ]
    ])

    available = wallet['available']
    active = wallet['active']
    claimable = wallet['claimable']
    totalRewards = wallet['totalRewards']
    if available == 0 and active == 0 and claimable == 0 and totalRewards == 0:
        available = wallet['available']
        active = wallet['active']
        claimable = wallet['claimable']
        totalRewards = wallet['totalRewards']
        while not (available == 0 and active == 0 and claimable == 0 and totalRewards == 0):
            time.sleep(0.05)
    text = wallet_information.format(wallet['address'], wallet['label'], wallet['address'][:10], wallet['address'][-6:],
                                     available, available * price,
                                     active, active * price,
                                     claimable, claimable * price,
                                     totalRewards, totalRewards * price,
                                     )
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
