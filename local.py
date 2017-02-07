import pickle
import os.path


OWN_USERNAME = 'tourniquet'


def save_cookies_to_file(cookie_jar, filename):
    with open(filename, 'wb') as f:
        pickle.dump(cookie_jar, f)


def load_cookies_from_file(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)


def cookie_jar_to_string(cookie_jar):
    cookie = 'timezone=Europe/Berlin; '
    cookie += 'lad_sock_user_id=' + cookie_jar['lad_sock_user_id'] + '; '
    cookie += 'lad_sock_hash=' + cookie_jar['lad_sock_hash'] + '; '
    cookie += 'lad_sock_remember_me=' + cookie_jar['lad_sock_remember_me'] + '; '
    return cookie


COOKIE_FILE = 'conf/cookies.dat'
cookie_jar = load_cookies_from_file(COOKIE_FILE)

WHITELISTED_COUNTRIES_FILE = 'conf/whitelisted_countries'
HIGH_PING_PLAYERS_FILE = 'conf/high_ping_players'

if os.path.isfile(WHITELISTED_COUNTRIES_FILE):
    with open(WHITELISTED_COUNTRIES_FILE, 'rb') as f:
        WHITELISTED_COUNTRIES = pickle.load(f)
else:
    WHITELISTED_COUNTRIES = [ 'Sweden',
                              'Norway',
                              'Denmark',
                              'Netherlands',
                              'Finland',
                              'Sverige' ]

if os.path.isfile(HIGH_PING_PLAYERS_FILE):
    with open(HIGH_PING_PLAYERS_FILE, 'rb') as f:
        HIGH_PING_PLAYERS = pickle.load(f)
else:
    HIGH_PING_PLAYERS = [ 'grandma',
                          'jatuni',
                          'Djentalist',
                          'Nibl33t',
                          'chaosmessenger',
                          'Grodan',
                          'cornflaco',
                          'EarlyPeso',
                          'lelkan',
                          'Vesp',
                          'vliegende1snor',
                          'pwnagewolf',
                          'Tipsi',
                          'BK333',
                          'w4zab1' ]


def whitelist_country(country):
    WHITELISTED_COUNTRIES.append(country)
    with open(WHITELISTED_COUNTRIES_FILE, 'wb') as f:
        pickle.dump(WHITELISTED_COUNTRIES, f)


def add_high_ping_player(player):
    HIGH_PING_PLAYERS.append(player)
    with open(HIGH_PING_PLAYERS_FILE, 'wb') as f:
        pickle.dump(HIGH_PING_PLAYERS, f)


WHITELISTED_GAMES = { 'Melee': '2', }
