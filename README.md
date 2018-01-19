# smashladder-python

Small project to matchmake automatically on Anther's (https://www.smashladder.com).

![App](https://github.com/thomaav/smashladder-python/raw/master/static/app.png)

## Functionality

### Automatic matchmaking

Press «Start» to have the application run automatic matchmaking for
you. You will automatically be searching, challenging any players
queuing up that fit your configuration, as well as accepting any
received challenges.

### Choose who to play against

There are several ways to decide who you want to have the script challenge
and accept:

#### Blacklisting

It is possible to add players that you do not want to have the script
matchmake to a blacklist. This can be because of high ping etc.

It is also possible to only temporarily blacklist someone until your
next session of playing by right clicking their name in the list. They
will then be deleted off the blacklist the next time you start the
application. Useful for when you just want to play someone else for a
bit.

#### Whitelisting

To have the script work at all, you have to whitelist countries that
you usually receive good ping towards, to have the script recognize
which players you want to play against.

#### Preferring players

If you play someone you enjoy playing a lot, you can hit the + icon in
the match to add them to your preferred players. If someone you prefer
to play starts queueing when you are idling, a sound will be played,
and you will be able to click their name in the chat to challenge them
immediately.

### Idling

The application will always show when someone that you would otherwise
be challenging if you were running the script by printing this to the
main window, so that you can start playing if you see someone you
like.


### Private chat

If you click the «Private chat» letters beside the checkbox, a private
chat window will be opened. You can change the user you want to talk
to by issuing «/change_user $username», and the script will then fetch
your chat history as well. This is only meant for small messaging if
you just want to hit someone up, as the application is mostly meant
just for finding matches -- not chatting.