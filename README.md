# flask_dirview
A reimplementation of Apache's directory browser in flask. [Try it](https://cld.sh/static) for yourself

## how to use
just copy `flask_dirview.py` from this repo into your project's folder.

## Usage:
```py
from flask import Flask
from flask_dirview import DirView, Apache

app = Flask(__name__)
DirView(app, "/home/foo", "/bar", frontend=Apache)
# this maps the directory `/home/foo` to `/bar` url
# thats it, enjoy.
```

when run directly (`./flask_dirview.py`) it will fire up a demo of this micro-library. (flask is required)

## FAQ
- what in the world is this big binary blob?
	- it's a uuencoded, gzipped tarball of apache's icons, (they are public domain)
