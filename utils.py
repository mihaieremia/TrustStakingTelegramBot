MainMenu, AgencyInfo, RedelegationPerion, SubscriptionsMenu, availableSpace = range(5)

from erdpy.contracts import SmartContract
from erdpy.proxy import ElrondProxy
mainnet_proxy = ElrondProxy('https://gateway.elrond.com')
TrustStaking_contract = SmartContract('erd1qqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqzhllllsp9wvyl')


agency_info = '''
<code>Agency: </code><a href="http://truststaking.com/">Trust Staking {}</a>
<code>Contract Address: </code>{}
<code>Service fee: </code>{}% {}
<code>Max delegation cap: </code>{:.0f} eGLD ({:.2f}% filled)
<code>Delegators: </code>{}
<code>Total active stake: </code>{:.2f} eGLD
<code>Available: </code>{:.2f} eGLD
'''
# <code>Nodes: </code>{}
# <code>Top-up per node: </code>{} eGLD
# <code>APR: </code>{}%
from database import Database
telegramDb = Database()