#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2014 Davide Andreoli <dave@gurumeditation.it>
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

from efl.elementary.entry import Entry, ELM_WRAP_NONE, ELM_WRAP_MIXED
from efl.elementary.window import StandardWindow
from efl.elementary.box import Box
from efl.elementary.panes import Panes
from efl.elementary.button import Button

from egitu.utils import DiffedEntry, EXPAND_BOTH, FILL_BOTH, \
    EXPAND_HORIZ, FILL_HORIZ


class CommitDialog(StandardWindow):
    def __init__(self, repo):
        StandardWindow.__init__(self, 'Egitu', 'Egitu', autodel=True)

        vbox = Box(self, size_hint_weight=EXPAND_BOTH,
                   size_hint_align=FILL_BOTH)
        self.resize_object_add(vbox)
        vbox.show()

        # title
        en = Entry(self, editable=False,
                   text='<title><align=center>Commit changes</align></title>',
                   size_hint_weight=EXPAND_HORIZ, size_hint_align=FILL_HORIZ)
        vbox.pack_end(en)
        en.show()

        panes = Panes(self, content_left_size = 0.2, horizontal=True,
                      size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        vbox.pack_end(panes)
        panes.show()
        
        # message entry
        en = Entry(self, editable=True, scrollable=True,
                   size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        en.part_text_set('guide', 'Enter commit message here')
        panes.part_content_set("left", en)
        en.show()

        # diff entry
        self.diff_entry = DiffedEntry(self)
        panes.part_content_set("right", self.diff_entry)
        self.diff_entry.show()

        # buttons
        hbox = Box(self, horizontal=True, size_hint_weight=EXPAND_HORIZ,
                   size_hint_align=FILL_HORIZ)
        vbox.pack_end(hbox)
        hbox.show()

        bt = Button(self, text="Cancel")
        bt.callback_clicked_add(lambda b: self.delete())
        hbox.pack_end(bt)
        bt.show()

        bt = Button(self, text="Commit", disabled=True)
        hbox.pack_end(bt)
        bt.show()

        # show the window and give focus to the editable entry
        self.size = 500, 500
        self.show()
        en.focus = True

        # load the diff
        repo.request_diff(self.diff_done_cb, None, only_staged=True)

    def diff_done_cb(self, lines):
        self.diff_entry.lines_set(lines)
