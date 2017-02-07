import json
import local
import smashladder
import smashladder_qt
import websocket


def on_message(ws, message):
    if '\"authentication\":false' in message:
        print('Authentication: false. Exiting.')
        exit(1)
    elif 'private_chat' in message:
        smashladder.handle_private_chat_message(message)
    elif 'current_matches' in message:
        smashladder.handle_match_message(message)
    elif 'open_challenges' in message:
        smashladder.handle_open_challenges(local.cookie_jar, message)


def on_error(ws, error):
    print(error)


def on_close(ws):
    print('WebSocket to smashladder closed.')


def connect_to_smashladder(cookie_jar):
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp('wss://www.smashladder.com/?type=1&version=9.11.4',
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close,
                                cookie = local.cookie_jar_to_string(local.cookie_jar))
    ws.run_forever()

