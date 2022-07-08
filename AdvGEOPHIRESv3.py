#! python
# -*- coding: utf-8 -*-
"""
Created on Wed Dec  6 10:34:04 2017

@author: kbeckers V1 and V2; Malcolm Ross V3
"""

#GEOPHIRES v3.0 Advanced for GUI interfacing
#build date: May 2022
#github address: https://github.com/malcolm-dsider/GEOPHIRES-X

import os
import sys
import logging
import logging.config
import AdvModel

def main():
    #set up logging.
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger('root')
    logger.info("Init " + str(__name__))

    #set the starting directory to be the directory that this file is in
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    #initiate the entire model
    model = AdvModel.AdvModel()

    #read the parameters that apply to the model
    model.read_parameters()

    #Calculate the entire model
    model.Calculate()

    #write the outputs, if requested
    model.addoutputs.PrintOutputs(model)
    model.ccusoutputs.PrintOutputs(model)
        
    #if the user has asked for it, copy the HDR file to the screen
    if model.outputs.printoutput:
        with open('HDR.out','r', encoding='UTF-8') as f:
            content = f.readlines()    #store all output in one long list

            #Now write each line to the screen
            for line in content: sys.stdout.write(line)
    
    logger.info("Complete "+ str(__name__) + ": " + sys._getframe().f_code.co_name)

if __name__ == "__main__":
    main()