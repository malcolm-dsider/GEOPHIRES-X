import sys
import os
import math
from functools import lru_cache
import numpy as np
from mpmath import *
from OptionList import ReservoirModel, FractureShape, ReservoirVolume
from Parameter import intParameter, floatParameter, strParameter, listParameter, OutputParameter, ReadParameter
from Units import *
import Model

class Reservoir:
    """This class is the parent class for modeling the Reservoir.
    """
    def __init__(self, model:Model):
        """
        The __init__ function is called automatically when a class is instantiated. 
        It initializes the attributes of an object, and sets default values for certain arguments that can be overridden by user input. 
        The __init__ function is used to set up all the parameters in the Reservoir.
        
        :param self: Store data that will be used by the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)

        #Set up all the Parameters that will be predefined by this class using the different types of parameter classes.  Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc) and Unit Name of that value, sets it as required (or not), sets allowable range, the error message if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        #This includes setting up temporary variables that will be available to all the class but noy read in by user, or used for Output
        #This also includes all Parameters that are calculated and then published using the Printouts function.
        #If you choose to subclass this master class, you can do so before or after you create your own parameters.  If you do, you can also choose to call this method from you class, which will effectively add and set all these parameters to your class.
         
        #These disctionaries contains a list of all the parameters set in this object, stored as "Parameter" and OutputParameter Objects.  This will alow us later to access them in a user interface and get that list, along with unit type, preferred units, etc.
        self.ParameterDict = {}
        self.OutputParameterDict = {}

        self.resoption = self.ParameterDict[self.resoption.Name] = intParameter("Reservoir Model", value = ReservoirModel.ANNUAL_PERCENTAGE, AllowableRange=[1,2,3,4,5,6], Required=True, ErrMessage = "run default reservoir model (Thermal Drawdown Percentage Model)", ToolTipText="1: Multiple parallel fractures model, 2: 1D linear heat sweep model,  3: m/a single fracture drawdown model, 4: Linear thermal drawdown model, 5: Generic user-provided temperature profile, 6: TOUGH2")
        self.depth = self.ParameterDict[self.depth.Name] = floatParameter("Reservoir Depth", value = 3.0, Min=0.1, Max = 15, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.KILOMETERS, CurrentUnits = LengthUnit.KILOMETERS, Required=True, ErrMessage = "assume default reservoir depth (3 km)", ToolTipText="Depth of the reservoir")
        self.Tmax = self.ParameterDict[self.Tmax.Name] = floatParameter("Maximum Temperature", value = 400.0, Min = 50, Max = 400, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS, Required=True, ErrMessage = "assume default maximum temperature (400 deg.C)", ToolTipText="Maximum allowable reservoir temperature (e.g. due to drill bit or logging tools constraints). GEOPHIRES will cap the drilling depth to stay below this maximum temperature.")
        self.drawdp = self.ParameterDict[self.drawdp.Name] = floatParameter("Drawdown Parameter", value = 0.005, Min=0, Max=0.2, UnitType = Units.DRAWDOWN, PreferredUnits = DrawdownUnit.PERYEAR, CurrentUnits = DrawdownUnit.PERYEAR, ErrMessage="assume default drawdown parameter", ToolTipText="specify the thermal drawdown for reservoir model 3 and 4")
        self.numseg = self.ParameterDict[self.numseg.Name] = intParameter("Number of Segments", value = 1, AllowableRange=[1,2,3,4], UnitType = Units.NONE, Required=True, ErrMessage="assume default number of segments (1)", ToolTipText="Number of rock segments from surface to reservoir depth with specific geothermal gradient")
        self.gradient = self.ParameterDict[self.gradient.Name] = listParameter("Gradient 1", value = [0.05, 0.0, 0.0, 0.0], Min=0.0, Max=500.0, UnitType = Units.TEMP_GRADIENT, PreferredUnits = TemperatureGradientUnit.DEGREESCPERKM, CurrentUnits = TemperatureGradientUnit.DEGREESCPERKM, Required=True, ErrMessage = "assume default geothermal gradient (50 deg.C/km)", ToolTipText="Geothermal gradient in rock segment")
        self.layerthickness = self.ParameterDict[self.layerthickness.Name] = listParameter("Thickness 1", value = [0.0, 100000.0, 100000.0, 100000.0], Min=0.01, Max=100.0, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.KILOMETERS, CurrentUnits = LengthUnit.KILOMETERS, ErrMessage = "assume default layer thickness (2 km)", ToolTipText="Thickness of rock segment")
        self.resvoloption = self.ParameterDict[self.resvoloption.Name] = intParameter("Reservoir Volume Option", value = ReservoirVolume.RES_VOL_FRAC_NUM, AllowableRange=[1,2,3,4], Required=True, UnitType = Units.NONE, ErrMessage="assume default reservoir volume option", ToolTipText="Specifies how the reservoir volume, and fracture distribution (for reservoir models 1 and 2) are calculated. The reservoir volume is used by GEOPHIRES to estimate the stored heat in place. The fracture distribution is needed as input for the EGS fracture-based reservoir models 1 and 2: Specify number of fractures and fracture separation, 2: Specify reservoir volume and fracture separation, 3: Specify reservoir volume and number of fractures, 4: Specify reservoir volume only (sufficient for reservoir models 3, 4, 5 and 6)")
        self.fracshape = self.ParameterDict[self.fracshape.Name] = intParameter("Fracture Shape", value = FractureShape.CIRCULAR_AREA, AllowableRange=[1,2,3,4], UnitType = Units.NONE, ErrMessage= "assume default fracture shape (1)", ToolTipText="Specifies the shape of the (identical) fractures in a fracture-based reservoir: 1: Circular fracture with known area, 2: Circular fracture with known diameter, 3: Square fracture, 4: Rectangular fracture")
        self.fracarea = self.ParameterDict[self.fracarea.Name] = floatParameter("Fracture Area", value = 250000.0, Min=1, Max=1E8, UnitType = Units.AREA, PreferredUnits = AreaUnit.METERS2, CurrentUnits = AreaUnit.METERS2, ErrMessage = "assume default fracture shape (1)", ToolTipText="Effective heat transfer area per fracture")
        self.fracheight = self.ParameterDict[self.fracheight.Name] = floatParameter("Fracture Height", value = 500.0, Min=1, Max=10000, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.METERS, ErrMessage = "assume default fracture height (500 m)", ToolTipText="Diameter (if fracture shape = 2) or height (if fracture shape = 3 or 4) of each fracture")
        self.fracwidth = self.ParameterDict[self.fracwidth.Name] = floatParameter("Fracture Width", value = 500.0, Min=1, Max=10000, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.METERS, ErrMessage = "assume default fracture width (500 m)", ToolTipText="Width of each fracture")
        self.fracnumb = self.ParameterDict[self.fracnumb.Name] = intParameter("Number of Fractures", value = 10, AllowableRange=list(range(1,21,1)), UnitType = Units.NONE, ErrMessage = "assume default number of fractures (10)", ToolTipText="Number of identical parallel fractures in EGS fracture-based reservoir model.")
        self.fracsep = self.ParameterDict[self.fracsep.Name] = floatParameter("Fracture Separation", value = 50.0, Min=1, Max = 1E4, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.METERS, ErrMessage = "assume default fracture separation (50 m)", ToolTipText="Separation of identical parallel fractures with uniform spatial distribution in EGS fracture-based reservoir")
        self.resvol = self.ParameterDict[self.resvol.Name] = floatParameter("Reservoir Volume", value = 125000000.0, Min=10, Max=1E12, UnitType = Units.VOLUME, PreferredUnits = VolumeUnit.METERS3, CurrentUnits = VolumeUnit.METERS3, ErrMessage = "assume default reservoir volume (1.25E8 m3)", ToolTipText="Geothermal reservoir volume")
        self.waterloss = self.ParameterDict[self.waterloss.Name] = floatParameter("Water Loss Fraction", value = 0.0, Min=0.0, Max=0.99, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, ErrMessage = "assume default water loss fraction (0)", ToolTipText="Fraction of water lost in the reservoir defined as (total geofluid lost)/(total geofluid produced).")
        self.cprock = self.ParameterDict[self.cprock.Name] = floatParameter("Reservoir Heat Capacity", value = 1000.0, Min=100, Max=10000, UnitType = Units.HEAT_CAPACITY, PreferredUnits = HeatCapacityUnit.JPERKGPERK, CurrentUnits = HeatCapacityUnit.JPERKGPERK, Required=True, ErrMessage = " assume default reservoir heat capacity (1000 J/kg/K)", ToolTipText="Constant and uniform reservoir rock heat capacity")
        self.rhorock = self.ParameterDict[self.rhorock.Name] = floatParameter("Reservoir Density", value = 2700.0, Min=100, Max=10000, UnitType = Units.DENSITY, PreferredUnits = DensityUnit.KGPERMETERS3, CurrentUnits = DensityUnit.KGPERMETERS3, Required=True, ErrMessage = "assume default reservoir density (2700 kg/m^3)", ToolTipText="Constant and uniform reservoir rock density")
        self.krock = self.ParameterDict[self.krock.Name] = floatParameter("Reservoir Thermal Conductivity", value = 3.0, Min=0.01, Max = 100, UnitType = Units.THERMAL_CONDUCTIVITY, PreferredUnits = ThermalConductivityUnit.WPERMPERK, CurrentUnits = ThermalConductivityUnit.WPERMPERK, ErrMessage = "assume default reservoir thermal conductivity (3 W/m/K)", ToolTipText="Constant and uniform reservoir rock thermal conductivity")
        self.permrock = self.ParameterDict[self.permrock.Name] = floatParameter("Reservoir Permeability", value = 1E-13, Min=1E-20, Max=1E-5, UnitType = Units.PERMEABILITY, PreferredUnits = AreaUnit.METERS2, CurrentUnits = AreaUnit.METERS2, ErrMessage = "assume default reservoir permeability (1E-13 m^2)", ToolTipText="Constant and uniform reservoir permeability")
        self.porrock = self.ParameterDict[self.porrock.Name] = floatParameter("Reservoir Porosity", value = 0.04, Min=0.001, Max=0.99, UnitType = Units.POROSITY, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, ErrMessage = "assume default reservoir porosity (0.04)", ToolTipText="Constant and uniform reservoir porosity")
        self.Tsurf = self.ParameterDict[self.Tsurf.Name] = floatParameter("Surface Temperature", value = 15.0, Min = -50, Max = 50, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS, Required=True, ErrMessage="assume default surface temperature (15 deg.C)", ToolTipText="Surface temperature used for calculating bottom-hole temperature (with geothermal gradient and reservoir depth)")

        self.usebuiltintough2model = False
        self.cpwater = 0.0
        self.rhowater = 0.0
        self.averagegradient = 0.0
        sclass = str(__class__).replace("<class \'", "")
        self.MyClass = sclass.replace("\'>","")
        self.MyPath = os.path.abspath(__file__)

        #Results - note the first 6 values are copies of the input values.  They are required because it is a bad practice to change input values after the user has assigned them.  Instead, we make new parameters that are copies of the input parameters, but then modify these values - we only use and display the calculated values. This is OK because the calculated value starts a a copy of the input value and only changes if needed.
        self.fracsepcalc = self.OutputParameterDict[self.fracsepcalc.Name] = OutputParameter("Calculated Fracture Separation", value = self.fracsep.value, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.METERS)
        self.fracnumbcalc = self.OutputParameterDict[self.fracnumbcalc.Name] = OutputParameter("Calculated Number of Fractures", value = self.fracnumb.value, UnitType = Units.NONE)
        self.fracwidthcalc = self.OutputParameterDict[self.fracwidthcalc.Name] = OutputParameter("Calculated Fracture Width", value = self.fracwidth.value, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.METERS)
        self.fracheightcalc = self.OutputParameterDict[self.fracheightcalc.Name] = OutputParameter("Calculated Fracture Height", value = self.fracheight.value, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.METERS)
        self.fracareacalc = self.OutputParameterDict[self.fracareacalc.Name] = OutputParameter("Calculated Fracture Area", value = self.fracarea.value, UnitType = Units.AREA, PreferredUnits = AreaUnit.METERS2, CurrentUnits = AreaUnit.METERS2)
        self.resvolcalc = self.ParameterDict[self.resvolcalc.Name] = floatParameter("Calculated Reservoir Volume", value = self.resvol.value, UnitType = Units.VOLUME, PreferredUnits = VolumeUnit.METERS3, CurrentUnits = VolumeUnit.METERS3)
        self.Trock = self.OutputParameterDict[self.Trock.Name] = OutputParameter(Name = "Bottom-hole temperature", value=-999.9, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS)
        self.InitialReservoirHeatContent = self.OutputParameterDict[self.InitialReservoirHeatContent.Name] = OutputParameter(Name = "Initial Reservoir Heat Content", value=-999.9, UnitType = Units.ENERGY, PreferredUnits = EnergyUnit.MW, CurrentUnits = EnergyUnit.MW)
        self.timevector = self.OutputParameterDict[self.timevector.Name] = OutputParameter(Name = "Time Vector", value=[], UnitType = Units.NONE)
        self.Tresoutput = self.OutputParameterDict[self.Tresoutput.Name] = OutputParameter(Name = "Reservoir Temperature History", value=[], UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS)

        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)

    def __str__(self):
        return "Reservoir"

    def read_parameters(self, model:Model) -> None:
        """
        The read_parameters function reads in the parameters from a dictionary created by reading the user-provided file and updates the parameter values for this object. 
        
        The function reads in all of the parameters that relate to this object, including those that are inherited from other objects. It then updates any of these parameter values that have been changed by the user.  It also handles any special cases.
        
        :param self: Reference the class instance (such as it is) from within the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)

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

                    #handle special cases
                    if ParameterToModify.Name == "Reservoir Model":
                        if ParameterReadIn.sValue == '1': ParameterToModify.value = ReservoirModel.MULTIPLE_PARALLEL_FRACTURES   #Multiple parallel fractures model (LANL)
                        elif ParameterReadIn.sValue == '2': ParameterToModify.value = ReservoirModel.LINEAR_HEAT_SWEEP    #Volumetric block model (1D linear heat sweep model (Stanford))                       
                        elif ParameterReadIn.sValue == '3': ParameterToModify.value = ReservoirModel.SINGLE_FRACTURE     #Drawdown parameter model (Tester)
                        elif ParameterReadIn.sValue == '4': ParameterToModify.value = ReservoirModel.ANNUAL_PERCENTAGE    #Thermal drawdown percentage model (GETEM)
                        elif ParameterReadIn.sValue == '5': ParameterToModify.value = ReservoirModel.USER_PROVIDED_PROFILE     #Generic user-provided temperature profile
                        else: ParameterToModify.value = ReservoirModel.TOUGH2_SIMULATOR    #TOUGH2 is called

                    if ParameterToModify.Name == "Reservoir Depth": ParameterToModify.value = ParameterToModify.value*1000

                    if ParameterToModify.Name == "Reservoir Volume Option":
                        if ParameterReadIn.sValue == '1': ParameterToModify.value = ReservoirVolume.FRAC_NUM_SEP
                        elif ParameterReadIn.sValue == '2': ParameterToModify.value = ReservoirVolume.RES_VOL_FRAC_SEP
                        elif ParameterReadIn.sValue == '3': ParameterToModify.value = ReservoirVolume.RES_VOL_FRAC_NUM
                        else: ParameterToModify.value = ReservoirVolume.RES_VOL_ONLY

                        if ParameterToModify.value == ReservoirVolume.RES_VOL_ONLY and ParameterToModify.value in [ReservoirModel.MULTIPLE_PARALLEL_FRACTURES, ReservoirModel.LINEAR_HEAT_SWEEP]:
                            ParameterToModify.value = ReservoirVolume.RES_VOL_FRAC_NUM
                            print("Warning: If user-selected reservoir model is 1 or 2, then user-selected reservoir volume option cannot be 4 but should be 1, 2, or 3. GEOPHIRES will assume reservoir volume option 3.")    
                            model.logger.warning("If user-selected reservoir model is 1 or 2, then user-selected reservoir volume option cannot be 4 but should be 1, 2, or 3. GEOPHIRES will assume reservoir volume option 3.")
 
                    if ParameterToModify.Name == "Fracture Shape":
                        if ParameterReadIn.sValue == '1': ParameterToModify.value = FractureShape.CIRCULAR_AREA     #   fracshape = 1  Circular fracture with known area
                        elif ParameterReadIn.sValue == '2': ParameterToModify.value = FractureShape.CIRCULAR_DIAMETER      #   fracshape = 2  Circular fracture with known diameter
                        elif ParameterReadIn.sValue == '3': ParameterToModify.value = FractureShape.SQUARE #   fracshape = 3  Square fracture
                        else: ParameterToModify.value = FractureShape.RECTANGULAR   #   fracshape = 4  Rectangular fracture
                            
                    if ParameterToModify.Name.startswith("Gradient"):
                        parts = ParameterReadIn.Name.split(' ')
                        position = int(parts[1]) - 1
                        ParameterToModify.value[position] = ParameterToModify.value[position] / 1000.0
                        if ParameterToModify.value[position] < 1e-6: ParameterToModify.value[position] = 1e-6    #convert 0 C/m gradients to very small number, avoids divide by zero errors later
                            
                    if ParameterToModify.Name.startswith("Thickness"):
                        parts = ParameterReadIn.Name.split(' ')
                        position = int(parts[1]) - 1
                        ParameterToModify.value[position] = ParameterToModify.value[position] * 1000.0
                        ParameterToModify.value.append(100000)            # set thickness of bottom segment to large number to override lower, unused segments
        else:
            model.logger.info("No parameters read becuase no content provided")
            model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

