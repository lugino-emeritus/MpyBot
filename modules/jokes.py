import requests
from bs4 import BeautifulSoup

default_lang = 'en'

def set_options(options):
	global default_lang
	default_lang = options.get('language', default_lang)

def msg_call(room, sender, msg, **kwargs):
	if msg:
		return get_joke(msg.split()[0])
	return get_joke()

def get_joke(language=None):
	if not language:
		language = default_lang
	try:
		if language == 'de':
			data = requests.get('http://www.witze.net/?embed&image=none&menu=off', timeout=30).text
			soup = BeautifulSoup(data, 'html.parser')
			x = [el for el in soup.findAll(text=True) if el.parent.name not in ['style', 'head', 'title']]
			return '\n'.join(x)
		elif language == 'en':
			pass
		return "Settings (language = {}) are not available yet.".format(language)
	except Exception as e:
		return "Something went wrong while receiving joke: {}".format(repr(e))
