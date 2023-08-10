import random
import string

def get_random_string(length: int) -> string:
    return ''.join(random.choice(string.ascii_letters + string.digits) for i in range(length))