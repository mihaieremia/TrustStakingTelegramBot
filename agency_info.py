import json
import threading
import time
from datetime import datetime, timedelta
from threading import Thread
from uuid import uuid4

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, InlineQueryResultArticle, \
    InputTextMessageContent
from telegram import Update
from telegram.ext import CallbackContext
from database import telegramDb
from utils import *


class Agency:
    def __init__(self, proxy=mainnet_proxy, contract=TrustStaking_contract, extra_info=False):
        self.proxy = proxy
        self.contract = contract
        self.numNode = self.query('getNumNodes')
        self.delegators = self.query('getNumUsers')
        self.totalActiveStake = convert_number(self.query('getTotalActiveStake'))
        config = self.contract.query(self.proxy, 'getContractConfig', [])
        self.serviceFee, self.changebleFee = self.get_agency_fee(config)
        self.maxDelegationCap, self.delegationCap = self.get_agency_cap(config)
        self.name, self.website, self.identity = self.get_agency_name()
        if self.name == '':
            self.name = self.contract.address.bech32()

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
        self.totalUnstaked = 0
        if extra_info:
            self.get_extra_info()

    def get_extra_info(self):
        self.totalUnstaked = convert_number(self.query('getTotalUnStaked'))
        if self.__node_status():
            print("\tNodes status read.")
            if self.__info():
                print("\tApr+topup status read.")

    def query(self, function, args=None):
        if args is None:
            args = []
        return get_value(self.contract.query(self.proxy, function, args))


    def get_agency_name(self):
        metaData = self.contract.query(self.proxy, 'getMetaData', [])
        if metaData == []:
            return "", "", ""
        name_in_hex = json.loads(metaData[0].to_json())['hex']
        name = bytes.fromhex(name_in_hex).decode('utf-8')
        if 'Pro Crypto' in name:
            name = 'ProCrypto 🌍 Distributed Staking'
        website_in_hex = json.loads(metaData[1].to_json())['hex']
        website = bytes.fromhex(website_in_hex).decode('utf-8')
        identity_in_hex = json.loads(metaData[2].to_json())['hex']
        identity = bytes.fromhex(identity_in_hex).decode('utf-8')
        return name, website, identity

    def get_agency_fee(self, config):
        if config[1] == None:
            fee = 0
        else:
            fee = json.loads(config[1].to_json())['number'] / 100
        if config[6] == []:
            changeble = False
        else:
            changeble = json.loads(config[6].to_json())['number'] == 1953658213
        return fee, changeble

    def get_agency_cap(self, config):
        if isinstance(config[2], str):
            maxDelegationCap = "unlimited"
            delegationCap = 0
        else:
            maxDelegationCap = convert_number(json.loads(config[2].to_json())['number'])
            delegationCap = int(self.totalActiveStake * 100 / maxDelegationCap * 100) / 100
        return maxDelegationCap, delegationCap

    def __node_status(self):
        nodes = {
            'eligible': {'online': 0, 'total': 0},
            'waiting': {'online': 0, 'total': 0},
            'new': {'online': 0, 'total': 0},
            'queued': {'online': 0, 'total': 0},
            'jailed': {'online': 0, 'total': 0},
            'total': {'active': 0, 'staked': 0}
        }
        print("__node_status called")
        url = 'https://api.elrond.com/nodes'
        params = {'provider': self.contract.address,
                  'from': 0,
                  'size': 100,
                  }
        try:
            resp = requests.get(url, params)
            data = resp.json()
            #print(f'\t__node_status reply: {data}')
            for node in data:
                nodes[node['status']]['total'] += 1
                if isinstance(node, dict) and 'online' in node.keys() and node['online']:
                    nodes[node['status']]['online'] += 1
            nodes['total']['staked'] = nodes['queued']['total'] + nodes['jailed']['total']
            nodes['total']['active'] = nodes['eligible']['total'] + nodes['waiting']['total'] + nodes['new']['total']
            self.nodes = nodes
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
        print("\tidentity = ", self.identity)
        params = {'identity': self.identity}
        try:
            resp = requests.get(url, params)
            data = resp.json()
            print(f'\t__info reply: {data}')
            self.APR = data[0]['apr']
            self.topUp = (convert_number(int(data[0]['topUp'])) + 2500 * self.nodes['total']['staked']) / \
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
        claimable = convert_number(get_value(self.contract.query(self.proxy, 'getClaimableRewards', [addr])), 6)
        totalRewards = convert_number(
            get_value(self.contract.query(self.proxy, 'getTotalCumulatedRewardsForUser', [addr])), 6)
        active = convert_number(get_value(self.contract.query(self.proxy, 'getUserActiveStake', [addr])), 6)
        undelegated_list = self.contract.query(self.proxy, 'getUserUnDelegatedList', [addr])

        return active, claimable, totalRewards

