import builtins
import json
import re
import sys
import time
from smashladder.local import *
from smashladder.slrequests import *


builtins.current_match_id = None
builtins.in_match = False
builtins.in_queue = False
builtins.search_match_id = None
builtins.idle = True


current_fm_build = 'Faster Melee 5.8.7'
melee_id = '2'


class SlConfig(object):
    def __init__(self,
                 friendlies = True,
                 ranked = False,
                 doubles = False,
                 enabled_games = { 'Melee': '2' },
                 enabled_builds = ['Faster Melee 5.8.7']
    ):
        self.friendlies = friendlies
        self.ranked = ranked
        self.doubles = doubles
        self.enabled_games = enabled_games
        self.enabled_builds = enabled_builds


    def set_friendlies(self, val):
        if type(val) is bool:
            self.friendlies = val


    def set_ranked(self, val):
        if type(val) is bool:
            self.ranked = val


    def set_doubles(self, val):
        if type(val) is bool:
            self.doubles = val


active_config = SlConfig()


class Match(object):
    def __init__(self, match):
        if 'is_removed' in match:
            self.removed = True
            return

        self.removed = False
        self.opponent_username = match['player1']['username']
        self.opponent_id = match['player1']['id']
        self.opponent_country = match['player1']['location']['country']['name']
        self.is_ranked = match['is_ranked']
        self.ladder_name = match['ladder_name']
        self.match_id = match['id']
        self.team_size = match['team_size']
        self.preferred_builds = match['player1']['preferred_builds']


    def relevant(self):
        # first weed out definite irrelevant matches
        if self.removed:
            return False

        if self.ladder_name not in active_config.enabled_games.keys():
            return False

        # walk through all preferred builds of opponent to see if we
        # have _any_ matches across any enabled game
        builds_match = False
        for game in self.preferred_builds:
            if game in active_config.enabled_games.values():
                for build in self.preferred_builds[game]:
                    if build['name'] in active_config.enabled_builds and build['active'] == True:
                        builds_match = True
        if not builds_match:
            return False

        # handle doubles specifically to avoid confusion in friendlies
        # vs. ranked
        if self.team_size == 2 and not active_config.doubles:
            return False

        # now if we match certain config, we're relevant
        if (not self.is_ranked and active_config.friendlies) or \
           (self.is_ranked and active_config.ranked):
            return True

        return False


def begin_matchmaking(cookie_jar, team_size, game_id, match_count,
                      title, ranked, host_code):
    """
    cookie_jar is required, as you need to be logged in
    team_size is 1, not doubles
    game_id is game, 2 for melee
    match_count is 0, probably for ranked
    title i dont fucking know, use ''
    ranked, 0 or 1 accordingly
    host_code is can be added if wanted, '' if none
    """

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

            if not opponent_uses_active_build(match):
                continue

            if match_is_doubles(match) and \
               not active_config.doubles:
                continue

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


def player_relevant(country, username):
    if country.lower() in [c.lower() for c in WHITELISTED_COUNTRIES] \
       and username.lower() not in [p.lower() for p in BLACKLISTED_PLAYERS]:
        return True
    return False


def retrieve_relevant_searches(cookie_jar):
    active_searches = retrieve_active_searches(cookie_jar)

    relevant_searches = dict()
    for match_id in active_searches:
        country = active_searches[match_id]['country']
        username = active_searches[match_id]['username']
        ladder_name = active_searches[match_id]['ladder_name']

        if ladder_name != 'Melee':
            continue

        if player_relevant(country, username):
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


