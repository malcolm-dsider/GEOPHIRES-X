# copyright, 2023, Malcolm I Ross
import sys
import os
import Model
import EconomicsAddOns
import EconomicsCCUS
import OutputsAddOns
import OutputsCCUS
import AdvGeoPHIRESUtils

class AdvModel(Model.Model, AdvGeoPHIRESUtils.AdvGeoPHIRESUtils):
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
        

        model_elements = self.RunStoredProcedure("model_elements", [1])
        model_connections = self.RunStoredProcedure("model_connections", [1])
        self.RunStoredProcedure("delete_model", [14])
        self.RunStoredProcedure("add_new_model", ["dummy", "new", 999])

        #Initiate the elements of the Model
        #this is where you can change what class get initiated - the superclass, or one of the subclasses.  By calling the __init__ (above), all the standard parenst will be initiated, so just initiate the ones you want that exceed those
        self.logger.info("Initiate the newer elements of the Model")
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
        
        #The read parameter function may have switched
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
        
        #This is where all the calcualtions are made using all the values that have been set.  This is handled on a class-by-class basis
        #We choose not to call the calculate of the parent, but rather handle the calls here.
        #before we calculate anything, let's see if there is a suitable result already in the database
        
        self.SmartCalculate(self, self.reserv)
        self.SmartCalculate(self, self.wellbores)
        self.SmartCalculate(self, self.surfaceplant)
        self.SmartCalculate(self, self.economics)
        self.SmartCalculate(self, self.addeconomics)
        self.SmartCalculate(self, self.ccuseconomics)
 
        self.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def __str__(self):
        return "AdvModel"