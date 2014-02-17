
EFL Git user interface
==================

 TODO #1: find a better name


## Features ##

* Draw the DAG of the repo
* View the diff of each revision
* Edit repository description
* Switch branch


## Requirements ##

* Python 2.7 or higher
* Python-EFL 1.8 or higher
* python modules: efl, xdg


## Installation ##

* Run directly from the repo (without installing):

 `python egitu/egitu.py`

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
