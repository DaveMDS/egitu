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

from __future__ import absolute_import, print_function, unicode_literals


from efl import elementary as elm
from efl.elementary.box import Box
from efl.elementary.entry import Entry
from efl.elementary.icon import Icon
from efl.elementary.label import Label
from efl.elementary.menu import Menu
from efl.elementary.genlist import Genlist, GenlistItemClass, \
    ELM_GENLIST_ITEM_GROUP, ELM_GENLIST_ITEM_TREE

from egitu.vcs import Branch, Tag, StashItem
from egitu.utils import \
    EXPAND_BOTH, EXPAND_HORIZ, EXPAND_VERT, FILL_BOTH, FILL_HORIZ, FILL_VERT


class WorkingCopyItemClass(GenlistItemClass):
    def __init__(self, app):
        self.app = app
        GenlistItemClass.__init__(self, item_style='default')

    def text_get(self, gl, part, item_data):
        return 'Local status'

    def content_get(self, gl, part, item_data):
        if part == 'elm.swallow.icon':
            return Icon(gl, standard='git-commit')
        elif self.app.repo.status.changes and part == 'elm.swallow.end':
            return Label(gl, #editable=False, single_line=True,
                    text='<name>{}</name>'.format(len(self.app.repo.status.changes)))

class HistoryItemClass(GenlistItemClass):
    def __init__(self, app):
        self.app = app
        GenlistItemClass.__init__(self, item_style='default')

    def text_get(self, gl, part, item_data):
        return 'Full history'

    def content_get(self, gl, part, item_data):
        if part == 'elm.swallow.icon':
            return Icon(gl, standard='git-history')

class EmptyItemClass(GenlistItemClass):
    def __init__(self, app):
        self.app = app
        GenlistItemClass.__init__(self, item_style='no_icon')

    def text_get(self, gl, part, item_data):
        return 'No items'

class TreeItemClass(GenlistItemClass):
    def __init__(self, app):
        self.app = app
        GenlistItemClass.__init__(self, item_style='full')

    def content_get(self, gl, part, item_data):
        if item_data == 'STASHES':
            count = len(self.app.repo.stash)
        elif item_data == 'BRANCHES':
            count = len(self.app.repo.branches)
        elif item_data == 'TAGS':
            count = len(self.app.repo.tags)
        elif item_data == 'REMOTES':
            count = len(self.app.repo.remotes)

        box = Box(gl, horizontal=True,
                  size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_HORIZ)

        lb = Label(gl, text='<align=left><b>{}</b></align>'.format(item_data),
                   size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_HORIZ)
        box.pack_end(lb)
        lb.show()

        lb = Entry(gl, editable=False, single_line=True,
                   text='<name>{}</name>'.format(count))
        box.pack_end(lb)
        lb.show()

        return box

class StashItemClass(GenlistItemClass):
    def __init__(self, app):
        self.app = app
        GenlistItemClass.__init__(self, item_style='one_icon')

    def text_get(self, gl, part, si):
        return si.desc

    def content_get(self, gl, part, branch):
        return Icon(gl, standard='git-stash')

class BranchItemClass(GenlistItemClass):
    def __init__(self, app):
        self.app = app
        GenlistItemClass.__init__(self, item_style='default')

    def text_get(self, gl, part, branch):
        return branch.name

    def content_get(self, gl, part, branch):
        if part == 'elm.swallow.icon':
            return Icon(gl, standard='git-branch')

        if branch == self.app.repo.status.current_branch:
            return Icon(gl, standard='git-head')

class TagItemClass(GenlistItemClass):
    def __init__(self, app):
        self.app = app
        GenlistItemClass.__init__(self, item_style='one_icon')

    def text_get(self, gl, part, tag):
        return tag.name

    def content_get(self, gl, part, tag):
        return Icon(gl, standard='git-tag')

class RemoteItemClass(GenlistItemClass):
    def __init__(self, app):
        self.app = app
        GenlistItemClass.__init__(self, item_style='one_icon')

    def text_get(self, gl, part, remote):
        return remote.name

    def content_get(self, gl, part, remote):
        return Icon(gl, standard='git-remote')

class RemoteBranchItemClass(GenlistItemClass):
    def __init__(self, app):
        self.app = app
        GenlistItemClass.__init__(self, item_style='one_icon')

    def text_get(self, gl, part, remote_branch):
        return '/'.join(remote_branch.split('/')[1:])

    def content_get(self, gl, part, remote_branch):
        return Icon(gl, standard='git-branch')


