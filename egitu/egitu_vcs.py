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
from datetime import datetime

from efl.ecore import Exe, ECORE_EXE_PIPE_READ, ECORE_EXE_PIPE_READ_LINE_BUFFERED

from egitu_utils import file_get_contents, file_put_contents


def LOG(text):
    print(text)
    # pass


def repo_factory(url):
    LOG("Trying to load a repo from: %s" % url)
    for cls in Repository.__subclasses__():
        backend = cls()
        if backend.check_url(url) is True:
            return backend
    LOG('ERROR: Cannot find a repo at: "%s"' % url)



class Commit(object):
    def __init__(self):
        self.sha = ""
        self.author = ""
        self.author_email = ""
        self.committer = ""
        self.title = ""
        self.message = ""
        self.commit_date = None
        self.parents = []
        self.refs = []

    def __str__(self):
        return '<Commit:%s parents:%s refs:%s "%s">' % (
                    self.sha[:7],
                    [p[:7] for p in self.parents],
                    self.refs,
                    self.title[:20])

    def is_a_merge(self):
        return len(self.parents) > 1


class Status(object):
    def __init__(self):
        self.mods = []
        self.mods_staged = []
        self.untr = []

    @property
    def is_clean(self):
        return (len(self.mods)+len(self.mods_staged)+len(self.untr) == 0)


class Repository(object):

    def check_url(self, url):
        # here implementation must check if url is a valid repo
        raise NotImplementedError("check_url() not implemented in backend")

    def load_from_url(self, url, done_cb, *args):
        # implementation fill basic repo info (name, desc, branches, tags, ...)
        raise NotImplementedError("load_from_url() not implemented in backend")

    def refresh(self, done_cb, *args):
        raise NotImplementedError("refresh not implemented in backend")

    @property
    def name(self):
        raise NotImplementedError("name not implemented in backend")

    def name_set(self, name, done_cb, *args):
        raise NotImplementedError("name_set() not implemented in backend")

    @property
    def description(self):
        raise NotImplementedError("description not implemented in backend")

    def description_set(self, description, done_cb, *args):
        raise NotImplementedError("description_set() not implemented in backend")

    @property
    def status(self):
        raise NotImplementedError("status() not implemented in backend")

    @property
    def current_branch(self):
        raise NotImplementedError("current_branch not implemented in backend")

    def current_branch_set(self, branch, done_cb, *args):
        raise NotImplementedError("current_branch_set() not implemented in backend")

    @property
    def branches(self):
        raise NotImplementedError("branches not implemented in backend")


    def request_commits(self, done_cb, prog_cb, max_count=100):
        raise NotImplementedError("request_commits() not implemented in backend")


    def request_diff(self, done_cb, prog_cb, max_count=0, commit1=None, commit2=None):
        raise NotImplementedError("request_diff() not implemented in backend")




class GitCmd(Exe):
    def __init__(self, local_path, cmd, done_cb=None, line_cb=None, *args):
        self.done_cb = done_cb
        self.line_cb = line_cb
        self.args = args
        self.lines = []

        git_dir = os.path.join(local_path, '.git')
        real_cmd = 'git --git-dir="%s" --work-tree="%s" %s' % \
                   (git_dir, local_path, cmd)

        print("CMD", real_cmd)
        Exe.__init__(self, real_cmd, ECORE_EXE_PIPE_READ | ECORE_EXE_PIPE_READ_LINE_BUFFERED)
        self.on_data_event_add(self.event_data_cb)
        self.on_del_event_add(self.event_del_cb)

    def event_data_cb(self, exe, event):
        print("Received %d lines" % len(event.lines))
        if callable(self.line_cb):
            for line in event.lines:
                self.line_cb(line)
        else:
            self.lines += event.lines

    def event_del_cb(self, exe, event):
        if callable(self.done_cb):
            self.done_cb(self.lines, *self.args)

