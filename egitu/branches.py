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

from efl.evas import Rectangle
from efl.elementary.window import DialogWindow
from efl.elementary.entry import Entry
from efl.elementary.box import Box
from efl.elementary.button import Button
from efl.elementary.list import List
from efl.elementary.separator import Separator
from efl.elementary.frame import Frame
from efl.elementary.popup import Popup
from efl.elementary.icon import Icon
from efl.elementary.label import Label
from efl.elementary.radio import Radio
from efl.elementary.table import Table

from egitu.utils import theme_resource_get, ErrorPopup, \
    EXPAND_BOTH, FILL_BOTH, EXPAND_HORIZ, FILL_HORIZ


class BranchesDialog(DialogWindow):
    def __init__(self, repo, win):
        self.repo = repo
        self.win = win

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
        li.show()
        self.branches_list = li

        # buttons
        hbox = Box(self, horizontal=True,
                   size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_BOTH)
        vbox.pack_end(hbox)
        hbox.show()

        bt = Button(self, text='Create')
        bt.callback_clicked_add(lambda b: CreateBranchPopup(self, self.repo))
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

        # populate the list and show the dialog
        self.populate()
        self.show()

    def populate(self):
        self.branches_list.clear()
        for bname, b in self.repo.branches.iteritems():
            if b.is_tracking:
                label = '{} → {}/{}'.format(b.name, b.remote, b.remote_branch)
            else:
                label = bname
            icon = Icon(self, file=theme_resource_get('branch.png'))
            self.branches_list.item_append(label, icon)
        self.branches_list.go()


class CreateBranchPopup(Popup):
    def __init__(self, parent, repo, branch=None):
        self.repo = repo

        Popup.__init__(self, parent)
        self.part_text_set('title,text', 'Create a new local branch')
        self.part_content_set('title,icon',
                              Icon(self, file=theme_resource_get('branch.png')))

        # main table
        # TODO padding should be (4,4) but it seems buggy for colspan > 1
        tb = Table(self, padding=(0,4),
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        self.content = tb
        tb.show()

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        tb.pack(sep, 0, 0, 2, 1)
        sep.show()

        # branch name
        lb = Label(self, text='Branch name', size_hint_align=(0.0, 0.5))
        tb.pack(lb, 0, 1, 1, 1)
        lb.show()

        en = Entry(self, single_line=True, scrollable=True,
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        tb.pack(en, 1, 1, 1, 1)
        en.show()
        self.name_entry = en

        # branch type
        lb = Label(self, text='Branch type', size_hint_align=(0.0, 0.5))
        tb.pack(lb, 0, 2, 1, 1)
        lb.show()

        hbox = Box(self, horizontal=True, padding=(6,0),
                   size_hint_expand=EXPAND_BOTH, size_hint_align=(0.0, 0.5))
        tb.pack(hbox, 1, 2, 1, 1)
        hbox.show()

        rdg = Radio(self, state_value=0, text='Local branch')
        rdg.callback_changed_add(self._type_radio_changed_cb)
        hbox.pack_end(rdg)
        rdg.show()

        rd = Radio(self, state_value=1, text='Tracking branch')
        rd.callback_changed_add(self._type_radio_changed_cb)
        rd.group_add(rdg)
        hbox.pack_end(rd)
        rd.show()
        
        self.type_radio = rdg

        # starting revision
        fr = Frame(self, text='Starting revision',
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        tb.pack(fr, 0, 3, 2, 1)
        fr.show()

        r = Rectangle(self.evas, size_hint_min=(300,200),
                      size_hint_expand=EXPAND_BOTH)
        tb.pack(r, 0, 3, 2, 1)

        # TODO: use genlist to speedup population
        li = List(self, size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        li.callback_selected_add(self._revision_selected_cb)
        fr.content = li
        li.show()
        self.rev_list = li

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        tb.pack(sep, 0, 4, 2, 1)
        sep.show()

        # buttons
        hbox = Box(self, horizontal=True,
                   size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_BOTH)
        tb.pack(hbox, 0, 5, 2, 1)
        hbox.show()

        bt = Button(self, text='Close')
        bt.callback_clicked_add(lambda b: self.delete())
        hbox.pack_end(bt)
        bt.show()

        sep = Separator(self, size_hint_expand=EXPAND_HORIZ)
        hbox.pack_end(sep)

        bt = Button(self, text='Create')
        bt.callback_clicked_add(self._create_clicked_cb)
        hbox.pack_end(bt)
        bt.show()

        # populate the revision list and show the popup
        self.populate()
        self.show()
        self.name_entry.focus = True

    def populate(self, only_tracking=False):
        self.rev_list.clear()

        # local branches
        if not only_tracking:
            for bname in self.repo.branches_names:
                ic = Icon(self, file=theme_resource_get('branch.png'))
                self.rev_list.item_append(bname, ic)

        # remote tracking branches
        for bname in self.repo.remote_branches_names:
            ic = Icon(self, file=theme_resource_get('branch.png'))
            self.rev_list.item_append(bname, ic)

        # tags
        if not only_tracking:
            for tag in self.repo.tags:
                self.rev_list.item_append(tag) # TODO: add tags icon

        self.rev_list.go()

    def _type_radio_changed_cb(self, chk):
        self.populate(only_tracking=True if chk.state_value else False)

    def _revision_selected_cb(self, li, it):
        name = it.text
        if '/' in name:
            self.name_entry.text = name.split('/')[-1]

    def _create_clicked_cb(self, bt):
        name = self.name_entry.text
        if not name:
            ErrorPopup(self.parent, msg='Invalid branch name')
            return

        if not self.rev_list.selected_item:
            ErrorPopup(self.parent, msg='You must select a starting revision')
            return
        rev = self.rev_list.selected_item.text

        self.repo.branch_create(self._branch_created_cb, name, rev,
                                track=True if self.type_radio.value else False)

    def _branch_created_cb(self, success, err_msg=None):
        if success:
            self.parent.populate() # update branches dialog list
            self.parent.win.update_header() # update main win header
            self.delete()
        else:
            ErrorPopup(self.parent, msg=err_msg)
