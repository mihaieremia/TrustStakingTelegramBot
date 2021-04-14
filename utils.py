MainMenu, AgencyInfo, RedelegationPerion, SubscriptionsMenu, availableSpace = range(5)

from erdpy.contracts import SmartContract
from erdpy.proxy import ElrondProxy
import emoji
mainnet_proxy = ElrondProxy('https://gateway.elrond.com')
TrustStaking_contract = SmartContract('erd1qqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqzhllllsp9wvyl')

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
<code>Eligible:</code> 
    ''' + emoji.full_moon + '''<code>Online:</code> {} ''' + emoji.new_moon + '''<code>Offline:</code> {}
<code>Waiting:</code>
    ''' + emoji.full_moon + '''<code>Online:</code> {} ''' + emoji.new_moon + '''<code>Offline:</code> {}
<code>New:</code>
    ''' + emoji.full_moon + '''<code>Online:</code> {} ''' + emoji.new_moon + '''<code>Offline:</code> {}
<code>Queued:</code>
    ''' + emoji.full_moon + '''<code>Online:</code> {} ''' + emoji.new_moon + '''<code>Offline:</code> {}
<code>Jailed:</code>
    ''' + emoji.full_moon + '''<code>Online:</code> {} ''' + emoji.new_moon + '''<code>Offline:</code> {}
'''
# <code>Nodes: </code>{}
# <code>Top-up per node: </code>{} eGLD
# <code>APR: </code>{}%
from database import Database
telegramDb = Database()