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
from datetime import datetime
import logging
import logging.config
from AdvModel import AdvModel
import jsons
from deepdiff import DeepDiff
from pprint import pprint

def main():
    #set up logging.
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger('root')
    logger.info("Init " + str(__name__))

    #set the starting directory to be the directory that this file is in
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    #initiate the entire model
    model = AdvModel()

    #read the parameters that apply to the model
    model.read_parameters()

    #Calculate the entire model
    model.Calculate()

    #write the outputs, if requested
    model.addoutputs.PrintOutputs(model)
    model.ccusoutputs.PrintOutputs(model)
    
    model1 = AdvModel()
    model1.read_parameters()
    model1.reserv.gradient.value[0] = 0.08
    model1.Calculate()
    dd=DeepDiff(model, model1, significant_digits=0).pretty()
    pprint(dd)
    ToDump = {model.reserv, model.wellbores, model.surfaceplant, model.ccuseconomics, model.addeconomics}
    dJson = {}
    Json1 = {}
    for obj in ToDump:
        dJson1 = jsons.dump(obj, indent=4, sort_keys = True, supress_warnings=True, strip_microseconds = True, strip_nulls = True, strip_privates = True, strip_properties = True, use_enum_name = True)
        dJson.update(dJson1)

    #convert dict to string
    strJson = str(dJson)
    #makesure that string 100% conforms to JSON spec
    strJson = strJson.replace("\'", "\"")
    strJson = strJson.replace("True", "\"True\"")
    strJson = strJson.replace("False", "\"False\"")

    #now wtite it as a date-time stamped file
    now = datetime.now() # current date and time
    date_time = now.strftime("%Y%m%d%H%M%S")
    with open(date_time+'.json','w', encoding='UTF-8') as f:
        f.write(str(strJson))

    #analysis
    with open('20220709141207.json','r', encoding='UTF-8') as f:
            content1 = f.readlines()    #store all output in one long list
    with open('20220709140954.json','r', encoding='UTF-8') as f:
            content2 = f.readlines()    #store all output in one long list

    dd=DeepDiff(content1, content2)
    with open('output.txt', 'wt') as out:
        pprint(dd, stream=out)
        
    #if the user has asked for it, copy the HDR file to the screen
    if model.outputs.printoutput:
        with open('HDR.out','r', encoding='UTF-8') as f:
            content = f.readlines()    #store all output in one long list

            #Now write each line to the screen
            for line in content: sys.stdout.write(line)
    
    logger.info("Complete "+ str(__name__) + ": " + sys._getframe().f_code.co_name)

if __name__ == "__main__":
    main()