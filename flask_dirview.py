#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
One-file flask module that mimics the apache's httpd directory listing.

Usage:
```py
from flask_dirview import DirView

DirView(app, "/home/foo", "/bar")
```
The first argument is of type `Flask.Flask`
The second argument is of type `os.PathLike` and is the base path of the dirview
The third argument is of type `str` and is the base url of the dirview
"""

__author__ = "Cloud11665"
__copyright__ = "Copyright 2020-present Cloud11665"
__credits__ = ["Cloud11665"]
__version__ = "1.0.0"
__email__ = "Cloud11665@protonmail.com"
__status__ = "Production"
__license__ = """
Copyright 2020-present Cloud11665

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import os.path
from posixpath import expanduser
import re
import tarfile
import uu
from collections import defaultdict
from datetime import datetime
from functools import partial
from io import BytesIO
from os import PathLike, listdir
from os.path import (basename, getmtime, getsize, isdir, isfile, normpath,
                     realpath, relpath)
from pathlib import Path
from pprint import pprint
from random import randint
from subprocess import check_output
from textwrap import dedent
from typing import Union, Any
from urllib.parse import urlparse

import flask
from flask import (Blueprint, Flask, make_response, render_template, request,
                   send_file)
from jinja2 import Template


def sizeof_fmt(num, suffix='B'):
  for unit in ['', 'ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
    if abs(num) < 1024.0:
      if (num - int(num)) < 0.000001:
        return "%d%s%s" % (num, unit, suffix)
      return "%3.1f%s%s" % (num, unit, suffix)
    num /= 1024.0

def is_subdir(path, directory):
  path = realpath(path)
  directory = realpath(directory)
  rel = os.path.relpath(path, directory)

  return rel.startswith(os.pardir) or (path == directory)

def mimetype(path):
  return check_output(f"file -rb --mime-type \"{path}\"", shell=True)\
        .decode("utf8")\
        .strip()

def get_adress_info():
  version = flask.__version__
  host = urlparse(request.host_url).netloc
  port = request.environ.get("SERVER_PORT", "")
  distro = check_output(r'cat /etc/*release | grep "^NAME=" | cut -d "\"" -f 2',
                        shell=True)\
          .decode("utf8")\
          .strip()

  if host.endswith(port):
    host = host[:-(1+len(port))]

  return f"Flask/{version} ({distro}) Server at {host} Port {port}"


listing_template = Template(r"""
<!DOCTYPE HTML>
<html>
<head>
  <title>Index of {{ fullpath }}</title>
  <!-- Made by Cloud11665 [https://cld.sh] under Apache License 2.0 -->
</head>
<body>
  <h1>Index of {{ fullpath }}</h1>
  <table>
    <tr>
      <th valign="top">
        <img src="{{ icons }}/blank.gif" alt="[ICO]">
      </th>
      <th>
        <a href="?col=name&asc={{ ordering.name }}">Name</a>
      </th>
      <th>
        <a href="?col=lastmod&asc={{ ordering.lastmod }}">Last modified</a>
      </th>
      <th>
        <a href="?col=size&asc={{ ordering.size }}">Size</a>
      </th>
    </tr>
    <tr><th colspan="4"><hr></th></tr>
    {% if is_base %}
      {% set href = os.path.join(urlpath, "..") %}
      {% set icon_url = "%s/back.gif" % icons %}
      <tr>
        <td valign="top"><img src="{{ icon_url }}" alt="[PARENTDIR]"></td>
        <td><a href="{{ href }}">Parent Directory</a></td>
        <td>&nbsp;</td>
        <td align="right">  - </td>
      </tr>
    {% endif %}
    {% for item in listing %}
      {% set href = normpath(os.path.join(urlpath, item.href)) %}
      {% set icon_url = "%s/%s" % (icons, item.icon) %}
      <tr>
        <td valign="top"><img src="{{ icon_url }}" alt="{{ item.alt }}"></td>
        <td><a href="{{ href }}">{{ item.name }}</a></td>
        <td align="right">{{ item.lastmod }}</td>
        <td align="right">{{ item.size }}</td>
      </tr>
    {% endfor %}
    <tr><th colspan="5"><hr></th></tr>
  </table>
  <adress style="font-style: italic;">{{ address_bar }}</adress>
</body>
</html>
""")
listing_template.globals.update(globals())

mimedict = {
  "inode/x-empty": "generic.gif",
  "inode/directory": "dir.gif",
  "inode/symlink": "link.gif",
  "application/x-7z-compressed": "compressed.gif",
  "application/x-bzip2": "compressed.gif",
  "application/x-lzma": "compressed.gif",
  "application/vnd.rar": "compressed.gif",
  "application/x-rar": "compressed.gif",
  "application/gzip": "compressed.gif",
  "application/x-xz": "compressed.gif",
  "application/zip": "compressed.gif",
  "application/x-tar": "tar.gif",
  "application/x-shockwave-flash": "layout.gif",
  "application/pgp-signature": "generic.sec.gif",
  "application/octet-stream": "binary.gif",
  "application/x-sqlite3": "box1.gif",
  "application/csv": "box1.gif",
  "application/json": "box2.gif",
  "text/html": "layout.gif",
  "text/xml": "layout.gif",
  "application/pdf": "pdf.gif",
  "text/x-diff": "patch.gif",
  "application/x-innosetup": "binary.gif",
  "application/java-archive": "binary.gif",
  "application/x-executable": "binary.gif",
  "application/x-sharedlib": "binary.gif",
  "application/x-dosexec": "binary.gif",
  "text/x-tex": "tex.gif",}

proglang_exts = {
  "gst","mly","mm","gtpl","rno","aug","f08","fs","nimrod","pir","cfm","erl","g",
  "f","rbfrm","ston","rd","html","auk","b","pl6","a51","me","pbi","_js","vhost",
  "numpy","vbs","xojo_code","dita","eam.fs","t","adp","erb","thor","styl","zpl",
  "lhs","jsfl","emacs.desktop","targets","h","jelly","cuh","ily","sv","rst.txt",
  "nim","cps","pat","gcode","yacc","haml.deface","properties","fxh","cgi","gms",
  "tsx","rsh","factor","apib","tcc","inc","fx","yang","y","h","sublime-snippet",
  "jq","xml.dist","tac","jsproj","nginxconf","pyw","ebuild","mod","hb","watchr",
  "p6l","diff","gml","syntax","tcsh","tmSnippet","ct","vshader","launch","gawk",
  "pac","sce","ex","gyp","cu","cs","cake","jl","clp","g4","cls","ma","xsd","ny",
  "qml","pm6","viw","sublime_session","vcxproj","xul","rktd","ron","nawk","sma",
  "sl","fs","uc","cshtml","xojo_window","scad","xojo_menu","unity","xqm","wisp",
  "cxx","xqy","oz","b","ldml","sexp","ruby","mustache","builder","thy","clixml",
  "druby","css","http","ncl","arc","pm","svh","dm","djs","rbmnu","thrift","ftl",
  "axi.erb","asc","toml","fcgi","fxml","ada","bison","m","m","ads","vhd","bats",
  "cljscm","emberscript","glslv","vhs","ch","asc","robot","csl","xrl","objdump",
  "sch","nqp","ur","xpy","aw","tmLanguage","sublime_metrics","sublime-settings",
  "scxml","befunge","jscad","scd","aspx","pub","asciidoc","3m","mod","pxd","1m",
  "php5","jflex","t","glsl","ld","veo","vue","pri","elm","textile","matah","md",
  "ooc","mk","als","wlt","pd_lua","for","flex","reek","s","hlsli","tsx","hlean",
  "lsp","fth","gnu","sls","coffee","em","hx","gnuplot","agda","cql","prc","hbs",
  "rs","brs","brd","rabl","prg","p","dart","podsl","maxpat","com","proto","mms",
  "iced","pyx","xsp-config","vhf","f77","au3","xpl","d","scala","pt","abap","n",
  "prolog","pot","jss","ss","grxml","lex","mkdown","pde","m4","frg","gf","pyde",
  "cw","n","tcl","twig","udf","mkdn","parrot","cpp","sublime-menu","tpl","cson",
  "java","rb","ijs","tpp","sps","xslt","raml","opal","scrbl","pytb","r","nlogo",
  "mtml","geo","njs","cls","rsx","xojo_toolbar","xmi","dll.config","mxml","prw",
  "mkiv","moo","ui","scm","ash","l","sublime-macro","jbuilder","d-objdump","cp",
  "sig","ctp","htm","cxx-objdump","hh","for","tab","vrx","ps","dlm","php","clw",
  "wsf","cls","ahk","weechatlog","ncl","mod","wsdl","pl","rbuistate","xc","6pl",
  "fp","rss","xml","oxo","gvy","srdf","muf","sthlp","cc","inc","fr","dyl","jsx",
  "gd","cobol","sublime-theme","lol","minid","ml","feature","ccxml","_ls","f95",
  "coq","pike","maxhelp","nl","sjs","1x","ninja","vbproj","xsl","webidl","mkvi",
  "xq","ttl","volt","clj","hy","csx","php4","mathematica","fun","god","graphql",
  "cl","psc","ll","applescript","cbl","php","r","vh","dylan","pm","pp","groovy",
  "awk","wlua","fish","vxml","wiki","emacs","ch","pl","vhw","ec","kml","cl","e",
  "doh","ktm","xql","ashx","sch","mask","rebol","apl","sbt","tea","uno","smali",
  "rake","sparql","ps1","krl","stTheme","rhtml","ls","pwn","f90","xacro","reds",
  "xht","x","t","hqf","ditamap","lidr","xliff","man","xsp.metadata","csh","fan",
  "mss","j","edn","mu","litcoffee","mirah","yrl","nix","zone","wl","rbtbar","m",
  "5","lid","shen","sublime-syntax","kid","mll","nproj","vhdl","r3","perl","rg",
  "swift","cpp-objdump","cljs.hl","sci","wsgi","go","xm","mod","axml","sas","1",
  "bb","cr","cob","vbhtml","cdf","xtend","dpr","ascx","sass","ux","lhtml","hcl",
  "axs","yap","spin","gs","pb","oxh","xhtml","sj","E","asm","vark","yml","cfml",
  "cy","jsp","ps1xml","rbres","bsv","pig","zsh","3qt","las","mao","plist","lsp",
  "glade","rl","asd","nbp","ms","tmux","omgrofl","pkb","plt","ms","c","command",
  "psc1","vho","ck","mm","storyboard","cats","opencl","kit","fx","pasm","forth",
  "nc","ino","pro","el","vim","inc","sublime-mousemap","php3","sc","kts","urdf",
  "golo","desktop","plsql","es","rs.in","pod","cfg","rbxs","fpp","dfm","lookml",
  "sld","js","phps","vapi","g","vba","nit","cl2","ik","xojo_script","tmCommand",
  "rktl","gradle","prefs","lfe","gs","cmake.in","idr","asax","ml4","es","json5",
  "cl","escript","phtml","geom","capnp","filters","al","8","adoc","fcgi","frag",
  "xquery","xojo_report","pck","io","sublime-workspace","dcl","ihlp","3","fcgi",
  "cake","pov","mkd","pd","ditaval","org","plb","zep","rbx","fancypack","mumps",
  "json","axi","markdown","cljs","mcr","st","yy","pony","iss","nb","darcspatch",
  "rbbas","mediawiki","haml","reb","csproj","liquid","v","boot","sublime-build",
  "asmx","lasso9","podspec","cljx","txl","glf","lua","_coffee","6pm","tu","plx",
  "cppobjdump","mmk","urs","scpt","pyp","ado","gap","zimpl","vhost","hxx","icl",
  "fshader","numsc","ms","dyalog","frx","p6m","sql","lvproj","bbx","l","fsproj",
  "fy","eliom","fcgi","matlab","slim","scaml","v","gd","cp","nse","stan","zcml",
  "pluginspec","raw","dtx","pp","rmd","ox","yaml-tmlanguage","smt2","ecl","ltx",
  "arpa","jsonld","fcgi","xproj","jsb","d","sqf","eliomi","oxygene","axd","sls",
  "plot","sql","pkl","xsjslib","gemspec","rq","sql","decls","inl","monkey","sh",
  "3x","lslp","ls","vert","erb.deface","bas","sh-session","ts","d","ssjs","mat",
  "hsc","ahkl","2","hic","cpy","grace","grt","fr","rpy","xi","vht","dockerfile",
  "scss","ru","mata","toc","pluginspec","bf","pmod","h","handlebars","gml","ts",
  "c++","inc","gp","fs","myt","qbs","lsl","gsx","xsjs","hh","owl","c++-objdump",
  "shader","m","gi","dpatch","hxsl","aux","lmi","x3d","xib","6","fsx","cs","bb",
  "wxl","ksh","nsi","t","x10","mir","sp","bmx","rst","mdpolicy","gshader","ivy",
  "ins","rdf","ceylon","hats","4","rest.txt","latte","vala","inc","frag","sage",
  "lasso","cproject","frm","sats","odd","flux","hs","chpl","tml","bf","sty","f",
  "mli","lisp","no","ni","rdoc","mak","bat","lock","rbuild","jinja","psd1","kt",
  "c++objdump","tm","ML","gsp","for","gco","nut","rkt","c-objdump","vcl","yaml",
  "intr","brd","m","fr","moo","zmpl","fsi","bones","opa","eps","sql","j","psgi",
  "click","eclass","csv","mako","dats","m4","fs","rviz","vb","mspec","ccp","mo",
  "inc","m","cjsx","bash","po","pro","less","pas","lds","r2","cgi","vssettings",
  "tool","inc","logtalk","1in","hrl","meta","ini","ipf","ph","pro","asc","lisp",
  "tst","cbx","bro","rbw","desktop.in","hpp","svg","sublime-project","boo","ly",
  "idc","inc","py","eclxml","adb","nl","p6","nsh","upc","w","xaml","tst","phpt",
  "irclog","mt","pks","ant","cfc","tf","pogo","vsh","lbx","fcgi","xlf","lasso8",
  "nasm","rpy","patch","moon","jake","metal","tex","html.hl","nu","4th","ipynb",
  "sc","aj","pxi","tmTheme","asset","gv","creole","jsm","topojson","roff","lpr",
  "cljc","xs","sublime-commands","sagews","eex","st","cmd","self","asp","irbrc",
  "pls","as","es6","psm1","exs","bzl","do","numpyw","red","epj","tmPreferences",
  "chs","rs","m","9","3in","ipp","props","purs","l","sh.in","cgi","dotsettings",
  "ampl","kicad_pcb","iml","ddl","pyt","axs.erb","cirru","pan","sublime-keymap",
  "eh","duby","f03","jade","h++","osm","rest","sublime-completions","pod","mxt",
  "sml","lean","dot","frt","xproc","apacheconf","l","gml","lagda","prefab","pl",
  "hlsl","inc","di","i7x","cmake","fsh","geojson","ecl","db2","mawk","vhi","nb",
  "smt","anim","mkii","pro","maxproj","cls","lgt","wxs","nuspec","wxi","mkfile",
  "bib","7",}

# a gzipped tarball containing icon files
_icons_fh = BytesIO(r"""begin 666 -
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
5!"S[P08VL(%-)-O_`[FGV>8`6`(`
`
end""".encode())

# uudecode the gzipped tarball of icons into `_icons_dec`
_icons_dec = BytesIO()
uu.decode(_icons_fh, _icons_dec)
_icons_dec.seek(0)

# uncompress `_icons_dec` into `_icons_uc`
_icons_uc = tarfile.open(None, "r:gz", _icons_dec)

# create a mapping that maps a filename to its binary content
icon_map = {}
for icon in _icons_uc.getmembers():
  i_name = basename(icon.name)
  i_name = i_name[:i_name.rfind(".")]
  icon_map[i_name] = _icons_uc.extractfile(icon).read()

# delete useless artifacts
del _icons_fh, _icons_dec, _icons_uc


class DirItem:
  def __init__(self, path:PathLike):
    self.path = path

    self._isdir = isdir(path)
    self._basename = basename(path)
    self._rawsize = getsize(path)
    self._rawlastmod = datetime.fromtimestamp(getmtime(path))

    self.name = self._basename + ("/" if self._isdir else "")
    self.href = f"./{self._basename}"
    self.lastmod = self._rawlastmod.strftime(r"%Y-%m-%d %H:%M")
    self.alt = "[DIR]" if self._isdir else "[   ]"
    self.size = sizeof_fmt(self._rawsize) if not self._isdir else "  - "
    self.mime = mimetype(self.path)

  @property
  def icon(self):
    name = self._basename
    ext  = name.split(".")[-1]

    if self.mime in mimedict:                return mimedict[self.mime]
    if re.match(r"^readme.*$", name, re.I):  return "alert.black.gif"
    if re.match(r"^license.*$", name, re.I): return "quill.gif"
    if ext in {"md", "rst"}:                 return "a.gif"
    if re.match(r"^text\/x-.+$", self.mime): return "script.gif"
    if ext in proglang_exts:                      return "script.gif"
    if re.match(r"^text.+$", self.mime):     return "text.gif"
    if re.match(r"^image.+$", self.mime):    return "image2.gif"
    if re.match(r"^audio.+$", self.mime):    return "sound1.gif"
    if re.match(r"^video.+$", self.mime):    return "movie.gif"

    return "generic.gif"


def render_dirview(path, basepath, iconpath, baserelative, urlpath, address_bar,
                   column="name", ascending=True):
  listing = []
  for x in sorted(listdir(path)):
    try: listing.append(DirItem(os.path.join(path, x)))
    except Exception: ...

  sort_key_dict = defaultdict(lambda: (lambda x:x._basename), {
    "size":    lambda x:x._rawsize if not x._isdir else 0,
    "lastmod": lambda x:x._rawlastmod,
    "name":    lambda x:x._basename
  })

  sort_key = sort_key_dict[column]

  listing.sort(key=sort_key, reverse=not ascending)

  is_base = realpath(path) != realpath(basepath)
  return listing_template.render(
    fullpath=path,
    icons=iconpath,
    is_base=is_base,
    baserelative=baserelative,
    listing=listing,
    urlpath=urlpath,
    address_bar=address_bar,
    ordering={
      "size":    "0" if (column == "size" and ascending) else "1",
      "lastmod": "0" if (column == "lastmod" and ascending) else "1",
      "name":    "0" if (column == "name" and ascending) else "1"
    })


class DirView:
  __slots__ = ["app", "fpath", "vpath", "_uid", "_imgfnptr", "_dirfnptr"]

  def __init__(self, app:Union[Flask, Blueprint], folder_path:PathLike,
               view_path:str):
    self.app = app
    self.fpath = folder_path
    self.vpath = view_path

    is_static = self.vpath == self.app.static_url_path

    self._uid = hex(randint(0x11111111, 0xFFFFFFFF))[2:]

    __func = compile(dedent(rf"""
    def __imgget{self._uid}(name):
      if name not in icon_map: return "", 404
      resp = make_response(icon_map[name])
      resp.headers.set("Content-Type", "image/gif")
      return resp
    """), "<string>", "exec", optimize=2)
    exec(__func)
    self._imgfnptr = locals()[f"__imgget{self._uid}"]

    icon_rule = f"/__{self._uid}/icons/<name>.gif"
    self.app.add_url_rule(icon_rule, None, self._imgfnptr)

    __func = compile(dedent(rf"""
    def __srvdir{self._uid}(filename):
      dirpath = os.path.join({self.fpath!r}, filename)

      if not os.path.exists(dirpath):
        return "<h1>Path doesn't exist</h1>", 404
      if not is_subdir({self.fpath!r}, dirpath):
        return "<h1>Path out of bounds</h1>", 403
      if not os.access(dirpath, os.R_OK):
        return "<h1>Permission denied</h1>",  403
      if isfile(dirpath):
        return send_file(dirpath)

      column = request.args.get("col", "name")
      ascending = request.args.get("asc", "1") == "1"

      return render_dirview(
        path=dirpath,               # full path `/home/foo/.config/bar`
        basepath={self.fpath!r},    # base path `/home/foo`
        baserelative=filename,      # relative `.config/bar`
        iconpath="/__{self._uid}/icons",
        urlpath=os.path.join({self.vpath!r}, filename),
        address_bar=get_adress_info(),
        column=column,
        ascending=ascending,)
    """), "<string>", "exec", optimize=2)
    exec(__func)
    self._dirfnptr = locals()[f"__srvdir{self._uid}"]

    _homefunc = partial(self._dirfnptr, "")
    setattr(_homefunc, "__name__", f"__srvhome{self._uid}")

    dir_rule = os.path.join(self.vpath, "<path:filename>")
    self.app.add_url_rule(dir_rule, None, self._dirfnptr)
    self.app.add_url_rule(f"{self.vpath}", None, _homefunc) # handle `basedir/`
    self.app.add_url_rule(f"{self.vpath}/", None, _homefunc)# and `basedir`

    if is_static: # what the fuck??
      self.app.view_functions["static"] = self._dirfnptr
      # a partial function would be nicer
      # but this works. don't touch it.

  def __repr__(self):
    return f"DirView({self.vpath} -> {self.fpath})"

  def __eq__(self, other) -> bool:
    return all([
      self.app == other.app,
      self.fpath == other.fpath,
      self.vpath == other.vpath,
    ])

  def __ne__(self, other) -> bool:
    return not self == other

if __name__ == "__main__":
  import webbrowser, threading
  app = flask.Flask("DirViewer")

  user = expanduser("~")
  DirView(app, user, f"/{basename(user)}")

  @app.get("/")
  def index():
    return f"""
    <h1>Welcome to flask_dirview demo.</h1>
    go to <a href="/{basename(user)}">/{basename(user)}</a>
    """

  threading.Thread(target=app.run, kwargs={"port":9898}).start()
  webbrowser.open("http://localhost:9898")