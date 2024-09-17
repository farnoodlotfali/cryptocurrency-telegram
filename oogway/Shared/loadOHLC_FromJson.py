from Shared.helpers import load_json

def loadOHLC_FromJson(symbolName, path):
   try:
        data = load_json(f"{path}/{symbolName}.json")
   except FileNotFoundError:
        data = []  
   return data