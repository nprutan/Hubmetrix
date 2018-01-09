import random


def get_happy():
    return random.choice(happy_scale), random.choice(happy_encouragement)


happy_scale = [
    '100 out of 100',
    '100 bazillion out of 100 bazillion',
    'Everything out of All The Things',
    '1 million to the 1 millionth cubed',
    '500 out of 500',
    'All the things out of All the things',
    'No scale, it\'s just all good',
    '1 million doggos and puppers out of 1 million'
]

happy_encouragement = [
    'Sit back and enjoy the sweet sales metrics :) Then go make some awesome workflows!',
    'Lean back, grab some refreshments and savor the feeling of metrics automagically finding their way to HubSpot!',
    'Go out, sit in the sun and watch some metrics roll into your HubSpot while you chillax!',
    'Now, sit back, chill a little and enjoy some sales metrics with your tea and honey courtesy of Hubmetrix!',
    'Go outside, take a deep breathe and get real hyped on these metrics flowing into your HubSpot!',
    'Find a friend, take them aside and tell them how easy it was to get some sweet metrics into your HubSpot!',
    'Lean back, pop a can of chillax and watch these metrics scale your business like a Bawse!',
    'With these metrics flowing into your HubSpot,  you\'ll have to say today it was a good day!'
]

