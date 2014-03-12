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
    url = os.path.abspath(url) # TODO is this right for real url ??
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
        self.heads = []
        self.remotes = []
        self.tags = []

    def __str__(self):
        return '<Commit:%s parents:%s heads:%s remotes:%s tags:%s "%s">' % (
                    self.sha[:7],
                    [p[:7] for p in self.parents],
                    self.heads,
                    self.remotes,
                    self.tags,
                    self.title[:20])

    def is_a_merge(self):
        return len(self.parents) > 1

class Status(object):
    def __init__(self):
        self.mods = []
        self.mods_staged = []
        self.untr = []
        self.ahead = 0
        self.textual = ''

    @property
    def is_clean(self):
        return (len(self.mods)+len(self.mods_staged)+len(self.untr) == 0)

### Base class for backends ###################################################
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
    def url(self):
        raise NotImplementedError("name not implemented in backend")

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

    @property
    def tags(self):
        raise NotImplementedError("tags not implemented in backend")


    def request_commits(self, done_cb, prog_cb, max_count=100, skip=0):
        raise NotImplementedError("request_commits() not implemented in backend")

    def request_diff(self, done_cb, prog_cb, max_count=0, commit1=None, commit2=None):
        raise NotImplementedError("request_diff() not implemented in backend")

    def request_changes(self, done_cb, commit1=None, commit2=None):
        raise NotImplementedError("request_changes() not implemented in backend")

