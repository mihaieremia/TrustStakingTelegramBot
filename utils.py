import json

MainMenu, AgencyInfo, ChangeAgency, Wallets, WalletConfiguration, WalletStatus, \
RedelegationPerion, SubscriptionsMenu, availableSpace, MEXCalc = range(10)

import requests
from erdpy.contracts import SmartContract
from erdpy.accounts import Address
from erdpy.proxy import ElrondProxy
import emoji

mainnet_proxy = ElrondProxy('https://gateway.elrond.com')
TrustStaking_contract = SmartContract('erd1qqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqzhllllsp9wvyl')
default_agency = 'trust staking (10% fees until phase 4)'
db_token = 'mongodb+srv://dragos:Ao3myNA5TAA9AJvzwHxPNq2ZP7pza8T@cluster0.hdusz.mongodb.net/telegramBot?retryWrites=true&w=majority'
bot_token = '1654360962:AAFNJTAZxdplj1nrgsv9LnfmCntOMR-DdGg'

main_menu_message = emoji.cat + '''Main menu\n'''

agency_info = '''
<code>Agency: </code><a href="{}">{}</a>
<code>Contract Address: </code>{}
<code>Service fee: </code>{}% {}
<code>Max delegation cap: </code>{}
<code>Nodes: </code>{} <code>active</code> +{} <code>staked</code>
<code>Eligible today: </code>{}
<code>Delegators: </code>{}
<code>Total active stake: </code>{:.2f} eGLD
<code>Available: </code>{}
<code>Top-up per node: </code>{:.2f} eGLD
<code>APR: </code>{}
'''

extra = '''
<code>Eligible:</code>{} ''' + emoji.full_moon + ''' {} ''' + emoji.new_moon + '''
<code>Waiting: </code>{} ''' + emoji.full_moon + ''' {} ''' + emoji.new_moon + '''
<code>Queued:   </code>{} ''' + emoji.full_moon + ''' {} ''' + emoji.new_moon + '''
<code>New:      </code>{} ''' + emoji.full_moon + ''' {} ''' + emoji.new_moon + '''
<code>Jailed:   </code>{} ''' + emoji.full_moon + ''' {} ''' + emoji.new_moon + '''
'''

wallet_information = '''
<code>Wallet:</code> <a href="https://explorer.elrond.com/accounts/{}">{}</a> - <code>{}...{}</code>

<code>Available:</code> {} <code>eGLD</code> (${:.2f})

'''
wallet_for_agency_info = '''
<code>Agency: </code>{}
<code>Active delegation:</code> {} <code>eGLD</code> (${:.2f})
<code>Claimable:</code> {} <code>eGLD</code> (${:.2f})
<code>Total rewards:</code> {} <code>eGLD</code> (${:.2f})

'''

mex_calculator_info = '''
<code>You will receive </code>{:.6} MEX<code> in total </code>per week<code>.
-</code>{:.6} MEX<code> for </code>{:.6} eGLD<code> staked
-</code>{:.6} MEX<code> for </code>{:.6} eGLD<code> available(stored in Web Wallet, Maiar, Ledger)

*For the available amounts, if you have more that 5 referrals, you shall multiple with 1.25 for the exact amount.</code>
**Those values represents only an aproximation, the actual rewards may be different.
'''
delegate = "wallet.elrond.com/hook/transaction?receiver={}&value={}&gasLimit=12000000&data=delegate"  # b.walletHook, utils.ContractAddress, iAmount)
undelegate = "wallet.elrond.com/hook/transaction?receiver={}&value=0&gasLimit=12000000&data=unDelegate@{}"
withdraw = "wallet.elrond.com/hook/transaction?receiver={}&value=0&gasLimit=12000000&data=withdraw"  # b.walletHook, utils.ContractAddress)
claimURL = "https://wallet.elrond.com/hook/transaction?receiver={}&value=0&gasLimit=6000000&data=claimRewards"
restake = "wallet.elrond.com/hook/transaction?receiver={}&value=0&gasLimit=12000000&data=reDelegateRewards"

best_period = '''
<code>Best APY for redelegation at</code> {:d} days. 
<code>Total reward after one year:</code> {:.6f}

<code>*The current APR(</code>{}%<code>) from your default agency(</code>{}<code>) is taken into consideration.
Change your default agency if you want to calculate the optimal redelegation period for another agency.</code>
'''
# <code>Nodes: </code>{}
# <code>Top-up per node: </code>{} eGLD
# <code>APR: </code>{}%

choose_agency = '''
Type @TrustStakingBot *agency_name* to set a new agency by default\n
ex: \n
    @TrustStakingBot tr -> a list including all agencies that include "tr" in their name will appear.\n
    Select the one that you want from the list.
'''


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


def convert_number(number, decimals=2):
    return number // 10 ** (18 - decimals) / 10 ** decimals


def get_value(obj):
    if obj == [] or obj[0] == "":
        return 0
    return json.loads(obj[0].to_json())['number']


def get_active_balance(addr):
    print("get_active_balance called")
    url = 'https://api.elrond.com/accounts/' + addr
    try:
        resp = requests.get(url)
        data = resp.json()
        print(f'\tget_active_balance reply: {data}')
        return convert_number(float(data['balance']), 6)
    except KeyError as e:
        print("\tKeyError: %s" % str(e))
        return '-'
    except TypeError as e:
        print("\tTypeError: %s" % str(e))
        return '-'
    except Exception as e:
        print("\tError: %s" % str(e))
        return '-'


price = None


def update_price(job):
    global price
    price = get_current_price()
