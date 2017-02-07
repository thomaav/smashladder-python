import builtins
import json
import main
import smashladder_qt
import re
import time
from local import *
from smashladder_requests import *


builtins.current_match_id = None
builtins.in_match = False


def begin_matchmaking(cookie_jar, team_size, game_id, match_count,
                      title, ranked, host_code):
    """
    cookie_jar is required, as you need to be logged in
    team_size is 1, not doubles
    game_id is game, 2 for melee
    match_count is 0, probably for ranked
    title i dont fucking know, use ''
    ranked, 0 or 1 accordingly
    host_code is can be added if wanted, '' if none """

    match_content = { 'team_size': team_size,
                      'game_id': game_id,
                      'match_count': match_count,
                      'title': title,
                      'ranked': ranked,
                      'host_code': host_code, }

    response = http_post_request('https://www.smashladder.com/matchmaking/begin_matchmaking',
                                    match_content,
                                    cookie_jar)
    response_body = json.loads(response.text)

    # go through returned current searches, the first is your own
    for match_id in response_body['searches']:
        if (re.match('[0-9]{7,9}', match_id)):
            own_match_id = match_id

    if (own_match_id):
        smashladder_qt.qt_print("Success! Matchmaking began in begin_matchmaking.")
        return own_match_id
    else:
        return("Failure! Matchmaking aborted in begin_matchmaking.")


def quit_matchmaking(cookie_jar, match_id):
    content = { 'match_id': match_id }

    response = http_post_request('https://www.smashladder.com/matchmaking/end_matchmaking',
                                 content, cookie_jar)
    response_body = json.loads(response.text)

    if 'success' in response_body:
        smashladder_qt.qt_print('Success! Quit matchmaking with id: ' + match_id)
    else:
        smashladder_qt.qt_print('Failure! Could not quit match with id: ' + match_id)


def retrieve_active_searches(cookie_jar):
    response = http_get_request('https://www.smashladder.com/matchmaking/retrieve_match_searches',
                                cookie_jar)
    response_body = json.loads(response.text)

    active_searches = dict()
    for match_id in response_body['searches']:
        if (re.match('[0-9]{7,9}', match_id)):
            match = response_body['searches'][match_id]

            country = match['player1']['location']['country']['name']
            username = match['player1']['username']
            search_time_remaining = match['search_time_remaining']
            is_ranked = match['is_ranked']
            player_id = match['player1']['id']
            ladder_name = match['ladder_name']

            match_info = { 'username': username,
                           'country': country,
                           'search_time_remaining': search_time_remaining,
                           'is_ranked': is_ranked,
                           'player_id': player_id,
                           'ladder_name': ladder_name }
            active_searches[match_id] = match_info

    return active_searches


def retrieve_active_whitelisted_searches(cookie_jar):
    active_searches = retrieve_active_searches(cookie_jar)

    active_whitelisted_searches = dict()
    for match_id in active_searches:
        country = active_searches[match_id]['country']
        if country in WHITELISTED_COUNTRIES:
            active_whitelisted_searches[match_id] = active_searches[match_id]

    return active_whitelisted_searches


def retrieve_challenges_awaiting_reply(cookie_jar):
    response = http_get_request('https://www.smashladder.com/matchmaking/retrieve_match_searches',
                                cookie_jar)
    response_body = json.loads(response.text)

    match_info = []
    for match_id in response_body['awaiting_replies']:
        if (re.match('[0-9]{7,9}', match_id)):
            match = response_body['awaiting_replies'][match_id]
            username = match['player1']['username']
            match_info.append(username)

    return match_info


def accept_match_challenge(cookie_jar, match_id):
    builtins.current_match_id = match_id
    builtins.in_match = True

    content = { 'accept': '1',
                'match_id': match_id,
                'host_code': '' }
    http_post_request('https://www.smashladder.com/matchmaking/reply_to_match',
                      content, cookie_jar)


def challenge_active_searches_friendlies(cookie_jar):
    active_whitelisted_searches = retrieve_active_whitelisted_searches(cookie_jar)

    # don't challenge people again if already waiting for reply,
    # users who are ignored,
    # players that you have blacklisted for e.g. high ping
    challenges_awaiting_reply = retrieve_challenges_awaiting_reply(cookie_jar)
    ignored_users = retrieve_ignored_users(cookie_jar)
    high_ping_players = HIGH_PING_PLAYERS

    for match_id in active_whitelisted_searches:
        match = active_whitelisted_searches[match_id]
        ladder_name = match["ladder_name"]
        player_id = match["player_id"]
        if ladder_name in WHITELISTED_GAMES.keys():
            content = { 'team_size': '1',
                        'game_id': WHITELISTED_GAMES[ladder_name],
                        'match_count': '0',
                        'ranked': '0',
                        'challenge_player_id': player_id,
                        'match-id': '' }

            opponent_username = match['username']
            opponent_country = match['country']

            if opponent_username == OWN_USERNAME or \
               opponent_username in challenges_awaiting_reply or \
               opponent_username in ignored_users or \
               opponent_username in high_ping_players:
                continue

            http_post_request('https://www.smashladder.com/matchmaking/challenge_search',
                              content, cookie_jar)
            smashladder_qt.qt_print("Trying to challenge " + opponent_username + " from " + opponent_country + " to " + ladder_name)


