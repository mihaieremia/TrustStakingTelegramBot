import re
info = u'\U00002139'
back = u'\U00002B05'
attention = u'\U0000203C'
mail = u'\U00002709'
pencil = u'\U0000270F'
money = u'\U0001F4B0'
hourglass = u'\U000023F3'
checkmark = u'\U00002705'
fire = u'\U0001F525'
no_entry = u'\U0001F6AB'
no_entry2 = u'\U000026D4'
change = u'\U0001F503'
thunder = u'\U000026A1'
cross_mark = u'\U0000274C'
red_circle = u'\U00002B55'
white_circle = u'\U000026AA'
new_moon = u'\U0001F311'
full_moon = u'\U0001F315'
cat = u'\U0001F431'
credit_card = u'\U0001F4B3'
plus = u'\U00002795'
trash = u'\U0001F5D1'
bookmark = u'\U0001F516'
sparkles = u'\U00002728'
anticlockwise = u'\U0001F504'
pocket_calculator = u'\U0001F5A9'
sad_face = u'\U0001F613'
chain = u'\U000026D3'
pushpin = u'\U0001F4CD'
barber_pole = u'\U0001F488'
black_right_triangle = u'\U000021AA'
usa = u'\U0001F1FA'

emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags=re.UNICODE)