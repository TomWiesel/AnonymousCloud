--------------- WIP !!! ----------  PLEASE IGNORE FOR NOW 
# 1. AnonymousCloud
This program's goal is to ensure an encrypted connection between client and server and high standards when it comes to data privacy.

# 2. Preface
Hello! Thank you for showing interest for my project I am currently working on. Let me introduce you to myself: I am Tom, 18 y/o, living in germany and I am programming for three years now. This is the first project I've ever published and it won't be the last. It took me around two weeks for everything to learn, plan, develop and fix the bugs. During the development, I gained a lot of knowledge about cryptography and specificly about how RSA encryption and the math behind it works. 
So much about me and the background stuff, let's start with the project!

# 3. What does the Software provide?
AnonymousCloud is written in Python and uses sockets and encryption to provide a secure file transmission between client and server. On top, the server owner can only see, how much space is being used and how the files are structured. Due to encryption with a secret key, that only the client posseses, and the files being stored with fake names and fake extensions, the server owner has no chance to get an insight of what the users are storing. In other words: The server provides space on which data can be stored without the user having to be afraid of leaking any data to the server owner or to a potential hacker attacking the server. 
The project contains three .py script files, which are the client, the server and the remote file explorer(which was the hardest to develop). To get a deeper understanding about how the software works, I want to explain every Python script file one by one.

# 3.1 Server.py
The server can handle many users at the time (how many can be assigned in the server script) and controls access with a login system. When connecting, the server creates a       client-object, which gets stored in a list, where all currently active users are being stored, and starts a thread which handles the user. I've also planned to implement a process mode, which allocates every user to a new process. This is to seperate client handling from server activity even more pronounced. When the client-server connection has been established, the encryption key, to cipher all in- and outcoming traffic between both parties, has to be created. This is done with the Diffie-Hellman method, where both parties generate a private and public key (RSA) with the same parameters, to exchange them and mix them with the destination private key. So on both sides, the same exact symmetric key gets calculated and will be used to encrypt all future messages.
No that's done, the user has to decide whether to register or to login with an already existing account. All accounts are being stored in a SQL-database in which the user ID, username, password, the name of virtual harddrive and activity status is being stored. When signing or loggin in, the user password runs through a SHA256 hashing algorithm and is send over to the server to compare both hashes. 
Now that the user is logged in, the client can either send or receive their files. Whenever the server receives commands from the client, the server always returns a response whether everything worked fine. So when the user asks to send files, it gets a "success" or a "fail". When succeeding, the server then receives the file and buffer size, after the user selected which file on his pc to send over. The buffer size is an integer which determines the amount of bytes a packet contains. After the user selected the location in the virtual space, the file transmission now begins. The file transmission and location selection needs an entire chapter, so we save this for later.

# File sharing
Let's start with the client. Like I mentioned before, it possesses two keys. One generates each time it starts and the other one is stored forever on the clients pc.
I've done little search on how to store keys securely, so for now it remains in a simple txt-file. When the client selects his file from a Windows File Explorer API, which provided by Tkinter, he creates a new encrypted version of the file.  he sends over important information such as buffer and file size. 


# FUTURE PLANS
- Encrypted chat
- Encrypted voice chat
- Encrypted video chat
