import sys
#from Parameter import ParameterEntry, floatParameter, intParameter, boolParameter, strParameter, Parameter
from os.path import exists
import json
import jsons
#import AdvModel

def DumpObjectAsJson(MyObject)->str:
    """
    The DumpObjectAsJson function accepts a Python object and returns a JSON string representation of that object.
    The function is useful for debugging purposes, as it allows you to dump an object's contents to the console in 
    a human-readable format.
    
    :param MyObject: Pass in the object that you want to convert into a json string
    :return: A string of the object in json format
    :doc-author: Malcolm Ross
    """
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
    """
    The read_JSONinput_file function reads a JSON input file and returns a dictionary of parameters.  The function is called by the run_model function to read in the JSON input file.
    
    
    :param fname:str: Pass the name of the json file that contains the input parameters
    :param model: The container class of the application, giving access to everything else, including the logger
    :param ReturnDict1: Return the dictionary of parameters to the main function
    :return: A dictionary of parameterentry objects
    :doc-author: Trelent
    """
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