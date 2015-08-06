
EFL Git user interface
==================


## Features ##

* Draw the **DAG** of the repo
* View the **diff** of each revision
* Edit repository **description**
* Switch **branch**
* **Stage/unstage** files
* **Commit** staged changes
* **Revert** commits (optionally autocommit the revert)
* Cool **Gravatar** integration

![Screenshot1](https://github.com/davemds/egitu/blob/master/data/screenshots/screenshot1.jpg)


## Requirements ##

* Python 2.7 or higher
* Python-EFL 1.13 or higher
* python modules: efl, xdg


## Installation ##

* For system-wide installation (needs administrator privileges):

 `(sudo) python setup.py install`

* For user installation:

 `python setup.py install --user`

* To install for different version of python:

 `pythonX setup.py install`

* Install with a custom prefix:

 `python setup.py install --prefix=/MY_PREFIX`

* To create distribution packages:

 `python setup.py sdist`


## License ##

GNU General Public License v3 - see COPYING
