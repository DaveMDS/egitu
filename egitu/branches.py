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

from __future__ import absolute_import, print_function

from efl.evas import Rectangle
from efl.elementary.window import DialogWindow
from efl.elementary.entry import Entry, utf8_to_markup
from efl.elementary.box import Box
from efl.elementary.button import Button
from efl.elementary.list import List
from efl.elementary.genlist import Genlist, GenlistItemClass
from efl.elementary.separator import Separator
from efl.elementary.frame import Frame
from efl.elementary.popup import Popup
from efl.elementary.icon import Icon
from efl.elementary.label import Label
from efl.elementary.radio import Radio
from efl.elementary.table import Table
from efl.elementary.check import Check

from egitu.utils import ErrorPopup, \
    EXPAND_BOTH, FILL_BOTH, EXPAND_HORIZ, FILL_HORIZ


class BranchesDialog(DialogWindow):
    def __init__(self, app):
        self.app = app
        self.selected_branch = None

        DialogWindow.__init__(self, app.win, 'Egitu-branches', 'Branches',
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
        li.callback_selected_add(self._list_selected_cb)
        vbox.pack_end(li)
        li.show()
        self.branches_list = li

        # buttons
        hbox = Box(self, horizontal=True,
                   size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_BOTH)
        vbox.pack_end(hbox)
        hbox.show()

        ic = Icon(self, standard='git-branch')
        bt = Button(self, text='Create', content=ic)
        bt.callback_clicked_add(lambda b: CreateBranchPopup(self, app))
        hbox.pack_end(bt)
        bt.show()

        ic = Icon(self, standard='user-trash')
        bt = Button(self, text='Delete', content=ic)
        bt.callback_clicked_add(lambda b: DeleteBranchPopup(self, self.app,
                                                    self.selected_branch.name))
        hbox.pack_end(bt)
        bt.show()
        self.delete_btn = bt

        ic = Icon(self, standard='git-merge')
        bt = Button(self, text='Merge', content=ic)
        bt.callback_clicked_add(lambda b: MergeBranchPopup(self, app, 
                                                    self.selected_branch.name))
        hbox.pack_end(bt)
        bt.show()
        self.merge_btn = bt

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
        for b in self.app.repo.branches:
            if b.is_tracking:
                label = '{} → {}/{}'.format(b.name, b.remote, b.remote_branch)
            else:
                label = b.name
            if b.is_current:
                end = Icon(self, standard='arrow-left')
                selected = True
            else:
                end = None
                selected = False
            icon = Icon(self, standard='git-branch')
            it = self.branches_list.item_append(label, icon, end)
            it.data['Branch'] = b
            it.selected = selected

        self.branches_list.go()
    
    def _list_selected_cb(self, li, it):
        self.selected_branch = it.data['Branch']
        if self.selected_branch.is_current:
            self.delete_btn.disabled = True
            self.merge_btn.disabled = True
        else:
            self.delete_btn.disabled = False
            self.merge_btn.disabled = False


class MergeBranchPopup(Popup):
    def __init__(self, parent, app, branch):
        self.app = app
        self.branch = branch

        Popup.__init__(self, parent)
        self.part_text_set('title,text', 'Merge branch')
        self.part_content_set('title,icon', Icon(self, standard='git-merge'))

        box = Box(self)
        self.content = box
        box.show()

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        box.pack_end(sep)
        sep.show()

        # info entry
        text = 'We are going to merge branch:<br><hilight>%s</hilight><br><br>' \
               'into current branch:<br><hilight>%s</hilight><br><br>' \
               '<info>Note:</info> No commit will be performed, ' \
               'you will need to manually commit after the merge.' % \
                (self.branch, app.repo.current_branch.name)
        if not app.repo.status.is_clean:
            text += '<br><br><warning>Warning:</warning> The current status is not clean, ' \
                    'I suggested to only merge in a clean status, or you can make a mess.'
        en = Entry(self, editable=False, text=text,
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        box.pack_end(en)
        en.show()

        # fast forward ?
        rdg = Radio(self, state_value=0, text='Fast Forward when possible',
                    size_hint_align=(0.0, 0.5))
        box.pack_end(rdg)
        rdg.show()
        self.ff_rdg = rdg

        rd = Radio(self, state_value=1, text='Never Fast Forward',
                   size_hint_align=(0.0, 0.5))
        rd.group_add(rdg)
        box.pack_end(rd)
        rd.show()

        rd = Radio(self, state_value=2, text='Fast Forward Only',
                   size_hint_align=(0.0, 0.5))
        rd.group_add(rdg)
        box.pack_end(rd)
        rd.show()

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        box.pack_end(sep)
        sep.show()

        # buttons
        bt = Button(self, text='Close')
        bt.callback_clicked_add(lambda b: self.delete())
        self.part_content_set('button1', bt)
        bt.show()

        ic = Icon(self, standard='git-merge')
        bt = Button(self, text='Merge', content=ic)
        bt.callback_clicked_add(self._merge_clicked_cb)
        self.part_content_set('button2', bt)
        bt.show()

        #
        self.show()
    
    def _merge_clicked_cb(self, btn):
        if self.ff_rdg.value == 0:
            ff = 'ff'
        elif self.ff_rdg.value == 1:
            ff = 'no-ff'
        elif self.ff_rdg.value == 2:
            ff = 'ff-only'
        self.app.repo.branch_merge(self._merge_done_cb, self.branch, ff)

    def _merge_done_cb(self, success, err_msg=None):
        self.app.action_update_header()
        if success:
            self.delete()
            self.app.action_update_dag()
        else:
            ErrorPopup(self.parent, msg=utf8_to_markup(err_msg))


class CreateBranchPopup(Popup):
    def __init__(self, parent, app, branch=None):
        self.app = app

        Popup.__init__(self, parent)
        self.part_text_set('title,text', 'Create a new local branch')
        self.part_content_set('title,icon', Icon(self, standard='git-branch'))

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
        self.itc = GenlistItemClass(item_style='one_icon',
                                    text_get_func=self._gl_text_get,
                                    content_get_func=self._gl_content_get)
        li = Genlist(self, homogeneous=True,
                     size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
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
            for b in self.app.repo.branches:
                item_data = (b.name, 'git-branch')
                self.rev_list.item_append(self.itc, item_data)

        # remote tracking branches
        for bname in self.app.repo.remote_branches:
            item_data = (bname, 'git-branch')
            self.rev_list.item_append(self.itc, item_data)

        # tags
        if not only_tracking:
            for tag in self.app.repo.tags:
                item_data = (tag, 'git-tag')
                self.rev_list.item_append(self.itc, item_data)

    def _gl_text_get(self, li, part, item_data):
        label, icon = item_data
        return label

    def _gl_content_get(self, li, part, item_data):
        label, icon = item_data
        return Icon(li, standard=icon)

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

        self.app.repo.branch_create(self._branch_created_cb, name, rev,
                                 track=True if self.type_radio.value else False)

    def _branch_created_cb(self, success, err_msg=None):
        if success:
            self.parent.populate() # update branches dialog list
            self.app.action_update_header() # update main win header
            self.delete()
        else:
            ErrorPopup(self.parent, msg=err_msg)


class DeleteBranchPopup(Popup):
    def __init__(self, parent, app, branch):
        self.app = app
        self.branch = branch

        Popup.__init__(self, parent)
        self.part_text_set('title,text', 'Delete branch')
        self.part_content_set('title,icon',
                              Icon(self, standard='user-trash'))

        # main vertical box
        box = Box(self)
        self.content = box
        box.show()

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        box.pack_end(sep)
        sep.show()

        # label
        en = Entry(self, editable=False,
                   text='%s<br><br><hilight>%s</hilight><br>' % (
                        'Are you sure you want to delete this branch?', branch),
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        box.pack_end(en)
        en.show()

        # force checkbox
        ck = Check(self, text='Force delete (even if not fully merged)',
                   size_hint_expand=EXPAND_BOTH, size_hint_align=(0.0, 0.5))
        box.pack_end(ck)
        ck.show()
        self.force_chk = ck

        # buttons
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        box.pack_end(sep)
        sep.show()

        bt = Button(self, text='Cancel')
        bt.callback_clicked_add(lambda b: self.delete())
        self.part_content_set('button1', bt)
        bt.show()

        bt = Button(self, text='Delete branch')
        bt.callback_clicked_add(self._delete_btn_cb)
        self.part_content_set('button2', bt)
        bt.show()

        #
        self.show()

    def _delete_btn_cb(self, btn):
        self.app.repo.branch_delete(self._branch_deleted_cb, self.branch,
                                    force=self.force_chk.state)

    def _branch_deleted_cb(self, success, err_msg=None):
        if success:
            self.parent.populate() # update branches dialog list
            self.app.action_update_header() # update main win header
            self.delete()
        else:
            ErrorPopup(self, msg=err_msg)

