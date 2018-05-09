import wikipedia

def set_options(options):
	x = options.get('language')
	if x:
		wikipedia.set_lang(x)

def msg_call(room, sender, msg, **kwargs):
	if not msg:
		return ''
	return wikipedia.summary(msg)