def retrieve_ignored_users(cookie_jar):
    response = http_post_request('https://www.smashladder.com/matchmaking/ignore_list',
                                 {}, cookie_jar)
    response_body = json.loads(response.text)

    ignored_users = []
    for user in response_body['ignores']:
        ignored_users.append(user['username'])

    return ignored_users


def handle_private_chat_message(message):
    message = json.loads(message)
    chat_data = message['private_chat']

    for user_id in chat_data:
        if 'username' in chat_data[user_id]:
            username = chat_data[user_id]['username']
        else:
            username = OWN_USERNAME
        chat_messages = chat_data[user_id]['chat_messages']
        for message_key in chat_messages:
            chat_message = chat_messages[message_key]['message']

    # if your own message, you don't get a username
    if username:
        smashladder_qt.qt_print('[private chat] ' + username + ': ' + chat_message)
    else:
        smashladder_qt.qt_print('[private chat] ' + username + ': ' + chat_message)


def handle_match_message(message):
    message = json.loads(message)

    # if received message is about getting an answer to a challenge,
    # print a message and set globals
    for match_id in message['current_matches']:
        if 'start_time' in message['current_matches'][match_id]:
            builtins.current_match_id = match_id
            builtins.in_match = True
            return

    for match_id in message['current_matches']:
        match_chat_data = message['current_matches'][match_id]['chat']['chat_messages']
        # you also receive data for someone starts/stops typing, which
        # should be ignored
        if type(match_chat_data) is dict:
            for chat_message_id in match_chat_data:
                if re.match('[0-9]{7,9}', chat_message_id):
                    chat_message = match_chat_data[chat_message_id]['message']
                    username = match_chat_data[chat_message_id]['player']['username']

    if 'chat_message' in locals():
        smashladder_qt.qt_print('[match chat] ' + username + ': ', chat_message)


def handle_open_challenges(cookie_jar, message):
    message = json.loads(message)

    is_ranked = []
    ladder_name = []
    opponent_username = []
    opponent_country = []
    match_ids = []

    for match_id in message['open_challenges']:
        if re.match('[0-9]{7,9}', match_id):
            match_ids.append(match_id)
            challenge_info = message['open_challenges'][match_id]
            is_ranked.append(challenge_info['is_ranked'])
            ladder_name.append(challenge_info['ladder_name'])
            opponent_username.append(challenge_info['player2']['username'])
            opponent_country.append(challenge_info['player2']['location']['country']['name'])

    for i in range(len(match_ids)):
        smashladder_qt.qt_print(opponent_username[i] + ' from ' + opponent_country[i] + ' has challenged you to ' + ladder_name[i] + ' (ranked (' + str(is_ranked[i]) + '))')

    for i, country in enumerate(opponent_country):
        if country in WHITELISTED_COUNTRIES:
            accept_match_challenge(cookie_jar, match_ids[i])
            smashladder_qt.qt_print('Accepted challenge from ' + opponent_username[i] + ' from ' + opponent_country[i] + '.')
            break;


def report_friendly_done(cookie_jar, match_id):
    content = { 'won': 4,
                'message': '',
                'match_id': match_id }
    http_post_request('https://www.smashladder.com/matchmaking/report_match',
                      content, cookie_jar)


def finished_chatting_with_match(cookie_jar, match_id):
    content = { 'match_id': match_id }
    http_post_request('https://www.smashladder.com/matchmaking/finished_chatting_with_match',
                      content, cookie_jar)
    builtins.current_match_id = None
    builtins.in_match = False


def matchmaking_loop(cookie_jar):
    while True:
        if builtins.in_match:
            smashladder_qt.qt_print('Already in match, not going to start matchmaking.')
            time.sleep(5)
        else:
            match_id = begin_matchmaking(cookie_jar, 1, 2, 0, '', 0, '')
            time.sleep(305)


def challenge_loop(cookie_jar):
    while True:
        if builtins.in_match:
            smashladder_qt.qt_print('Already in match, will not challenge people to matches.')
            time.sleep(5)
        else:
            challenge_active_searches_friendlies(cookie_jar)
            time.sleep(5)
