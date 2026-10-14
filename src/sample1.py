import sys

def add(a, b):
    return a + b

def greet(name):
    return f"Hello, {name}!"

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "Say Hello"
    
    if q == "add":
        a = int(sys.argv[2])
        b = int(sys.argv[3])
        print(add(a, b))

    elif q == "greet":
        name = sys.argv[2]
        print(greet(name))