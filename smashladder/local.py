import pickle
import os.path


COOKIE_FILE = 'conf/cookies.dat'
WHITELISTED_COUNTRIES_FILE = 'conf/whitelisted_countries'
BLACKLISTED_PLAYERS_FILE = 'conf/blacklisted_players'
PREFERRED_PLAYERS_FILE = 'conf/preferred_players'


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


if os.path.isfile(WHITELISTED_COUNTRIES_FILE):
    with open(WHITELISTED_COUNTRIES_FILE, 'rb') as f:
        WHITELISTED_COUNTRIES = pickle.load(f)
else:
    WHITELISTED_COUNTRIES = []

if os.path.isfile(BLACKLISTED_PLAYERS_FILE):
    with open(BLACKLISTED_PLAYERS_FILE, 'rb') as f:
        BLACKLISTED_PLAYERS = pickle.load(f)
else:
    BLACKLISTED_PLAYERS = []

if os.path.isfile(PREFERRED_PLAYERS_FILE):
    with open(PREFERRED_PLAYERS_FILE, 'rb') as f:
        PREFERRED_PLAYERS = pickle.load(f)
else:
    PREFERRED_PLAYERS = []

TMP_BLACKLISTED_PLAYERS = []


def dump_whitelisted_countries():
    with open(WHITELISTED_COUNTRIES_FILE, 'wb') as f:
        pickle.dump(WHITELISTED_COUNTRIES, f)


def dump_blacklisted_players():
    with open(BLACKLISTED_PLAYERS_FILE, 'wb') as f:
        pickle.dump(BLACKLISTED_PLAYERS, f)


def dump_preferred_players():
    with open(PREFERRED_PLAYERS_FILE, 'wb') as f:
        pickle.dump(PREFERRED_PLAYERS, f)


def whitelist_country(country):
    WHITELISTED_COUNTRIES.append(country)
    dump_whitelisted_countries()


def blacklist_player(player):
    BLACKLISTED_PLAYERS.append(player)
    dump_blacklisted_players()


def prefer_player(player):
    PREFERRED_PLAYERS.append(player)
    dump_preferred_players()


def tmp_blacklist_player(player):
    if player not in BLACKLISTED_PLAYERS or \
       player in TMP_BLACKLISTED_PLAYERS:
        return

    TMP_BLACKLISTED_PLAYERS.append(player)


def remove_whitelisted_country(country):
    if country not in WHITELISTED_COUNTRIES:
        return

    WHITELISTED_COUNTRIES.remove(country)
    dump_whitelisted_countries()


def remove_blacklisted_player(player):
    if player not in BLACKLISTED_PLAYERS:
        return

    BLACKLISTED_PLAYERS.remove(player)
    dump_blacklisted_players()


def remove_preferred_player(player):
    if player not in PREFERRED_PLAYERS:
        return

    PREFERRED_PLAYERS.remove(player)
    dump_preferred_players()


def remove_tmp_blacklisted_player(player):
    if player not in TMP_BLACKLISTED_PLAYERS:
        return

    TMP_BLACKLISTED_PLAYERS.remove(player)


def remove_tmp_blacklisted():
    for player in TMP_BLACKLISTED_PLAYERS:
        if player in BLACKLISTED_PLAYERS:
            BLACKLISTED_PLAYERS.remove(player)

    dump_blacklisted_players()


WHITELISTED_GAMES = { 'Melee': '2', }