def challenge_opponent(cookie_jar, opponent_id, match_id):
    content = { 'challenge_player_id': opponent_id,
                'match_id': match_id }

    return http_post_request('https://www.smashladder.com/matchmaking/challenge_search',
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
            opponent_username = match['username']
            opponent_country = match['country']

            if opponent_username == own_username or \
               opponent_username in challenges_awaiting_reply or \
               opponent_username in ignored_users:
                continue

            if not match_relevant(match):
                continue

            if not builtins.debug_smashladder:
                response = challenge_opponent(cookie_jar, player_id, match_id)
            else:
                print('[DEBUG]: Would challenge ' + opponent_username + ' from ' + opponent_country)

            challenged_players.append({ 'username': decorate_username(opponent_username),
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
        return { 'info': '[private chat] ' + decorate_username(username) + ': ' + chat_message }
    else:
        return { 'info': 'Unspecified failure in handling private chat message' }


def process_match_message(message):
    message = json.loads(message)

    # if received message is about getting an answer to a challenge,
    # print a message and set globals
    for match_id in message['current_matches']:
        if 'start_time' in message['current_matches'][match_id]:
            opponent = message['current_matches'][match_id]['player1']
            return { 'match_id': match_id,
                     'typing': False,
                     'info': 'Entered match: ' + match_id,
                     'opponent_username': opponent['username'],
                     'opponent_country': opponent['location']['country']['name'] }

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
        if player_relevant(country, opponent_username[i]) and \
           match_relevant(is_ranked=is_ranked[i], ladder_name=ladder_name[i]):
            if not builtins.debug_smashladder:
                accept_match_challenge(cookie_jar, match_ids[i])
            else:
                print('[DEBUG]: Would accept challenge ' + opponent_username[i] + ' from ' + country)

            return { 'match_id': match_ids[i],
                     'info': 'Accepted challenge from ' + decorate_username(opponent_username[i]) + ' from ' + opponent_country[i],
                     'opponent_username': opponent_username[i],
                     'opponent_country': opponent_country[i] }
        else:
            decline_match_challenge(cookie_jar, match_ids[i])
            return { 'match_id': match_ids[i],
                     'info': 'Declined challenge from ' + decorate_username(opponent_username[i]) + ' from ' + opponent_country[i],
                     'opponent_username': opponent_username[i],
                     'opponent_country': opponent_country[i] }

    return { 'match_id': None,
             'info': 'No awaiting challenges matching config criteria',
             'opponent_username': None,
             'opponent_country': None }


def get_search_info(message):
    message = json.loads(message)
    new_match = next(iter(message['searches'].values()))
    match = Match(new_match)
    if match.removed:
        return None
    else:
        return match


def process_new_search(cookie_jar, message, own_username):
    message = json.loads(message)
    new_match = next(iter(message['searches'].values()))
    match = Match(new_match)

    if not match.relevant():
        return

    if player_relevant(match.opponent_country, match.opponent_username) and \
       match.opponent_username != own_username:
        response = challenge_opponent(cookie_jar, match.opponent_id, match.match_id)
        return { 'username': decorate_username(match.opponent_username),
                 'country': match.opponent_country }


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


def opponent_uses_active_build(match):
    if melee_id in match['player1']['preferred_builds']:
        for build in match['player1']['preferred_builds'][melee_id]:
            if build['name'] == current_fm_build and build['active'] == False:
                return False
    return True


def match_is_doubles(match):
    return match['team_size'] == 2


def match_relevant(match=None, is_ranked=None, ladder_name=None):
    if match:
        is_ranked = match['is_ranked']
        ladder_name = match['ladder_name']

    if ladder_name != 'Melee':
        return False

    if not is_ranked and active_config.friendlies:
        return True

    if is_ranked and active_config.ranked:
        return True

    return False


def send_match_chat_message(cookie_jar, match_id, message):
    content = { 'match_id': match_id,
                'message': message,
                'send_id': 20 }
    response = http_post_request('https://www.smashladder.com/matchmaking/send_chat',
                                 content, cookie_jar)


def send_private_chat_message(cookie_jar, username, message):
    try:
        user_id = fetch_user_id(cookie_jar, username)
        message_content = { 'to_user_id': user_id,
                            'message': message,
                            'send_id': 1 }
        response = http_post_request('https://www.smashladder.com/matchmaking/send_chat',
                                     message_content, cookie_jar)
    except Exception as e:
        print('[DEBUG]: Error in sending private chat: ' + str(e))


def fetch_private_messages(cookie_jar, username):
    try:
        user_id = fetch_user_id(cookie_jar, username)
        content = { 'id': user_id,
                    'username': username }
        response = http_post_request('https://www.smashladder.com/matchmaking/private_chat',
                                     content, cookie_jar)
        messages = (response.json())['private_chat_user']['private_chat']['chat_messages']
        messages_ids = sorted(list(messages.keys()))
        latest_messages_ids = messages_ids[max(-10, -1 * len(messages)):]
        latest_messages = []

        for message_id in sorted(latest_messages_ids):
            message_username = messages[message_id]['player']['username']
            message_message = messages[message_id]['message']
            latest_messages.append({ 'username': message_username, 'message': message_message})
        return latest_messages
    except Exception as e:
        print('[DEBUG]: Error in fetching private messages: ' + str(e))
        return []


def decorate_username(username):
    return '<span class="username">' + username + '</span>'


def fetch_user_id(cookie_jar, username):
    fetch_user_content = { 'username': username }
    response = http_post_request('https://www.smashladder.com/matchmaking/user',
                                 fetch_user_content, cookie_jar)
    try:
        user_id = (response.json())['user']['id']
        return user_id
    except Exception as e:
        print('[DEBUG]: Error in fetching user id: ' + str(e))
        return None


def fetch_match_messages(cookie_jar):
    content = { 'is_in_ladder': True,
                'match_only_mode': True }
    response = http_post_request('https://www.smashladder.com/matchmaking/get_user_going',
                                 content, cookie_jar)

    if not response.json()['current_matches']:
        return []

    chat = list(response.json()['current_matches'].values())[0]['chat']['chat_messages']

    messages = []
    for message_id in chat:
        username = chat[message_id]['player']['username']
        message = chat[message_id]['message']
        messages.append({ 'username': username, 'message': message })

    return messages


def fetch_existing_match(cookie_jar):
    content = { 'is_in_ladder': True,
                'match_only_mode': True }
    response = http_post_request('https://www.smashladder.com/matchmaking/get_user_going',
                                 content, cookie_jar)

    if not response.json()['current_matches']:
        return None

    match_id = list(response.json()['current_matches'].keys())[0]
    return match_id
