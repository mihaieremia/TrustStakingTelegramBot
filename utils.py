MainMenu, AgencyInfo, Wallets, WalletConfiguration, WalletStatus, \
RedelegationPerion, SubscriptionsMenu, availableSpace, = range(8)

import requests
from erdpy.contracts import SmartContract
from erdpy.accounts import Address
from erdpy.proxy import ElrondProxy
import emoji

mainnet_proxy = ElrondProxy('https://gateway.elrond.com')
TrustStaking_contract = SmartContract('erd1qqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqzhllllsp9wvyl')
db_token = 'mongodb+srv://dragos:Ao3myNA5TAA9AJvzwHxPNq2ZP7pza8T@cluster0.hdusz.mongodb.net/telegramBot?retryWrites=true&w=majority'
bot_token = '1654360962:AAFNJTAZxdplj1nrgsv9LnfmCntOMR-DdGg'

agency_info = '''
<code>Agency: </code><a href="http://truststaking.com/">Trust Staking''' + emoji.thunder + '''</a>
<code>Contract Address: </code>{}
<code>Service fee: </code>{}% {}
<code>Max delegation cap: </code>{:.0f} eGLD ({:.2f}% filled)
<code>Nodes: </code>{} <code>active</code> +{} <code>staked</code>
<code>Eligible today: </code>{}
<code>Delegators: </code>{}
<code>Total active stake: </code>{:.2f} eGLD
<code>Available: </code>{} eGLD
<code>Top-up per node: </code>{:.2f} eGLD
<code>APR: </code>{}
'''

extra = '''
<code>Eligible:</code> {} ''' + emoji.full_moon + ''' {} ''' + emoji.new_moon + '''
<code>Waiting:</code>     {} ''' + emoji.full_moon + ''' {} ''' + emoji.new_moon + '''
<code>Queued:</code>     {} ''' + emoji.full_moon + ''' {} ''' + emoji.new_moon + '''
<code>New:</code>             {} ''' + emoji.full_moon + ''' {} ''' + emoji.new_moon + '''
<code>Jailed:</code>       {} ''' + emoji.full_moon + ''' {} ''' + emoji.new_moon + '''
'''

wallet_information = '''
<code>Wallet:</code> <a href="https://explorer.elrond.com/accounts/{}">{}</a> - <code>{}...{}</code>

<code>Available:</code> {} <code>eGLD</code> (${:.2f})
<code>Active delegation:</code> {} <code>eGLD</code> (${:.2f})
<code>Claimable:</code> {} <code>eGLD</code> (${:.2f})
<code>Total rewards:</code> {} <code>eGLD</code> (${:.2f})
'''
delegate = "wallet.elrond.com/hook/transaction?receiver={}&value={}&gasLimit=12000000&data=delegate&callbackUrl=none"  # b.walletHook, utils.ContractAddress, iAmount)
undelegate = "wallet.elrond.com/hook/transaction?receiver={}&value=0&gasLimit=12000000&data=unDelegate@{}&callbackUrl=none"
withdraw = "wallet.elrond.com/hook/transaction?receiver={}&value=0&gasLimit=12000000&data=withdraw&callbackUrl=none"  # b.walletHook, utils.ContractAddress)
claimURL = "https://wallet.elrond.com/hook/transaction?receiver={}&value=0&gasLimit=6000000&data=claimRewards&callbackUrl=none"
restake = "wallet.elrond.com/hook/transaction?receiver={}&value=0&gasLimit=12000000&data=reDelegateRewards&callbackUrl=none"

# <code>Nodes: </code>{}
# <code>Top-up per node: </code>{} eGLD
# <code>APR: </code>{}%
from database import Database

telegramDb = Database()


def get_current_price():
    print("get_current_price called")
    url = 'https://data.elrond.com/market/quotes/egld/price'
    try:
        resp = requests.get(url)
        data = resp.json()
        print(f'\tget_current_price reply: {data}')
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


price = get_current_price()


def update_price(job):
    global price
    price = get_current_price()