# 1. AnonymousCloud
This program's goal is to ensure an encrypted connection between client and server and high standards when it comes to data privacy.

# 2. Preface
Hello! Thank you for showing interest for my project I am currently working on. This is the first I've ever published and it won't be the last. It took me around two weeks for everything to learn, plan, develop and fix the bugs. During the development, I gained a lot of knowledge about cryptography and specificly about how RSA encryption and the math behind it works. 
Please feel free to comment the code I've written, so I can fix the bugs and gain some new experience.

# 3. What does the Software provide?
AnonymousCloud is written in Python and uses sockets and encryption to provide a secure file transmission between client and server. On top, the server owner can only see, how much space is being used and how the files are structured. Due to encryption with a secret key, that only the client posseses, and the files being stored with fake names and fake extensions, the server owner has no chance to get an insight of what the users are storing. In other words:
The server provides space on which data can be stored without the user having to be afraid of leaking any data to the server owner or to a potential hacker attacking the server. 
The project contains three .py script files, which are the client, the server and the remote file explorer(which was the hardest to develop). To get a deeper understanding about how the software works, I want to explain every Python script file one by one.

# FUTURE PLANS
- Encrypted chat
- Encrypted voice chat
- Encrypted video chat
