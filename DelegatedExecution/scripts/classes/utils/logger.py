from colorama import Fore, Style
from datetime import datetime

class Logger:
    colors = Fore
    loggingActive = True
    indentationLevel = 0
    encoding = "utf8"
    logsFile = "logs.txt"

    def log(message, color=Fore.GREEN, raw=False, logIndentation=None, indentationPattern="| "):
        if logIndentation == None:
            logIndentation = Logger.indentationLevel
        indentation = logIndentation * indentationPattern
        message += Style.RESET_ALL + "\n"
        message = message if raw else f"[{datetime.now().strftime('%m-%d %H:%M:%S')}] {indentation}{message}"
        if Logger.loggingActive:
            with open(Logger.logsFile, "a", encoding=Logger.encoding) as f:
                f.write(color + message)  # [console]::bufferwidth = 327;cls;Get-Content -Encoding UTF8 -Path "logs.txt" -Wait
    
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
                Logger.log(f"┌Called {methodPrefix}{methodToDecorate.__name__} with args: {list(args)}{list(kwargs)}", color=color)
                Logger.indentationLevel += 1
                returnVal = methodToDecorate(*args, **kwargs)
                Logger.indentationLevel -= 1
                Logger.log(f"└Returned from {methodPrefix}{methodToDecorate.__name__}: {returnVal}", color=color)
                return returnVal
            return decoratedMethod
        return methodDecorator