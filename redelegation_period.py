import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode
from agency_info import AllAgencies
from database import telegramDb
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
    global AllAgencies
    user_id = update.effective_chat['id']
    user_agency = telegramDb.get_user_agency(user_id)['name']
    if user_agency not in AllAgencies:
        telegramDb.set_user_agency(user_id, default_agency)
        user_agency = telegramDb.get_user_agency(user_id)['name']
    TS = AllAgencies[user_agency]
    if TS.APR == 0:
        for i in range(30):
            TS = AllAgencies[user_agency]
            if TS.APR != 0:
                break
            print("\tsleeping")
            time.sleep(0.01)

    egld = update.message.text

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(emoji.back + " Back", callback_data='back')]
    ])
    text = ''
    try:
        egld = float(egld)
        if not egld > 0:
            text = "Please enter a positive number:"
        else:
            best_i, best_amount = get_best_step(egld, TS.APR)
            text = best_period.format(best_i, best_amount, TS.APR, TS.name)
    except Exception as e:
        text = "Please enter a number"
        print("\tError: %s" % str(e))
    update.message.reply_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )
    return RedelegationPerion
