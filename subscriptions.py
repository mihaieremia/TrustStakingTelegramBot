from telegram import InlineKeyboardMarkup, InlineKeyboardButton

import emoji
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
    return subscribe(update, context, 'availableSpace')


def get_return_state(subscription):
    returnType = None
    if subscription == 'availableSpace':
        returnType = availableSpace

    return returnType


def subscribe(update, context, subscription):
    user_id = update.effective_chat['id']
    user = telegramDb.get_user(user_id)
    text = "You have been subscribed.\n"
    if user is None:
        telegramDb.add_user(user_id)

    if telegramDb.is_subscribed(user_id, subscription):
        text = "Amount notification changed.\n"
    egld = update.message.text
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(emoji.back + " Back", callback_data='back')]
    ])

    try:
        egld = float(egld)
        if not egld > 0:
            raise TypeError("You introduced a negative number.\n")
        telegramDb.subscribe(user_id, subscription, egld)

        update.message.reply_text(
            text=text,
            reply_markup=reply_markup
        )
    except TypeError as e:
        update.message.reply_text(
            text=str(e) + "Please enter a positive number:",
            reply_markup=reply_markup
        )
    except:
        update.message.reply_text(
            text="Please enter a number",
            reply_markup=reply_markup
        )

    return get_return_state(subscription)


def unsubscribe(update, context):
    bot = context.bot
    query = update.callback_query
    unsubscribe_method = query.data.split("_")[0]
    user_id = query.from_user.id
    user = telegramDb.get_user(user_id)
    if user is not None:
        telegramDb.unsubscribe(user_id, unsubscribe_method)
        reply_text = "You have been unsubscribed. You will no longer receive notifications regarding "
        if unsubscribe_method == 'availableSpace':
            reply_text += "availability of staking with us."
        bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text=reply_text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(emoji.back + " Back", callback_data='back')
                ]
            ])
        )
    return get_return_state(unsubscribe_method)


def change(update, context):
    query = update.callback_query
    reply_text = 'Please indicate over how much eGLD do you want to be notified.'
    returnType = get_return_state(query.data.split("_")[0])

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(emoji.back + " Back", callback_data='back')
        ]
    ])

    context.bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=reply_text,
        reply_markup=keyboard
    )
    return returnType


def callback_subscription(update, context):
    query = update.callback_query
    subscription = query.data
    user_id = query.from_user.id
    returnType = SubscriptionsMenu
    user = telegramDb.get_user(user_id)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(emoji.back + " Back", callback_data='back')
        ]
    ])
    if user is None:  # if user does not exist
        reply_text = 'Please indicate over how much eGLD do you want to be notified.'
        returnType = get_return_state(query.data)
    else:  # if user exists
        subscribed = telegramDb.is_subscribed(user_id, subscription)
        if subscribed:
            reply_text = "You are already subscribed.\n"
            if subscription == 'availableSpace':
                reply_text += 'You will be notified when TrustStaking will have at least {} eGLD available to be staked.'.format(
                    user['availableSpace'])
                keyboard.inline_keyboard.insert(0, [InlineKeyboardButton(emoji.no_entry + " Unsubscribe",
                                                                         callback_data='availableSpace_unsubscribe'),
                                                    InlineKeyboardButton(emoji.change + " Change alert amount",
                                                                         callback_data='availableSpace_change')]
                                                )
        else:  # not subscribed
            reply_text = 'Please indicate over how much eGLD do you want to be notified.'
            returnType = get_return_state(query.data)

    context.bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=reply_text,
        reply_markup=keyboard
    )
    return returnType


def subscriptions(update, context):
    print("subscriptions called")
    query = update.callback_query
    bot = context.bot
    keyboard = get_keyboard()
    user_id = query.from_user.id
    user = telegramDb.get_user(user_id)
    subscribed = False
    if user is not None:
        subscribed = telegramDb.is_subscribed(user_id, "availableSpace")
    if subscribed:
        keyboard.inline_keyboard[0][0].text = emoji.checkmark + keyboard.inline_keyboard[0][0].text
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text='Here you can choose to be notified by the bot on different scenarios:',
        reply_markup=keyboard
    )
    return SubscriptionsMenu
