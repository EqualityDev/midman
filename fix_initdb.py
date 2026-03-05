content = open('main.py').read()
old = 'load_dotenv()\nTOKEN = os.getenv("TOKEN")'
new = 'load_dotenv()\nTOKEN = os.getenv("TOKEN")\n\nfrom utils.db import init_db\ninit_db()'
content = content.replace(old, new)
open('main.py', 'w').write(content)
print("Done!")
