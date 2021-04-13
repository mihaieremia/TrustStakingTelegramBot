import json

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram import Update
from telegram.ext import CallbackContext

import emoji
from utils import *


class Agency:
    def __init__(self, proxy=mainnet_proxy, contract=TrustStaking_contract):
        self.proxy = proxy
        self.contract = contract
        self.numNode = self.query('getNumNodes')
        self.delegators = self.query('getNumUsers')
        self.totalActiveStake = self.convert_number(self.query('getTotalActiveStake'))
        config = self.contract.query(self.proxy, 'getContractConfig', [])
        self.serviceFee = json.loads(config[1].to_json())['number'] / 100
        self.maxDelegationCap = self.convert_number(json.loads(config[2].to_json())['number'])
        self.delegationCap = int(self.totalActiveStake * 100 / self.maxDelegationCap * 100) / 100
        self.changebleFee = json.loads(config[6].to_json())['number'] == 1953658213

    def query(self, function, args=[]):
        return self.get_value(self.contract.query(self.proxy, function, args))

    def convert_number(self, number):
        return number // 10000000000000000 / 100

    def get_value(self, obj):
        return json.loads(obj[0].to_json())['number']


def agency_info_handle(update: Update, context: CallbackContext):
    TS = Agency()
    query = update.callback_query
    bot = context.bot
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=agency_info.format(emoji.thunder, TS.contract.address, TS.serviceFee,
                                "(changeble)" if TS.changebleFee else "(not changeble)",
                                TS.maxDelegationCap, TS.delegationCap,
                                TS.delegators, TS.totalActiveStake, TS.maxDelegationCap - TS.totalActiveStake),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(emoji.back + " Back", callback_data='back')
            ]
        ])
    )
    return AgencyInfo
