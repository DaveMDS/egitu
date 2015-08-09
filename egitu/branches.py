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

from efl.elementary.window import DialogWindow
from efl.elementary.entry import Entry
from efl.elementary.box import Box
from efl.elementary.button import Button
from efl.elementary.list import List
from efl.elementary.separator import Separator
from efl.elementary.frame import Frame

from egitu.utils import EXPAND_BOTH, FILL_BOTH, EXPAND_HORIZ, FILL_HORIZ


class BranchesDialog(DialogWindow):
    def __init__(self, repo, win):
        self.repo = repo
        # self.win = win

        DialogWindow.__init__(self, win, 'Egitu-branches', 'Branches', 
                              size=(500,500), autodel=True)

        # main vertical box (inside a padding frame
        vbox = Box(self, padding=(0, 6), size_hint_weight=EXPAND_BOTH,
                   size_hint_align=FILL_BOTH)
        fr = Frame(self, style='pad_medium', size_hint_weight=EXPAND_BOTH)
        self.resize_object_add(fr)
        fr.content = vbox
        fr.show()
        vbox.show()

        # title
        en = Entry(self, editable=False,
                   text='<title><align=center>%s</align></title>' % 'Local branches',
                   size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_HORIZ)
        vbox.pack_end(en)
        en.show()

        # list
        li = List(self, size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        vbox.pack_end(li)

        for bname, branch in repo.branches.iteritems():
            if branch.is_tracking:
                li.item_append('{} → {}/{}'.format(bname, branch.remote, branch.remote_branch))
            else:
                li.item_append(bname)

        li.show()
        li.go()

    
        # buttons
        hbox = Box(self, horizontal=True,
                   size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_BOTH)
        vbox.pack_end(hbox)
        hbox.show()
        
        bt = Button(self, text='Add (TODO)')
        hbox.pack_end(bt)
        bt.show()
        
        bt = Button(self, text='Delete (TODO)')
        hbox.pack_end(bt)
        bt.show()
        
        bt = Button(self, text='Rename (TODO)')
        hbox.pack_end(bt)
        bt.show()
        
        sep = Separator(self, size_hint_expand=EXPAND_HORIZ)
        hbox.pack_end(sep)

        bt = Button(self, text='Close')
        bt.callback_clicked_add(lambda b: self.delete())
        hbox.pack_end(bt)
        bt.show()
        
        #
        self.show()
