import sys
import logging
import time
import logging
from GeoPHIRESUtils import read_input_file
from Reservoir import Reservoir, MPFReservoir, LHSReservoir, SFReservoir, TDPReservoir, UPPReservoir, TOUGH2Reservoir
from WellBores import WellBores
from SurfacePlant import SurfacePlant
from Economics import Economics
from Outputs import Outputs
from OptionList import ReservoirModel

class Model(object):
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
        #get logging started
        logging.config.fileConfig('logging.conf')
        self.logger = logging.getLogger('root')
        self.logger.setLevel(logging.INFO)
        self.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)

        #keep track of execution time
        self.tic = time.time()

        #declare some dictionaries
        self.InputParameters = {}  #dictionary to hold all the input parameter the user wants to change

        #This should give us a dictionary with all the parameters the user wants to set.  Should be only those value that they want to change from the default.
        #we do this as soon as possible because what we instantiate may depend on settings in this file
        read_input_file(self, self.InputParameters)

        #Initiate the elements of the Model
        #this is where you can change what class get initiated - the superclass, or one of the subclasses
        self.logger.info("Initiate the elements of the Model")
        # we need to decide which reservoir to instantiate based on the user input (InputParameters), which we just read above for the first time
        if self.InputParameters['Reservoir Model'].sValue == '1': self.reserv = MPFReservoir(self)     #Multiple parallel fractures model (LANL)
        elif self.InputParameters['Reservoir Model'].sValue == '2': self.reserv = LHSReservoir(self)    #Multiple parallel fractures model (LANL)
        elif self.InputParameters['Reservoir Model'].sValue == '3': self.reserv = SFReservoir(self)    #Drawdown parameter model (Tester)
        elif self.InputParameters['Reservoir Model'].sValue == '4': self.reserv = TDPReservoir(self)     #Thermal drawdown percentage model (GETEM)
        elif self.InputParameters['Reservoir Model'].sValue == '5': self.reserv = UPPReservoir(self)    #Generic user-provided temperature profile
        elif self.InputParameters['Reservoir Model'].sValue == '6': self.reserv = TOUGH2Reservoir(self)    #Tough2 is called
        self.wellbores = WellBores(self)
        self.surfaceplant = SurfacePlant(self)
        self.economics = Economics(self)
        self.outputs = Outputs(self)

        self.logger.info("Complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def __str__(self):
        return "Model"

    def read_parameters(self) -> None:
        """
        The read_parameters function reads the parameters from the input file and stores them in a dictionary. 
        
        :param self: Access the variables and other functions of the class
        :return: None
        :doc-author: Malcolm Ross
        """
        self.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)

        #Deal with all the parameter values that the user has provided.  This is handled on a class-by-class basis.

        #Read parameters for the elements of the Model
        self.logger.info("Read parameters for the elements of the Model")
        self.reserv.read_parameters(self) #read the reservoir parameters
        self.wellbores.read_parameters(self)   #read the wellbore parameters
        self.surfaceplant.read_parameters(self) #read the surfaceplant parameters
        self.economics.read_parameters(self) #read the economic parameters
        self.outputs.read_parameters(self) #read the out parameters

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

        #calculate the results
        self.logger.info("Run calcuations for the elements of the Model")
        self.reserv.Calculate(self) #model the reservoir
        self.wellbores.Calculate(self) #model the wellbores
        self.surfaceplant.Calculate(self) #model the surfaceplant
        self.economics.Calculate(self)  #model the econoimcs
        
        self.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)