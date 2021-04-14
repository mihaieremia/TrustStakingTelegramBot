import json

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram import Update
from telegram.ext import CallbackContext

import emoji
from utils import *


class Agency:
    def __init__(self, proxy=mainnet_proxy, contract=TrustStaking_contract, extra_info=False):
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
        self.nodes = {
            'eligible': {'online': 0, 'total': 0},
            'waiting': {'online': 0, 'total': 0},
            'new': {'online': 0, 'total': 0},
            'queued': {'online': 0, 'total': 0},
            'jailed': {'online': 0, 'total': 0},
            'total': {'active': 0, 'staked': 0}
        }
        self.APR = 0
        self.topUp = 0
        if extra_info:
            self.__node_status()
            self.__info()

    def query(self, function, args=[]):
        return self.get_value(self.contract.query(self.proxy, function, args))

    def convert_number(self, number):
        return number // 10000000000000000 / 100

    def get_value(self, obj):
        return json.loads(obj[0].to_json())['number']

    def __node_status(self):
        url = 'https://beta-api.elrond.com/nodes'
        params = {'provider': TrustStaking_contract.address,
                  'from': 0,
                  'size': 100,
                  # 'status': 'jailed'
                  }
        resp = requests.get(url, params)
        data = resp.json()
        for node in data:
            self.nodes[node['status']]['total'] += 1
            if node['online']:
                self.nodes[node['status']]['online'] += 1
        self.nodes['total']['staked'] = self.nodes['queued']['total'] + self.nodes['jailed']['total']
        self.nodes['total']['active'] = self.nodes['eligible']['total'] + self.nodes['waiting']['total'] + \
                                        self.nodes['new']['total']

    def __info(self):
        url = 'https://api.elrond.com/providers'
        params = {'identity': 'truststaking'}
        resp = requests.get(url, params)
        data = resp.json()
        self.APR = data[0]['apr']
        self.topUp = (self.convert_number(int(data[0]['topUp'])) + 2500 * self.nodes['total']['staked']) / \
                     self.nodes['total']['active']
        print(self.APR, self.topUp)


GTS = Agency(extra_info=True)


def update_agency_info(job):
    global GTS
    GTS = Agency(extra_info=True)


def agency_info_handle(update: Update, context: CallbackContext):
    TS = GTS
    query = update.callback_query
    bot = context.bot
    available = TS.maxDelegationCap - TS.totalActiveStake
    available_string = emoji.checkmark if available > 0 else emoji.no_entry
    available_string += ' {:.2f}'.format(available)
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=agency_info.format(TS.contract.address, TS.serviceFee,
                                "(changeble)" if TS.changebleFee else "(not changeble)",
                                TS.maxDelegationCap, TS.delegationCap,
                                TS.nodes['total']['active'], TS.nodes['total']['staked'],
                                TS.nodes['eligible']['total'],
                                TS.delegators, TS.totalActiveStake, available_string,
                                TS.topUp, TS.APR),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("More info", callback_data='more_info'),
                InlineKeyboardButton(emoji.back + " Back", callback_data='back')
            ]
        ])
    )
    return AgencyInfo


def agency_info_handle_extra(update: Update, context: CallbackContext):
    TS = GTS
    query = update.callback_query
    bot = context.bot
    available = TS.maxDelegationCap - TS.totalActiveStake
    available_string = emoji.checkmark if available > 0 else emoji.no_entry
    available_string += ' {:.2f}'.format(available)
    text = (agency_info + extra).format(TS.contract.address, TS.serviceFee,
                                        "(changeble)" if TS.changebleFee else "(not changeble)",
                                        TS.maxDelegationCap, TS.delegationCap,
                                        TS.nodes['total']['active'], TS.nodes['total']['staked'],
                                        TS.nodes['eligible']['total'],
                                        TS.delegators, TS.totalActiveStake, available_string,
                                        TS.topUp, TS.APR,
                                        TS.nodes['eligible']['online'],
                                        TS.nodes['eligible']['total'] - TS.nodes['eligible']['online'],
                                        TS.nodes['waiting']['online'],
                                        TS.nodes['waiting']['total'] - TS.nodes['waiting']['online'],
                                        TS.nodes['new']['online'], TS.nodes['new']['total'] - TS.nodes['new']['online'],
                                        TS.nodes['queued']['online'],
                                        TS.nodes['queued']['total'] - TS.nodes['queued']['online'],
                                        TS.nodes['jailed']['online'],
                                        TS.nodes['jailed']['total'] - TS.nodes['jailed']['online'],
                                        )
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Less info", callback_data='less_info'),
                InlineKeyboardButton(emoji.back + " Back", callback_data='back')
            ]
        ])
    )
    return AgencyInfo
