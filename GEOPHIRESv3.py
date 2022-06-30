#! python
# -*- coding: utf-8 -*-
"""
Created on Wed Dec  6 10:34:04 2017

@author: kbeckers V1 and V2; Malcolm Ross V3
"""

#GEOPHIRES v3.0
#build date: May 2022
#github address...

#import functions
import os
import sys
import logging
import logging.config
import Model


def main():
    #set up logging.
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger('root')
    logger.info("Init " + str(__name__))

    #set the starting directory to be the directory that this file is in
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    #initiate the entire model
    model = Model()

    #read the parameters that apply to the model
    model.read_parameters()

    #Calculate the entire model
    model.Calculate()
    
    logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)

if __name__ == "__main__":
    main()