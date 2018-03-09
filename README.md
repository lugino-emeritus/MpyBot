# MpyBot

Python Bot for [matrix](https://matrix.org) with modules.

## Setting up the bot

The Bot is based on [matrix_client](https://github.com/matrix-org/matrix-python-sdk) and is written for python 3 (tested with python 3.5).

```bash
pip3 install matrix_client

git clone https://github.com/lugino-emeritus/MpyBot
cd MpyBot
```

Copy config.yaml.sample to config.yaml and modify it:

```bash
mv config.yaml.sample config.yaml
nano config.yaml
```

Start the bot:
```bash
python3 -m mpybot
```

### Module set up

Modules has to be in the folder modules. A module must have following methods:

- `set_options(options)`: Called when loading a module
- `msg_call(**kwargs)`: Called when the bot receiving a message for the module. Available keywords are:
	- `room`: The matrix room (see matrix_client)
	- `sender`: The sender of the message
	- `msg`: The message (without commands), e.g. `!mpybot ping 42` would result in the message `42`.

To configure a module following keywords are possible:

- `name`: REQUIRED. Name of the module (e.g. ping for module ping.py)
- `local_cmd`: Command to call the module when typing the bot_startcmd followed by the local_cmd, e.g. `!mpybot ping`
- `full_cmd`: Calls the module directly, e.g. `!ping`
- `options`: Options of the module, passed to `set_options` when loading the module

For modules additional requirement could be necessary.


## Default commands

The following commands are always availble:

- `!mpybot -time`: Shows the UTC-timestamp in seconds
- `!mpybot -help`: Shown available commands

A admin also has following commands:

- `!mpybotctl join roomname`: Bot joins room with given roomname
- `!mpybotctl leave roomname`: Bot leaves room with given roomname. roomname could be this to leave current room.

Maybe you have to replace `!mpybot` by your own bot_startcmd.

#### Note:

The matrix_client has no timeout while doing a request. See [here](https://github.com/matrix-org/matrix-python-sdk/pull/157).
