from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

import emoji
from utils import *


def total_amount(n, m, P, APR, fee=0.0001355):
    I = APR / (100 * n)
    J = (1 + I) ** m
    return J * P - (J - 1) * fee / I


def get_best_step(init_delegation, APR, total_days=365):
    print("get_best_step called")
    max_step = 1
    max_amount = init_delegation
    steps_to_test = range(1, total_days)
    for i in steps_to_test:
        step = total_days // i
        # print("step= ", step)
        amount = total_amount(step, step, init_delegation, APR)
        # print(i, " -----------a= ", amount)
        if max_amount < amount:
            max_amount = amount
            max_step = total_days // step
    print("\tBest value with step : ", max_step, " ", max_amount)
    reward = max_amount - init_delegation
    return max_step, reward


def redelegation_period(update, context):
    query = update.callback_query
    bot = context.bot

    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text='Please indicate your staked amount:',
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(emoji.back + " Back", callback_data='back')
            ]
        ])
    )

    return RedelegationPerion


def send_result(update: Update, context):
    egld = update.message.text
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(emoji.back + " Back", callback_data='back')]
    ])
    try:
        egld = float(egld)
        if not egld > 0:
            raise TypeError("You introduced a negative number.\n")
        best_i, best_amount = get_best_step(egld, 17.9)

        update.message.reply_text(
            text="Best APY for redelegation at %d days. Total reward after one year: %.6f \n" % (best_i, best_amount) +
                 "You can indicate another eGLD amount to calculate the optimal redelegation period",
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
    return RedelegationPerion
