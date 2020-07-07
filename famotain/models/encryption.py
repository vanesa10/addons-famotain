from cryptography.fernet import Fernet
FERNET_KEY = b'mbX-Ae_7DX3aF6a1iJwqnEsXyVyOcJmB9VuRSles5TE='


def encrypt(sales_order):
    f = Fernet(FERNET_KEY)
    token = f.encrypt(str.encode(sales_order))
    return token.decode()


def decrypt(code):
    f = Fernet(FERNET_KEY)
    order = f.decrypt(str.encode(code))
    return order.decode()
