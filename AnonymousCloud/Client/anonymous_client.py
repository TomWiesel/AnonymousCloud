import socket
from tkinter import Tk, filedialog
from tkinter.filedialog import askopenfilename
import os
import time
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import sys
import base64
import threading
from getpass import getpass
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import explorer

class Client:

    def __init__(self, ip, port, transport):
        self.register_state = False
        self.loading_state = False
        self.waiting_thread_state = False
        self.ip, self.port = ip, port
        self.abs_path = os.path.dirname(__file__)

        if transport == 'TCP':
            self.transport = socket.SOCK_STREAM
        elif transport == 'UDP':
            self.transport = socket.SOCK_DGRAM
        else:
            pass
        self.client = socket.socket(socket.AF_INET, self.transport)
        self.init_encryption()

    def init_encryption(self):
        if not os.path.exists(self.abs_path + '\\key.key'):
            f_key = open(self.abs_path + '\\key.key', 'wb')
            f_salt = open(self.abs_path + '\\salt.key', 'wb')
            pwd = Fernet.generate_key()
            salt = os.urandom(16)
            f_key.write(pwd)
            f_key.close()
            f_salt.write(salt)
            f_salt.close()
        f_key = open(self.abs_path + '\\key.key', 'rb')
        f_salt = open(self.abs_path + '\\salt.key', 'rb')
        pwd = f_key.read()
        salt = f_salt.read()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        c_key = base64.urlsafe_b64encode(kdf.derive(pwd))
        self.c_fernet = Fernet(c_key)
        f_key.close()
        f_salt.close()

    def key_exchange(self):
        parameter_numbers = dh.DHParameterNumbers(0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF,2)
        parameters = parameter_numbers.parameters()
        private_key = parameters.generate_private_key()
        public_key = private_key.public_key()

        s_public_key = serialization.load_pem_public_key(self.client.recv(1024))
        self.client.send(public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))

        key = private_key.exchange(s_public_key)
        c_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'exchange successfull'
        ).derive(key)
        c_key = base64.urlsafe_b64encode(c_key)
        self.fernet = Fernet(c_key)

    def register(self):
        if self.fernet.decrypt(self.client.recv(1024)) == b'<success>':
            self.name = input('Please select a name: \n')
            self.client.send(self.fernet.encrypt(self.name.encode()))
            if self.fernet.decrypt(self.client.recv(1024)) == b'<fail>':
                print('Please select a name, which hasn\'t already been taken !')
                del self.name
                self.register()
            else:
                pwd_hash = hashes.Hash(hashes.SHA256())
                pwd_hash.update(getpass('Enter the password: \n').encode())
                self.client.send(self.fernet.encrypt(pwd_hash.finalize()))

                if self.fernet.decrypt(self.client.recv(1024)) == b'<success>':
                    print('Successfully registered!')
                    self.register_state = True
                else:
                    print('ERROR')
                    del self.name, pwd_hash

    def login(self):
        if self.fernet.decrypt(self.client.recv(1024)) == b'<fail>':
            print('SERVER ERROR')
        else:
            self.name = input('Please select a name:\n')
            self.client.send(self.fernet.encrypt(self.name.encode()))
            if self.fernet.decrypt(self.client.recv(1024)) == b'<fail>':
                print('This name doesn\'t exist!')
                del self.name
                self.wait()
                self.login()
            else:
                self.client.send(self.fernet.encrypt(b'<success>'))
                if self.fernet.decrypt(self.client.recv(1024)) == b'<fail>':
                    print('The user is already logged in!')
                    self.wait()
                    self.login()
                else:
                    pwd_hash = hashes.Hash(hashes.SHA256())
                    pwd_hash.update(getpass('Please enter the password: \n').encode())
                    self.client.send(self.fernet.encrypt(pwd_hash.finalize()))

                    if self.fernet.decrypt(self.client.recv(1024)) == b'<success>':
                        self.register_state = True
                        print('Welcome back ' + self.name + '!')
                    else:
                        del self.name
                        print('Wrong password!')
                        self.wait()
                        self.login()

    def wait(self):
        self.client.send(self.fernet.encrypt(b'b'))
        seconds = int(self.fernet.decrypt(self.client.recv(1024)))
        for i in range(seconds, 0, -1):
            self.client.recv(1024)
            sys.stdout.flush()
            sys.stdout.write((f'\r --- Wait {i} seconds. ---').format())
        print('')

    def run(self):
        self.client.connect((self.ip, self.port))
        self.client.send(b'hallo!')
        self.client.recv(1024).decode('UTF-8')
        self.key_exchange()

        new_line = ''
        while not self.register_state:
            options = input(new_line + 'Do you want to sign in, or to sign up? (l | r)\n').encode()
            if options == b'r':
                self.client.send(self.fernet.encrypt(options))
                self.register()
            elif options == b'l':
                self.client.send(self.fernet.encrypt(options))
                self.login()
            else:
                print('Wrong input!')
            new_line = '\n'


        while self.register_state:
            while not self.waiting_thread_state:
                options = input('Please select an option: (s = send | r = receive)\n')
                try:
                    if options == 's':
                        self.client.send(self.fernet.encrypt(b'<send>'))
                        self.send_to_client()
                    elif options == 'r':
                        self.client.send(self.fernet.encrypt(b'<receive>'))
                        self.receive_file()
                except:
                    print('ERROR')

    def send_to_client(self):
        if self.fernet.decrypt(self.client.recv(1024)) == b'<fail>':
            print('No valid option!')
        else:
            Tk().withdraw()
            file_path = askopenfilename()
            if not os.path.exists(file_path):
                print('Fail')
                self.client.send(self.fernet.encrypt(b'<fail>'))
                return ''
            else:
                self.client.send(self.fernet.encrypt(b'<success>'))

            state = explorer.File_Explorer(client=self.client, username=self.name, fernet=self.fernet, option='<send>', file_path=file_path).start()
            if not state == '<success>':
                return ''

            self.loading_state = True
            waiting_print = threading.Thread(target=self.waiting_message, args=('Encrypting file...',))
            waiting_print.start()

            with open(file_path + '.encrypt', 'wb') as file_encrypt:
                with open(file_path, 'rb') as file:
                    file_encrypt.write(self.c_fernet.encrypt(file.read()))
            self.loading_state = False
            while self.waiting_thread_state:
                time.sleep(1)

            file = open(file_path + '.encrypt', 'rb')
            buffer = 1024*20
            self.client.recv(1024)
            self.client.send(self.fernet.encrypt(str(buffer).encode()))
            self.client.recv(1024)
            file_size = int(os.path.getsize(file_path + '.encrypt'))
            self.client.send(self.fernet.encrypt(str(file_size).encode()))
            self.client.recv(1024)

            if self.fernet.decrypt(self.client.recv(1024)) == b'<fail>':
                print('A loading error occured!')
                file.close()
                os.remove(file_path + '.encrypt')

            else:
                file_src = file.read(buffer)
                self.client.send(file_src)
                total = len(file_src)
                last_time = time.time()
                last_total, last_time = self.progressBar(file_size, total, 'Sending File', last_time)
                while file_src:
                    file_src = file.read(buffer)
                    self.client.send(file_src)
                    total += len(file_src)
                    if (total - last_total) >= file_size / 50:
                        last_total, last_time = self.progressBar(file_size, total, 'Sending File', last_time)

                self.progressBar(file_size, total, 'Sending File', last_time)
                print('--- Complete -- ')
                file.close()
                os.remove(file_path + '.encrypt')
                self.client.recv(1024)

    def receive_file(self):
        if self.fernet.decrypt(self.client.recv(1024)) == b'<fail>':
            print('No valid option!')
        else:
            filename = explorer.File_Explorer(client=self.client, username=self.name, fernet=self.fernet, option='<receive>').start()
            if filename == '<fail>':
                print('ERROR')
                return ''
            self.client.send(self.fernet.encrypt(b'<success>'))
            buffer = int(self.fernet.decrypt(self.client.recv(4096)).decode('UTF-8'))
            self.client.send(self.fernet.encrypt(b'<success>'))
            file_size = self.fernet.decrypt(self.client.recv(4096*20)).decode('UTF-8')
            file_size = int(file_size)
            Tk().withdraw()
            storing_path = filedialog.askdirectory()
            if not os.path.exists(storing_path):
                self.client.send(self.fernet.encrypt(b'<fail>'))
                return ''
            else:
                self.client.send(self.fernet.encrypt(b'<success>'))
                storing_path += '\\' + filename
                file_encrypt = open(storing_path + '.encrypt', 'wb')
                total = 0
                file_src = self.client.recv(buffer)
                file_encrypt.write(file_src)

                total += len(file_src)
                last_time = time.time()
                last_total, last_time = self.progressBar(file_size, total, 'Sending File', last_time)
                while file_size > total:
                    file_src = self.client.recv(buffer)
                    file_encrypt.write(file_src)
                    total += len(file_src)
                    if (total - last_total) >= file_size / 50:
                        last_total, last_time = self.progressBar(file_size, total, 'Sending File', last_time)
                self.progressBar(file_size, total, 'Sending File', last_time)
                file_encrypt.close()

                self.loading_state = True
                waiting_print = threading.Thread(target=self.waiting_message, args=('Decrypting file...',))
                waiting_print.start()
                with open(storing_path + '.encrypt', 'rb') as file_encrypt:
                    with open(storing_path, 'wb') as file:
                        file.write(self.c_fernet.decrypt(file_encrypt.read()))
                os.remove(storing_path + '.encrypt')
                self.loading_state = False
                print('-- COMPLETE --')

    def waiting_message(self, message):
        loading_icon = ['|', '/', '\\', '-', '|', '/', '-', '\\']
        count = 0
        self.waiting_thread_state = True
        while self.loading_state:
            time.sleep(0.5)
            count += 1
            load_icon = loading_icon[count]
            sys.stdout.flush()
            sys.stdout.write((f'\r {load_icon} =| {message} |= {load_icon}').format(load_icon, message, load_icon))
            if count == len(loading_icon)-1:
                count = 0
        print('')
        self.waiting_thread_state = False

    def progressBar(self, file_size, total, message, last_time):
        percentage = total / file_size
        length = 50
        progr = '█' * int(percentage*length)
        neg_progr = '░' * int(length*(1-percentage))
        past_time = time.time() - last_time
        if past_time < 1:
            past_time = str(round(past_time, 4)) + 's'
        elif 1 < past_time < 60:
            past_time = str(round(past_time, 2)) + 's'
        else:
            past_time = str(round(past_time/60,2)) + 'm'
        percentage_print = str(round(percentage*100,2))
        sys.stdout.flush()
        sys.stdout.write((f'\r=| {message} |{progr}{neg_progr}|[{percentage_print}%][{past_time}]').format(message, progr, neg_progr,percentage_print,past_time))
        return total, time.time()

l = Client('127.0.0.1', 11100, 'TCP')
l.run()