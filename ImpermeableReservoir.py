import sys
from Reservoir import Reservoir
from GeoPHIRESUtils import DumpObjectAsJson, ReadParameter
from Parameter import floatParameter, intParameter, boolParameter, strParameter

class ImpermeableReservoir(Reservoir):
    """
    ImpermeableReservoir Child class of Reservoir for a simple Impermeable Reservoir

    Args:
        Reservoir (Reservoir): The parent class
    """
    def __init__(self, model):
        """
        The __init__ function is called automatically every time the class is instantiated.  This function sets up all the parameters that will be used by this class, and also creates temporary variables that are available to all classes but not read in by user or used for Output.
        
        :param self: Reference the object instance to itself
        :param model (Model): The conatiner class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe(  ).f_code.co_name)

        #Initialze the superclass first
        super().__init__(model)
         
        #These disctionaries contains a list of all the parameters set in this object, stored as "Parameter" and OutputParameter Objects.  This will alow us later to access them in a user interface and get that list, along with unit type, preferred units, etc. 
        self.ParameterDict = {}
        self.OutputParameterDict = {}

        #Set up all the Parameters that will be predefined by this class using the different types of parameter classes.  Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc) and Unit Name of that value, sets it as required (or not), sets allowable range, the error message if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        #This includes setting up temporary variables that will be available to all the class but noy read in by user, or used for Output
        #This also includes all Parameters that are calculated and then published using the Printouts function.
        #If you choose to sublass this master class, you can do so before or after you create your own parameters.  If you do, you can also choose to call this method from you class, which will effectively add and set all these parameters to your class.

        model.logger.info("Complete "+ str(__class__) + ": " + sys._getframe(  ).f_code.co_name)

    def __str__(self):
        return "Economics"

    def dump_self_as_Json(self)->str: return(DumpObjectAsJson(self))

    def read_parameter_from_Json(self, dJson):
        for item in dJson.items():
            if item[0] in self.ParameterDict:
                if isinstance(self.ParameterDict[item[0]], floatParameter): val = float(item[1]['Value'])
                if isinstance(self.ParameterDict[item[0]], intParameter): val = int(item[1]['Value'])
                if isinstance(self.ParameterDict[item[0]], boolParameter): val = bool(item[1]['Value'])
                if isinstance(self.ParameterDict[item[0]], strParameter): val = str(item[1]['Value'])
                self.ParameterDict[item[0]].value = val

    def read_parameters(self, model) -> None:
        """
        The read_parameters function is called by the model to read in all the parameters that have been set for this object.  It loops through all the parameters that have been set for this object, looking for ones that match those of this class.  If it finds a match, it reads in and sets those values.
        
        :param self: Access variables that belong to the class
        :param model (Model): The conatiner class of the application, giving access to everything else, including the logger
        :return: Nothing
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe(  ).f_code.co_name)
        super().read_parameters(model)    #read the paremeters for the parent.

        #Deal with all the parameter values that the user has provided.  They should really only provide values that they want to change from the default values, but they can provide a value that is already set because it is a defaulr value set in __init__.  It will ignore those.
        #This also deals with all the special cases that need to be talen care of after a vlaue has been read in and checked.
        #If you choose to sublass this master class, you can also choose to override this method (or not), and if you do, do it before or after you call you own version of this method.  If you do, you can also choose to call this method from you class, which can effectively modify all these superclass parameters in your class.

        if len(model.InputParameters) > 0:
            #loop thru all the parameters that the user wishes to set, looking for parameters that match this object
            for item in self.ParameterDict.items():
                ParameterToModify = item[1]
                key = ParameterToModify.Name.strip()
                if key in model.InputParameters:
                    ParameterReadIn = model.InputParameters[key]
                    ParameterToModify.CurrentUnits = ParameterToModify.PreferredUnits    #Before we change the paremeter, let's assume that the unit preferences will match - if they don't, the later code will fix this.
                    ReadParameter(ParameterReadIn, ParameterToModify, model)   #this should handle all the non-special cases

                    #handle special cases....
                    
        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe(  ).f_code.co_name)

    def Calculate(self, model) -> None:
        """
        The Calculate function is the main function that runs all the calculations for this child.
        
        :param self: Reference the class itself
        :param model (Model): The conatiner class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe(  ).f_code.co_name)
        super().Calculate(model)    #run calculate for the parent.

        #This is where all the calcualtions are made using all the values that have been set.
        #If you sublcass this class, you can choose to run these calculations before (or after) your calculations, but that assumes you have set all the values that are required for these calculations
        #If you choose to sublass this master class, you can also choose to override this method (or not), and if you do, do it before or after you call you own version of this method.  If you do, you can also choose to call this method from you class, which can effectively run the calculations of the superclass, making all thr values available to your methods. but you had n=betteer have set all the paremeters!

        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe(  ).f_code.co_name)