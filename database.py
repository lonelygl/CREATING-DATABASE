import struct
import os
import hashlib
from datetime import datetime
HEADER_SIZE = 256
RECORD_SIZE = 100
MAGIC_NUMBER = b'MEDDBv1'
RECORD_FORMAT = 'i50sfi30s12s'

class HashIndex:
    def __init__(self,size = 1000):
        self.size = size
        self.table = [None] * size
        self.collisions = 0

    def _hash(self,key,attempt=0):
        h1 = key % self.size
        h2 = 1 + (key % (self.size - 1))
        return (h1 + attempt * h2) % self.size

    def add(self,key,file_position):
        attempt = 0
        while (attempt < self.size):
            index = self._hash(key,attempt)
            if self.table[index] is None:
                self.table[index] = (key,file_position)
                return True
            self.collisions += 1
            attempt += 1
            return False

    def get(self,key):
        attempt = 0
        while (attempt < self.size):
            index = self._hash(key,attempt)
            if self.table[index] is None:
                return None
            if self.table[index][0] == key:
                return self.table[index][1]
        return None