#user-defined functions
    def densitywater(self, Twater) -> float:   
        T = Twater+273.15
        rhowater = ( .7983223 + (1.50896E-3 - 2.9104E-6*T) * T) * 1E3 #water density correlation as used in Geophires v1.2 [kg/m3]
        return  rhowater

    def viscositywater(self, Twater) -> float:
        muwater = 2.414E-5*np.power(10,247.8/(Twater+273.15-140))     #accurate to within 2.5% from 0 to 370 degrees C [Ns/m2]
        return muwater

    def heatcapacitywater(self, Twater) -> float:
    #J/kg/K (based on TARB in Geophires v1.2)
        Twater = (Twater + 273.15)/1000
        A = -203.6060
        B = 1523.290
        C = -3196.413
        D = 2474.455
        E = 3.855326
        cpwater = (A + B*Twater + C*Twater**2 + D*Twater**3 + E/(Twater**2))/18.02*1000 #water specific heat capacity in J/kg-K
        return cpwater

    @lru_cache(maxsize = 1024)
    def Calculate(self, model:Model) ->None:
        """
        The Calculate function is where all the calculations are done.
        This function can be called multiple times, and will only recalculate what has changed each time it is called.
        
        :param self: Access variables that belongs to the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: Nothing, but it does make calculations and set values in the model
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)

        #This is where all the calcualtions are made using all the values that have been set.
        #If you sublcass this class, you can choose to run these calculations before (or after) your calculations, but that assumes you have set all the values that are required for these calculations
        #If you choose to sublass this master class, you can also choose to override this method (or not), and if you do, do it before or after you call you own version of this method.  If you do, you can also choose to call this method from you class, which can effectively run the calculations of the superclass, making all thr values available to your methods. but you had n=betteer have set all the paremeters!.

        #calculate fracture geometry
        if self.fracshape.value == FractureShape.CIRCULAR_AREA:
            self.fracheightcalc.value = math.sqrt(4/math.pi*self.fracareacalc.value)
            self.fracwidthcalc.value = self.fracheightcalc.value
        elif self.fracshape.value == FractureShape.CIRCULAR_DIAMETER:
            self.fracwidthcalc.value = self.fracheightcalc.value
            self.fracareacalc.value = math.pi/4*self.fracheightcalc.value*self.fracheightcalc.value
        elif self.fracshape.value == FractureShape.SQUARE:
            self.fracwidthcalc.value = self.fracheightcalc.value
            self.fracareacalc.value = self.fracheightcalc.value*self.fracwidthcalc.value
        elif self.fracshape.value == FractureShape.RECTANGULAR:
            self.fracareacalc.value = self.fracheightcalc.value*self.fracwidthcalc.value

        #calculate reservoir geometry:
        if self.resvoloption.value == ReservoirVolume.FRAC_NUM_SEP:
            self.resvolcalc.value = (self.fracnumbcalc.value-1)*self.fracareacalc.value*self.fracsepcalc.value
        elif self.resvoloption.value == ReservoirVolume.RES_VOL_FRAC_SEP:
            self.fracnumbcalc.value = self.resvolcalc.value/self.fracareacalc.value/self.fracsepcalc.value+1
        elif self.resvoloption.value == ReservoirVolume.RES_VOL_FRAC_NUM:
            self.fracsepcalc.value = self.resvol.value/self.fracareacalc.value/(self.fracnumbcalc.value-1)

        #some additional preprocessing calculations
        #calculate maximum well depth (m)
        intersecttemperature = [1000., 1000., 1000., 1000.]
        if self.numseg.value == 1:
            maxdepth = (self.Tmax.value-self.Tsurf.value)/self.gradient.value[0]
        else:
            maxdepth = 0
            intersecttemperature[0] = self.Tsurf.value+self.gradient.value[0]*self.layerthickness.value[0]
            for i in range(1,self.numseg.value-1):
                intersecttemperature[i] = intersecttemperature[i-1]+self.gradient.value[i]*self.layerthickness.value[i]
            layerindex = next(loc for loc, val in enumerate(intersecttemperature) if val > self.Tmax.value)
            if layerindex>0:
                for i in range(0,layerindex): maxdepth = maxdepth + self.layerthickness.value[i]
                maxdepth = maxdepth + (self.Tmax.value-intersecttemperature[layerindex-1])/self.gradient.value[layerindex]
            else:
                maxdepth = (self.Tmax.value-self.Tsurf.value)/self.gradient.value[0]

        if self.depth.value>maxdepth: self.depth.value = maxdepth

        #calculate initial reservoir temperature
        intersecttemperature = [self.Tsurf.value] + intersecttemperature
        totaldepth = np.append(np.array([]), np.cumsum(self.layerthickness.value))
        temperatureindex = max(loc for loc, val in enumerate(self.depth.value > totaldepth) if val == True)
        self.Trock.value = intersecttemperature[temperatureindex] + self.gradient.value[temperatureindex]*(self.depth.value - totaldepth[temperatureindex])

        #calculate average geothermal gradient
        if self.numseg.value == 1: self.averagegradient = self.gradient.value[0]
        else: self.averagegradient = (self.Trock.value-self.Tsurf.value)/self.depth.value

        # specify time-stepping vectors
        self.timevector.value = np.linspace(0, model.surfaceplant.plantlifetime.value, model.economics.timestepsperyear.value*model.surfaceplant.plantlifetime.value+1)
        self.Tresoutput.value = np.zeros(len(self.timevector.value))

        # calculate reservoir water properties
        self.cpwater = self.heatcapacitywater(model.wellbores.Tinj.value*0.5+(self.Trock.value*0.9+model.wellbores.Tinj.value*0.1)*0.5)
        self.rhowater = self.densitywater(model.wellbores.Tinj.value*0.5+(self.Trock.value*0.9+model.wellbores.Tinj.value*0.1)*0.5)

        # temperature gain in injection wells
        model.wellbores.Tinj.value = model.wellbores.Tinj.value + model.wellbores.tempgaininj.value

        #-------------------------------- 
        #calculate reservoir heat content
        #-------------------------------- 
        self.InitialReservoirHeatContent.value = self.resvolcalc.value*self.rhorock.value*self.cprock.value*(self.Trock.value-model.wellbores.Tinj.value)/1E15   #10^15 J
                
        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

class MPFReservoir(Reservoir):
    """
    This class models the Multiple Parallel Fractures Reservoir.
    """
    def __init__(self, model:Model):
        """
        The __init__ function is called automatically when a class is instantiated. 
        It initializes the attributes of an object, and sets default values for certain arguments that can be overridden by user input. 
        
        :param self: Store data that will be used by the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().__init__(model)   # initialize the parent parameters and variables
        sclass = str(__class__).replace("<class \'", "")
        self.MyClass = sclass.replace("\'>","")

        #Set up all the Parameters that will be predefined by this class using the different types of parameter classes.  Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc) and Unit Name of that value, sets it as required (or not), sets allowable range, the error message if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        #This includes setting up temporary variables that will be available to all the class but noy read in by user, or used for Output
        #This also includes all Parameters that are calculated and then published using the Printouts function.
        #If you choose to subclass this master class, you can do so before or after you create your own parameters.  If you do, you can also choose to call this method from you class, which will effectively add and set all these parameters to your class.

        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)
 
    def __str__(self):
        return "MPFReservoir"

    def read_parameters(self, model:Model) -> None:
        """
        The read_parameters function reads in the parameters from a dictionary created by reading the user-provided file and updates the parameter values for this object. 
        
        The function reads in all of the parameters that relate to this object, including those that are inherited from other objects. It then updates any of these parameter values that have been changed by the user.  It also handles any special cases.
        
        :param self: Reference the class instance (such as it is) from within the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().read_parameters(model)    #read the paremeters for the parent.

        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)

    def Calculate(self, model:Model):
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().Calculate(model)    #run calculate for the parent.
    
        # convert flowrate to volumetric rate
        q = model.wellbores.nprod.value*model.wellbores.prodwellflowrate.value/model.reserv.rhowater # m^3/s

        # specify Laplace-space function
        fp = lambda s: (1./s)*exp(-sqrt(s)*tanh((model.reserv.rhowater*model.reserv.cpwater*(q/model.reserv.fracnumbcalc.value/model.reserv.fracwidthcalc.value)*(model.reserv.fracsepcalc.value/2.)/(2.*model.reserv.krock.value*model.reserv.fracheightcalc.value))*sqrt(s)))

        #calculate non-dimensional time
        td = (model.reserv.rhowater*model.reserv.cpwater)**2/(4*model.reserv.krock.value*model.reserv.rhorock.value*model.reserv.cprock.value)*(q/float(model.reserv.fracnumbcalc.value)/model.reserv.fracwidthcalc.value/model.reserv.fracheightcalc.value)**2*model.reserv.timevector.value*365.*24.*3600

        # calculate non-dimensional temperature array
        Twnd = []
        try:
            for t in range(1, len(model.reserv.timevector.value)):
                Twnd = Twnd + [float(invertlaplace(fp, td[t], method='talbot'))]
        except:
            print("Error: GEOPHIRES could not execute numerical inverse laplace calculation for reservoir model 1. Simulation will abort.")
            sys.exit()

        Twnd = np.asarray(Twnd)

        # calculate dimensional temperature, add initial rock temperature to beginning of array
        model.reserv.Tresoutput.value = model.reserv.Trock.value - (Twnd*(model.reserv.Trock.value-model.wellbores.Tinj.value))
        model.reserv.Tresoutput.value = np.append([model.reserv.Trock.value], model.reserv.Tresoutput.value)

        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)

class LHSReservoir(Reservoir):
    """
    This class models the Linear Heat Sweep Reservoir.
    """
    def __init__(self, model:Model):
        """
        The __init__ function is called automatically when a class is instantiated. 
        It initializes the attributes of an object, and sets default values for certain arguments that can be overridden by user input. 
        
        :param self: Store data that will be used by the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().__init__(model)   # initialize the parent parameters and variables
        sclass = str(__class__).replace("<class \'", "")
        self.MyClass = sclass.replace("\'>","")

        #Set up all the Parameters that will be predefined by this class using the different types of parameter classes.  Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc) and Unit Name of that value, sets it as required (or not), sets allowable range, the error message if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        #This includes setting up temporary variables that will be available to all the class but noy read in by user, or used for Output
        #This also includes all Parameters that are calculated and then published using the Printouts function.
        #If you choose to subclass this master class, you can do so before or after you create your own parameters.  If you do, you can also choose to call this method from you class, which will effectively add and set all these parameters to your class.
         
        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)
 
    def __str__(self):
        return "LHSReservoir"

    def read_parameters(self, model:Model) -> None:
        """
        The read_parameters function reads in the parameters from a dictionary created by reading the user-provided file and updates the parameter values for this object. 
        
        The function reads in all of the parameters that relate to this object, including those that are inherited from other objects. It then updates any of these parameter values that have been changed by the user.  It also handles any special cases.
        
        :param self: Reference the class instance (such as it is) from within the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().read_parameters(model)    #read the paremeters for the parent.
        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)

    def Calculate(self, model:Model):
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().Calculate(model)    #run calculate for the parent.

        # specify rock properties
        phi = model.reserv.porrock.value # porosity [%]
        h = 500. # heat transfer coefficient [W/m^2 K]
        shape = 0.2 # ratio of conduction path length
        alpha = model.reserv.krock.value/(model.reserv.rhorock.value*model.reserv.cprock.value)

        # storage ratio
        gamma = (model.reserv.rhowater*model.reserv.cpwater*phi)/(model.reserv.rhorock.value*model.reserv.cprock.value*(1-phi))
        # effective rock radius
        r_efr = 0.83*(0.75*(model.reserv.fracsepcalc.value*model.reserv.fracheightcalc.value*model.reserv.fracwidthcalc.value)/math.pi)**(1./3.)
        # Biot number
        Bi = h*r_efr/model.reserv.krock.value
        # effective rock time constant
        tau_efr = r_efr**2.*(shape + 1./Bi)/(3.*alpha)

        # reservoir dimensions and flow properties
        hl = (model.reserv.fracnumbcalc.value-1)*model.reserv.fracsepcalc.value
        wl = model.reserv.fracwidth.value
        aave = hl*wl
        u0 = model.wellbores.nprod.value*model.wellbores.prodwellflowrate.value/(model.reserv.rhowater*aave)
        tres = (model.reserv.fracheightcalc.value*phi)/u0

        # number of heat transfer units
        ntu = tres/tau_efr

        # specify Laplace-space function
        fp = lambda s: (1/s)*(1-exp(-(1+ntu/(gamma*(s+ntu)))*s))

        # calculate non-dimensional temperature array
        Twnd = []
        try:
            for t in range(1,len(model.reserv.timevector.value)):
                Twnd = Twnd + [float(invertlaplace(fp, model.reserv.timevector.value[t]*365.*24.*3600./tres, method='talbot'))]
        except:
            print("Error: GEOPHIRES could not execute numerical inverse laplace calculation for reservoir model 2. Simulation will abort.")
            sys.exit()
        Twnd = np.asarray(Twnd)

        # calculate dimensional temperature, add error-handling for non-sensical temperatures
        model.reserv.Tresoutput.value = Twnd*(model.reserv.Trock.value-model.wellbores.Tinj.value) + model.wellbores.Tinj.value
        model.reserv.Tresoutput.value = np.append([model.reserv.Trock.value], model.reserv.Tresoutput.value)
        model.reserv.Tresoutput.value = np.asarray([model.reserv.Trock.value if x>model.reserv.Trock.value or x<model.wellbores.Tinj.value else x for x in model.reserv.Tresoutput.value])

        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)

class SFReservoir(Reservoir):
    """
    This class models the Single Fracture Reservoir.
    """
    def __init__(self, model:Model):
        """
        The __init__ function is called automatically when a class is instantiated. 
        It initializes the attributes of an object, and sets default values for certain arguments that can be overridden by user input. 
        
        :param self: Store data that will be used by the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().__init__(model)   # initialize the parent parameters and variables
        sclass = str(__class__).replace("<class \'", "")
        self.MyClass = sclass.replace("\'>","")

        #Set up all the Parameters that will be predefined by this class using the different types of parameter classes.  Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc) and Unit Name of that value, sets it as required (or not), sets allowable range, the error message if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        #This includes setting up temporary variables that will be available to all the class but noy read in by user, or used for Output
        #This also includes all Parameters that are calculated and then published using the Printouts function.
        #If you choose to subclass this master class, you can do so before or after you create your own parameters.  If you do, you can also choose to call this method from you class, which will effectively add and set all these parameters to your class.
         
        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)
 
    def __str__(self):
        return "LHSReservoir"

    def read_parameters(self, model:Model) -> None:
        """
        The read_parameters function reads in the parameters from a dictionary created by reading the user-provided file and updates the parameter values for this object. 
        
        The function reads in all of the parameters that relate to this object, including those that are inherited from other objects. It then updates any of these parameter values that have been changed by the user.  It also handles any special cases.
        
        :param self: Reference the class instance (such as it is) from within the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().read_parameters(model)    #read the paremeters for the parent.
        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)

    def Calculate(self, model:Model):
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().Calculate(model)    #run calculate for the parent.

        model.reserv.Tresoutput.value[0] = model.reserv.Trock.value
        for i in range(1,len(model.reserv.timevector.value)): model.reserv.Tresoutput.value[i] = math.erf(1./model.reserv.drawdp.value/model.reserv.cpwater*math.sqrt(model.reserv.krock.value*model.reserv.rhorock.value*model.reserv.cprock.value/model.reserv.timevector[i]/(365.*24.*3600.)))*(model.reserv.Trock.value-model.wellbores.Tinj.value)+model.wellbores.Tinj.value

        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)

class TDPReservoir(Reservoir):
    """
    This class models the Thermal Drawdown Percentage Reservoir.
    """
    def __init__(self, model:Model):
        """
        The __init__ function is called automatically when a class is instantiated. 
        It initializes the attributes of an object, and sets default values for certain arguments that can be overridden by user input. 
        
        :param self: Store data that will be used by the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().__init__(model)   # initialize the parent parameters and variables
        sclass = str(__class__).replace("<class \'", "")
        self.MyClass = sclass.replace("\'>","")

        #Set up all the Parameters that will be predefined by this class using the different types of parameter classes.  Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc) and Unit Name of that value, sets it as required (or not), sets allowable range, the error message if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        #This includes setting up temporary variables that will be available to all the class but noy read in by user, or used for Output
        #This also includes all Parameters that are calculated and then published using the Printouts function.
        #If you choose to subclass this master class, you can do so before or after you create your own parameters.  If you do, you can also choose to call this method from you class, which will effectively add and set all these parameters to your class.

        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)
 
    def __str__(self):
        return "TDPReservoir"

    def read_parameters(self, model:Model) -> None:
        """
        The read_parameters function reads in the parameters from a dictionary created by reading the user-provided file and updates the parameter values for this object. 
        
        The function reads in all of the parameters that relate to this object, including those that are inherited from other objects. It then updates any of these parameter values that have been changed by the user.  It also handles any special cases.
        
        :param self: Reference the class instance (such as it is) from within the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().read_parameters(model)    #read the paremeters for the parent.
        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)

    def Calculate(self, model:Model):
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().Calculate(model)    #run calculate for the parent.

        model.reserv.Tresoutput.value = (1-model.reserv.drawdp.value*model.reserv.timevector.value)*(model.reserv.Trock.value-model.wellbores.Tinj.value)+model.wellbores.Tinj.value #this is no longer as in thesis (equation 4.16)

        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)

class UPPReservoir(Reservoir):
    """
    This class models the User Provided Profile Reservoir.
    """
    def __init__(self, model:Model):
        """
        The __init__ function is called automatically when a class is instantiated. 
        It initializes the attributes of an object, and sets default values for certain arguments that can be overridden by user input. 
        
        :param self: Store data that will be used by the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().__init__(model)   # initialize the parent parameters and variables
        sclass = str(__class__).replace("<class \'", "")
        self.MyClass = sclass.replace("\'>","")

        #Set up all the Parameters that will be predefined by this class using the different types of parameter classes.  Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc) and Unit Name of that value, sets it as required (or not), sets allowable range, the error message if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        #This includes setting up temporary variables that will be available to all the class but noy read in by user, or used for Output
        #This also includes all Parameters that are calculated and then published using the Printouts function.
        #If you choose to subclass this master class, you can do so before or after you create your own parameters.  If you do, you can also choose to call this method from you class, which will effectively add and set all these parameters to your class.
        #specific to this class:
        
        self.filenamereservoiroutput = self.ParameterDict[self.filenamereservoiroutput.Name] = strParameter("Reservoir Output File Name", value = 'ReservoirOutput.txt', UnitType = Units.NONE, ErrMessage="assume default reservoir output file name (ReservoirOutput.txt)", ToolTipText="File name of reservoir output in case reservoir model 5 is selected")

        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)
 
    def __str__(self):
        return "UPPReservoir"

    def read_parameters(self, model:Model) -> None:
        """
        The read_parameters function reads in the parameters from a dictionary created by reading the user-provided file and updates the parameter values for this object. 
        
        The function reads in all of the parameters that relate to this object, including those that are inherited from other objects. It then updates any of these parameter values that have been changed by the user.  It also handles any special cases.
        
        :param self: Reference the class instance (such as it is) from within the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().read_parameters(model)    #read the paremeters for the parent.
        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)

    def Calculate(self, model:Model):
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().Calculate(model)    #run calculate for the parent.

        model.reserv.Tresoutput.value[0] = model.reserv.Trock.value
        try:
            with open(model.reserv.filenamereservoiroutput.value, encoding='UTF-8') as f:
                contentprodtemp = f.readlines()    
        except:
                model.logger.critical('Error: GEOPHIRES could not read reservoir output file ('+model.reserv.filenamereservoiroutput.value+') and will abort simulation.')
                print('Error: GEOPHIRES could not read reservoir output file ('+model.reserv.filenamereservoiroutput.value+') and will abort simulation.')
                sys.exit()
        numlines = len(contentprodtemp)
        if numlines!= model.surfaceplant.plantlifetime.value*model.economics.timestepsperyear.value+1:
            model.logging.critical('Error: Reservoir output file ('+model.reserv.filenamereservoiroutput.value+') does not have required ' + str(model.surfaceplant.plantlifetime.value*model.economics.timestepsperyear.value+1) + ' lines. GEOPHIRES will abort simulation.')
            print('Error: Reservoir output file ('+model.reserv.filenamereservoiroutput.value+') does not have required ' + str(model.surfaceplant.plantlifetime.value*model.economics.timestepsperyear.value+1) + ' lines. GEOPHIRES will abort simulation.')
            sys.exit()
        for i in range(0,numlines):
            model.reserv.Tresoutput.value[i] = float(contentprodtemp[i].split(',')[1].strip('\n'))

        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)

class TOUGH2Reservoir(Reservoir):
    """
    This class models the TOUGH2 Reservoir.
    """
    def __init__(self, model:Model):
        """
        The __init__ function is called automatically when a class is instantiated. 
        It initializes the attributes of an object, and sets default values for certain arguments that can be overridden by user input. 
        
        :param self: Store data that will be used by the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().__init__(model)   # initialize the parent parameters and variables
        sclass = str(__class__).replace("<class \'", "")
        self.MyClass = sclass.replace("\'>","")
        
        #Set up all the Parameters that will be predefined by this class using the different types of parameter classes.  Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc) and Unit Name of that value, sets it as required (or not), sets allowable range, the error message if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        #This includes setting up temporary variables that will be available to all the class but noy read in by user, or used for Output
        #This also includes all Parameters that are calculated and then published using the Printouts function.
        #specific to this stype of reservoir
        self.tough2modelfilename = self.ParameterDict[self.tough2modelfilename.Name] = strParameter("TOUGH2 Model/File Name", value = 'Doublet', UnitType = Units.NONE, ErrMessage="assume default built-in TOUGH2 model (Doublet).", ToolTipText="File name of reservoir output in case reservoir model 5 is selected")
        self.resthickness = self.ParameterDict[self.resthickness.Name] = floatParameter("Reservoir Thickness", value = 250.0, Min=10, Max=10000, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.METERS, ErrMessage = "assume default reservoir thickness (250 m)", ToolTipText="Reservoir thickness for built-in TOUGH2 doublet reservoir model")
        self.reswidth = self.ParameterDict[self.reswidth.Name] = floatParameter("Reservoir Width", value = 500.0, Min=10, Max=10000, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.METERS, ErrMessage = "assume default reservoir width (500 m)", ToolTipText="Reservoir width for built-in TOUGH2 doublet reservoir model")

        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)
 
    def __str__(self):
        return "TOUGH2Reservoir"

    def read_parameters(self, model:Model) -> None:
        """
        The read_parameters function reads in the parameters from a dictionary created by reading the user-provided file and updates the parameter values for this object. 
        
        The function reads in all of the parameters that relate to this object, including those that are inherited from other objects. It then updates any of these parameter values that have been changed by the user.  It also handles any special cases.
        
        :param self: Reference the class instance (such as it is) from within the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().read_parameters(model)    #read the paremeters for the parent.
        
        #Deal with all the parameter values that the user has provided.  They should really only provide values that they want to change from the default values, but they can provide a value that is already set because it is a defaulr value set in __init__.  It will ignore those
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

                    #handle special cases
                    if ParameterToModify.Name == "TOUGH2 Model/File Name":
                        if self.tough2modelfilename.value == 'Doublet': self.usebuiltintough2model = True
                        else: self.usebuiltintough2model = False

        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)

    def Calculate(self, model:Model):
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().Calculate(model)    #run calculate for the parent.

        # GEOPHIRES assumes TOUGH2 executable and input file are in same directory as GEOPHIRESv2.py
        #create tough2 input file
        path_to_exe = str('xt2_eos1.exe')
        if not os.path.exists(os.path.join(os.getcwd(), path_to_exe)):
            model.logger.critical('TOUGH2 executable file does not exist in current working directory. GEOPHIRES will abort simulation.')
            print('TOUGH2 executable file does not exist in current working directory. GEOPHIRES will abort simulation.')
            sys.exit()
        if model.reserv.tough2modelfilename.value == 'Doublet':
            infile = str('Doublet.dat')
            outfile = str('Doublet.out')
            initialtemp = model.reserv.Trock.value
            rockthermalcond = model.reserv.krock.value
            rockheatcap = model.reserv.cprock.value
            rockdensity = model.reserv.rhorock.value
            rockpor = model.reserv.porrock.value
            rockperm = model.reserv.permrock.value
            reservoirthickness = model.reserv.resthickness.value
            reservoirwidth = model.reserv.reswidth.value
            wellseperation = model.wellbores.wellsep.value
            DeltaXgrid = wellseperation/15
            DeltaYgrid = reservoirwidth/11
            DeltaZgrid = reservoirthickness/5
            flowrate = model.wellbores.prodwellflowrate.value
        
            #convert injection temperature to injection enthalpy
            arraytinj = np.array([1.8,    11.4,  23.4,  35.4,  47.4,  59.4,  71.3,  83.3,  95.2, 107.1, 118.9])
            arrayhinj = np.array([1.0E4, 5.0E4, 1.0E5, 1.5E5, 2.0E5, 2.5E5, 3.0E5, 3.5E5, 4.0E5, 4.5E5, 5.0E5])
            injenthalpy = np.interp(model.wellbores.Tinj.value,arraytinj,arrayhinj)
            #write doublet input file
            f = open(infile,'w', encoding='UTF-8')
            f.write('Doublet\n')
            f.write('MESHMAKER1----*----2----*----3----*----4----*----5----*----6----*----7----*----8\n')
            f.write('XYZ\n')
            f.write('	0.\n')
            f.write('NX      17 %9.3f\n' % (DeltaXgrid))
            f.write('NY      11 %9.3f\n' % (DeltaYgrid))
            f.write('NZ       5 %9.3f\n' % (DeltaZgrid))
            f.write('\n')
            f.write('\n')
            f.write('ROCKS----1----*----2----*----3----*----4----*----5----*----6----*----7----*----8\n')
            f.write('POMED    3%10.1f %9.4f %9.2E %9.2E %9.2E %9.4f %9.2f          \n' % (rockdensity, rockpor, rockperm, rockperm, rockperm, rockthermalcond, rockheatcap))
            f.write('       0.0       0.0       2.0       0.0       0.0\n')
            f.write('    3            0.3      0.05\n')
            f.write('    8\n')
            f.write('\n')
            f.write('MULTI----1----*----2----*----3----*----4----*----5----*----6----*----7----*----8\n')
            f.write('    1    2    2    6\n')
            f.write('START----1----*----2----*----3----*----4----*----5----*----6----*----7----*----8\n')
            f.write('PARAM----1-MOP* 123456789012345678901234----*----5----*----6----*----7----*----8\n')
            f.write(' 8 19999       5000000000001  03 000   0                                        \n')
            f.write('       0.0 %9.3E 5259490.0       0.0                9.81       4.0       1.0\n' % (model.surfaceplant.plantlifetime.value*365*24*3600))
            f.write('    1.0E-5       1.0                 1.0       1.0          \n')
            f.write('           1000000.0          %10.1f\n' % (initialtemp))
            f.write('                                                                                \n')
            f.write('SOLVR----1----*----2----*----3----*----4----*----5----*----6----*----7----*----8\n')
            f.write('3  Z1   O0       0.1    1.0E-6\n')
            f.write('\n')
            f.write('\n')
            f.write('GENER----1----*----2----*----3----*----4----*----5----*----6----*----7----*----8\n')
            f.write('A36 2  012                   0     COM1  %9.3f %9.1f          \n' % (flowrate, injenthalpy))
            f.write('A3616  021                   0     MASS  %9.3f             \n' % (-flowrate))
            f.write('\n')
            f.write('INCON----1----*----2----*----3----*----4----*----5----*----6----*----7----*----8\n')
            f.write('\n')
            f.write('FOFT ----1----*----2----*----3----*----4----*----5----*----6----*----7----*----8\n')
            f.write('A36 2\n')
            f.write('A3616\n')
            f.write('\n')
            f.write('GOFT ----1----*----2----*----3----*----4----*----5----*----6----*----7----*----8\n')
            f.write('A36 2  012\n')
            f.write('A3616  021\n')
            f.write('\n')
            f.write('ENDCY\n')    
            f.close()
            print("GEOPHIRES will run TOUGH2 simulation with built-in Doublet model ...")
    
        else:
            infile = model.reserv.tough2modelfilename.value
            outfile = str('tough2output.out')
            print("GEOPHIRES will run TOUGH2 simulation with user-provided input file = "+model.reserv.tough2modelfilename.value+" ...") 

        # run TOUGH2 executable            
        try:
            os.system('%s < %s > %s' % (path_to_exe, infile, outfile))
        except:
            print("Error: GEOPHIRES could not run TOUGH2 and will abort simulation.")        
            sys.exit()

        # read output temperature and pressure
        try:    
            fname = 'FOFT'    
            with open(fname, encoding='UTF-8') as f:
                content = f.readlines()  
    
            NumerOfResults = len(content)
            SimTimes = np.zeros(NumerOfResults)
            ProdPressure = np.zeros(NumerOfResults)
            ProdTemperature = np.zeros(NumerOfResults)
            for i in range(0,NumerOfResults):
                SimTimes[i] = float(content[i].split(',')[1].strip('\n'))
                ProdPressure[i] = float(content[i].split(',')[8].strip('\n'))
                ProdTemperature[i] = float(content[i].split(',')[9].strip('\n'))
        
            #print(ProdTemperature)    
            model.reserv.Tresoutput.value = np.interp(model.reserv.timevector.value*365*24*3600,SimTimes,ProdTemperature)
        except:
            print("Error: GEOPHIRES could not import production temperature and pressure from TOUGH2 output file ("+infile+") and will abort simulation.")

        model.logger.info("Complete " + str(__class__) + ": " + sys._getframe().f_code.co_name)