class GitBackend(Repository):
    def __init__(self):
        self._url = ""
        self._name = ""
        self._description = ""
        self._status = None
        self._current_branch = ""
        self._branches = []

    def check_url(self, url):
        return True if os.path.isdir(os.path.join(url, '.git')) else False
        
    def load_from_url(self, url, done_cb, *args):
        url = os.path.abspath(url) # TODO is this right for real url ??
        if url.endswith(os.sep):
            url = url[:-len(os.sep)]

        self._url = url
        self._name = self._url.split(os.sep)[-1]
        desc_file = os.path.join(self._url, '.git', 'description')
        self._description = file_get_contents(desc_file)

        self.refresh(done_cb, *args)

    def refresh(self, done_cb, *args):
        def _multi_done_cb(success, *args):
            self._op_count -= 1
            if self._op_count == 0:
                done_cb(True, *args)
        self._op_count = 2
        self._fetch_status(_multi_done_cb, *args)
        self._fetch_branches(_multi_done_cb, *args)

    def _fetch_status(self, done_cb, *args):
        def _cmd_done_cb(lines):
            if len(lines) < 1 and not lines[0].startswith('## '):
                done_cb(False)
                return
            self._current_branch = lines.pop(0)[3:]

            self._status = Status()
            for line in lines:
                fname = line[3:]
                if line[1] == 'M': # ' M'
                    self._status.mods.append(fname)
                if line[0] == 'M': # 'M '
                    self._status.mods_staged.append(fname)
                if line.startswith('??'):
                    self._status.untr.append(fname)
                # TODO more status
            done_cb(True, *args)
        GitCmd(self._url, 'status --porcelain -b', done_cb=_cmd_done_cb)

    def _fetch_branches(self, done_cb, *args):
        def _cmd_done_cb(lines):
            L = []
            for branch in lines:
                if branch.startswith('* '):
                    L.append(branch[2:].strip())
                else:
                    L.append(branch.strip())
            self._branches = L
            done_cb(True, *args)
        GitCmd(self._url, 'branch', _cmd_done_cb)

    @property
    def name(self):
        return self._name

    # name_set(self, name, done_cb, *args) not implemented
    
    @property
    def description(self):
        return self._description

    def description_set(self, description, done_cb, *args):
        desc_file = os.path.join(self._url, '.git', 'description')
        if file_put_contents(desc_file, description) is True:
            self._description = description
            done_cb(True, *args)
        else:
            done_cb(False, *args)

    @property
    def status(self):
        return self._status

    @property
    def current_branch(self):
        return self._current_branch

    def current_branch_set(self, branch, done_cb, *args):
        def _cmd_done_cb(lines):
            # TODO check result
            print(lines)
            self._fetch_status(done_cb, *args)
        cmd = "checkout %s" % (branch)
        GitCmd(self._url, cmd, _cmd_done_cb)

    @property
    def branches(self):
        return self._branches

    def request_commits(self, done_cb, prog_cb, max_count=100):

        def _cmd_done_cb(lines):
            done_cb()

        def _cmd_line_cb(line):
            c = Commit()
            (c.sha, c.parents, c.author, c.author_email, c.commit_date,
                c.title, c.refs) = line.split(chr(0x00))
            if c.parents:
                c.parents = c.parents.split(' ')
            if c.commit_date:
                c.commit_date = datetime.fromtimestamp(int(c.commit_date))
            if c.refs:
                c.refs = c.refs.strip().strip(')(').split(', ')
            prog_cb(c)
        
        # fmt = 'format:{"sha":"%H", "parents":"%P", "author":"%an", "author_email":"%ae", "commit_ts":%ct, "title":"%s", "refs":"%d"}'
        fmt = '%x00'.join(('%H','%P','%an','%ae','%ct','%s','%d'))
        cmd = "log --pretty='format:%s' --all -n %d" % (fmt, max_count)
        GitCmd(self._url, cmd, _cmd_done_cb, _cmd_line_cb)

    def request_diff(self, done_cb, prog_cb, max_count=100, commit1=None, commit2=None):
        def _cmd_done_cb(lines):
            done_cb()
        def _cmd_line_cb(line):
            prog_cb(line)

        if commit1 is not None and commit1.sha:
            cmd = "diff %s^ %s" % (commit1.sha, commit1.sha)
        else:
            cmd = "diff"
        GitCmd(self._url, cmd, _cmd_done_cb, _cmd_line_cb)



