#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2014-2015 Davide Andreoli <dave@gurumeditation.it>
#
# This file is part of Egitu.
#
# Egitu is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# Egitu is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Egitu.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import

import os
import sys
import argparse

from efl import elementary as elm
from efl.elementary.theme import theme_extension_add
from egitu.utils import options, config_path, theme_file_get
from egitu.gui import EgituWin, RepoSelector


def main():

    # parse command line arguments
    parser = argparse.ArgumentParser(description='Efl GIT GUI')
    parser.add_argument('--repo', default=None)
    # parser.add_argument('integers', metavar='N', type=int, nargs='+',
                   # help='an integer for the accumulator')
    # parser.add_argument('--sum', dest='accumulate', action='store_const',
                   # const=sum, default=max,
                   # help='sum the integers (default: find the max)')
    args = parser.parse_args()

    # load config and create necessary folders
    options.load()
    if not os.path.exists(config_path):
        os.makedirs(config_path)

    # create the main window
    elm.init()
    theme_extension_add(theme_file_get())
    win = EgituWin()

    # try to load a repo, from command-line or cwd (else show the RepoSelector)
    RepoSelector(win, args.repo or os.getcwd())

    # enter the mainloop
    elm.run()

    # mainloop done, shutdown
    elm.shutdown()
    options.save()

    return 0


if __name__ == "__main__":
    sys.exit(main())

