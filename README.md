# flask_dirview
A reimplementation of Apache's directory browser in flask

## how to use
just copy `flask_dirview.py` from this repo into your project's folder.

## Usage:
```py
from flask import Flask
from flask_dirview import DirView

app = Flask(__name__)
DirView(app, "/home/foo", "/bar")
# this maps the directory `/home/foo` to `/bar` url
# thats it, enjoy.
```

when run directly (`./flask_dirview.py`) it will fire up a demo of this micro-library. (flask is required)

## FAQ
- what in the world is this big binary blob?
- it's a uuencoded, gzipped tarball of apache's icons

- what is the performance?
- good, very good. Many optimizations have been applied, starting from serving icons over HTTP and not base64, applying heuristics so in most cases, the icon choosing function branches only 3 times.