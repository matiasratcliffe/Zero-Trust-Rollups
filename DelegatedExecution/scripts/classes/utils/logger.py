from colorama import Fore, Style
from datetime import datetime

class Logger:
    colors = Fore
    loggingActive = True
    logIndentation = 0
    def log(message, color=Fore.GREEN, raw=False):
        indentation = Logger.logIndentation * '  '
        message += Style.RESET_ALL + "\n"
        message = message if raw else f"[{datetime.now().strftime('%m-%d %H:%M:%S')}] {indentation}{message}"
        if Logger.loggingActive:
            with open("logs.txt", "a", encoding='utf8') as f:
                f.write(color + message)
    
    def LogClassMethods(color=Fore.WHITE):
        def classDecorator(classToDecorate):
            exclusion_list = ["__str__"]
            for name, obj in vars(classToDecorate).items():
                if name not in exclusion_list and callable(obj):
                    setattr(classToDecorate, name, Logger.LogMethod(methodPrefix=f"{classToDecorate.__name__}.", color=color)(obj))
            return classToDecorate
        return classDecorator

    def LogMethod(methodPrefix='', color=Fore.WHITE):
        def methodDecorator(methodToDecorate):
            def decoratedMethod(*args, **kwargs):
                Logger.log(f"Called {methodPrefix}{methodToDecorate.__name__} with args: {list(args)}{list(kwargs)}", color=color)
                Logger.logIndentation += 1
                returnVal = methodToDecorate(*args, **kwargs)
                Logger.logIndentation -= 1
                Logger.log(f"Returned from {methodPrefix}{methodToDecorate.__name__}: {returnVal}", color=color)
                return returnVal
            return decoratedMethod
        return methodDecorator