### Git backend ###############################################################
class GitCmd(Exe):
    def __init__(self, local_path, cmd, done_cb=None, line_cb=None, *args):
        self.done_cb = done_cb
        self.line_cb = line_cb
        self.args = args
        self.lines = []

        git_dir = os.path.join(local_path, '.git')
        real_cmd = 'git --git-dir="%s" --work-tree="%s" %s' % \
                   (git_dir, local_path, cmd)

        print("GITCMD: %s" % cmd)
        Exe.__init__(self, real_cmd, ECORE_EXE_PIPE_READ | ECORE_EXE_PIPE_READ_LINE_BUFFERED)
        self.on_data_event_add(self.event_data_cb)
        self.on_del_event_add(self.event_del_cb)

    def event_data_cb(self, exe, event):
        if callable(self.line_cb):
            for line in event.lines:
                self.line_cb(line, *self.args)
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
        self._tags = []

    def check_url(self, url):
        if url and os.path.isdir(os.path.join(url, '.git')):
            return True
        return False

    def load_from_url(self, url, done_cb, *args):
        if url.endswith(os.sep):
            url = url[:-len(os.sep)]

        self._url = url
        self._name = self._url.split(os.sep)[-1]
        desc_file = os.path.join(self._url, '.git', 'description')
        self._description = file_get_contents(desc_file)
        if self._description.startswith('Unnamed repository'):
            self._description = ''

        self.refresh(done_cb, *args)

    def refresh(self, done_cb, *args):
        def _multi_done_cb(success, *args):
            self._op_count -= 1
            if self._op_count == 0:
                done_cb(True, *args)

        self._status = Status()
        self._op_count = 4
        self._fetch_status(_multi_done_cb, *args)
        self._fetch_status_text(_multi_done_cb, *args)
        self._fetch_branches(_multi_done_cb, *args)
        self._fetch_tags(_multi_done_cb, *args)

    def _fetch_status(self, done_cb, *args):
        def _cmd_done_cb(lines):
            if len(lines) < 1 and not lines[0].startswith('## '):
                done_cb(False)
                return

            branch = lines.pop(0)[3:]
            if '...' in branch:
                spl = branch.split('...')
                branch = spl[0]
                self._status.ahead = int(''.join([s for s in spl[1] if s.isdigit()]))
            self._current_branch =  branch

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

    def _fetch_status_text(self, done_cb, *args):
        def _cmd_done_cb(lines):
            self._status.textual = '<br>'.join(lines)
            done_cb(True, *args)
        GitCmd(self._url, 'status', done_cb=_cmd_done_cb)

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

    def _fetch_tags(self, done_cb, *args):
        def _cmd_done_cb(lines):
            self._tags = lines
            done_cb(True, *args)
        GitCmd(self._url, 'tag', _cmd_done_cb)

    @property
    def url(self):
        return self._url

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
            self.refresh(done_cb, *args)
        cmd = "checkout %s" % (branch)
        GitCmd(self._url, cmd, _cmd_done_cb)

    @property
    def branches(self):
        return self._branches

    @property
    def tags(self):
        return self._tags

    def request_commits(self, done_cb, prog_cb, max_count=100, skip=0):

        def _cmd_done_cb(lines, lines_buf):
            done_cb()

        def _cmd_line_cb(line, lines_buf):
            lines_buf.append(line)
            if line and line[-1] == chr(0x03):
                _parse_commit('\n'.join(lines_buf)[:-1])
                del lines_buf[:]

        def _parse_commit(buf):
            c = Commit()
            (c.sha, c.parents, c.author, c.author_email, c.commit_date,
                c.title, c.message, refs) = buf.split(chr(0x00))
            if c.parents:
                c.parents = c.parents.split(' ')
            if c.commit_date:
                c.commit_date = datetime.fromtimestamp(int(c.commit_date))
            if refs:
                refs = refs.strip().strip(')(').split(', ')
                for ref in refs:
                    if ref.startswith('refs/tags/'):
                        c.tags.append(ref[10:])
                    elif ref == 'HEAD':
                        c.heads.append(ref)
                    elif ref.startswith(('refs/heads/')):
                        c.heads.append(ref[11:])
                    elif ref.startswith('refs/remotes/'):
                        c.remotes.append(ref[13:])
                    else:
                        c.heads.append(ref) # TODO REMOVE ME
                        LOG("UNKNOWN REF: %s" % ref)
            prog_cb(c)
        
        # fmt = 'format:{"sha":"%H", "parents":"%P", "author":"%an",
        #                "author_email":"%ae", "commit_ts":%ct, "title":"%s",
        #                "body": "%b", "refs":"%d"}'
        # Use ascii char 00 as field separator and char 03 as commits separator
        fmt = '%x00'.join(('%H','%P','%an','%ae','%ct','%s','%b','%d')) + '%x03'
        cmd = "log --pretty='tformat:%s' --decorate=full --all -n %d" % (fmt, max_count)
        if skip > 0: cmd += ' --skip %d' % skip
        GitCmd(self._url, cmd, _cmd_done_cb, _cmd_line_cb, list())

    def request_diff(self, done_cb, prog_cb, max_count=100,
                           commit1=None, commit2=None, path=None):
        cmd = 'diff'
        if commit2 and commit2.sha and commit1 and commit1.sha:
            cmd += ' %s %s' % (commit1.sha, commit2.sha)
        if commit1 is not None and commit1.sha:
            cmd += ' %s^ %s' % (commit1.sha, commit1.sha)
        if path is not None:
            cmd += ' -- %s' % path
        GitCmd(self._url, cmd, done_cb, prog_cb)

    def request_changes(self, done_cb, commit1=None, commit2=None):
        def _cmd_done_cb(lines):
            L = [ line.split('\t') for line in lines ]
            # A: addition of a file
            # C: copy of a file into a new one
            # D: deletion of a file
            # M: modification of the contents or mode of a file
            # R: renaming of a file
            # T: change in the type of the file
            # U: file is unmerged (you must complete the merge before it can be committed)
            # X: "unknown" change type (most probably a bug, please report it)

            # TODO handle move, rename (unmerged ??)
            
            done_cb(True, L)

        cmd = 'diff --name-status'
        if commit2 and commit2.sha and commit1 and commit1.sha:
            cmd += ' %s %s' % (commit1.sha, commit2.sha)
        elif commit1 is not None and commit1.sha:
            cmd += ' %s^ %s' % (commit1.sha, commit1.sha)
        else:
            cmd += ' HEAD'
        GitCmd(self._url, cmd, _cmd_done_cb)

