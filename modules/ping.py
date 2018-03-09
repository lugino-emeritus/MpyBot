def set_options(options):
	global text
	text = options.get('text', 'No text.')

def msg_call(room, sender, msg, **kwargs):
	if msg:
		return 'PONG ' + msg
	room.send_notice('PONG ' + text)