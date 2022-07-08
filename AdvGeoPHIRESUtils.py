import sys
#from Parameter import ParameterEntry, floatParameter, intParameter, boolParameter, strParameter
from os.path import exists
import json
import jsons

def DumpObjectAsJson(MyObject)->str:
    jsons.suppress_warnings(True)
    return(jsons.dumps(MyObject, indent=4, sort_keys = True, supress_warnings=True))

def  ReadParameterFromJson(self, dJson:dict):
    """
    The ReadParameterFromJson function reads a JSON string and updates the parameters of this class accordingly.
        
    Args: 
        dJson (dictionary): dictionary derived from encoding a JSON string. 
        
    :param self: Reference the class object itself
    :param dJson:dict: Pass the dictionary that is derived from encoding a json string to the function
    :return: The value of the parameter that is passed in
    :doc-author: Malcolm Ross
    """
    for item in dJson.items():
        if item[0] in self.ParameterDict:
            if isinstance(self.ParameterDict[item[0]], Parameter.floatParameter): val = float(item[1]['Value'])
            if isinstance(self.ParameterDict[item[0]], Parameter.intParameter): val = int(item[1]['Value'])
            if isinstance(self.ParameterDict[item[0]], Parameter.boolParameter): val = bool(item[1]['Value'])
            if isinstance(self.ParameterDict[item[0]], Parameter.strParameter): val = str(item[1]['Value'])
            self.ParameterDict[item[0]].value = val

def read_JSONinput_file(fname:str, model, ReturnDict1):
    model.logger.info("Init " + str(__name__))

    #read input data
    try:
        if exists(fname):
            content = []
            model.logger.info("Found filename: " + fname + " Proceeding with run using JSON input parameters from that file")
            with open(fname, encoding='UTF-8') as f:
                if fname.upper().endswith('.JSON'):
                    dJson = json.load(f)
        else:
            model.logger.warn("File: "+  fname + "  not found - proceeding with default parameter run...")
            return

    except BaseException as ex:
        print (ex)
        model.logger.error("Error " + str(ex) + "using JSON filename:" + fname + " proceeding with default parameter run...")
        return

    if fname.upper().endswith('.JSON'):
        for item in dJson.items():
            PEntry = Parameter.ParameterEntry(item[0], str(item[1]['Value']), item[1]['Comment'])
            ReturnDict1[item[0]] = PEntry     #make the dictionary element with the key set to lowercase without spaces.  This should help the algorithm br more forgiving about finding thingsin the dictionary
    
    model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe().f_code.co_name)