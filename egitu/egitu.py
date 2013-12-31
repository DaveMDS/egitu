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

import os
import sys
import argparse

from efl import elementary as elm
from egitu_vcs import repo_factory
from egitu_gui_win import EgituWin


def load_done_cb(success, repo):
    print("==="*9)
    print("name: %s" % repo.name)
    print("desc: %s" % repo.description)
    print("current_branch: %s" % repo.current_branch)
    print("branches: %s" % repo.branches)
    print("status_is_clean: %s" % repo.status.is_clean)
    print("status_mods: %s" % repo.status.mods)
    print("status_mods_staged: %s" % repo.status.mods_staged)
    print("status_untr: %s" % repo.status.untr)
    win = EgituWin(repo)


def main():

    parser = argparse.ArgumentParser(description='Efl GIT GUI')
    parser.add_argument('--repo', default=None)
    # parser.add_argument('integers', metavar='N', type=int, nargs='+',
                   # help='an integer for the accumulator')
    # parser.add_argument('--sum', dest='accumulate', action='store_const',
                   # const=sum, default=max,
                   # help='sum the integers (default: find the max)')
    args = parser.parse_args()
    

    url = args.repo if args.repo else os.getcwd()
    repo = repo_factory(url)
    if not repo:
        # TODO ask with the gui
        return 1

    repo.load_from_url(url, load_done_cb, repo)
    elm.init()
    elm.run()
    elm.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())



"""
class GitGraph(ClippedSmartObject):
    def __init__(self, parent, *args, **kargs):
        self.theme = theme_resource_get('main.edj')
        # self.commits = []
        self.points = []
        self.lines = []
        self.parent_obj = parent
        self.canvas = parent.evas
        self._rowh = 30
        self._colw = 20
        self._lins = 5
        self._cols = [(), (100, 0, 0, 100), (0, 100, 0, 100)]
        ClippedSmartObject.__init__(self, self.canvas, *args, **kargs)

        l = self.Line(geometry=(0, 0, 100, 100), color=(0, 0, 200, 200))
        # self.member_add(l)
        l.show()

        # self.populate()

    def populate(self):
        # {'f9b7f0d...': [(int col_num, int row_num), (...)]}
        reservations = {}

        l = self.Line(geometry=(0, 0, 100, 100), color=(200, 200, 200, 200))
        # self.member_add(l)
        l.show()
        
        
        cols = col = row = 1
        for commit in repo.commits('master', n=30):
            if row == 1:
                self.point_add(commit, 5, 0)
                
            if commit.sha in reservations:
                # child_row, child_col = reservations.pop(commit.sha)[-1]
                # col = child_col

                for child_row, child_col in reservations.pop(commit.sha):
                    col = child_col # TODO FIXME
                    self.line_add(child_row, child_col, row, col)

            else:
                col = cols
                cols += 1

            if commit.parent:
                if commit.parent in reservations:
                    reservations[commit.parent].append((row, col))
                else:
                    reservations[commit.parent] = [(row, col)]

            self.point_add(commit, row, col)
            row += 1

            # print(reservations)

        # print(reservations)


    def clear(self):
        for l in self.lines + self.points:
            self.member_del(l)
            l.delete()
        self.lines = []
        self.points = []
        
        
    def update(self):
        # self.clear()
        self.populate()

    # def move(self, x, y):
        # print("move", x, y)
        # ClippedSmartObject.move(self, x, y)
        # for l in self.lines + self.points:
            # l.pos = x + l.pos[0], y + l.pos[1]
        
    def resize(self, w, h):
        print("resize", w, h)
        # self.size = (w, h)
        # self.pos = 200, 200
        print("size", self.size[0], self.size[1])
        # self.size_hint_min = 600, 2000
        # pass

    def line_add(self, row1, col1, row2, col2):
        
        print ("LINE", row1, col1, row2, col2)
        x = self._colw * col1 - self._lins / 2
        y = self._rowh * row1
        w = self._lins
        h = (row2 - row1) * self._rowh

        if col1 != col2:
            y -= self._rowh

            l = self.Line(geometry=(self._colw * col1, self._rowh * row1,
                                    self._colw * col2, self._rowh * row2),
                          color=(200, 200, 200, 200))
            # self.member_add(l)
            # l.lower()
            l.show()
        
        l = self.Rectangle(geometry=(x, y, w, h), color=self._cols[col1])
        # self.member_add(l)
        self.lines.append(l)
        l.lower()
        l.show()
        
    def point_add(self, commit, row, col):
        print(commit)
        # print(str(commit.refs))
        # self.commits.append(commit)
        
        
        r = Edje(self.evas, file=self.theme, group='egitu/graph/item')
        self.member_add(r)
        self.points.append(r)
        r.signal_callback_add("mouse,in", "*", self.point_mouse_in_cb, commit)
        r.signal_callback_add("mouse,out", "*", self.point_mouse_out_cb, commit)
        # if len(self.commits)<2:
        for ref in commit.refs:
            # if ref == 'HEAD':
                # r.signal_emit('head,show', 'egitu')
                # pass
            # if not ref.startswith('origin/'):
                # r.part_text_set('label.text', ref)
                # r.signal_emit('label,show', 'egitu')
            # else:
            if 1:
                print("TAGGG", ref)
                l = Layout(self.parent_obj, file=(self.theme, 'egitu/graph/tag'))
                
                l.part_text_set('tag.text', ref)
                l.show()
                r.part_box_append('tag.box', l)
        
        r.pos = col * self._colw, row * self._rowh
        r.show()

    def point_mouse_in_cb(self, obj, signal, source, commit):
        if not 'popup_obj' in obj.data:
            obj.data['popup_obj'] = CommitPopup(self.parent_obj, commit)

    def point_mouse_out_cb(self, obj, signal, source, commit):
        if 'popup_obj' in obj.data:
            obj.data['popup_obj'].delete()
            del obj.data['popup_obj']
"""
