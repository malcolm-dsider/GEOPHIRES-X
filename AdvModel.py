import sys
import logging
import time
import logging
from AdvGeoPHIRESUtils import DumpObjectAsJson
import Model
import Reservoir
import EconomicsAddOns
import EconomicsCCUS
import OutputsAddOns
import OutputsCCUS

class AdvModel(Model.Model):
    """
    Model is the container class of the application, giving access to everything else, including the logger
    """

    def __init__(self):
        """
        The __init__ function is called automatically every time the class is being used to create a new object.
        
        The self parameter is a Python convention. It must be included in each function definition and points to the current instance of the class (the object that is being created). 
        
        :param self: Reference the class instance itself
        :return: Nothing
        :doc-author: Malcolm Ross
        """
        super().__init__()   # initialize the parent parameters and variables

        #Initiate the elements of the Model
        #this is where you can change what class get initiated - the superclass, or one of the subclasses.  By calling the __init__ (above), all the standard parenst will be initiated, so just initiate the ones you want that exceed those
        self.logger.info("Initiate the newer elements of the Model")
        self.reserv = Reservoir.Reservoir(self)
        self.addeconomics = EconomicsAddOns.EconomicsAddOns(self)
        self.ccuseconomics = EconomicsCCUS.EconomicsCCUS(self)
        self.addoutputs = OutputsAddOns.OutputsAddOns(self)
        self.ccusoutputs = OutputsCCUS.OutputsCCUS(self)

        self.logger.info("Complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def read_parameters(self) -> None:
        """
        The read_parameters function reads the parameters from the input file and stores them in a dictionary. 
        
        :param self: Access the variables and other functions of the class
        :return: None
        :doc-author: Malcolm Ross
        """
        self.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().read_parameters()   # read the parent parameters and variables

        #Deal with all the parameter values that the user has provided.  This is handled on a class-by-class basis.
        #Read parameters for the elements of the newer Model
        self.logger.info("Read parameters for the newer elements of the Model")
        
        self.reserv.read_parameters(self)
        self.addeconomics.read_parameters(self)
        self.ccuseconomics.read_parameters(self)
        self.addoutputs.read_parameters(self)
        self.ccusoutputs.read_parameters(self)
        self.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def Calculate(self):
        """
        The Calculate function is where all the calculations are made.  This is handled on a class-by-class basis.
        
        The Calculate function does not return anything, but it does store the results in self.reserv, self.wellbores and self.surfaceplant for later use by other functions.
        
        :param self: Access the class variables
        :return: None
        :doc-author: Malcolm Ross
        """
        self.logger.info("Init "+ str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().Calculate()   # read the parent parameters and variables

        #This is where all the calcualtions are made using all the values that have been set.  This is handled on a class-by-class basis

        #calculate the results
        self.logger.info("Run calcuations for the newer elements of the Model")
        self.addeconomics.Calculate(self)
        self.ccuseconomics.Calculate(self)
        
        self.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def __str__(self):
        return "AdvModel"

    def dump_self_as_Json(self)->str: return(DumpObjectAsJson(self))