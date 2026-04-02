import os, sys,subprocess

list1 = [[1,2,3],[4,5,6],[7,8,9],[10,11,12]]
skip = True

def func():
    for i in list1:
        for j in i:
            print(j)
        if skip == True:
            return

func()


