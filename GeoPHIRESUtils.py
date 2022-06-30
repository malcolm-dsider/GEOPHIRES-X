import sys
from Parameter import ParameterEntry
from os.path import exists
import json
import jsons
import Model

def read_input_file(model:Model, ReturnDict1):
    model.logger.info("Init " + str(__name__))

    # specify path of input file - it will always be the first command line argument.  If it doesn't exist, simply run the default model without any inputs
    #read input data (except input from optional filenames)
    if len(sys.argv) > 1:
        fname=sys.argv[1]
        try:
            if exists(fname):
                content = []
                model.logger.info("Found filename: " + fname + " Proceeding with run using input parameters from that file")
                with open(fname, encoding='UTF-8') as f:
                    if fname.upper().endswith('.JSON'):
                        dJson = json.load(f)
                    else:
                        content = f.readlines()    #store all input in one long strong that will be passed to all objects so they can parse out their specific parameters (and ignore the rest)
            else:
                model.logger.warn("File: "+  fname + "  not found - proceeding with default parameter run...")
                return

        except BaseException as ex:
            print (ex)
            model.logger.error("Error " + str(ex) + "using filename:" + fname + " proceeding with default parameter run...")
            return

        if fname.upper().endswith('.JSON'):
            for item in dJson.items():
                PEntry = ParameterEntry(item[0], str(item[1]['Value']), item[1]['Comment'])
                ReturnDict1[item[0]] = PEntry     #make the dictionary element with the key set to lowercase without spaces.  This should help the algorithm br more forgiving about finding thingsin the dictionary
        else:
            #successful read of data into list.  Now make a dictionary with all the parameter entries.  Index will be the unique name of the parameter.  The value with be a "ParameterEntry" structure, with name, value (optionally with units), optional comment
            for line in content:
                Desc = ""
                sVal = ""
                Comm = ""
                #now deal with the comma delimited parameters
                elements = line.split(',')   #split on a comma - that should give us major divisions,  Could be: 1) Desc and Val (2 elements), 2) Desc and Val with Unit (2 elements, Unit split from Val by space}, 3) Desc, Val, and comment (3 elements), 4) Desc, Val with Unit, Comment (3 elements, Unit split from Val by space}
                if len(elements) == 2:
                    Desc = elements[0].strip()     #cases 1 & 2
                    sVal = elements[1].strip()
                    Comm = ""
                elif len(elements) == 3:         #cases 3 & 4
                    Desc = elements[0].strip()
                    sVal = elements[1].strip()
                    Comm = elements[2].strip()
                else:
                    continue      #This must be a comment line, so jump back to the top
                #done with parsing, now create the object and add to the dictionary
                PEntry = ParameterEntry(Desc, sVal, Comm)
                ReturnDict1[Desc] = PEntry     #make the dictionary element

    else: model.logger.warn("No input parameter file specified on the command line. Proceeding with deafult parameter run... ")
    
    model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)

def DumpObjectAsJson(MyObject)->str:
    jsons.suppress_warnings(True)
    return(jsons.dumps(MyObject, indent=4, sort_keys = True, supress_warnings=True))