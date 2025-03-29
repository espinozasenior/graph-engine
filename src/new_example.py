class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def sayhello(self):
        print(f"hello, my name is {self.name} and i am {self.age} years old")
        
class Employee(Person):
    def __init__(self, name, age, salary):
        super().__init__(name, age)
        self.salary = salary

    def sayhello(self):
        super().sayhello()
