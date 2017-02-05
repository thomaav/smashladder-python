import time
import threading
import builtins
from smashladder_requests import *
# avoid circular import of cookie_jar
cookie_jar = load_cookies_from_file("conf/cookies.dat")


builtins.current_match_id = None
builtins.in_match = False


def matchmaking_loop(cookie_jar):
    while True:
        if builtins.in_match:
            print('Already in match, not going to start matchmaking.')
            time.sleep(5)
        else:
            match_id = begin_matchmaking(cookie_jar, 1, 2, 0, '', 0, '')
            time.sleep(305)


def challenge_loop(cookie_jar):
    while True:
        print(current_match_id, in_match)
        if builtins.in_match:
            print('Already in match, will not challenge people to matches.')
            time.sleep(5)
        else:
            challenge_active_searches_friendlies(cookie_jar)
            time.sleep(5)


from smashladder_qt import *
from smashladder_sockets import *
from smashladder import *


def main():
    # matchmaking_thread = threading.Thread(target=matchmaking_loop, args=(cookie_jar,))
    # matchmaking_thread.daemon = True
    # challenge_thread = threading.Thread(target=challenge_loop, args=(cookie_jar,))
    # challenge_thread.daemon = True
    # main_socket_thread = threading.Thread(target=connect_to_smashladder, args=(cookie_jar,))
    # main_socket_thread.daemon = True

    # matchmaking_thread.start()
    # challenge_thread.start()
    # main_socket_thread.start()

    # while True:
    #     if builtins.in_match:
    #         report_friendly_done(cookie_jar, builtins.current_match_id)
    #         finished_chatting_with_match(cookie_jar, builtins.current_match_id)
    #     time.sleep(3)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
