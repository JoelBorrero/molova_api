import ast

BASE_HOST = 'https://2ksanrpxtd.execute-api.us-east-1.amazonaws.com/dev/molova'
CATEGORIES = ('Camisas y Camisetas', 'Pantalones y Jeans', 'Vestidos y Enterizos', 'Faldas y Shorts',
              'Abrigos y Blazers', 'Ropa deportiva', 'Zapatos', 'Bolsos', 'Accesorios', 'Otros')
GENDERS = (('h', 'Hombre'), ('m', 'Mujer'))
IMAGE_FORMATS = ('image/png', 'image/jpeg', 'image/jpg')
SETTINGS = ast.literal_eval(open('Settings.json', 'r').read())
USER_AGENTS = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)'
               'Chrome/92.0.4515.131 Safari/537.36',
               'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)'
               'Chrome/47.0.2526.111 Safari/537.36',
               'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko)'
               'Version/9.0.2 Safari/601.3.9',
               'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1',
               'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
               'Chrome/42.0.2311.135 Safari/537.36 Edge/12.246')
