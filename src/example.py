test = "test"

def sayhello():
    print("hello")

def sayhello(name, age):
    print(f"hello, my name is {name} and i am {age} years old")

class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def sayhello(self):
        print(f"hello, my name is {self.name} and i am {self.age} years old")
        
    def __str__(self):
        return f"Person(name={self.name}, age={self.age})"
        
    