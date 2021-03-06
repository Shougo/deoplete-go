import json
import os
import re
import subprocess

from .base import Base


class Source(Base):

    def __init__(self, vim):
        Base.__init__(self, vim)

        self.name = 'go'
        self.mark = '[go]'
        self.filetypes = ['go']
        self.input_pattern = r'[^. \t0-9]\.\w*'

        try:
            self.sort_class = self.vim.vars['deoplete#sources#go#sort_class']
        except Exception:
            self.sort_class = None

    def get_complete_position(self, context):
        m = re.search(r'\w*$', context['input'])
        return m.start() if m else -1

    def gather_candidates(self, context):
        line = self.vim.current.window.cursor[0]
        column = context['complete_position']

        buf = self.vim.current.buffer
        buf_path = buf.name
        offset = self.ByteOffset(buf, line) + (column - 1)
        source = '\n'.join(buf).encode()

        process = subprocess.Popen([self.GoCodeBinary(),
                                    '-f=json',
                                    'autocomplete',
                                    buf_path,
                                    str(offset)],
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   start_new_session=True)
        process.stdin.write(source)
        stdout_data, stderr_data = process.communicate()
        result = json.loads(stdout_data.decode('utf-8'))

        out = []
        if not self.sort_class == None:
            # TODO(zchee): Why not work with this?
            #              class_dict = {}.fromkeys(self.sort_class, [])
            class_dict = {
                'package': [],
                'func': [],
                'type': [],
                'var': [],
                'const': [],
            }
        try:
            for complete in result[1]:
                word = complete['name']
                _class = complete['class']

                if _class == 'package':
                    word += '.'
                elif _class == 'func':
                    word += '('
                elif re.match(r'\[\]', complete['type']):
                    word += '['

                candidates = dict(word=word,
                                  abbr=complete['name'],
                                  kind='{:5}'.format(_class) +
                                  complete['type'].replace('func', ''),
                                  info=complete['type'],
                                  icase=1,
                                  dup=1
                                  )
                if self.sort_class == None:
                    out.append(candidates)
                else:
                    class_dict[_class].append(candidates)

            # append with sort by complete['class']
            if not self.sort_class == None:
                for c in self.sort_class:
                    for x in class_dict[c]:
                        out.append(x)

            return out
        except Exception:
            return []

    def ByteOffset(self, buf, line):
        offset = 0
        cursor_line = 1
        if line == 1:
            return 1
        for i, byte in enumerate(buf):
            if cursor_line == line:
                offset += 1
                break
            else:
                offset += (len(str(byte)) + 1)
                cursor_line += 1
        return offset

    def GoCodeBinary(self):
        try:
            binary_path = self.vim.vars['deoplete#sources#go#gocode_binary']
            if binary_path:
                if os.path.isfile(binary_path):
                    return binary_path
                else:
                    return None
        except Exception:
            return self.FindBinaryPath('gocode')

    def FindBinaryPath(self, cmd):
        def is_exec(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        fpath, fname = os.path.split(cmd)
        if fpath:
            if is_exec(cmd):
                return cmd
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                binary = os.path.join(path, cmd)
                if is_exec(binary):
                    return binary
        return None
