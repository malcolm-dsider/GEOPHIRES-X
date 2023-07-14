import sys
from Parameter import ParameterEntry
from os.path import exists
#import Model

def read_input_file(model, ReturnDict1):
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
                    content = f.readlines()    #store all input in one long strong that will be passed to all objects so they can parse out their specific parameters (and ignore the rest)
            else:
                model.logger.warn("File: "+  fname + "  not found - proceeding with default parameter run...")
                return

        except BaseException as ex:
            print (ex)
            model.logger.error("Error " + str(ex) + "using filename:" + fname + " proceeding with default parameter run...")
            return

        #successful read of data into list.  Now make a dictionary with all the parameter entries.  Index will be the unique name of the parameter.  The value with be a "ParameterEntry" structure, with name, value (optionally with units), optional comment
        for line in content:
            if line.startswith("#"): continue    #skp any line that strts with "#" - # will be the comment parameter
            Desc = ""
            sVal = ""
            Comm = ""
            #now deal with the comma delimited parameters
            elements = line.split(',')   #split on a comma - that should give us major divisions,  Could be: 1) Desc and Val (2 elements), 2) Desc and Val with Unit (2 elements, Unit split from Val by space}, 3) Desc, Val, and comment (3 elements), 4) Desc, Val with Unit, Comment (3 elements, Unit split from Val by space}
                                            #if there are more than 3 comments, we are g oing to assume it is parseable, and that the commas are in the comment
            if len(elements) < 2: continue   #not enough commas, so must not be data to parse
                
            #we have good data, so make intial assumptions
            Desc = elements[0].strip()
            sVal = elements[1].strip()
            Comm = ""     #cases 1 & 2 - no comment
            if len(elements) == 3:         #cases 3 & 4
                Comm = elements[2].strip()
            if len(elements) > 3:         #too many commas, so assume they are in comments
                for i in range(2, len(elements), 1):
                    Comm = Comm + elements[i]

            #done with parsing, now create the object and add to the dictionary
            PEntry = ParameterEntry(Desc, sVal, Comm)
            ReturnDict1[Desc] = PEntry     #make the dictionary element

    else: model.logger.warn("No input parameter file specified on the command line. Proceeding with default parameter run... ")
    
    model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe().f_code.co_name)