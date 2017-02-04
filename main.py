from smashladder_requests import *
from smashladder_sockets import *
from smashladder import *

cookie_jar = load_cookies_from_file("conf/cookies.dat")

def main():
    own_match_id = begin_matchmaking(cookie_jar, 1, 2, 0, '', 0, '')
    connect_to_smashladder(cookie_jar)

if __name__ == '__main__':
    main()
