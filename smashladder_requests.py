import local
import requests
from getpass import getpass


DEFAULT_HEADERS = { 'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
		    'accept-encoding': 'gzip, deflate, sdch',
		    'accept-language': 'nb-NO,nb;q=0.8,no;q=0.6,nn;q=0.4,en-US;q=0.2,en;q=0.2',
		    'cache-control': 'max-age=0',
		    'connection': 'keep-alive',
		    'content-type': 'application/x-www-form-urlencoded',
		    'host': 'www.smashladder.com',
		    'origin': 'https://www.smashladder.com',
		    'referrer': 'https://smashladder.com/log-in',
		    'upgrade-insecure-requests' : '1',
		    'user-agent': 'python',
};


def http_get_request(url, cookie_jar={}, headers=DEFAULT_HEADERS):
    return requests.get(url, cookies=cookie_jar, data=headers)


def http_post_request(url, data, cookie_jar={}, headers=DEFAULT_HEADERS):
    return requests.post(url, data=data, cookies=cookie_jar, headers=headers)


def get_login_credentials():
    username = input('Enter your username: ').strip()
    password = getpass()
    return username, password


def login_to_smashladder(username='', password=''):
    if not (username and password):
        username, password = get_login_credentials()

    login_content =  { 'username': username,
                       'password': password,
                       'remember': '1',
                       'json': '1' }

    response = http_post_request('https://www.smashladder.com/log-in', login_content)

    if (response.json()['success']):
        local.save_cookies_to_file(response.cookies, local.COOKIE_FILE)
        return True

    return False
