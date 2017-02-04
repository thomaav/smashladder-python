from smashladder_requests import *
from smashladder_sockets import *
from smashladder import *

def main():
    cookie_jar = load_cookies_from_file("conf/cookies.dat")
    # own_match_id = begin_matchmaking(cookie_jar, 1, 2, 0, '', 0, '')
    # quit_matchmaking(cookie_jar, own_match_id)
    # retrieve_active_searches(cookie_jar)
    # retrieve_active_whitelisted_searches(cookie_jar)
    # print(retrieve_challenges_awaiting_reply(cookie_jar))
    ## accept_match_challenge
    # print(retrieve_ignored_users(cookie_jar))
    # challenge_active_searches_friendlies(cookie_jar)
    # print(cookie_jar_to_string(cookie_jar))

    connect_to_smashladder(cookie_jar)

if __name__ == '__main__':
    main()
