# import sys

# print('参数个数为:', len(sys.argv), '个参数。')
# print('参数列表:', str(sys.argv))
# print(type(sys.argv))

import threading
import random

# class A(object):
#     def append(self):
#         # global a
#         while True:
#             self.lock.acquire()
#             if len(self.a) < 10:
#                 self.a.append(random.randint(1, 10000))
#             self.lock.release()

#     def pop(self):
#         while True:
#             self.lock.acquire()
#             if len(self.a) > 10:
#                 self.a.pop(0)
#             self.lock.release()

#     def __init__(self):
#         self.lock = threading.Lock()
#         self.a = []
#         self.t1 = threading.Thread(target=self.append)
#         self.t2 = threading.Thread(target=self.pop)
#         self.t1.setDaemon(True)
#         self.t2.setDaemon(True)
#         self.t1.start()
#         self.t2.start()

import threading
import time


class M(object):
    def match(self):
        while True:
            self.lock.acquire()
            if self.a == 1:
                self.a += 1
                print('match1')
            if self.stop == 1:
                self.lock.release()
                break
            self.lock.release()

    def match2(self):
        while True:
            self.lock.acquire()
            if self.a == 2:
                print('match2')
                self.stop = 1
            if self.stop == 1:
                self.lock.release()
                break
            self.lock.release()

    def start(self):
        self.a = 1

    def __init__(self):
        self.a = -1
        self.stop = 0
        self.lock = threading.Lock()
        funcs = [self.match, self.match2]
        pool = []
        for i in funcs:
            pool.append(threading.Thread(target=i))
        for i in pool:
            # i.setDaemon(True)
            i.start()


if __name__ == "__main__":
    m = M()
    m.start()
    # time.sleep(1)