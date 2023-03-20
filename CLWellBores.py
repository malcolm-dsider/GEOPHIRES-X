# copyright, 2023, Malcolm I Ross
#except for code from Wanju Yuan based on: "Closed-Loop Geothermal Energy Recovery from Deep High Enthalpy Systems"
#ref: Yuan, Wanju, et al. "Closed-loop geothermal energy recovery from deep high enthalpy systems." Renewable Energy 177 (2021): 976-991.
import math
import sys
import os
import numpy as np

from Parameter import ReadParameter
import AdvModel
import Wellbores
import AdvGeoPHIRESUtils
esp2 = 10.0e-10

class CLWellBores(WellBores.WellBores, AdvGeoPHIRESUtils.AdvGeoPHIRESUtils):
    """
    CLWellBores Child class of WellBores; it is the same, but has advanced closed-loop functionality

    Args:
        WellBores (WellBores): The parent class
        AdvGeoPHIRESUtils (AdvGeoPHIRESUtils): the utilities class
    """
    def __init__(self, model:AdvModel):
        """
        The __init__ function is called automatically every time the class is instantiated.  This function sets up all the parameters that will be used by this class, and also creates temporary variables that are available to all classes but not read in by user or used for Output.
        
        :param self: Reference the object instance to itself
        :param model (AdvModel): The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)

        #Initialze the superclass first
        super().__init__(model)
        sclass = str(__class__).replace("<class \'", "")
        self.MyClass = sclass.replace("\'>","")
        self.MyPath = os.path.abspath(__file__)

        #Set up all the Parameters that will be predefined by this class using the different types of parameter classes.  Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc) and Unit Name of that value, sets it as required (or not), sets allowable range, the error message if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        #This includes setting up temporary variables that will be available to all the class but noy read in by user, or used for Output
        #This also includes all Parameters that are calculated and then published using the Printouts function.
        #If you choose to sublass this master class, you can do so before or after you create your own parameters.  If you do, you can also choose to call this method from you class, which will effectively add and set all these parameters to your class.
                #set up the parameters using the Parameter Constructors (intParameter, floatParameter, strParameter, etc); initialize with their name, default value, and valid range (if int or float).  Optionally, you can specify:
        # Required (is it reuired to run? default value = False), ErrMessage (what GEOPHIRES will report if the value provided is invalid, "assume default value (see manual)"), ToolTipText (when there is a GIU, this is the text that the user will see, "This is ToolTip Text"),
        # UnitType (the type of units associated with this parameter (length, temperature, density, etc), Units.NONE), CurrentUnits (what the units are for this parameter (meters, celcius, gm/cc, etc, Units:NONE), and PreferredUnits (ususally equal to CurrentUnits, but these are the units that the calculations assume when running, Units.NONE
        self.WaterThermalConductivity = self.ParameterDict[self.WaterThermalConductivity.Name] = floatParameter("Water Thermal Conductivity", value = 0.6, DefaultValue=0.6, Min=0.0, Max = 100.0, UnitType = Units.THERMAL_CONDUCTIVITY, PreferredUnits = ThermalConductivityUnit.WPERMPERK, CurrentUnits = ThermalConductivityUnit.WPERMPERK, ErrMessage="assume default for water thermal conductivity (0.6 W/m/K)", ToolTipText="Water Thermal Conductivity")
        self.l_pipe = self.ParameterDict[self.l_pipe.Name] = floatParameter("Horizontal Wellbore Length", value = 5000.0, DefaultValue=5000.0, Min=0.01, Max = 100000.0, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.METERS, ErrMessage="assume default for Horizontal Wellbore Length (5000.0 m)", ToolTipText="Horizontal Wellbore Length")
        self.diameter = self.ParameterDict[self.diameter.Name] = floatParameter("Horizontal Wellbore Diameter", value = 0.156, DefaultValue=0.156, Min=0.01, Max = 100.0, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.METERS, ErrMessage="assume default for Horizontal Wellbore Diameter (5000.0 m)", ToolTipText="Horizontal Wellbore Diameter")
        self.numhorizontalsections = self.ParameterDict[self.numhorizontalsections.Name] = intParameter("Number of Horizontal Wellbore Sections", value = 1, DefaultValue=1, Min=1, Max = 100, UnitType = Units.NONE, ErrMessage="assume default for Number of Horizontal Wellbore Sections (1)", ToolTipText="Number of Horizontal Wellbore Sections")
        self.time_operation = self.ParameterDict[self.calculationstartyear.Name] = floatParameter("Closed Loop Calculation Start Year", value = 0.01, DefaultValue=0.01, Min=0.01, Max = 100.0, UnitType = Units.TIME, PreferredUnits = TimeUnit.YEARS, CurrentUnits = TimeUnit.YEARS, ErrMessage="assume default for Closed Loop Calculation Start Year (0.01)", ToolTipText="Closed Loop Calculation Start Year")

        #local variables that need initialization

        #results are stored in the parent ProducedTemperature array

        model.logger.info("Complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def read_parameters(self, model:AdvModel) -> None:
        """
        The read_parameters function is called by the model to read in all the parameters that have been set for this object.  It loops through all the parameters that have been set for this object, looking for ones that match those of this class.  If it finds a match, it reads in and sets those values.
        
        :param self: Access variables that belong to the class
        :param model (AdvModel): The container class of the application, giving access to everything else, including the logger
        :return: Nothing
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().read_parameters(model)    #read the paremeters for the parent.

        #Deal with all the parameter values that the user has provided.  They should really only provide values that they want to change from the default values, but they can provide a value that is already set because it is a defaulr value set in __init__.  It will ignore those.
        #This also deals with all the special cases that need to be talen care of after a vlaue has been read in and checked.
        #If you choose to sublass this master class, you can also choose to override this method (or not), and if you do, do it before or after you call you own version of this method.  If you do, you can also choose to call this method from you class, which can effectively modify all these superclass parameters in your class.

        #only need to do this if you add any of your own parameters
        #if len(model.InputParameters) > 0:
        #    #loop thru all the parameters that the user wishes to set, looking for parameters that match this object
        #    for item in self.ParameterDict.items():
        #        ParameterToModify = item[1]
        #        key = ParameterToModify.Name.strip()
        #        if key in model.InputParameters:
        #            ParameterReadIn = model.InputParameters[key]
        #            ParameterToModify.CurrentUnits = ParameterToModify.PreferredUnits    #Before we change the paremeter, let's assume that the unit preferences will match - if they don't, the later code will fix this.
        #            ReadParameter(ParameterReadIn, ParameterToModify, model)   #this should handle all the non-special cases
        
        self.area = math.pi * (self.diameter.value * 0.5) * (self.diameter.value * 0.5)
        self.q_circulation = (self.prodwellflowrate.value * 3.6) / self.numhorizontalsections.value #need to convert prodwellflowrate in l/sec to m3/hour and then split the flow equally across all the sections
        self.velocity = self.q_circulation / self.area * 24.0
        self.x_boundary = self.y_boundary = self.z_boundary = 2.0e15 #Wanju says it ts KO to make these numbers large - "we consider it is an infinite system"
        self.y_well = 0.5 * self.y_boundary###Horizontal wellbore in the center
        self.z_well = 0.5 * self.z_boundary###Horizontal wellbore in the center
        self.alpha_fluid = self.WaterThermalConductivity.value / self.densitywawater(Tini) / self.heatcapacitywater(Tini) * 24.0 * 3600.0
        self.alpha_rock = self.krock.value / self.rhorock.value / self.cprock.value * 24.0 * 3600.0
        self.al = 365.0/4.0 * self.timestepsperyear.value
        self.time_max = model.surfaceplant.plantlifetime.value * 365.0
        self.Tini = 0.0

        #handle special cases for the parameters you added
                    
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

    def thetaY(self, yt, ye, alpha, t):
    ############################################point source/sink solution functions#########################################
    y = 0
    y1 = 0
    i = 0
    while abs(1.0 / math.sqrt(math.pi*alpha*t) * math.exp(-(yt + 2 * i*ye) * (yt + 2 * i*ye) / 4.0 / alpha / t)) > esp2: i += 1
    k = -1
    while abs(1.0 / math.sqrt(PI*alpha*t) * math.exp(-(yt + 2 * k*ye) * (yt + 2 * k*ye) / 4.0 / alpha / t)) > esp2: k -= 1
    for j in range(i, -1, -1): y += 1.0 / math.sqrt(PI*alpha*t) * math.exp(-(yt + 2 * j*ye) * (yt + 2 * j*ye) / 4.0 / alpha / t)
    for w in range(k, 0): y1 += 1.0 / math.sqrt(PI*alpha*t) * math.exp(-(yt + 2 * w*ye) * (yt + 2 * w*ye) / 4.0 / alpha / t)
    return y + y1

    def inverselaplace(self, NL, MM):
        ################################Numerical Laplace transformation algorism#########################

        V = np.zeros(50)
        Gi = np.zeros(50)
        H = np.zeros(25)
        DLN2 = 0.6931471805599453
        FI = 0.0
        SN = 0.0
        Az = 0.0
        Z = 0.0
    
        if NL != MM:
            Gi[1] = 1.0
            NH = NL // 2
            SN = 2.0 * (NH % 2) - 1.0
        
            for i in range(1,NL+1):
                Gi[i + 1] = Gi[i] * (i)
            
            H[1] = 2.0 / Gi[NH]
            for i in range(1,NH+1):
                FI = i
                H[i] = math.pow(FI, NH) * Gi[2 * i + 1] / Gi[NH - i+1] / Gi[i + 1] / Gi[i]
            
            for i in range(1,NL+1):
                V[i] = 0.0
                KBG = (i + 1) // 2
                temp = NH if i >= NH else i
                KND = temp
                for k in range(KBG, KND+1):
                    V[i] = V[i] + H[k] / Gi[i - k + 1] / Gi[2 * k - i + 1]
                V[i] = SN * V[i]
                SN = -SN
            MM = NL
    
        FI = 0.0
        Az = DLN2 / self.time_operation.value
        Toutlet = 0.0
        for k in range(1,NL+1):
            Z = Az * (k)
            Toutletl = laplace_solution(Z)
            Toutlet += Toutletl * V[k]
        Toutlet = self.Tini-Az * Toutlet
        return Toutlet
    def laplace_solution(self, sp):
    ##################################################Duhamerl convolution method for closed-loop system######################################

        Toutletl = 0.0
        ss = 1.0 / sp / chebeve_pointsource(y_well, z_well, y_well, z_well-0.078, y_boundary, z_boundary, alpha_rock, sp)
  
        Toutletl = (self.Tini - self.Tinj.value) / sp * np.exp(-sp * ss / self.q_circulation.value / 24.0 / self.densitywater(Tini) / self.heatcapacitywater(Tini) * self.l_pipe.value - sp / self.velocity * self.l_pipe.value)
        return Toutletl

    def thetaZ(self, zt, ze, alpha, t):
        y = 0
        y1 = 0
        i = 0
        while abs(1.0 / math.sqrt(math.pi*alpha*t) * math.exp(-(zt + 2 * i*ze) * (zt + 2 * i*ze) / 4.0 / alpha / t)) > esp2:
            i += 1
        k = -1
        while abs(1.0 / math.sqrt(math.pi*alpha*t) * math.exp(-(zt + 2 * k*ze) * (zt + 2 * k*ze) / 4.0 / alpha / t)) > esp2:
            k -= 1
        for j in range(i, -1, -1):
            y += 1.0 / math.sqrt(math.pi*alpha*t) * math.exp(-(zt + 2 * j*ze) * (zt + 2 * j*ze) / 4.0 / alpha / t)
        for w in range(k, 0):
            y1 += 1.0 / math.sqrt(math.pi*alpha*t) * math.exp(-(zt + 2 * w*ze) * (zt + 2 * w*ze) / 4.0 / alpha / t)
        return y + y1

    def pointsource(self, yy, zz, yt, zt, ye, ze, alpha, sp, t):
        z = 1.0 / self.rhorock.value / self.cprock.value / 4.0 * (thetaY(yt - yy, ye, alpha, t) + thetaY(yt + yy, ye, alpha, t)) * (thetaZ(zt - zz, ze, alpha, t) + thetaZ(zt + zz, ze, alpha, t)) * math.exp(-sp*t)
        return z
    ############################################Chebyshev approximation for numerical Laplace transformation integration from 1e-8 to 1e30##############################
    def Chebyshev(self, a, b, n,yy, zz, yt, zt, ye, ze, alpha, sp, func):
        bma = 0.5 * (b - a)
        bpa = 0.5 * (b + a)
        f = [func(yy, zz, yt, zt, ye, ze, alpha, sp,math.cos(math.pi * (k + 0.5) / n) * bma + bpa) for k in range(n)]
        fac = 2.0 / n
        c = [fac * np.sum([f[k] * math.cos(math.pi * j * (k + 0.5) / n)
                      for k in range(n)]) for j in range(n)]
        con=0.25*(b-a)
        fac2=1.0
        cint=np.zeros(513)
        sum=0.0
        for j in range (1,n-1):
            cint[j]=con*(c[j-1]-c[j+1])/j
            sum += fac2*cint[j]
            fac2=-fac2
            cint[n-1]=con*c[n-2]/(n-1)
            sum += fac2*cint[n-1]
            cint[0]=2.0*sum   
        d=0.0
        dd=0.0
        y = (2.0 * b - a - b) * (1.0 / (b - a))
        y2 = 2.0 * y   
        for j in range (n-1,0,-1):
            sv=d
            d=y2*d-dd+cint[j]
            dd=sv   
        return y * d - dd + 0.5 *cint[0]   # Last step is different

    def chebeve_pointsource(self, yy, zz, yt, zt, ye, ze, alpha, sp):
        m=32
        t_1 = 1.0e-8
        n = int(math.log10(1.0e4 / 1.0e-8) + 1)
        #t_2 = t_1 * 10 ** n
        a = t_1
        temp = 0.0
        for i in range(1, n + 1):
            b = a * 10.0
            temp = temp + Chebyshev(a,b,m,yy, zz, yt, zt, ye, ze, alpha, sp,pointsource)
            a = b
        return temp + (1 / sp * (math.exp(-sp * 1.0e5) - math.exp(-sp * 1.0e30))) / (ye * ze) / self.rhorock.value / self.cprock.value

    def Calculate(self, model:AdvModel) -> None:
        """
        The Calculate function is the main function that runs all the calculations for this child.
        
        :param self: Reference the class itself
        :param model (AdvModel): The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)

        #before we calculate anything, let's see if there is a suitable result already in the database
        key = self.CheckForExistingResult(model, os.path.abspath(__file__))
        if key == None: 
            super().Calculate(model)    #run calculation because there was nothing in the database
            
            with open("temperature.txt", "w") as fp_temperature:
                while self.time_operation.value <= time_max:
                    year=1   #MIR figure out how to calculate year ands extract Tini from reserv Tresoutput array
                    Tini = model.Reservoir.Tresoutput[year].Value
                    Toutlet=inverselaplace(16, 0)
                    self.ProducedTemperature[].value = Toutlet
                    self.time_operation.value += al

            #store the calculate result and associated object paremeters in the database
            resultkey = self.store_result(model, str(__class__), os.path.abspath(__file__), self)
            if resultkey == None: model.logger.warn("Failed To Store "+ str(__class__) + " " + os.path.abspath(__file__))
            else: model.logger.info("stored " + str(__class__) + " " + os.path.abspath(__file__) + " as: " + resultkey)

        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)
        
    def __str__(self):
        return "CLWellBores"
