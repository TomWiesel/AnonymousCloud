from tkinter import *
import tkinter.ttk
from tkinter import simpledialog
import json
import os


class File_Explorer():
    def __init__(self, username, client, fernet, option, file_path=''):
        self.master = Tk()
        self.master.minsize(500, 300)
        self.master.title(username + '\'s encrypted Cloud')
        self.path_for_selected_file = file_path
        self.name_of_file_to_send = list(os.path.splitext(os.path.basename(file_path)))
        file = open(os.path.dirname(os.path.abspath(__file__)) + '\\filesystem.json', 'r+')
        self.filesystem = json.loads(file.read())
        file.close()
        self.username = username
        self.fernet = fernet
        self.client = client
        self.actions = {'<send>': self.send_file, '<receive>': self.receive_file}[option]
        self.client.send(self.fernet.encrypt(b'<success>'))
        self.s_filesys = self.update_list()
        self.state = '<fail>'
        self.createGUI()

    def start(self):
        self.master.mainloop()
        if self.state == '<fail>':
            self.client.send(self.fernet.encrypt(b'<fail>'))
        self.master.destroy()
        return self.state

    def createGUI(self):
        self.treeview = tkinter.ttk.Treeview(self.master, columns=('Filetype', 'Size', 'Path', 'Used'))
        for i in self.treeview['columns']:
            self.treeview.heading(i, text=i)
        self.refresh_tree(s_filesys=self.s_filesys, c_filesys=self.filesystem)
        self.treeview.bind('<Double-1>', self.actions)

        self.add_dir = tkinter.ttk.Button(self.master)
        self.add_dir['text'] = 'Create Directory'
        self.add_dir.bind('<Button-1>', self.create_dir)

        self.delete = tkinter.ttk.Button(self.master)
        self.delete['text'] = 'Delete'
        self.delete.bind('<Button-1>', self.delete_file)

        self.add_dir.pack(side=tkinter.BOTTOM)
        self.treeview.pack(side=tkinter.TOP, fill=tkinter.X)
        self.delete.pack(side=tkinter.BOTTOM)

        self.master.protocol('WM_DELETE_WINDOW', self.master.quit)

    def create_translator(self, s_folder, c_folder):
            translator = {}
            for i in s_folder:
                translator[c_folder[i]['name']] = {'name': i}
                if 'sub' in s_folder[i]:
                    translator[c_folder[i]['name']]['sub'] = self.create_translator(s_folder[i]['sub'], c_folder[i]['sub'])
                else:
                    translator[c_folder[i]['name']] = {'name': i}
            return translator

    def update_list(self):
        s_filesys = self.fernet.decrypt(self.client.recv(4096 * 20))
        if s_filesys == b'<fail>':
            print('Error')
            return 0
        else:
            s_filesys = json.loads(s_filesys.decode('utf-8'))
            self.translator = self.create_translator(s_filesys, self.filesystem)
            return s_filesys

    def refresh_tree(self, s_filesys, c_filesys, count=0,parent='', path=''):
        items = []
        if count == 0:
            root = self.treeview.insert(parent=parent, index=count, text=c_filesys['Filesys']['name'],values=(c_filesys['Filesys']['filetype'], str(round(s_filesys['Filesys']['size']/10**9,2)) + ' gb', '', str(round(s_filesys['Filesys']['used']/10**9, 2)) + ' gb'))
            self.refresh_tree(parent=root, c_filesys=c_filesys['Filesys']['sub'], s_filesys=s_filesys['Filesys']['sub'],path=path + '\\' + c_filesys['Filesys']['name'], count=1)
        else:
            for i in s_filesys:
                size = s_filesys[i]['size']
                if size < 1000:
                    size = str(size) + ' b'
                else:
                    if size < 10**6:
                        size = str(round(size/10**3)) + ' kb'
                    else:
                        if size < 10**9:
                            size = str(round(size/10**6)) + ' mb'
                        else:
                            size = str(round(size/10**9)) + ' gb'

                items.append(self.treeview.insert(parent=parent, index=count, text=c_filesys[i]['name'], values=(c_filesys[i]['filetype'], size, path)))
                if 'sub' in s_filesys[i]:
                    self.refresh_tree(parent=items[len(items) - 1], c_filesys=c_filesys[i]['sub'], s_filesys=s_filesys[i]['sub'], path=path+ '\\' + c_filesys[i]['name'], count=1)

    def send_file(self, e):
        if len(self.treeview.selection()) != 0:
            selection = self.get_select_file()
            selected_file = self.fernet.encrypt(b'<send>,<' + selection.encode()+ b'>')
            self.client.send(selected_file)
            filename = self.fernet.decrypt(self.client.recv(2048))
            if filename == b'<fail>':
                print('Please select a Directory')
                return ''

            translator = self.translator['Root']
            filesys = self.filesystem['Filesys']
            for i in self.path_list:
                filesys = filesys['sub'][translator['sub'][i]['name']]
                translator = translator['sub'][i]

            c_filename = self.name_of_file_to_send
            count = 0
            place = ''
            for i in filesys['sub']:
                if filesys['sub'][i]['name'] + filesys['sub'][i]['filetype'] == self.name_of_file_to_send[0] + place + self.name_of_file_to_send[1]:
                    count += 1
                    place = '(' + str(count) + ')'
            c_filename[0] += place

            if 'sub' in filesys:
                filesys['sub'][filename.decode('utf-8')] = {'name': c_filename[0], 'filetype': c_filename[1]}
            else:
                filesys['sub'] = {filename.decode('utf-8'): {'name': c_filename[0], 'filetype': c_filename[1]}}

            file = open(os.path.dirname(os.path.abspath(__file__)) + '\\filesystem.json', 'w')
            file.write(json.dumps(self.filesystem))
            file.close()
            self.state = '<success>'
            self.master.quit()

    def receive_file(self, e):
        if len(self.treeview.selection()) != 0:
            self.client.send(self.fernet.encrypt(b'<receive>,<' + self.get_select_file().encode()+ b'>'))
            if self.fernet.decrypt(self.client.recv(1024)) == b'<fail>':
                print('Can\'t receive directory!')
                return ''
            self.state = self.treeview.item(self.treeview.selection()[0])['text'] + self.treeview.item(self.treeview.selection()[0])['values'][0]
            self.master.quit()

    def create_dir(self, e):
        if len(self.treeview.selection()) != 0:
            name = simpledialog.askstring(title='Please choose a name', prompt='Directory name')
            if not name:
                print('Please select a directory name!')
                return ''
            c_filename = [name, 'Directory']
            selected = self.get_select_file()
            self.client.send(self.fernet.encrypt(b'<dir>,<' + selected.encode() + b'>'))
            server_filename = self.fernet.decrypt(self.client.recv(2048))
            if server_filename == b'<fail>':
                print('Can\'t send directories')
                return ''

            filesys = self.filesystem['Filesys']
            if selected != '\\':
                for i in selected.split('\\')[1:]:
                    filesys = filesys['sub'][i]

            count = 0
            place = ''
            for i in filesys['sub']:
                if filesys['sub'][i]['name'] + filesys['sub'][i]['filetype'] == c_filename[0] + c_filename[1]:
                    count += 1
                    place = '(' + str(count) + ')'
            c_filename[0] += place
            filesys['sub'][server_filename.decode('utf-8')] = {'name': c_filename[0], 'filetype': 'Directory','sub': {}}
            self.client.send(self.fernet.encrypt(b'<success>'))
            self.s_filesys = self.update_list()
            file = open(os.path.dirname(os.path.abspath(__file__)) + '\\filesystem.json', 'w')
            file.write(json.dumps(self.filesystem))
            file.close()
            self.treeview.insert(parent=self.treeview.selection()[0], index=0, text=c_filename[0],values=(c_filename[1], '0 b', self.path))

    def delete_file(self, e):
        if len(self.treeview.selection()) != 0:
            selected = self.get_select_file()
            selected_file = self.fernet.encrypt(b'<delete>,<' + selected.encode() + b'>')
            if self.treeview.item(self.treeview.selection()[0])['text'] == self.filesystem['Filesys']['name']:
                print('Cannot delete root file!')
                return ''
            self.client.send(selected_file)
            if self.fernet.decrypt(self.client.recv(2048)) == b'<fail>':
                print('Wrong path!')
            else:
                self.remove_from_filesystem(self.filesystem['Filesys'], selected.split('\\')[1:])
                file = open(os.path.dirname(os.path.abspath(__file__)) + '\\filesystem.json', 'w')
                file.write(json.dumps(self.filesystem))
                file.close()
                self.treeview.delete(self.treeview.selection()[0])
    def remove_from_filesystem(self, filesys, path):
        if len(path) == 1:
            del filesys['sub'][path[0]]
        else:
            filesys = filesys['sub'][path[0]]
            self.remove_from_filesystem(filesys=filesys, path=path[1:])

    def get_select_file(self):
        if len(self.treeview.selection()) != 0:
            self.path_list = []
            self.path = self.treeview.item(self.treeview.selection()[0])['values'][2] + '\\' + self.treeview.item(self.treeview.selection()[0])['text']
            if self.path == '' or self.path == '\\' + self.filesystem['Filesys']['name']:
                return '\\'
            self.path_list = self.path.split('\\')[2:]
            real_path = ''
            file_sub = self.translator['Root']
            for i in self.path_list:
                file_sub = file_sub['sub'][i]
                real_path += '\\' + file_sub['name']
            return real_path
        return 0