class RepoTree(Genlist):
    def __init__(self, parent, app):
        self.app = app
        self._ignore_next_selection = False
        self._itc_wcopy = WorkingCopyItemClass(app)
        self._itc_history = HistoryItemClass(app)
        self._itc_empty = EmptyItemClass(app)
        self._itc_tree = TreeItemClass(app)
        self._itc_branch = BranchItemClass(app)
        self._itc_tag = TagItemClass(app)
        self._itc_stash = StashItemClass(app)
        self._itc_remote = RemoteItemClass(app)
        self._itc_remote_branch = RemoteBranchItemClass(app)

        Genlist.__init__(self, parent, homogeneous=False,
                         select_mode=elm.ELM_OBJECT_SELECT_MODE_ALWAYS)
        self.callback_expand_request_add(self._expand_request_cb)
        self.callback_contract_request_add(self._contract_request_cb)
        self.callback_selected_add(self._selected_cb)
        self.callback_clicked_right_add(self._clicked_right_cb)

    def populate(self):
        self.clear()
        self.item_append(self._itc_wcopy, 'LOCAL')
        self.item_append(self._itc_history, 'FULLHIST')
        self.item_append(self._itc_tree, 'STASHES', flags=ELM_GENLIST_ITEM_TREE) \
                        .select_mode = elm.ELM_OBJECT_SELECT_MODE_NONE
        self.item_append(self._itc_tree, 'BRANCHES', flags=ELM_GENLIST_ITEM_TREE) \
                        .select_mode = elm.ELM_OBJECT_SELECT_MODE_NONE
        self.item_append(self._itc_tree, 'TAGS', flags=ELM_GENLIST_ITEM_TREE) \
                        .select_mode = elm.ELM_OBJECT_SELECT_MODE_NONE
        self.item_append(self._itc_tree, 'REMOTES', flags=ELM_GENLIST_ITEM_TREE) \
                        .select_mode = elm.ELM_OBJECT_SELECT_MODE_NONE

    def unselect_local(self):
        item = self.selected_item
        if item and item.data == 'LOCAL':
            item.selected = False

    def _expand_request_cb(self, gl, item):
        c = 0
        if item.data == 'STASHES':
            for si in self.app.repo.stash:
                self.item_append(self._itc_stash, si, item)
                c += 1
        elif item.data == 'BRANCHES':
            for b in self.app.repo.branches:
                self.item_append(self._itc_branch, b, item)
                c += 1
        elif item.data == 'TAGS':
            for t in self.app.repo.tags:
                self.item_append(self._itc_tag, t, item)
                c += 1
        elif item.data == 'REMOTES':
            for r in self.app.repo.remotes:
                self.item_append(self._itc_remote, r, item,
                                 flags=ELM_GENLIST_ITEM_TREE)
                c += 1
        else: # remote branch
            remote = item.data
            for rb in self.app.repo.remote_branches:
                if rb.startswith(remote.name+'/'):
                    self.item_append(self._itc_remote_branch,
                                     rb, item)
                    c += 1
        if c == 0:
            self.item_append(self._itc_empty, None, item).disabled = True
        item.expanded = True

    def _contract_request_cb(self, gl, item):
        item.subitems_clear()
        item.expanded = False

    def _selected_cb(self, gl, item):
        if self._ignore_next_selection is True:
            self._ignore_next_selection = False
            return

        if item.data == 'LOCAL':
            self.app.action_show_local_status()
        elif item.data == 'FULLHIST':
            self.app.action_show_full_history()
        elif isinstance(item.data, Branch):
            self.app.action_show_branch(item.data)
        elif isinstance(item.data, Tag):
            self.app.action_show_tag(item.data)
        elif isinstance(item.data, StashItem):
            self.app.action_stash_show(item.data)

    def _clicked_right_cb(self, gl, item):
        if isinstance(item.data, StashItem):
            if not item.selected:
                self._ignore_next_selection = True
                item.selected = True
            SidebarStashMenu(self.app, item.data)



class SidebarStashMenu(Menu):
    def __init__(self, app, stash_item):
        self.app = app
        self.stash_item = stash_item
        
        Menu.__init__(self, app.win)
        self.item_add(None, stash_item.desc, 'git-stash').disabled = True
        self.item_separator_add()
        self.item_add(None, 'Show', None,
                      lambda m,i: self.app.action_stash_show_item(self.stash_item))
        self.item_add(None, 'Apply', None,
                      lambda m,i: self.app.action_stash_apply(self.stash_item))
        self.item_add(None, 'Pop (apply & delete)', None,
                      lambda m,i: self.app.action_stash_pop(self.stash_item))
        self.item_add(None, 'Branch & Delete', 'git-branch',
                      lambda m,i: self.app.action_stash_branch(self.stash_item))
        self.item_add(None, 'Delete', 'user-trash',
                      lambda m,i: self.app.action_stash_drop(self.stash_item))

        # show the menu at mouse position
        x, y = self.evas.pointer_canvas_xy_get()
        self.move(x + 2, y)
        self.show()
