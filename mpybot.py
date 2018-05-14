import time
import yaml
import logging
import importlib

from matrix_client.client import MatrixClient
from matrix_client.errors import MatrixError

logger = logging.getLogger(__name__)

CONFIG_FILENAME = 'config.yaml'
STARTCMD = 'mpybot'

def load_yaml_config(filename):
	with open(filename, 'r') as conf_file:
		return yaml.load(conf_file)

class MpyBot:
	def __init__(self, configfile, run=True):
		logger.debug('load config')
		config_dic = load_yaml_config(configfile)
		self.bot_startcmd = config_dic.get('bot_startcmd', STARTCMD)

		self._full_cmds = {}
		self._local_cmds = {}
		self._module_calls = {}
		for moduledic in config_dic.get('modules', []):
			self.add_module(moduledic)

		matrix_server = config_dic['matrix_server']

		logger.debug('init bot')
		self.mcl = MatrixClient(**matrix_server)

		self.auto_join_invited_rooms = config_dic.get('auto_join_invited_rooms', True)
		self.auto_join_servers = set(config_dic.get('auto_join_servers', []))

		self.admin_ids = set(config_dic.get('admin_ids', []))

		disp_name = config_dic.get('bot_display_name', '')
		if disp_name:
			user = self.mcl.get_user(self.mcl.user_id)
			if user.get_display_name() != disp_name:
				user.set_display_name(disp_name)

		self.mcl.add_invite_listener(self._process_invite)
		self.mcl.add_listener(self._process_message, 'm.room.message')

		logger.info('bot initialized')

		if run:
			self._run()

	def _run(self):
		logger.debug('run listen_forever')
		self.mcl.listen_forever()


	def join_room(self, room_id):
		try:
			logger.info('joining new room {}'.format(room_id))
			room = self.mcl.join_room(room_id)
			room.send_text("Welcome! Type {} to control me.".format(self.bot_startcmd))
			return True
		except MatrixError as e:
			logger.exception('{} while joining room {}'.format(repr(e), room_id))
			return False

	def leave_room(self, room_id):
		logger.info('trying to leave room with id {}'.format(room_id))
		leave_room = self.mcl.get_rooms().get(room_id, '')
		if not leave_room:
			logger.debug('bot not in room {}'.format(room_id))
			return False
		if leave_room.leave():
			logger.debug('left room {}'.format(room_id))
			return True
		else:
			logger.debug('failed to leave known room with id {}'.format(leave_room.room_id))
		return False


	def _process_invite(self, room_id, state=None):
		logger.debug('received invitation to {}, state: {}'.format(room_id, state))
		if self.auto_join_invited_rooms:
			if self.auto_join_servers and \
					room_id.split(':')[-1] not in self.auto_join_servers:
				return
			self.join_room(room_id)

	def _process_message(self, roomchunk):
		if roomchunk['sender'] == self.mcl.user_id:
			return

		age = roomchunk.get('unsigned', {}).get('age')
		if age is None:
			# fallback
			age = abs(time.time() - roomchunk['origin_server_ts']/1000)
		else:
			age /= 1000

		if age > 60:
			logger.debug('received old message in {}, event_id: {}'.format(roomchunk['room_id'], roomchunk['event_id']))
			return

		content = roomchunk['content']
		if content['msgtype'] == 'm.text':
			msg = content['body'].lstrip()
			if msg.startswith(self.bot_startcmd):
				room = self.mcl.get_rooms()[roomchunk['room_id']]
				msg = msg[len(self.bot_startcmd):].lstrip()
				self._evaluate_bot_message(room, roomchunk['sender'], msg)
			else:
				s_msg = msg.split(' ', 1)
				cmd = s_msg[0]
				msg = s_msg[1] if len(s_msg) > 1 else ''
				modulename = self._full_cmds.get(cmd)
				if modulename:
					room = self.mcl.get_rooms()[roomchunk['room_id']]
					self._call_module(modulename, room, roomchunk['sender'], msg)

	def _evaluate_bot_message(self, room, sender, msg):
		if msg.startswith('ctl'):
			logger.debug("received control message '{}' in room '{}'".format(msg, room.room_id))
			if sender not in self.admin_ids:
				logger.debug('{} has no permissions to send a ctl-message'.format(sender))
				room.send_notice('{} has no permissions to send a ctl-message'.format(sender))
				return
			data = msg.split()[1:]
			if len(data) == 2:
				if data[0] == 'join':
					if not self.join_room(data[1]):
						room.send_notice('something went wrong while joining room')
				elif data[0] == 'leave':
					if data[1] == 'this':
						data[1] = room.room_id
					if not self.leave_room(data[1]):
						room.send_notice('room could not be left')
			return

		elif msg.startswith('-'):
			msg = msg[1:].strip()
			if msg.startswith('help'):
				text = 'Available local commands:\n'
				for k in self._local_cmds:
					text += ' - ' + k + '\n'
				text += 'Available full commands:\n'
				for k in self._full_cmds:
					text += ' - ' + k + '\n'
				room.send_text(text)
			elif msg.startswith('time'):
				room.send_text('UTC: {:.0f}'.format(time.time()))

		s_msg = msg.split(' ', 1)
		cmd = s_msg[0]
		msg = s_msg[1] if len(s_msg) > 1 else ''

		modulename = self._local_cmds.get(cmd)
		if modulename:
			self._call_module(modulename, room, sender, msg)


	def add_module(self, moduledic):
		try:
			name = moduledic['name']
			module = importlib.import_module('modules.' + name)
			opt = moduledic.get('options')
			logging.debug('here')
			if opt:
				module.set_options(opt)

			self._module_calls[name] = module.msg_call

			cmd = moduledic.get('local_cmd')
			if cmd:
				self._local_cmds[cmd] = name
			cmd = moduledic.get('full_cmd')
			if cmd:
				self._full_cmds[cmd] = name

			logger.info('module {} added'.format(moduledic))
		except Exception as e:
			logger.exception('not possible to add module {}: {}'.format(moduledic, repr(e)))

	def _call_module(self, modulename, room, sender, msg):
		logger.debug("modulecall {} for message '{}' in room {}".format(modulename, msg, room.room_id))
		try:
			res = self._module_calls[modulename](room=room, sender=sender, msg=msg)
			if res and isinstance(res, str):
				room.send_text(res)
		except Exception as e:
			logger.exception('Failed to call module {}'.format(modulename))


if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(asctime)s: %(message)s')
	logger.setLevel(logging.DEBUG)

	sleeping_time = 5
	timestamp_last_exception = time.time()
	while True:
		try:
			mpybot = MpyBot(CONFIG_FILENAME)
		except Exception as e:
			logging.exception('A exception occured: {}'.format(repr(e)))

		if time.time() - timestamp_last_exception > 900:  # 15 min
			sleeping_time = 5
		elif sleeping_time < 450:
			sleeping_time = int(sleeping_time * 4/3 + 1)
		else:
			sleeping_time = 600
		timestamp_last_exception = time.time()
		time.sleep(sleeping_time)
