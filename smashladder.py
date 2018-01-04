import builtins
import json
import main
import smashladder_qt
import re
import sys
import time
from local import *
from smashladder_requests import *


builtins.current_match_id = None
builtins.in_match = False
builtins.in_queue = False
builtins.search_match_id = None
builtins.idle = True


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
    try:
        for match_id in response_body['searches']:
            if (re.match('[0-9]{7,9}', match_id)):
                own_match_id = match_id
    except KeyError:
        error_msg = response_body['error']

        if error_msg == 'You do not have access to this page':
            return { 'match_id': None, 'info': 'Log in to matchmake' }
        elif error_msg == 'A search like this is already active!':
            return { 'match_id': None, 'info': 'Already in queue, not starting matchmaking' }
        else:
            return { 'match_id': None, 'info': 'Unspecified failure. Matchmaking aborted' }

    if (own_match_id):
        return { 'match_id': own_match_id, 'info': 'Success! Queued for matchmaking: ' + own_match_id }
    else:
        return { 'match_id': None, 'info': 'Unspecified failure. Queueing aborted' }


def enter_match(match_id):
    builtins.current_match_id = match_id
    builtins.in_match = True
    builtins.in_queue = False
    builtins.search_match_id = None
    smashladder_qt.qt_change_status(smashladder_qt.MMStatus.IN_MATCH)


def quit_matchmaking(cookie_jar, match_id):
    content = { 'match_id': match_id }

    response = http_post_request('https://www.smashladder.com/matchmaking/end_matchmaking',
                                 content, cookie_jar)
    response_body = json.loads(response.text)

    if 'success' in response_body:
        return True
    return False


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


def retrieve_relevant_searches(cookie_jar):
    active_searches = retrieve_active_searches(cookie_jar)

    relevant_searches = dict()
    for match_id in active_searches:
        country = active_searches[match_id]['country']
        username = active_searches[match_id]['username']
        if country in WHITELISTED_COUNTRIES \
           and username not in BLACKLISTED_PLAYERS:
            relevant_searches[match_id] = active_searches[match_id]

    return relevant_searches


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
    enter_match(match_id)

    content = { 'accept': '1',
                'match_id': match_id,
                'host_code': '' }
    http_post_request('https://www.smashladder.com/matchmaking/reply_to_match',
                      content, cookie_jar)


def decline_match_challenge(cookie_jar, match_id):
    content = { 'accept': '0',
                'match_id': match_id,
                'host_code': '' }
    http_post_request('https://www.smashladder.com/matchmaking/reply_to_match',
                      content, cookie_jar)


def challenge_relevant_friendlies(cookie_jar, own_username):
    relevant_searches = retrieve_relevant_searches(cookie_jar)

    # don't challenge people again if already waiting for reply,
    # users who are ignored,
    # players that you have blacklisted for e.g. high ping
    challenges_awaiting_reply = retrieve_challenges_awaiting_reply(cookie_jar)
    ignored_users = retrieve_ignored_users(cookie_jar)
    blacklisted_players = BLACKLISTED_PLAYERS
    challenged_players = []

    for match_id in relevant_searches:
        match = relevant_searches[match_id]
        ladder_name = match["ladder_name"]
        player_id = match["player_id"]
        if ladder_name in WHITELISTED_GAMES.keys():
            content = { 'challenge_player_id': player_id,
                        'match-id': match_id }

            opponent_username = match['username']
            opponent_country = match['country']

            if opponent_username == own_username or \
               opponent_username in challenges_awaiting_reply or \
               opponent_username in ignored_users:
                continue

            if match['is_ranked']:
                continue

            if not builtins.debug_smashladder:
                response = http_post_request('https://www.smashladder.com/matchmaking/challenge_search',
                                             content, cookie_jar)
            else:
                print('[DEBUG]: Would challenge ' + opponent_username + ' from ' + opponent_country)

            challenged_players.append({ 'username': opponent_username,
                                        'country': opponent_country })

    return challenged_players


def retrieve_ignored_users(cookie_jar):
    response = http_post_request('https://www.smashladder.com/matchmaking/ignore_list',
                                 {}, cookie_jar)
    response_body = json.loads(response.text)

    ignored_users = []
    for user in response_body['ignores']:
        ignored_users.append(user['username'])

    return ignored_users


def process_private_chat_message(message):
    message = json.loads(message)
    chat_data = message['private_chat']

    for user_id in chat_data:
        if 'username' in chat_data[user_id]:
            username = chat_data[user_id]['username']
        else:
            username = 'You'
        chat_messages = chat_data[user_id]['chat_messages']
        for message_key in chat_messages:
            chat_message = chat_messages[message_key]['message']

    if username:
        return { 'info': '[private chat] ' + username + ': ' + chat_message }
    else:
        return { 'info': 'Unspecified failure in handling private chat message' }


def process_match_message(message):
    message = json.loads(message)

    # if received message is about getting an answer to a challenge,
    # print a message and set globals
    for match_id in message['current_matches']:
        if 'start_time' in message['current_matches'][match_id]:
            enter_match(match_id)
            return { 'match_id': match_id,
                     'typing': False,
                     'info': 'Entered match: ' + match_id }

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
        return { 'match_id': None,
                 'typing': False,
                 'info': '[match chat] ' + username + ': ' + chat_message }
    else:
        return { 'match_id': None,
                 'typing': True,
                 'info': 'Message for participant typing - safe to ignore' }


def process_open_challenges(cookie_jar, message):
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

    for i, country in enumerate(opponent_country):
        if country in WHITELISTED_COUNTRIES \
           and opponent_username[i] not in BLACKLISTED_PLAYERS:
            if not builtins.debug_smashladder:
                accept_match_challenge(cookie_jar, match_ids[i])
            else:
                print('[DEBUG]: Would accept challenge ' + opponent_username[i] + ' from ' + country)

            return { 'match_id': match_ids[i],
                     'info': 'Accepted challenge from ' + opponent_username[i] + ' from ' + opponent_country[i] }
        else:
            decline_match_challenge(cookie_jar, match_ids[i])
            return { 'match_id': match_ids[i],
                     'info': 'Declined challenge from ' + opponent_username[i] + ' from ' + opponent_country[i] }

    return { 'match_id': None,
             'info': 'No awaiting challenges matching config criteria' }


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

