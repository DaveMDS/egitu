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
from efl.elementary.entry import Entry, utf8_to_markup, ELM_WRAP_NONE
from efl.elementary.window import DialogWindow
from efl.elementary.box import Box
from efl.elementary.table import Table
from efl.elementary.button import Button
from efl.elementary.separator import Separator
from efl.elementary.frame import Frame
from efl.elementary.genlist import Genlist, GenlistItemClass
from efl.elementary.icon import Icon
from efl.elementary.popup import Popup
from efl.elementary.radio import Radio

from egitu.utils import ErrorPopup, \
    EXPAND_BOTH, EXPAND_HORIZ, EXPAND_VERT, FILL_BOTH, FILL_HORIZ, FILL_VERT


class TagsDialog(DialogWindow):
    def __init__(self, parent, app):
        self.app = app

        DialogWindow.__init__(self, parent, 'Egitu-tags', 'Tags',
                              size=(350,350), autodel=True)

        # main vertical box (inside a padding frame)
        vbox = Box(self, padding=(0, 6), size_hint_weight=EXPAND_BOTH,
                   size_hint_align=FILL_BOTH)
        fr = Frame(self, style='pad_medium', size_hint_weight=EXPAND_BOTH)
        self.resize_object_add(fr)
        fr.content = vbox
        fr.show()
        vbox.show()

        # title
        en = Entry(self, editable=False, single_line=True,
                   text='<title>%s</title>' % 'Tags',
                   size_hint_expand=EXPAND_HORIZ)
        vbox.pack_end(en)
        en.show()

        # tag list
        self.itc = GenlistItemClass(item_style='one_icon',
                                    text_get_func=self._gl_text_get,
                                    content_get_func=self._gl_content_get)
        li = Genlist(self, homogeneous=True,
                     size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        li.callback_selected_add(self._list_selected_cb)
        vbox.pack_end(li)
        li.show()
        self.tags_list = li

        # buttons
        hbox = Box(self, horizontal=True,
                   size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_BOTH)
        vbox.pack_end(hbox)
        hbox.show()


        bt = Button(self, text='Create', content=Icon(self, standard='git-tag'))
        bt.callback_clicked_add(lambda b: CreateTagPopup(self, self.app))
        hbox.pack_end(bt)
        bt.show()

        bt = Button(self, text='Delete', content=Icon(self, standard='user-trash'))
        bt.callback_clicked_add(self._delete_clicked_cb)
        hbox.pack_end(bt)
        bt.show()
        self.delete_btn = bt

        bt = Button(self, text='Checkout')
        bt.callback_clicked_add(self._checkout_clicked_cb)
        hbox.pack_end(bt)
        bt.show()
        self.checkout_btn = bt

        sep = Separator(self, size_hint_expand=EXPAND_HORIZ)
        hbox.pack_end(sep)

        bt = Button(self, text='Close')
        bt.callback_clicked_add(lambda b: self.delete())
        hbox.pack_end(bt)
        bt.show()

        #
        self.populate()
        self.show()

    def populate(self):
        self.tags_list.clear()
        self.delete_btn.disabled = True
        self.checkout_btn.disabled = True

        for tag in reversed(self.app.repo.tags): # TODO: perform a better sort
            self.tags_list.item_append(self.itc, tag)

        if self.tags_list.items_count == 0:
            self.tags_list.item_append(self.itc, None).disabled = True

    def _list_selected_cb(self, li, it):
        self.delete_btn.disabled = False
        self.checkout_btn.disabled = False

    def _gl_text_get(self, li, part, tag):
        return tag or 'No tags present'

    def _gl_content_get(self, li, part, tag):
        return Icon(li, standard='git-tag') if tag else None

    def _checkout_clicked_cb(self, btn):
        tag = self.tags_list.selected_item.data
        self.app.repo.checkout(self._checkout_done_cb, tag)

    def _checkout_done_cb(self, success, err_msg=None):
        if success:
            self.app.action_update_all()
            self.delete()
        else:
            ErrorPopup(self, 'Checkout Failed', utf8_to_markup(err_msg))

    def _delete_clicked_cb(self, btn):
        tag = self.tags_list.selected_item.data
        self.app.repo.tag_delete(self._delete_done_cb, tag)

    def _delete_done_cb(self, success, err_msg=None):
        if success:
            self.app.action_update_all()
            self.populate()
        else:
            ErrorPopup(self, 'Delete Failed', utf8_to_markup(err_msg))


class CreateTagPopup(Popup):
    def __init__(self, parent, app):
        self.app = app

        Popup.__init__(self, parent)
        self.part_text_set('title,text', 'Create tag')
        self.part_content_set('title,icon', Icon(self, standard='git-tag'))

        # main vertical box
        tb = Table(self, padding=(4,4),
                    size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        self.content = tb
        tb.show()

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        tb.pack(sep, 0, 0, 2, 1)
        sep.show()

        # tag name
        en = Entry(self, single_line=True, scrollable=True,
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        en.part_text_set('guide', 'Type the tag name, ex: v1.15.0')
        en.callback_changed_user_add(self._something_changed_cb)
        tb.pack(en, 0, 1, 2, 1)
        en.show()
        self.name_entry  = en

        # annotated or light
        rdg = Radio(self, state_value=1, value=1, text='Annotated',
                    size_hint_expand=EXPAND_BOTH)
        rdg.callback_changed_add(self._annotated_radio_changed_cb)
        rdg.callback_changed_add(self._something_changed_cb)
        tb.pack(rdg, 0, 2, 1, 1)
        rdg.show()
        self.annotated_radio  = rdg

        rd = Radio(self, state_value=0, text='Lightweight',
                   size_hint_expand=EXPAND_BOTH)
        rd.callback_changed_add(self._annotated_radio_changed_cb)
        rd.callback_changed_add(self._something_changed_cb)
        rd.group_add(rdg)
        tb.pack(rd, 1, 2, 1, 1)
        rd.show()

        # message entry
        en = Entry(self, scrollable=True,
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        en.part_text_set('guide', 'Type a message for the tag')
        en.callback_changed_user_add(self._something_changed_cb)

        r = Rectangle(self.evas, size_hint_min=(200,150),
                      size_hint_expand=EXPAND_BOTH)
        tb.pack(r, 0, 3, 2, 1)
        tb.pack(en, 0, 3, 2, 1)
        en.show()
        self.msg_entry  = en

        # buttons
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        tb.pack(sep, 0, 4, 2, 1)
        sep.show()

        bt = Button(self, text='Cancel')
        bt.callback_clicked_add(lambda b: self.delete())
        self.part_content_set('button1', bt)
        bt.show()

        bt = Button(self, text='Create', disabled=True,
                    content=Icon(self, standard='git-tag'))
        bt.callback_clicked_add(self._create_clicked_cb)
        self.part_content_set('button2', bt)
        bt.show()
        self.create_btn = bt

        #
        self.name_entry.focus = True
        self.show()

    def _something_changed_cb(self, obj):
        disable = False
        if self.annotated_radio.value == 1:
            if not self.msg_entry.text or not self.name_entry.text:
                disable = True
        else:
            if not self.name_entry.text:
                disable = True
        self.create_btn.disabled = disable

    def _annotated_radio_changed_cb(self, radio):
        if radio.value == 1:
            self.msg_entry.disabled = False
            self.msg_entry.text = None
        else:
            self.msg_entry.disabled = True
            self.msg_entry.text = 'No message needed for lightweight tags'

    def _create_clicked_cb(self, btn):
        name = self.name_entry.text
        annotated = True if self.annotated_radio.value == 1 else False
        msg = self.msg_entry.text

        self.app.repo.tag_create(self._create_done_cb, name, annotated, msg)

    def _create_done_cb(self, success, err_msg=None):
        if success:
            self.app.action_update_all()
            self.parent.populate()
            self.delete()
        else:
            ErrorPopup(self.parent, err_msg)

