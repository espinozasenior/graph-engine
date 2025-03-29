test = "test"

def sayhello():
    print("hello")

sayhello()

class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def sayhello(self):
        print(f"hello, my name is {self.name} and i am {self.age} years old")
