from colorama import Fore, Style
from datetime import datetime

class Logger:
    loggingActive = True
    logIndentation = 0
    def log(message, raw=False, indent=0):
        message += Style.RESET_ALL + "\n"
        message = message if raw else f"[{datetime.now()}] {message}"
        if Logger.loggingActive:
            with open("logs.txt", "a", encoding='utf8') as f:
                f.write(Fore.GREEN + message)
                print(Fore.GREEN + message, end='')
    
    def LogClassMethods(classToDecorate):
        for name, obj in vars(classToDecorate).items():
            if callable(obj):
                setattr(classToDecorate, name, Logger.LogMethod(obj))
        return classToDecorate

    def LogMethod(methodToDecorate):
        def decoratedMethod(*args, **kwargs):
            indentation = Logger.logIndentation * '  '
            Logger.log(f"{indentation}Called {methodToDecorate.__name__} with args: {args[1:]}")
            Logger.logIndentation += 1
            returnVal = methodToDecorate(*args, **kwargs)
            Logger.logIndentation -= 1
            Logger.log(f"{indentation}Returned from {methodToDecorate.__name__}: {returnVal}")
        return decoratedMethod

@Logger.LogClassMethods
class MiClase:
    Jajaja = 123
    def __init__(self):
        self.instanceFunc(123)
    
    def instanceFunc(self, asd):
        self.classFunc("Jaja")

    def classFunc(self, valor):
        pass

#MiClase()