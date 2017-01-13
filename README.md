About
-------------------------------

Connect to and use a remote database over an SSH tunnel in Django.

Installation
-------------------------------

`pip install django-dbtunnel`

Example Usage
-------------------------------

Usage is very simple by with the built-in context manager `database_tunnel(database, use_ssh_config=False)`. After starting the tunnel simply use query filters as you normally would with the using() method matching the name of the remote database you are connected to.

```python
from dbtunnel import database_tunnel
with database_tunnel('remote_db'):
	obj = SomeModel.objects.using('remote_db').filter(x=1)
```

Also available is the non-context manager methods:

* `start_tunnel(database, use_ssh_config=False)`
* `stop_tunnel(database)`

Where `database` is the keyname of the database to use from your Django DATABASES setting and `use_ssh_config` will apply any settings provided in your ~/.ssh/config file.

License
-------------------------------

MIT
