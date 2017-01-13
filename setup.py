from setuptools import setup, find_packages

setup(
	name='django-dbtunnel',
	version='1.0.0',
	description='Connect to and use a remote database over an SSH tunnel in Django.',
	url='https://github.com/mvx24/django-dbtunnel',
	author='mvx24',
	author_email='cram2400@gmail.com',
	license='MIT',
	classifiers=[
		'Development Status :: 5 - Production/Stable',
		'Environment :: Console',
		'Framework :: Django',
		'License :: OSI Approved :: MIT License',
		'Operating System :: MacOS :: MacOS X',
		'Operating System :: POSIX',
		'Operating System :: Unix',
		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 2 :: Only',
		'Topic :: System :: Systems Administration'
	],
	keywords='ssh tunnel production database django paramiko mysql postgresql',
	packages=find_packages(),
	install_requires=['django', 'paramiko'],
)