def get_all_contracts():
    global AllAgencies
    global Agencies_results
    global AgenciesLastUpdate
    print("get_all_contracts called")
    reply = SmartContract('erd1qqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqylllslmq6y6').query(mainnet_proxy,
                                                                                                  'getAllContractAddresses',
                                                                                                  [])
    for address in reply:
        hex_address = json.loads(address.to_json())['hex']
        contract = Address(hex_address).bech32()
        agency = Agency(contract=SmartContract(contract))
        if agency.name != '':
            if agency.name.lower() not in AllAgencies.keys():
                Agencies_results.append(InlineQueryResultArticle(id=str(uuid4()),
                                                                 title=agency.name,
                                                                 input_message_content=InputTextMessageContent(
                                                                     agency.name.lower())))
            AllAgencies[agency.name.lower()] = agency
            #print("\t", len(Agencies_results), AllAgencies.keys())
    print("get_all_contracts finished")


AllAgencies = {}
AgenciesLastUpdate = {}
Agencies_results = []
no_agency_to_be_updated = 0

def update_agency(agency_to_be_updated, extra_info=False):
    global no_agency_to_be_updated
    global AllAgencies
    global AgenciesLastUpdate
    reply = SmartContract('erd1qqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqylllslmq6y6').query(mainnet_proxy,
                                                                                                  'getAllContractAddresses',
                                                                                                [])
    if agency_to_be_updated is None:
        address = reply[no_agency_to_be_updated]
        if no_agency_to_be_updated + 1 < len(reply):
            no_agency_to_be_updated += 1
        else:
            no_agency_to_be_updated = 0
    else:
        address = reply[agency_to_be_updated]

    hex_address = json.loads(address.to_json())['hex']
    contract = Address(hex_address).bech32()
    agency = Agency(contract=SmartContract(contract), extra_info=extra_info)
    if agency.name != '':
        if agency.name.lower() not in AllAgencies.keys():
            Agencies_results.append(InlineQueryResultArticle(id=str(uuid4()),
                                                             title=agency.name,
                                                             input_message_content=InputTextMessageContent(
                                                                 agency.name.lower())))
        AllAgencies[agency.name.lower()] = agency
    print(agency.name, "updated!")

def get_user_staking_agencies(addr):
    print('get_user_staking_agencies called')
    global AllAgencies
    url = f'https://internal-delegation-api.elrond.com/accounts/{addr}/delegations'
    try:
        resp = requests.get(url)
        data = resp.json()
        print(f'\tget_user_staking_agencies reply: {data}')
        contracts = [agency['contract'] for agency in data]
        agencies = [agency for contract in contracts for agency in AllAgencies.keys()
                    if AllAgencies[agency].contract.address.bech32() == contract]
        return agencies
    except Exception as e:
        print("\tError: %s" % str(e))
        return []

def update_agencies_info(job):
    background_thread = Thread(target=update_agency, args=(None,))
    background_thread.start()


def update_user_agency(user_id):
    global AllAgencies
    global AgenciesLastUpdate
    print("update_user_agency called")
    user_agency = telegramDb.get_user_agency(user_id)
    if user_agency['name'] not in AllAgencies:
        telegramDb.set_user_agency(user_id, default_agency)
        user_agency = telegramDb.get_user_agency(user_id)
    now = datetime.now()
    if user_agency['name'] not in AgenciesLastUpdate \
        or now - AgenciesLastUpdate[user_agency['name']] > timedelta(seconds=30):
        print("\t updating current agency = ", user_agency['name'])
        AllAgencies[user_agency['name']].get_extra_info()
        AgenciesLastUpdate[user_agency['name']] = now


def agency_info_handle(update: Update, context: CallbackContext):
    global AllAgencies
    query = update.callback_query
    bot = context.bot
    user_id = query.from_user.id
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

    if isinstance(TS.maxDelegationCap, str):
        available_string = emoji.checkmark
        available_string += " unlimited"
        max_delegation_cap_str = TS.maxDelegationCap
    else:
        available = TS.maxDelegationCap - TS.totalActiveStake
        available_string = emoji.checkmark if available > 0 else emoji.no_entry
        available_string += ' {:.2f} eGLD'.format(available)
        max_delegation_cap_str = '{:.0f} eGLD ({:.2f}% filled)'.format(TS.maxDelegationCap, TS.delegationCap)
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=agency_info.format(TS.website, TS.name, TS.contract.address, TS.serviceFee,
                                "(changeble)" if TS.changebleFee else "(not changeble)",
                                max_delegation_cap_str,
                                TS.nodes['total']['active'], TS.nodes['total']['staked'],
                                TS.nodes['eligible']['total'],
                                TS.delegators, TS.totalActiveStake, available_string,
                                TS.topUp, TS.APR, TS.totalUnstaked),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Change default agency", callback_data='change_agency'),
            ],
            [
                InlineKeyboardButton("More info", callback_data='more_info'),
                InlineKeyboardButton(emoji.back + " Back", callback_data='back')
            ]
        ])
    )
    return AgencyInfo


