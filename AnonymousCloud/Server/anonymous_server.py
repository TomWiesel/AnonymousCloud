import json
import socket
import threading
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import sqlite3
import random
import string
import time
import base64
import shutil
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

class Server:

    def __init__(self, ip, port, listen, transport):
        self.clients = []
        self.ip, self.port = ip, port
        self.listen = listen
        if transport == 'TCP':
            self.transport = socket.SOCK_STREAM
        elif transport == 'UDP':
            self.transport = socket.SOCK_DGRAM
        else:
            print('No valid transport protocol!')
        self.s_server = socket.socket(socket.AF_INET, self.transport)
        query = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '\\database.db')
        query_cursor = query.cursor()
        query_cursor.execute('UPDATE user SET activity = 0;')
        query.commit()
        del query, query_cursor

    def run(self):
        online_users = threading.Thread(target=self.check_list, args=())
        online_users.start()
        self.s_server.bind((self.ip, self.port))
        self.s_server.listen(self.listen)
        while True:
            client_obj, addr = self.s_server.accept()
            self.clients.append(self.Client(self, self.s_server, client_obj, addr))
            self.clients[len(self.clients) - 1].start()

    def check_list(self):
        query = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '\\database.db')
        query_cursor = query.cursor()
        while True:
            time.sleep(5)
            if self.clients:
                for i in self.clients:
                    if not i.is_alive():
                        index = self.clients.index(i)
                        if hasattr(self.clients[index], 'name'):
                            client_name = self.clients[index].name
                            query_cursor.execute('UPDATE user SET activity=0 WHERE username = (?);', (client_name,))
                            query.commit()
                        del self.clients[index]
            print(self.clients)

    class Client(threading.Thread):

        def __init__(self, server, s_server, client, addr):
            threading.Thread.__init__(self)
            self.client, self.addr = client, addr
            self.s_server = s_server
            self.server = server
            self.register_status = False
            self.delay = 0

        def key_exchange(self):
            parameter_numbers = dh.DHParameterNumbers(0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF,2)
            parameter = parameter_numbers.parameters()
            private_key = parameter.generate_private_key()
            public_key = private_key.public_key()
            self.client.send(public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
            s_public_key = serialization.load_pem_public_key(self.client.recv(2048))
            key = private_key.exchange(s_public_key)
            c_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b'exchange successfull'
            ).derive(key)
            c_key = base64.urlsafe_b64encode(c_key)
            self.fernet = Fernet(c_key)

        def wait(self):
            self.client.recv(1024)
            self.delay += self.delay * 2 + 2
            self.client.send(self.fernet.encrypt(str(self.delay).encode()))
            for i in range(self.delay):
                self.client.send(self.fernet.encrypt(b'<wait>'))
                time.sleep(1)

        def register(self):
            self.client.send(self.fernet.encrypt(b'<success>'))
            query = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '\\database.db')
            query_cursor = query.cursor()
            name = self.fernet.decrypt(self.client.recv(2048)).decode()
            already_exist = query_cursor.execute('SELECT * FROM user WHERE username == (?)', (name,)).fetchall()
            if not already_exist:
                self.client.send(self.fernet.encrypt(b'<success>'))
                password = self.fernet.decrypt(self.client.recv(2048)).hex()
                self.virtual_storage = ''.join(random.choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(10))
                self.name = name
                information = (self.name, password, self.virtual_storage, 1)
                query_cursor.execute('INSERT INTO user VALUES(?,?,?,?)', information)
                query.commit()
                self.register_status = True
                os.mkdir(self.virtual_storage)
                os.mkdir(self.virtual_storage + '\\Filesys')
                self.client.send(self.fernet.encrypt(b'<success>'))
            else:
                query.rollback()
                self.client.send(self.fernet.encrypt(b'<fail>'))
                del query, query_cursor
                self.delay += self.delay*2 + 2
                self.register()

        def login(self):
            self.client.send(self.fernet.encrypt(b'<success>'))
            query = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '\\database.db')
            query_cursor = query.cursor()
            name = self.fernet.decrypt(self.client.recv(1024)).decode('utf-8')
            user = query_cursor.execute('SELECT * FROM user WHERE username = (?)', (name,)).fetchall()
            if user:
                self.client.send(self.fernet.encrypt(b'<success>'))
                self.client.recv(1024)
                if user[0][3] == 1:
                    del query, query_cursor
                    self.client.send(self.fernet.encrypt(b'<fail>'))
                    self.wait()
                    self.login()
                else:
                    self.client.send(self.fernet.encrypt(b'<success>'))
                    pwd = self.fernet.decrypt(self.client.recv(2048)).hex()
                    if pwd == user[0][1]:
                        self.name = name
                        query_cursor.execute('UPDATE user SET activity=1 WHERE username = (?);', (self.name,))
                        query.commit()
                        self.client.send(self.fernet.encrypt(b'<success>'))
                        self.register_status = True
                        self.virtual_storage = user[0][2]
                    else:
                        self.client.send(self.fernet.encrypt(b'<fail>'))
                        del query, query_cursor
                        self.wait()
                        self.login()
            else:
                self.client.send(self.fernet.encrypt(b'<fail>'))
                del query, query_cursor
                self.wait()
                self.login()

        def file_system(self):
            if self.fernet.decrypt(self.client.recv(2048)) == b'<fail>':
                print('fail')
                return ''
            absolute_path = os.path.dirname(os.path.abspath(__file__)) + '\\' + self.virtual_storage + '\\Filesys'
            virtual_drive = 3*(10**10)
            used = virtual_drive - os.path.getsize(absolute_path)
            open_files = {'Filesys': {'size': virtual_drive, 'used': used, 'sub': self.get_subtree(rel_path=absolute_path)}}
            self.client.send(self.fernet.encrypt(json.dumps(open_files).encode()))
            file_explorer_open = True
            while file_explorer_open:
                selection = self.fernet.decrypt(self.client.recv(4096)).decode()
                if selection == '<fail>':
                    return '<fail>'

                selection = selection.split(',')
                path = selection[1].replace('<', '').replace('>', '')
                complete_path = absolute_path + path

                if selection[0] == '<send>':
                    if os.path.exists(complete_path):
                        if not os.path.isdir(complete_path):
                            self.client.send(self.fernet.encrypt(b'<fail>'))
                        else:
                            filename = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=5))
                            while os.path.exists(os.path.dirname(complete_path) + '\\' + filename):
                                filename = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=5))
                            self.client.send(self.fernet.encrypt(filename.encode()))
                            return complete_path + '\\' + filename

                elif selection[0] == '<dir>':
                    if os.path.exists(absolute_path + path):
                        if not os.path.isdir(complete_path):
                            self.client.send(self.fernet.encrypt(b'<fail>'))
                        else:
                            filename = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=5))
                            while os.path.exists(os.path.dirname(complete_path) + '\\' + filename):
                                filename = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=5))
                            self.client.send(self.fernet.encrypt(filename.encode()))
                            os.mkdir(complete_path + '\\' + filename)
                            self.client.recv(1024)
                            open_files = {'Filesys': {'size': virtual_drive, 'used': used,'sub': self.get_subtree(rel_path=absolute_path)}}
                            self.client.send(self.fernet.encrypt(json.dumps(open_files).encode()))

                elif selection[0] == '<receive>':
                    complete_path = absolute_path + path
                    if os.path.isdir(complete_path):
                        self.client.send(self.fernet.encrypt(b'<fail>'))
                    else:
                        self.client.send(self.fernet.encrypt(b'<success>'))
                        return complete_path

                elif selection[0] == '<delete>':
                    if os.path.exists(complete_path):
                        if os.path.isdir(complete_path):
                            shutil.rmtree(complete_path)
                        else:
                            os.remove(complete_path)
                        self.client.send(self.fernet.encrypt(b'<success>'))

                    else:
                        print('Not exists')
                        self.client.send(self.fernet.encrypt(b'<fail>'))
                elif selection[0] == '<shutdown>':
                    pass
                else:
                    return '<>'
            return ''

        def get_subtree(self, rel_path='', count=0):
            subfolder = os.listdir(rel_path)
            temp = {}
            if subfolder:
                for i in subfolder:
                    sub_subfolder = rel_path + '\\' + i
                    count += 1
                    if os.path.isdir(sub_subfolder):
                        if os.listdir(sub_subfolder):
                            temp[os.path.basename(sub_subfolder)] = {'size': os.path.getsize(sub_subfolder), 'sub':self.get_subtree(rel_path=sub_subfolder, count=count)}
                        else:
                            temp[os.path.basename(sub_subfolder)] = {'size': os.path.getsize(sub_subfolder), 'sub':{}}
                    else:
                        temp[os.path.basename(sub_subfolder)] = {'size': os.path.getsize(sub_subfolder)}
                return temp
            else:
                return []

        def run(self):
            self.client.recv(1024)
            self.client.send(b'Connected!')
            self.key_exchange()
            while not self.register_status:
                try:
                    options = self.fernet.decrypt(self.client.recv(1024))
                    if options == b'r':
                        self.register()
                    elif options == b'l':
                        self.login()
                    else:
                        self.client.send(self.fernet.encrypt(b'<fail>'))
                except:
                    print('A user with the IP ' + str(self.addr[0]) + ' disconnected!')
                    break

            while self.register_status:
                try:
                    options = self.fernet.decrypt(self.client.recv(1024))
                    if options == b'<send>':
                        self.receive_file()
                    elif options == b'<receive>':
                        self.send_to_client()
                    else:
                        self.client.send(self.fernet.encrypt(b'<fail>'))
                except:
                    self.register_status = False
                    print('User ' + self.name + ' disconnected! (' + self.addr[0] + ')')

        def receive_file(self):
            self.client.send(self.fernet.encrypt(b'<success>'))
            if self.fernet.decrypt(self.client.recv(1024)) == b'<fail>':
                return ''
            filename = self.file_system()
            if filename == '<fail>':
                return ''

            self.client.send(self.fernet.encrypt(b'<success>'))
            buffer = self.fernet.decrypt(self.client.recv(1024)).decode('UTF-8')
            buffer = int(buffer)
            self.client.send(self.fernet.encrypt(b'<success>'))
            file_size = int(self.fernet.decrypt(self.client.recv(1024)).decode('UTF-8'))
            self.client.send(self.fernet.encrypt(b'<success>'))
            file_encrypt = open(filename, 'wb')
            self.client.send(self.fernet.encrypt(b'<success>'))

            file_src = self.client.recv(buffer)
            file_encrypt.write(file_src)
            total = len(file_src)
            while file_size > total:
                file_src = self.client.recv(buffer)
                file_encrypt.write(file_src)
                total += len(file_src)
            file_encrypt.close()
            self.client.send(self.fernet.encrypt(b'<success>'))

        def send_to_client(self):
            self.client.send(self.fernet.encrypt(b'<success>'))
            file_path = self.file_system()
            if file_path == '<fail>':
                return ''
            self.client.recv(1024)
            buffer = 1024 * 20
            self.client.send(self.fernet.encrypt(str(buffer).encode()))
            self.client.recv(1024)
            file_size = os.path.getsize(file_path)
            self.client.send(self.fernet.encrypt(str(file_size).encode()))
            if self.fernet.decrypt(self.client.recv(1024)) == b'<fail>':
                print('Loading error!')
                return ''
            else:
                file = open(file_path, 'rb')
                file_src = file.read(buffer)
                self.client.send(file_src)
                while file_src:
                    file_src = file.read(buffer)
                    self.client.send(file_src)
                file.close()

server = Server('127.0.0.1', 11100, 1, 'TCP')
server.run()
