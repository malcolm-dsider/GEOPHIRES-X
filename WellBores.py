import sys
import os
import math
import numpy as np
from Parameter import floatParameter, intParameter, boolParameter, OutputParameter, ReadParameter
from Units import *
import Model
from OptionList import ReservoirModel

class WellBores:
    def __init__(self, model:Model):
        """
        The __init__ function is the constructor for a class.  It is called whenever an instance of the class is created.  The __init__ function can take arguments, but self is always the first one. Self refers to the instance of the object that has already been created and it's used to access variables that belong to that object.&quot;
        
        :param self: Reference the class object itself
        :param model: The container class of the application, giving access to everything else, including the logger

        :return: Nothing, and is used to initialize the class
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)

        #Set up all the Parameters that will be predefined by this class using the different types of parameter classes.  Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc) and Unit Name of that value, sets it as required (or not), sets allowable range, the error message if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        #This includes setting up temporary variables that will be available to all the class but noy read in by user, or used for Output
        #This also includes all Parameters that are calculated and then published using the Printouts function.
        #If you choose to sublass this master class, you can do so before or after you create your own parameters.  If you do, you can also choose to call this method from you class, which will effectively add and set all these parameters to your class.

        #These disctionarie contains a list of all the parameters set in this object, stored as "Parameter" and OutputParameter Objects.  This will alow us later to access them in a user interface and get that list, along with unit type, preferred units, etc. 
        self.ParameterDict = {}
        self.OutputParameterDict = {}

        self.nprod = self.ParameterDict[self.nprod.Name] = intParameter("Number of Production Wells", value = 2, AllowableRange=list(range(1,201,1)), UnitType = Units.NONE, Required=True, ErrMessage = "assume default number of production wells (2)", ToolTipText="Number of (identical) production wells")
        self.ninj = self.ParameterDict[self.ninj.Name] = intParameter("Number of Injection Wells", value = 2, AllowableRange=list(range(1,201,1)), UnitType = Units.NONE, Required=True, ErrMessage = "assume default number of injection wells (2)", ToolTipText="Number of (identical) injection wells")
        self.prodwelldiam =  self.ParameterDict[self.prodwelldiam.Name] = floatParameter("Production Well Diameter", value = 0.2032, Min=1, Max=30, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.INCHES, CurrentUnits = LengthUnit.INCHES, Required=True, ErrMessage = "assume default production well diameter (8 inch)", ToolTipText="Inner diameter of production wellbore (assumed constant along the wellbore) to calculate frictional pressure drop and wellbore heat transmission with Rameys model")
        self.injwelldiam = self.ParameterDict[self.injwelldiam.Name] = floatParameter("Injection Well Diameter", value = 0.2032, Min=1, Max=30, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.INCHES, CurrentUnits = LengthUnit.INCHES, Required=True, ErrMessage = "assume default injection well diameter (8 inch)", ToolTipText="Inner diameter of production wellbore (assumed constant along the wellbore) to calculate frictional pressure drop and wellbore heat transmission with Rameys model")
        self.rameyoptionprod = self.ParameterDict[self.rameyoptionprod.Name] = boolParameter("Ramey Production Wellbore Model", value = True, UnitType = Units.NONE, Required=True, ErrMessage = "assume default production wellbore model (Ramey model active)", ToolTipText="Select whether to use Rameys model to estimate the geofluid temperature drop in the production wells")
        self.tempdropprod = self.ParameterDict[self.tempdropprod.Name] = floatParameter("Production Wellbore Temperature Drop", value = 5.0, Min=-5, Max=50, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS, ErrMessage = "assume default production wellbore temperature drop (5 deg.C)", ToolTipText="Specify constant production well geofluid temperature drop in case Rameys model is disabled.")
        self.tempgaininj = self.ParameterDict[self.tempgaininj.Name] = floatParameter("Injection Wellbore Temperature Gain", value = 0.0, Min=-5, Max=50, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS, ErrMessage = "assume default injection wellbore temperature gain (0 deg.C)", ToolTipText="Specify constant injection well geofluid temperature gain.")
        self.prodwellflowrate = self.ParameterDict[self.prodwellflowrate.Name] = floatParameter("Production Flow Rate per Well", value = 50.0, Min = 1, Max=500, UnitType = Units.FLOWRATE, PreferredUnits = FlowRateUnit.KGPERSEC, CurrentUnits = FlowRateUnit.KGPERSEC, ErrMessage = "assume default flow rate per production well (50 kg/s)", ToolTipText="Geofluid flow rate per production well.")
        self.impedance = self.ParameterDict[self.impedance.Name] = floatParameter("Reservoir Impedance", value = 1000.0, Min = 1E-4, Max = 1E4, UnitType = Units.IMPEDANCE, PreferredUnits = ImpedanceUnit.GPASPERM3, CurrentUnits = ImpedanceUnit.GPASPERM3, ErrMessage = "assume default reservoir impedance (0.1 GPa*s/m^3)", ToolTipText="Reservoir resistance to flow per well-pair. For EGS-type reservoirs when the injection well is in hydraulic communication with the production well, this parameter specifies the overall pressure drop in the reservoir between injection well and production well (see docs)")
        self.wellsep = self.ParameterDict[self.wellsep.Name] = floatParameter("Well Separation", value = 1000.0, Min=10, Max=10000, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.INCHES, ErrMessage = "assume default well seperation (1000 m)", ToolTipText="Well separation for built-in TOUGH2 doublet reservoir model")
        self.Tinj = self.ParameterDict[self.Tinj.Name] = floatParameter("Injection Temperature", value = 70.0, Min= 0, Max=200, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS, Required=True, ErrMessage = "assume default injection temperature (70 deg.C)", ToolTipText="Constant geofluid injection temperature at injection wellhead.")
        self.Phydrostatic = self.ParameterDict[self.Phydrostatic.Name] = floatParameter("Reservoir Hydrostatic Pressure", value = 1E2, Min=1E2, Max=1E5, UnitType = Units.PRESSURE, PreferredUnits = PressureUnit.KPASCAL, CurrentUnits = PressureUnit.KPASCAL, ErrMessage = "calculate reservoir hydrostatic pressure using built-in correlation", ToolTipText="Reservoir hydrostatic far-field pressure.  Default value is calculated with built-in modified Xie-Bloomfield-Shook equation (DOE, 2016).")
        self.II = self.ParameterDict[self.II.Name] = floatParameter("Injectivity Index", value = 10.0, Min=1E-2, Max=1E4, UnitType = Units.INJECTIVITY_INDEX, PreferredUnits = InjectivityIndexUnit.KGPERSECPERBAR, CurrentUnits = InjectivityIndexUnit.KGPERSECPERBAR, ErrMessage = "assume default injectivity index (10 kg/s/bar)", ToolTipText="Injectivity index defined as ratio of injection well flow rate over injection well outflow pressure drop (flowing bottom hole pressure - hydrostatic reservoir pressure).")
        self.PI = self.ParameterDict[self.PI.Name] = floatParameter("Productivity Index", value = 10.0, Min=1E-2, Max=1E4, UnitType = Units.PRODUCTIVITY_INDEX, PreferredUnits = ProductivityIndexUnit.KGPERSECPERBAR, CurrentUnits = ProductivityIndexUnit.KGPERSECPERBAR, ErrMessage = "assume default productivity index (10 kg/s/bar)", ToolTipText="Productivity index defined as ratio of production well flow rate over production well inflow pressure drop (see docs)")
        self.maxdrawdown = self.ParameterDict[self.maxdrawdown.Name] = floatParameter("Maximum Drawdown", value = 1.0, Min=0.0, Max=1.000001, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, ErrMessage = "assume default maximum drawdown (1)", ToolTipText="Maximum allowable thermal drawdown before redrilling of all wells into new reservoir (most applicable to EGS-type reservoirs with heat farming strategies). E.g. a value of 0.2 means that all wells are redrilled after the production temperature (at the wellhead) has dropped by 20% of its initial temperature")

#MIR Does Tinj, ninj, nprod, prodwellflowrate change values?

        #local variable initiation
        self.Pinjwellhead = 0.0
        self.usebuiltinhydrostaticpressurecorrelation = True
        self.rhowaterinj = 0.0
        self.usebuiltinppwellheadcorrelation = True
        self.Pminimum = 0.0
        sclass = str(__class__).replace("<class \'", "")
        self.MyClass = sclass.replace("\'>","")
        self.MyPath = os.path.abspath(__file__)

        #Results - used by other objects or printed in output downstream
        self.Phydrostaticcalc = self.OutputParameterDict[self.Phydrostaticcalc.Name] = floatParameter("Calculated Reservoir Hydrostatic Pressure", value = self.Phydrostatic.value, UnitType = Units.PRESSURE, PreferredUnits = PressureUnit.KPASCAL, CurrentUnits = PressureUnit.KPASCAL)
        self.redrill = self.OutputParameterDict[self.redrill.Name] = OutputParameter(Name = "redrill", value=0, UnitType = Units.NONE)
        self.PumpingPowerProd = self.OutputParameterDict[self.PumpingPowerProd.Name] = OutputParameter(Name = "PumpingPowerProd", value=[0.0], UnitType = Units.ENERGY, PreferredUnits = EnergyUnit.MW, CurrentUnits = EnergyUnit.MW)
        self.PumpingPowerInj = self.OutputParameterDict[self.PumpingPowerInj.Name] = OutputParameter(Name = "PumpingPowerInj", value=[0.0], UnitType = Units.ENERGY, PreferredUnits = EnergyUnit.MW, CurrentUnits = EnergyUnit.MW)
        self.pumpdepth = self.OutputParameterDict[self.pumpdepth.Name] = OutputParameter(Name = "pumpdepth", value=[0.0], UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.METERS)
        self.impedancemodelallowed = self.OutputParameterDict[self.impedancemodelallowed.Name] = OutputParameter(Name = "impedancemodelallowed", value=True, UnitType = Units.NONE)
        self.productionwellpumping = self.OutputParameterDict[self.productionwellpumping.Name] = OutputParameter(Name = "productionwellpumping", value=True, UnitType = Units.NONE)
        self.impedancemodelused = self.OutputParameterDict[self.impedancemodelused.Name] = OutputParameter(Name = "impedancemodelused", value=False, UnitType = Units.NONE)
        self.ProdTempDrop = self.OutputParameterDict[self.ProdTempDrop.Name] = OutputParameter(Name = "Production Well Temperature Drop", value=[0.0], UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS)
        self.DP = self.OutputParameterDict[self.DP.Name] = OutputParameter(Name = "Total Pressure Drop", value=[0.0], UnitType = Units.PRESSURE, PreferredUnits = PressureUnit.KPASCAL, CurrentUnits = PressureUnit.KPASCAL)
        self.DP1 = self.OutputParameterDict[self.DP1.Name] = OutputParameter(Name = "Injection Well Pressure Drop", value=[0.0], UnitType = Units.PRESSURE, PreferredUnits = PressureUnit.KPASCAL, CurrentUnits = PressureUnit.KPASCAL)
        self.DP2 = self.OutputParameterDict[self.DP2.Name] = OutputParameter(Name = "Reservoir Pressure Drop", value=[0.0], UnitType = Units.PRESSURE, PreferredUnits = PressureUnit.KPASCAL, CurrentUnits = PressureUnit.KPASCAL)
        self.DP3 = self.OutputParameterDict[self.DP3.Name] = OutputParameter(Name = "Production Well Pump Pressure Drop", value=[0.0], UnitType = Units.PRESSURE, PreferredUnits = PressureUnit.KPASCAL, CurrentUnits = PressureUnit.KPASCAL)
        self.DP4 = self.OutputParameterDict[self.DP4.Name] = OutputParameter(Name = "Bouyancy Pressure Drop", value=[0.0], UnitType = Units.PRESSURE, PreferredUnits = PressureUnit.KPASCAL, CurrentUnits = PressureUnit.KPASCAL)
        self.ProducedTemperature = self.OutputParameterDict[self.ProducedTemperature.Name] = OutputParameter(Name = "Produced Temperature", value=[0.0], UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS)
        self.PumpingPower = self.OutputParameterDict[self.PumpingPower.Name] = OutputParameter(Name = "Pumping Power", value=[0.0], UnitType = Units.ENERGY, PreferredUnits = EnergyUnit.MW, CurrentUnits = EnergyUnit.MW)
        self.Pprodwellhead = self.OutputParameterDict[self.Pprodwellhead.Name] = OutputParameter(Name = "Production wellhead pressure", value=-999.0, UnitType = Units.PRESSURE, PreferredUnits = PressureUnit.KPASCAL, CurrentUnits = PressureUnit.KPASCAL)

        model.logger.info("Complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def __str__(self):
        return "WellBores"

    def read_parameters(self, model:Model) -> None:
        """
        The read_parameters function reads in the parameters from a dictionary and stores them in the aparmeters.  It also handles special cases that need to be handled after a value has been read in and checked.  If you choose to sublass this master class, you can also choose to override this method (or not), and if you do
        
        :param self: Access variables that belong to a class
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
                    if ParameterToModify.Name == "Production Well Diameter": ParameterToModify.value = ParameterToModify.value * 0.0254        #prodwelldiam: production well diameter (input as inch and converted to m)
                    elif ParameterToModify.Name == "Injection Well Diameter": ParameterToModify.value = ParameterToModify.value * 0.0254        #pinjwelldiam: injection well diameter (input as inch and converted to m)
                    elif ParameterToModify.Name == "Reservoir Impedance":  #impedance: impedance per wellpair (input as GPa*s/m^3 and converted to KPa/kg/s (assuming 1000 for density; density will be corrected for later))
                        self.impedance.value = self.impedance.value * (1E6/1E3)    #shift it by a constant to make the units right, per line 619 of GEOPHIRES 2
                        self.impedancemodelused.value = True
                        if self.impedance.Provided == False: self.impedancemodelused.value = False
                    elif ParameterToModify.Name == "Reservoir Hydrostatic Pressure":
                        if ParameterToModify.value == -1: self.usebuiltinhydrostaticpressurecorrelation = True
                        else: self.usebuiltinhydrostaticpressurecorrelation = False
                    elif ParameterToModify.Name == "Production Wellhead Pressure":
                        if ParameterToModify.value == -1.0: self.usebuiltinppwellheadcorrelation = True
                        else: self.usebuiltinppwellheadcorrelation = False
        else:
            model.logger.info("No parameters read becuase no content provided")
        model.logger.info("read parameters complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)
    
    def vaporpressurewater(self, Twater) -> float: 
        if Twater < 100:
            A = 8.07131
            B = 1730.63
            C = 233.426
        else:
            A = 8.14019
            B = 1810.94
            C = 244.485 
        vaporpressurewater = 133.322*(10**(A-B/(C+Twater)))/1000 #water vapor pressure in kPa using Antione Equation
        return vaporpressurewater;
 
    def Calculate(self, model:Model)-> None:
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
        #If you choose to sublass this master class, you can also choose to override this method (or not), and if you do, do it before or after you call you own version of this method.  If you do, you can also choose to call this method from you class, which can effectively run the calculations of the superclass, making all thr values available to your methods. but you had n=betteer have set all the paremeters!

        #calculate wellbore temperature drop
        self.ProdTempDrop.value = 0
        if not self.rameyoptionprod.value:
            self.ProdTempDrop.value = self.tempdropprod.value
        else:
            alpharock = model.reserv.krock.value/(model.reserv.rhorock.value*model.reserv.cprock.value)
            framey = np.zeros(len(model.reserv.timevector.value))
            framey[1:] = -np.log(1.1*(self.prodwelldiam.value/2.)/np.sqrt(4.*alpharock*model.reserv.timevector.value[1:]*365.*24.*3600.*model.surfaceplant.utilfactor.value))-0.29
            framey[0] = -np.log(1.1*(self.prodwelldiam.value/2.)/np.sqrt(4.*alpharock*model.reserv.timevector.value[1]*365.*24.*3600.*model.surfaceplant.utilfactor.value))-0.29 #assume outside diameter of casing is 10% larger than inside diameter of production pipe (=prodwelldiam)
            #assume borehole thermal resistance negligible to rock thermal resistance
            rameyA = self.prodwellflowrate.value*model.reserv.cpwater.value*framey/2/math.pi/model.reserv.krock.value
            #this code is only valid so far for 1 gradient and deviation = 0 !!!!!!!!   For multiple gradients, use Ramey's model for every layer
        
            self.ProdTempDrop.value = -((model.reserv.Trock.value - model.reserv.Tresoutput.value) - model.reserv.averagegradient.value*(model.reserv.depth.value - rameyA) + (model.reserv.Tresoutput.value - model.reserv.averagegradient.value*rameyA - model.reserv.Trock.value)*np.exp(-model.reserv.depth.value/rameyA))

        self.ProducedTemperature.value = model.reserv.Tresoutput.value-self.ProdTempDrop.value

        #redrilling
        if model.reserv.resoption.value in [ReservoirModel.MULTIPLE_PARALLEL_FRACTURES, ReservoirModel.LINEAR_HEAT_SWEEP, ReservoirModel.SINGLE_FRACTURE, ReservoirModel.ANNUAL_PERCENTAGE]: #only applies to the built-in analytical reservoir models
            indexfirstmaxdrawdown = np.argmax(self.ProducedTemperature.value<(1-model.wellbores.maxdrawdown.value)*self.ProducedTemperature.value[0])
            if indexfirstmaxdrawdown > 0:   #redrilling necessary
                self.redrill.value = int(np.floor(len(self.ProducedTemperature.value)/indexfirstmaxdrawdown))
                ProducedTemperatureRepeatead = np.tile(self.ProducedTemperature.value[0:indexfirstmaxdrawdown], self.redrill.value+1)
                self.ProducedTemperature.value = ProducedTemperatureRepeatead[0:len(self.ProducedTemperature.value)]

        #------------------------------------------
        #calculate pressure drops and pumping power
        #------------------------------------------
        #production wellbore fluid conditions [kPa]
        Tprodaverage = model.reserv.Tresoutput.value-self.ProdTempDrop.value/4. #most of temperature drop happens in upper section (because surrounding rock temperature is lowest in upper section)
        rhowaterprod = model.reserv.densitywater(Tprodaverage)  #replace with correlation based on Tprodaverage
        muwaterprod = model.reserv.viscositywater(Tprodaverage) #replace with correlation based on Tprodaverage
        vprod = self.prodwellflowrate.value/rhowaterprod/(math.pi/4.*self.prodwelldiam.value**2)
        Rewaterprod = 4.*self.prodwellflowrate.value/(muwaterprod*math.pi*self.prodwelldiam.value) #laminar or turbulent flow?
        Rewaterprodaverage = np.average(Rewaterprod)
        if Rewaterprodaverage < 2300. :
            f3 = 64./Rewaterprod
        else:
            relroughness = 1E-4/self.prodwelldiam.value    
            f3 = 1./np.power(-2*np.log10(relroughness/3.7+5.74/np.power(Rewaterprod,0.9)),2.)
            f3 = 1./np.power((-2*np.log10(relroughness/3.7+2.51/Rewaterprod/np.sqrt(f3))),2.)
            f3 = 1./np.power((-2*np.log10(relroughness/3.7+2.51/Rewaterprod/np.sqrt(f3))),2.)
            f3 = 1./np.power((-2*np.log10(relroughness/3.7+2.51/Rewaterprod/np.sqrt(f3))),2.)
            f3 = 1./np.power((-2*np.log10(relroughness/3.7+2.51/Rewaterprod/np.sqrt(f3))),2.)
            f3 = 1./np.power((-2*np.log10(relroughness/3.7+2.51/Rewaterprod/np.sqrt(f3))),2.) #6 iterations to converge
    
        #injection well conditions
        Tinjaverage = self.Tinj.value
        self.rhowaterinj = model.reserv.densitywater(Tinjaverage)*np.linspace(1,1,len(self.ProducedTemperature.value))
        muwaterinj = model.reserv.viscositywater(Tinjaverage)*np.linspace(1,1,len(self.ProducedTemperature.value))  #replace with correlation based on Tinjaverage
        vinj = self.nprod.value/self.ninj.value*self.prodwellflowrate.value*(1.+model.reserv.waterloss.value)/self.rhowaterinj/(math.pi/4.*self.injwelldiam.value**2)
        Rewaterinj = 4.*self.nprod.value/self.ninj.value*self.prodwellflowrate.value*(1.+model.reserv.waterloss.value)/(muwaterinj*math.pi*self.injwelldiam.value) #laminar or turbulent flow?
        Rewaterinjaverage = np.average(Rewaterinj)
        if Rewaterinjaverage < 2300. : #laminar flow
            f1 = 64./Rewaterinj
        else: #turbulent flow
            relroughness = 1E-4/self.injwelldiam.value
            f1 = 1./np.power(-2*np.log10(relroughness/3.7+5.74/np.power(Rewaterinj,0.9)),2.)
            f1 = 1./np.power((-2*np.log10(relroughness/3.7+2.51/Rewaterinj/np.sqrt(f1))),2.)
            f1 = 1./np.power((-2*np.log10(relroughness/3.7+2.51/Rewaterinj/np.sqrt(f1))),2.)
            f1 = 1./np.power((-2*np.log10(relroughness/3.7+2.51/Rewaterinj/np.sqrt(f1))),2.)
            f1 = 1./np.power((-2*np.log10(relroughness/3.7+2.51/Rewaterinj/np.sqrt(f1))),2.)
            f1 = 1./np.power((-2*np.log10(relroughness/3.7+2.51/Rewaterinj/np.sqrt(f1))),2.)  #6 iterations to converge

        if self.impedancemodelused.value: #assumed everything stays liquid throughout
            #injecion well pressure drop [kPa]
            self.DP1.value = f1*(self.rhowaterinj*vinj**2/2)*(model.reserv.depth.value/self.injwelldiam.value)/1E3      #/1E3 to convert from Pa to kPa
    
            #reservoir pressure drop [kPa]
            rhowaterreservoir = model.reserv.densitywater(0.1*self.Tinj.value+0.9*model.reserv.Tresoutput.value)    #based on TARB in Geophires v1.2
            self.DP2.value = self.impedance.value*self.nprod.value*self.prodwellflowrate.value*1000./rhowaterreservoir
    
            #production well pressure drop [kPa]
            self.DP3.value = f3*(rhowaterprod*vprod**2/2.)*(model.reserv.depth.value/self.prodwelldiam.value)/1E3     #/1E3 to convert from Pa to kPa
    
            #buoyancy pressure drop [kPa]
            self.DP4.value = (rhowaterprod-self.rhowaterinj)*model.reserv.depth.value*9.81/1E3 # /1E3 to convert from Pa to kPa
    
            #overall pressure drop
            self.DP.value = self.DP1.value + self.DP2.value + self.DP3.value + self.DP4.value

            #calculate pumping power [MWe] (approximate)
            self.PumpingPower.value = self.DP.value*self.nprod.value*self.prodwellflowrate.value*(1+model.reserv.waterloss.value)/self.rhowaterinj/model.surfaceplant.pumpeff.value/1E3   

            #in GEOPHIRES v1.2, negative pumping power values become zero (b/c we are not generating electricity)
            self.PumpingPower.value = [0. if x<0. else x for x in self.PumpingPower.value]

        else: #PI and II are used
            #reservoir hydrostatic pressure [kPa]
            if self.usebuiltinhydrostaticpressurecorrelation:    
                CP = 4.64E-7
                CT = 9E-4/(30.796*model.reserv.Trock.value**(-0.552))
                self.Phydrostaticcalc.value = 0+1./CP*(math.exp(model.reserv.densitywater(model.reserv.Tsurf.value)*9.81*CP/1000*(model.reserv.depth.value-CT/2*model.reserv.averagegradient.value*model.reserv.depth.value**2))-1)

            if self.productionwellpumping.value:
                Pexcess = 344.7 #[kPa] = 50 psi. Excess pressure covers non-condensable gas pressure and net positive suction head for the pump
                self.Pminimum = self.vaporpressurewater(model.reserv.Trock.value) + Pexcess #[kPa] is minimum production pump inlet pressure and minimum wellhead pressure
                if self.usebuiltinppwellheadcorrelation:
                    #production wellhead pressure [kPa]
                    self.Pprodwellhead.value = self.Pminimum
                else:
                    self.Pprodwellhead.value = self.ppwellhead.value
                    if self.Pprodwellhead.value < self.Pminimum:
                        self.Pprodwellhead.value = self.Pminimum
                        print("Warning: provided production wellhead pressure under minimum pressure. GEOPHIRES will assume minimum wellhead pressure")
                        model.logger.warning("Provided production wellhead pressure under minimum pressure. GEOPHIRES will assume minimum wellhead pressure") 
        
                PIkPa = self.PI.value/100.000 #convert PI from kg/s/bar to kg/s/kPa

                #calculate pumping depth
                self.pumpdepth.value = model.reserv.depth.value + (self.Pminimum - self.Phydrostaticcalc.value + self.prodwellflowrate.value/PIkPa)/(f3*(rhowaterprod*vprod**2/2.)*(1/self.prodwelldiam.value)/1E3 + rhowaterprod*9.81/1E3)
                pumpdepthfinal = np.max(self.pumpdepth.value)
                if pumpdepthfinal < 0:
                    pumpdepthfinal = 0
                    print("Warning: GEOPHIRES calculates negative production well pumping depth. No production well pumps will be assumed")
                    model.logger.warning("GEOPHIRES calculates negative production well pumping depth. No production well pumps will be assumed")
                elif pumpdepthfinal > 600:
                    print("Warning: GEOPHIRES calculates pump depth to be deeper than 600 m. Verify reservoir pressure, production well flow rate and production well dimensions")  
                    model.logger.warning("GEOPHIRES calculates pump depth to be deeper than 600 m. Verify reservoir pressure, production well flow rate and production well dimensions")  
                #calculate production well pumping pressure [kPa]
                self.DP3.value = self.Pprodwellhead.value - (self.Phydrostaticcalc.value - self.prodwellflowrate.value/PIkPa - rhowaterprod*9.81*model.reserv.depth.value/1E3 - f3*(rhowaterprod*vprod**2/2.)*(model.reserv.depth.value/self.prodwelldiam.value)/1E3)
                #self.DP3.value = [0 if x<0 else x for x in DP3] #set negative values to 0        
                self.PumpingPowerProd.value = self.DP3.value*self.nprod.value*self.prodwellflowrate.value/rhowaterprod/model.surfaceplant.pumpeff.value/1E3 #[MWe] total pumping power for production wells
                self.PumpingPowerProd.value = np.array([0. if x<0. else x for x in self.PumpingPowerProd.value])

       
            IIkPa = self.II.value/100 #convert II from kg/s/bar to kg/s/kPa

            #necessary injection wellhead pressure [kPa]
            self.Pinjwellhead = self.Phydrostaticcalc.value + self.prodwellflowrate.value*(1+model.reserv.waterloss.value)*self.nprod.value/self.ninj.value/IIkPa - self.rhowaterinj*9.81*model.reserv.depth.value/1E3 + f1*(self.rhowaterinj*vinj**2/2)*(model.reserv.depth.value/self.injwelldiam.value)/1E3
            
            #plant outlet pressure [kPa]
            if model.surfaceplant.usebuiltinoutletplantcorrelation.value:
                DPSurfaceplant = 68.95 #[kPa] assumes 10 psi pressure drop in surface equipment
                model.surfaceplant.Pplantoutlet.value = self.Pprodwellhead.value - DPSurfaceplant

            #injection pump pressure [kPa]
            self.DP1.value = self.Pinjwellhead-model.surfaceplant.Pplantoutlet.value
            #wellbores.DP1.value = [0 if x<0 else x for x in DP1] #set negative values to 0
            self.PumpingPowerInj.value = self.DP1.value*self.nprod.value*self.prodwellflowrate.value*(1+model.reserv.waterloss.value)/self.rhowaterinj/model.surfaceplant.pumpeff.value/1E3 #[MWe] total pumping power for injection wells
            self.PumpingPowerInj.value = np.array([0. if x<0. else x for x in self.PumpingPowerInj.value])
    
            #total pumping power
            if self.productionwellpumping.value:
                self.PumpingPower.value = self.PumpingPowerInj.value + self.PumpingPowerProd.value
            else:
                self.PumpingPower.value = self.PumpingPowerInj.value 

            #negative pumping power values become zero (b/c we are not generating electricity)
            self.PumpingPower.value = [0. if x<0. else x for x in self.PumpingPower.value]
      
        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)