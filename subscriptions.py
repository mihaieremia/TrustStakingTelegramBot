from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from database import telegramDb
from agency_info import AllAgencies
from utils import *


def get_keyboard():
    return InlineKeyboardMarkup([
        # [
        #     InlineKeyboardButton(emoji.money + " Rewards received", callback_data='subscribe_1')
        # ],
        # [
        #     InlineKeyboardButton(emoji.hourglass + " Redelegation reminder", callback_data='subscribe_2')
        # ],
        [
            InlineKeyboardButton(emoji.fire + " Available delegation amount to be staked",
                                 callback_data='availableSpace')
        ],
        [
            InlineKeyboardButton(emoji.back + " Back", callback_data='back_main_menu')
        ]
    ])


def subscribeAvailableSpace(update, context):
    global AllAgencies
    print("\tsubscribeAvailableSpace called")
    user_id = update.effective_chat['id']
    if update.message is None:
        return
    agency = update.message.text
    if agency not in AllAgencies.keys():
        return
    telegramDb.subscribe(user_id, 'availableSpace', agency)
    text = "Subscribed!"
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(emoji.back + " Back", callback_data='availableSpace')]
    ])
    update.message.reply_text(
        text=text,
        reply_markup=reply_markup
    )
    return availableSpace


def get_return_state(subscription):
    returnType = None
    if subscription == 'availableSpace':
        returnType = availableSpace

    return returnType


def subscribe(update, context):
    query = update.callback_query
    subscription = query.data.split("_")[1]
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(emoji.back + " Back", callback_data='availableSpace')]
    ])
    bot = context.bot
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=choose_agency,
        reply_markup=reply_markup
    )

    return get_return_state(subscription)


def unsubscribe(update, context):
    global AllAgencies
    bot = context.bot
    query = update.callback_query
    agency, unsubscribe_method, _ = query.data.split("_")
    if len(agency) == 37:
        agency = [agency for agency in AllAgencies.keys() if agency in AllAgencies]
    user_id = query.from_user.id
    user = telegramDb.get_user(user_id)
    if user is not None:
        telegramDb.unsubscribe(user_id, unsubscribe_method, agency)
        reply_text = "You have been unsubscribed from " + AllAgencies[agency].name + " !"
        bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text=reply_text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(emoji.back + " Back", callback_data='availableSpace')
                ]
            ])
        )
    return get_return_state(unsubscribe_method)




def callback_subscription(update, context):
    global AllAgencies
    query = update.callback_query
    subscription = query.data
    user_id = query.from_user.id
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(emoji.plus + " Subscribe to new agency", callback_data='new_agency')
        ],
        [
            InlineKeyboardButton(emoji.back + " Back", callback_data='back_main_menu')
        ]
    ])
    reply_text = 'You subscribed to the following agencies:\n' \
                 '*Click on the agency name to unsubscribe.'
    agencies = telegramDb.get_agency_subscribed(user_id, subscription)

    for agency in agencies:
        keyboard.inline_keyboard.insert(0,
            [
                InlineKeyboardButton(AllAgencies[agency].name,
                                     callback_data=agency + '_' + subscription + '_unsubscribe'),
            ])
    if len(agencies) == 0:
        reply_text = 'No subscriptions yet.'
    context.bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=reply_text,
        reply_markup=keyboard
    )
    return get_return_state(query.data)


def subscriptions(update, context):
    print("subscriptions called")
    query = update.callback_query
    bot = context.bot
    keyboard = get_keyboard()

    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text='Here you can choose to be notified by the bot on different scenarios:',
        reply_markup=keyboard
    )
    return SubscriptionsMenu
