import binascii
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
            if self.__node_status():
                print("\tNodes status read.")
                if self.__info():
                    print("\tApr+topup status read.")


    def query(self, function, args=[]):
        return self.get_value(self.contract.query(self.proxy, function, args))

    def convert_number(self, number, decimals=2):

        return number // 10 ** (18 - decimals) / 10 ** decimals

    def get_value(self, obj):
        if obj == [] or obj[0] == "":
            return 0
        return json.loads(obj[0].to_json())['number']

    def __node_status(self):
        print("__node_status called")
        url = 'https://api.elrond.com/nodes'
        params = {'provider': TrustStaking_contract.address,
                  'from': 0,
                  'size': 100,
                  }
        try:
            resp = requests.get(url, params)
            data = resp.json()
            print(f'\t__node_status reply: {data}')
            for node in data:
                self.nodes[node['status']]['total'] += 1
                if isinstance(node, dict) and 'online' in node.keys() and node['online']:
                    self.nodes[node['status']]['online'] += 1
            self.nodes['total']['staked'] = self.nodes['queued']['total'] + self.nodes['jailed']['total']
            self.nodes['total']['active'] = self.nodes['eligible']['total'] + self.nodes['waiting']['total'] + \
                                            self.nodes['new']['total']
            return True
        except KeyError as e:
            print("\tKeyError: %s" % str(e))
            return False
        except TypeError as e:
            print("\tTypeError: %s" % str(e))
            return False
        except Exception as e:
            print("\tError: %s" % str(e))
            return False


    def __info(self):
        print("__info called")
        url = 'https://api.elrond.com/providers'
        params = {'identity': 'truststaking'}
        try:
            resp = requests.get(url, params)
            data = resp.json()
            print(f'\t__info reply: {data}')
            self.APR = data[0]['apr']
            self.topUp = (self.convert_number(int(data[0]['topUp'])) + 2500 * self.nodes['total']['staked']) / \
                         self.nodes['total']['active']
            return True
        except KeyError as e:
            print("\tKeyError: %s" % str(e))
            return False
        except TypeError as e:
            print("\tTypeError: %s" % str(e))
            return False
        except Exception as e:
            print("\tError: %s" % str(e))
            return False

    def get_address_info(self, address):
        print("get_address_info called")
        addr = f"0x{Address(address).hex()}"
        claimable = self.convert_number(
            self.get_value(self.contract.query(self.proxy, 'getClaimableRewards', [addr])), 6)
        totalRewards = self.convert_number(
            self.get_value(self.contract.query(self.proxy, 'getTotalCumulatedRewardsForUser', [addr])), 6)
        active = self.convert_number(
            self.get_value(self.contract.query(self.proxy, 'getUserActiveStake', [addr])), 6)
        undelegated_list = self.contract.query(self.proxy, 'getUserUnDelegatedList', [addr])
        available = self.get_active_balance(address)
        return available, active, claimable, totalRewards

    def get_active_balance(self, addr):
        print("get_active_balance called")
        url = 'https://api.elrond.com/accounts/' + addr
        try:
            resp = requests.get(url)
            data = resp.json()
            print(f'\tget_active_balance reply: {data}')
            return self.convert_number(float(data['balance']), 6)
        except KeyError as e:
            print("\tKeyError: %s" % str(e))
            return '-'
        except TypeError as e:
            print("\tTypeError: %s" % str(e))
            return '-'
        except Exception as e:
            print("\tError: %s" % str(e))
            return '-'


GTS = Agency(extra_info=True)


def update_agency_info(job):
    print('update_agency_info caled')
    global GTS
    GTS = Agency(extra_info=True)


def agency_info_handle(update: Update, context: CallbackContext):
    global GTS
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
    global GTS
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
                                        TS.nodes['new']['online'], TS.nodes['new']['total'] - TS.nodes['new']['online'],
                                        TS.nodes['waiting']['online'],
                                        TS.nodes['waiting']['total'] - TS.nodes['waiting']['online'],
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
