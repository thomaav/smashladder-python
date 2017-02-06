import pickle


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

OWN_USERNAME = 'tourniquet'

WHITELISTED_COUNTRIES = ( 'Sweden',
                          'Norway',
                          'Denmark',
                          'Netherlands',
                          'Finland',
                          'Sverige' )

HIGH_PING_PLAYERS = ( 'grandma',
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
                      'w4zab1' )

WHITELISTED_GAMES = { 'Melee': '2', }