def agency_info_handle_extra(update: Update, context: CallbackContext):
    global AllAgencies
    query = update.callback_query
    bot = context.bot
    user_id = query.from_user.id
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

    if isinstance(TS.maxDelegationCap, str):
        available_string = emoji.checkmark
        available_string += " unlimited"
        max_delegation_cap_str = TS.maxDelegationCap
    else:
        available = TS.maxDelegationCap - TS.totalActiveStake
        available_string = emoji.checkmark if available > 0 else emoji.no_entry
        available_string += ' {:.2f} eGLD'.format(available)
        max_delegation_cap_str = '{:.0f} eGLD ({:.2f}% filled)'.format(TS.maxDelegationCap, TS.delegationCap)

    text = (agency_info + extra).format(TS.website, TS.name, TS.contract.address, TS.serviceFee,
                                        "(changeble)" if TS.changebleFee else "(not changeble)",
                                        max_delegation_cap_str,
                                        TS.nodes['total']['active'], TS.nodes['total']['staked'],
                                        TS.nodes['eligible']['total'],
                                        TS.delegators, TS.totalActiveStake, available_string,
                                        TS.topUp, TS.APR, TS.totalUnstaked,
                                        TS.nodes['eligible']['online'],
                                        TS.nodes['eligible']['total'] - TS.nodes['eligible']['online'],
                                        TS.nodes['waiting']['online'],
                                        TS.nodes['waiting']['total'] - TS.nodes['waiting']['online'],
                                        TS.nodes['queued']['online'],
                                        TS.nodes['queued']['total'] - TS.nodes['queued']['online'],
                                        TS.nodes['new']['online'], TS.nodes['new']['total'] - TS.nodes['new']['online'],
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
                InlineKeyboardButton("Change default agency", callback_data='change_agency'),
            ],
            [
                InlineKeyboardButton("Less info", callback_data='less_info'),
                InlineKeyboardButton(emoji.back + " Back", callback_data='back')
            ]
        ])
    )
    return AgencyInfo


def agencies_search(update: Update, _: CallbackContext):
    print("agencies_search called")

    query = update.inline_query.query.lower()
    print("\tquery = ", query)
    global Agencies_results

    if query == "":
        return

    results = [result for result in Agencies_results if query in result.title.lower()]
    print("\tresults = ", results)

    update.inline_query.answer(results)
    return AgencyInfo


def show_agency(update: Update, context: CallbackContext):
    print("show_agency called")
    if update.message is None:
        return
    agency = update.message.text
    if agency not in AllAgencies.keys():
        return
    print("agency = ", agency)
    TS = Agency(contract=AllAgencies[agency].contract, extra_info=True)

    if isinstance(TS.maxDelegationCap, str):
        available_string = emoji.checkmark
        available_string += " unlimited"
        max_delegation_cap_str = TS.maxDelegationCap
    else:
        available = TS.maxDelegationCap - TS.totalActiveStake
        available_string = emoji.checkmark if available > 0 else emoji.no_entry
        available_string += ' {:.2f} eGLD'.format(available)
        max_delegation_cap_str = '{:.0f} eGLD ({:.2f}% filled)'.format(TS.maxDelegationCap, TS.delegationCap)


    text = agency_info.format(TS.website, TS.name, TS.contract.address, TS.serviceFee,
                              "(changeble)" if TS.changebleFee else "(not changeble)",
                              max_delegation_cap_str,
                              TS.nodes['total']['active'], TS.nodes['total']['staked'],
                              TS.nodes['eligible']['total'],
                              TS.delegators, TS.totalActiveStake, available_string,
                              TS.topUp, TS.APR, TS.totalUnstaked)
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
    try:
        context.bot.deleteMessage(update.message.chat_id, update.message.message_id)
    except:
        print("\t delete message failed")


def change_agency(update: Update, context: CallbackContext):
    print("change_agency called")
    try:
        agency = update.message.text
        if agency in AllAgencies.keys():
            user_id = update.effective_chat['id']

            telegramDb.set_user_agency(user_id, agency)
            update_user_agency(user_id)
            TS = AllAgencies[agency]

            if isinstance(TS.maxDelegationCap, str):
                available_string = emoji.checkmark
                available_string += " unlimited"
                max_delegation_cap_str = TS.maxDelegationCap
            else:
                available = TS.maxDelegationCap - TS.totalActiveStake
                available_string = emoji.checkmark if available > 0 else emoji.no_entry
                available_string += ' {:.2f} eGLD'.format(available)
                max_delegation_cap_str = '{:.0f} eGLD ({:.2f}% filled)'.format(TS.maxDelegationCap, TS.delegationCap)

            text = agency_info.format(TS.website, TS.name, TS.contract.address, TS.serviceFee,
                                      "(changeble)" if TS.changebleFee else "(not changeble)",
                                      max_delegation_cap_str,
                                      TS.nodes['total']['active'], TS.nodes['total']['staked'],
                                      TS.nodes['eligible']['total'],
                                      TS.delegators, TS.totalActiveStake, available_string,
                                      TS.topUp, TS.APR, TS.totalUnstaked)
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Change default agency", callback_data='change_agency'),
                    ],
                    [
                        InlineKeyboardButton("More info", callback_data='more_info'),
                        InlineKeyboardButton(emoji.back + " Back", callback_data='back')
                    ]
                ])
            )
            return AgencyInfo
    except:
        bot = context.bot
        query = update.callback_query

        bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text=choose_agency,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(emoji.back + " Back", callback_data='back')
                ]
            ])
        )
    return ChangeAgency
