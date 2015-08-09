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

from efl.elementary.entry import Entry, utf8_to_markup, ELM_WRAP_NONE
from efl.elementary.window import DialogWindow
from efl.elementary.panes import Panes
from efl.elementary.list import List
from efl.elementary.box import Box
from efl.elementary.button import Button
from efl.elementary.separator import Separator
from efl.elementary.frame import Frame
from efl.elementary.popup import Popup
from efl.elementary.table import Table
from efl.elementary.label import Label
from efl.elementary.icon import Icon

from egitu.utils import WaitPopup, ErrorPopup, \
    EXPAND_BOTH, FILL_BOTH, EXPAND_HORIZ, FILL_HORIZ


class RemotesDialog(DialogWindow):
    def __init__(self, repo, win):
        self.repo = repo

        DialogWindow.__init__(self, win, 'egitu-remotes', 'Remotes', 
                              autodel=True, size=(600,400))

        # main vertical box (inside a padding frame)
        fr = Frame(self, style='pad_medium', size_hint_weight=EXPAND_BOTH)
        self.resize_object_add(fr)
        fr.show()

        box = Box(fr, padding=(6,6))
        fr.content = box
        box.show()
        
        # panes
        panes = Panes(box, content_left_size=0.25,
                      size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        box.pack_end(panes)
        panes.show()
        
        # remotes List (on the left)
        li = List(panes)
        li.callback_selected_add(self._list_selected_cb)
        panes.part_content_set('left', li)
        li.show()
        self.remotes_list = li

        # remote info entry (on the right)
        en = Entry(panes, scrollable=True, editable=False,
                   line_wrap=ELM_WRAP_NONE)
        en.part_text_set('guide', 'Choose a remote from the list.')
        panes.part_content_set('right', en)
        en.show()
        self.info_entry = en

        # botton bar
        hbox = Box(box, horizontal=True, 
                   size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_BOTH)
        box.pack_end(hbox)
        hbox.show()

        bt = Button(hbox, text='Add')
        bt.callback_clicked_add(lambda b: RemoteAddPopup(self, self.repo))
        hbox.pack_end(bt)
        bt.show()

        bt = Button(hbox, text='Remove')
        bt.callback_clicked_add(self._remove_btn_cb)
        hbox.pack_end(bt)
        bt.show()

        bt = Button(hbox, text='Refresh')
        bt.callback_clicked_add(lambda b: self.restart_dialog())
        hbox.pack_end(bt)
        bt.show()

        sep = Separator(hbox, size_hint_expand=EXPAND_HORIZ)
        hbox.pack_end(sep)

        bt = Button(hbox, text='Close')
        bt.callback_clicked_add(lambda b: self.delete())
        hbox.pack_end(bt)
        bt.show()

        # request remotes (while showing a wait popup)
        self.restart_dialog()
        self.show()

    def restart_dialog(self):
        self.info_entry.text = None
        self.repo.request_remotes(self._remotes_cb)
        self.wait_popup = WaitPopup(self)
        
    def _remotes_cb(self, success, remotes, err_msg=None):
        self.wait_popup.delete()
        if success:
            self.remotes_list.clear()
            for r in remotes:
                self.remotes_list.item_append(r, Icon(self, standard='git-remote'))
            self.remotes_list.go()
        else:
             self.info_entry.text = '<code>%s</code>' % utf8_to_markup(err_msg)
    
    def _list_selected_cb(self, list, item):
        self.wait_popup = WaitPopup(self, text='Fetching remote info...')
        self.repo.request_remote_info(self._remote_info_cb, item.text)
    
    def _remote_info_cb(self, success, info, err_msg=None):
        self.wait_popup.delete()
        if success:
            self.info_entry.text = '<code>%s</code>' % utf8_to_markup(info)
        else:
            self.info_entry.text = '<code>%s</code>' % utf8_to_markup(err_msg)

    def _remove_btn_cb(self, bt):
        item = self.remotes_list.selected_item
        if not item:
            ErrorPopup(self, title='No remote selected',
                       msg='You must select a remote to delete.')
        else:
            self.repo.remote_del(self._del_done_cb, item.text)
    
    def _del_done_cb(self, success, err_msg=None):
        self.restart_dialog()


class RemoteAddPopup(Popup):
    def __init__(self, parent, repo):
        self.repo = repo

        Popup.__init__(self, parent)
        self.part_text_set('title,text', 'Add remote')

        tb = Table(self, padding=(3,3), size_hint_expand=EXPAND_BOTH)
        self.content = tb
        tb.show()

        # name
        lb = Label(tb, text='Name')
        tb.pack(lb, 0, 0, 1, 1)
        lb.show()

        en = Entry(tb, editable=True, single_line=True, scrollable=True,
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        en.part_text_set('guide', 'Name for the new remote')
        en.callback_changed_user_add(lambda e: self.err_unset())
        tb.pack(en, 1, 0, 1, 1)
        en.show()
        self.name_entry = en

        # url
        lb = Label(tb, text='URL')
        tb.pack(lb, 0, 1, 1, 1)
        lb.show()

        en = Entry(tb, editable=True, single_line=True, scrollable=True,
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        en.part_text_set('guide', 'git://git.example.com/repo.git')
        en.callback_changed_user_add(lambda e: self.err_unset())
        tb.pack(en, 1, 1, 1, 1)
        en.show()
        self.url_entry = en

        # error label
        lb = Label(tb, text='', size_hint_expand=EXPAND_HORIZ)
        tb.pack(lb, 0, 2, 2, 1)
        lb.show()
        self.error_label = lb

        # buttons
        bt = Button(self, text='Cancel')
        bt.callback_clicked_add(lambda b: self.delete())
        self.part_content_set('button1', bt)
        bt.show()

        bt = Button(self, text='Add remote')
        bt.callback_clicked_add(self._add_btn_cb)
        self.part_content_set('button2', bt)
        bt.show()

        self.show()

    def err(self, text):
        self.error_label.text = 'ERROR: ' + text
    
    def err_unset(self):
        self.error_label.text = ''

    def _add_btn_cb(self, btn):
        name = self.name_entry.text
        url = self.url_entry.text

        if not name: # TODO check name not exists already
            self.err('Invalid name')
            return

        if not url: # TODO check url is valid
            self.err('Invalid url')
            return

        # create the remote
        self.repo.remote_add(self._add_done_cb, name, url)
        
    def _add_done_cb(self, success, err_msg=None):
        self.parent.restart_dialog()
        self.delete()
