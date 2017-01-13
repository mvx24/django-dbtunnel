import os
import select
import socket
import SocketServer
import thread

from django.conf import settings
from django.db import connections
from django.db.utils import ConnectionDoesNotExist

"""
Tunneling mostly based on the sample paramiko code:
https://github.com/paramiko/paramiko/blob/master/demos/forward.py
Previously tried unsuccessfully based on using the subprocess module and runnning:
args = ['ssh', '-f', '-N', '-o', 'StrictHostKeyChecking=no', '-o', 'ExitOnForwardFailure=yes', '-L']
in addition to specifying the host, username, and identityfile
"""

SSH_CLIENT_KEY = '__DATABASE_SSH_CLIENT'
SSH_TUNNEL_KEY = '__DATABASE_SSH_TUNNEL'

class __PortForwardingServer(SocketServer.ThreadingTCPServer):
	daemon_threads = True
	allow_reuse_address = True

class __PortForwardingServerHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		try:
			chan = self.ssh_transport.open_channel('direct-tcpip', (self.chain_host, self.chain_port), self.request.getpeername())
		except Exception, e:
			#print 'Incoming request to %s:%d failed: %s' % (self.chain_host, self.chain_port, repr(e))
			return
		if chan is None:
			#print('Incoming request to %s:%d was rejected by the SSH server.' % (self.chain_host, self.chain_port))
			return
		#print('Connected!  Tunnel open %r -> %r -> %r' % (self.request.getpeername(), chan.getpeername(), (self.chain_host, self.chain_port)))
		while True:
			r, w, x = select.select([self.request, chan], [], [])
			if self.request in r:
				data = self.request.recv(1024)
				if len(data) == 0:
					break
				chan.send(data)
			if chan in r:
				data = chan.recv(1024)
				if len(data) == 0:
					break
				self.request.send(data)
		chan.close()
		self.request.close()
		#print('Tunnel closed from %r' % (self.request.getpeername(),))

def __start_tunnel(server):
	server.serve_forever()

def start_tunnel(database, use_ssh_config=False):
	if not database:
		return
	from paramiko import AutoAddPolicy, SSHClient, SSHConfig
	db = settings.DATABASES[database]
	if db.has_key(SSH_CLIENT_KEY):
		# Tunnel is already running
		return
	if not db.has_key('REMOTE_HOST'):
		raise ValueError('REMOTE_HOST not specified for ' + database)
	if not db.has_key('TUNNEL_HOST'):
		raise ValueError('TUNNEL_HOST not specified for ' + database)
	kwargs = {}
	hostname = db['TUNNEL_HOST']
	
	# Setup the kwargs
	if db.has_key('TUNNEL_USER'):
		kwargs['username'] = db['TUNNEL_USER']
	if db.has_key('TUNNEL_PASSWORD'):
		kwargs['password'] = db['TUNNEL_PASSWORD']
	if db.has_key('TUNNEL_IDENTITY'):
		kwargs['key_filename'] = db['TUNNEL_IDENTITY']
	if db.has_key('TUNNEL_PORT'):
		kwargs['port'] = int(db['TUNNEL_PORT'])
	if use_ssh_config:
		try:
			with open(os.path.expanduser('~/.ssh/config')) as f:
				sshConfig = SSHConfig()
				sshConfig.parse(f)
				config = sshConfig.lookup(db['TUNNEL_HOST'])
				hostname = config['hostname']
				# Use username and port if missing
				if not kwargs.has_key('username') and config.has_key('user'):
					kwargs['username'] = config['user']
				if not kwargs.has_key('port') and config.has_key('port'):
					kwargs['port'] = int(config['port'])
				# Add identityfile (a list)
				if config.has_key('identityfile'):
					if kwargs.has_key('key_filename'):
						if type(kwargs['key_filename']) is list:
							kwargs['key_filename'] += config['identityfile']
						else:
							kwargs['key_filename'] = [kwargs['key_filename']] + config['identityfile']
					else:
						kwargs['key_filename'] = config['identityfile']
		except:
			pass

	# Fix the identity files
	if kwargs.has_key('key_filename'):
		if type(kwargs['key_filename']) is list:
			for i in range(len(kwargs['key_filename'])):
				if kwargs['key_filename'][i].startswith('~'):
					kwargs['key_filename'][i] = os.path.expanduser(kwargs['key_filename'][i])
		elif kwargs['key_filename'].startswith('~'):
			kwargs['key_filename'] = os.path.expanduser(kwargs['key_filename'])

	# Setup the client
	client = SSHClient()
	client.load_system_host_keys()
	client.set_missing_host_key_policy(AutoAddPolicy())
	client.connect(hostname, **kwargs)

	# Setup the port forwarding server
	class __SubPortForwardingServerHandler(__PortForwardingServerHandler):
		chain_host = db['REMOTE_HOST']
		chain_port = int(db['PORT'])
		ssh_transport = client.get_transport()
	server = __PortForwardingServer(('', int(db['PORT'])), __SubPortForwardingServerHandler)
	# Save a reference to the client and port forwarding server
	db[SSH_TUNNEL_KEY] = server
	db[SSH_CLIENT_KEY] = client
	# Start port forwarding server on another thread
	thread.start_new_thread(__start_tunnel, (server,))

def stop_tunnel(database):
	if not database:
		return
	# Close the database connection, because it will no longer be reachable after the tunnel goes down
	try:
		connections[database].close()
	except ConnectionDoesNotExist:
		pass
	db = settings.DATABASES[database]
	# Stop the server
	if db.has_key(SSH_TUNNEL_KEY):
		db[SSH_TUNNEL_KEY].shutdown()
		del db[SSH_TUNNEL_KEY]
	# Stop the client
	if db.has_key(SSH_CLIENT_KEY):
		db[SSH_CLIENT_KEY].close()
		del db[SSH_CLIENT_KEY]

class database_tunnel(object):
	"""Creates a temporary tunnel to a remote database for management commands or whatever else.

	Passing None will not raise any exceptions.
	Database dictionary in settings must include REMOTE_HOST and TUNNEL_HOST (optionally TUNNEL_PORT)
	Also, TUNNEL_USER and TUNNEL_PASSWORD or TUNNEL_IDENTITY must be specified, or have the TUNNEL_HOST setup in ~/.ssh/config.
	After setting up, make queries like: Model.objects.using('other').all()
	"""
	def __init__(self, database, use_ssh_config=False):
		self.__database = database
		self.__use_ssh_config = use_ssh_config
	def __enter__(self):
		start_tunnel(self.__database, self.__use_ssh_config)
	def __exit__(self, *_):
		stop_tunnel(self.__database)
