import sys
import random

text = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghkmnpqrstuvwxyz'
num = '23456789'
special = '-/.?!@='
chars = text + num + special


if len(sys.argv) < 2:
    n = 16
else:
    n = int(sys.argv[1])

def generate(n):
    return ''.join(random.choice(chars) for i in range(n))

def okay(password):
    if not any(c in password for c in num):
        return False
    if not any(c in password for c in special):
        return False
    return True


p = generate(n)
while not okay(p):
    p = generate(n)

print(p)
