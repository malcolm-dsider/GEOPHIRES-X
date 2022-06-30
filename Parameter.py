import sys
from array import array
from dataclasses import dataclass, field
from enum import IntEnum
import jsons
from forex_python.converter import CurrencyRates, CurrencyCodes
import pint
from Units import *

ureg = pint.UnitRegistry()
ureg.load_definitions('GEOPHIRES3_newunits.txt') 

@dataclass
class ParameterEntry(jsons.JsonSerializable):
    """A dataclass that contains the three fields that are being read from thje user-provided file

    Args:
        jsons.JsonSerializable (???): Makes thi class serializable
    Attributes:
        Name (str): The official name of the parmeter that the user wants to set
        sValue (str): The value that the user wants it to be set to, as a string.
        Comment (str): The optional comment that the user provided with that parameter in the text file
    """
    Name: str
    sValue: str
    Comment: str

@dataclass
class OutputParameter:
    """A dataclass that is the holder values that are provide to the user as output but are claculated internally by GEOPHIRES

    Attributes:
        Name (str): The official name of that output
        value: (any): the value of this parameter - can be int, float, text, bool, list, etc...
        ToolTipText (str): Text to place in a ToolTip in a UI
        UnitType (IntEnum): The class of units that parameter falls in (i.e., "length", "time", "area"...)
        PreferredUnits (Enum): The units as reqwuired by GEOPHIRES (or your algorithms)
        CurrentUnits (Enum): The units that the parameter is provided in (usually the sanme PreferredUnits)
        UnitsMatch (boolean): Internal flag set when units are different
    """
    Name: str = ""
    value:int = 0
    ToolTipText: str = "This is ToolTip Text"
    UnitType:IntEnum = Units.NONE
    PreferredUnits:Enum = Units.NONE
    CurrentUnits:Enum = PreferredUnits    #set to PreferredUnits by default assuming that the current units are the preferred units - they will only change if the read function reads a different unit associated with a parameter
    UnitsMatch:bool = True

@dataclass
class Parameter:
    """
     A dataclass that is the holder values that are provided (optionally) by the user.  These are all the inout values to the model.  They all must have a default value that is reasonable and will provide a reasonable result if not changed.

    Attributes:
        Name (str): The official name of that output
        Required (bool, False): Is this parameter required to be set?  See user manual.
        Provided (bool, False): Has this value been provided by the user?
        Valid (bool, True): has this value been successfully validated? 
        ErrMessage (str): the error message that the user sees if the va;ue they provide does not pass validation - by default, it is: "assuming default value (see manual)"
        InputComment (str): The optional comment that the user provided with that parameter in the text file
        ToolTipText (str): Text to place in a ToolTip in a UI
        UnitType (IntEnum): The class of units that parameter falls in (i.e., "length", "time", "area"...)
        PreferredUnits (Enum): The units as reqwuired by GEOPHIRES (or your algorithms)
        CurrentUnits (Enum): The units that the parameter is provided in (usually the sanme PreferredUnits)
        UnitsMatch (boolean): Internal flag set when units are different
    """
    Name: str = ""
    Required: bool = False
    Provided: bool = False
    Valid: bool = True
    ErrMessage: str = "assume default value (see manual)"
    InputComment: str = ""
    ToolTipText: str = "This is ToolTip Text"
    UnitType:IntEnum = Units.NONE
    PreferredUnits:Enum = Units.NONE
    CurrentUnits:Enum = PreferredUnits    #set to PreferredUnits assuming that the current units are the preferred units - they will only change if the read function reads a different unit associated with a parameter
    UnitsMatch:bool = True


@dataclass
class boolParameter(Parameter):
    """
    boolParameter: a dataclass that stores the values for a Boolean value.  Includes the default value and the valdiation values (if appropriate).  Child of Parameter, so it gets all the Attributes of that class.

    Attributes:
        value (bool): The value of that parameter
        DefaultValue (bool, True):  The default value of that parameter
    """
    value: bool = True
    DefaultValue: bool = True

@dataclass
class intParameter(Parameter):
    """
    intParameter: a dataclass that stores the values for a Integer value.  Includes the default value and the valdiation values (if appropriate).  Child of Parameter, so it gets all the Attributes of that class.

    Attributes:
        value (int): The value of that parameter
        DefaultValue (int, 0):  The default value of that parameter
        AllowableRange (list): A list of the valid values
    """
    value: int = 0
    DefaultValue: int = 0
    AllowableRange: list[int] = field(default_factory=list)
 
@dataclass
class floatParameter(Parameter):
    """
    floatParameter: a dataclass that stores the values for a Float value.  Includes the default value and the valdiation values (if appropriate).  Child of Parameter, so it gets all the Attributes of that class.

    Attributes:
        value (float): The value of that parameter
        DefaultValue (float, 0.0):  The default value of that parameter
        Min (float, -1.8e308): minimum valid value - not that it is set to a very small value, which means that any value is valid by default
        Min (float, 1.8e308): maximum valid value - not that it is set to a very large value, which means that any value is valid by default 
    """
    value: float = 0.0
    DefaultValue: float = 0.0
    Min: float = -1.8e308
    Max: float = 1.8e308
   
@dataclass
class strParameter(Parameter):
    """
    strParameter: a dataclass that stores the values for a String value.  Includes the default value and the valdiation values (if appropriate).  Child of Parameter, so it gets all the Attributes of that class.

    Attributes:
        value (str): The value of that parameter
        DefaultValue (str, ""):  The default value of that parameter
    """
    value: str = ""
    DefaultValue: str = ""

@dataclass
class listParameter(Parameter):
    """
    listParameter: a dataclass that stores the values for a List of values.  Includes the default value and the valdiation values (if appropriate).  Child of Parameter, so it gets all the Attributes of that class.

    Attributes:
        value (list): The value of that parameter
        DefaultValue (list, []):  The default value of that parameter
        Min (float, -1.8e308): minimum valid value of each value in the list - not that it is set to a very small value, which means that any value is valid by default
        Min (float, 1.8e308): maximum valid value of each va;ue in the list - not that it is set to a very large value, which means that any value is valid by default 
    """
    value:  list[int] = field(default_factory=list)
    DefaultValue: list[int] = field(default_factory=list)
    Min: float = -1.8e308
    Max: float = 1.8e308

def ReadParameter(ParameterReadIn: ParameterEntry, ParamToModify, model):
    """
    ReadParameter: A method to take a single ParameterEntry object and use it to update the associated Parameter.  Does validation as well as Unit and Currency conversion

    Args:
        ParameterReadIn (ParameterEntry): The value the user wants to change
        ParamToModify (Parameter): The Parameter that will be modified (assuming it passes validation and conversion)
        model (Model):  The container class of the application, giving access to everything else, including the logger

    Returns:
        None

    Yields:
        None
    """
    model.logger.info("Init " + str(__name__) + ": " + sys._getframe(  ).f_code.co_name + " for " + ParamToModify.Name)
    if isinstance(ParamToModify, boolParameter) and isinstance(ParamToModify, strParameter):        #these Parameter Types don't have units so don't do anything fancy, and ingore it if the user has supplied units
        if isinstance(ParamToModify, boolParameter): ParamToModify.value = bool(ParameterReadIn.sValue)
        else: ParamToModify.value = ParameterReadIn.sValue
        ParamToModify.Provided = True      #set provided to true because we are using a user provide value now
        ParamToModify.Valid = True      #set Valid to true because it passed the validation tests
        model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)
        return

    #deal with the case where the value has a unit involved - that will be indicated by a space in it
    if ParameterReadIn.sValue.__contains__(" "):
        new_str = CovertUnits(ParamToModify, ParameterReadIn.sValue,  model)
        if len(new_str) > 0: ParameterReadIn.sValue = new_str
    else:
        ParamToModify.CurrentUnits = ParamToModify.PreferredUnits     #The value came in without any units, so it must be using the default PreferredUnits
        ParamToModify.UnitsMatch = True

    if isinstance(ParamToModify, intParameter):
        New_val = int(ParameterReadIn.sValue)
        if New_val == ParamToModify.value: return   #We have nothing to change - user provide value that was the same as the existing value (likely, the default value)
        if not (New_val in ParamToModify.AllowableRange):   #user provided value is out of range, so announce it, leave set to whatever it was set to (default value)
            if len(ParamToModify.ErrMessage) > 0: print("Warning: Parameter given (" + str(New_val) +") for " + ParamToModify.Name + " outside of valid range. GEOPHIRES will " + ParamToModify.ErrMessage)
            if len(ParamToModify.ErrMessage) > 0: model.logger.warning("Parameter given (" + str(New_val) +") for " + ParamToModify.Name + " outside of valid range. GEOPHIRES will " + ParamToModify.ErrMessage)
            model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)
            return
        else:   #All is good
            ParamToModify.value = New_val     #set the new value
            ParamToModify.Provided = True      #set provided to true because we are using a user provide value now
            ParamToModify.Valid = True      #set Valid to true because it passed the validation tests
    elif isinstance(ParamToModify, floatParameter):
        New_val = float(ParameterReadIn.sValue)
        if New_val == ParamToModify.value:
            model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)
            return #We have nothing to change - user provide value that was the same as the existing value (likely, the default value)
        if (New_val < float(ParamToModify.Min)) or (New_val > float(ParamToModify.Max)):   #user provided value is out of range, so announce it, leave set to whatever it was set to (default value)
            if len(ParamToModify.ErrMessage) > 0: print("Warning: Parameter given (" + str(New_val) +") for " + ParamToModify.Name + " outside of valid range. GEOPHIRES will " + ParamToModify.ErrMessage)
            if len(ParamToModify.ErrMessage) > 0: model.logger.warning("Parameter given (" + str(New_val) +") for " + ParamToModify.Name + " outside of valid range. GEOPHIRES will " + ParamToModify.ErrMessage)
            model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)
            return
        else:   #All is good
            ParamToModify.value = New_val     #set the new value
            ParamToModify.Provided = True      #set provided to true because we are using a user provide value now
            ParamToModify.Valid = True      #set Valid to true because it passed the validation tests
    elif isinstance(ParamToModify, listParameter):
        New_val = float(ParameterReadIn.sValue)
        if (New_val < float(ParamToModify.Min)) or (New_val > float(ParamToModify.Max)):   #user provided value is out of range, so announce it, leave set to whatever it was set to (default value)
            if len(ParamToModify.ErrMessage) > 0: print("Warning: Parameter given (" + str(New_val) +") for " + ParamToModify.Name + " outside of valid range. GEOPHIRES will " + ParamToModify.ErrMessage)
            if len(ParamToModify.ErrMessage) > 0: model.logger.warning("Parameter given (" + str(New_val) +") for " + ParamToModify.Name + " outside of valid range. GEOPHIRES will " + ParamToModify.ErrMessage)
            model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)
            return
        else:   #All is good.  With a list, we have to use the last character of the Description to get the position.  I.e., "Gradient 1" should yield a position = 0 ("1" - 1)
            parts = ParameterReadIn.Name.split(' ')
            position = int(parts[1]) - 1
            if position >= len(ParamToModify.value): ParamToModify.value.append(New_val)   #we are adding to the list, so use append
            else: #we are replacing a value, so pop the value we want to replace, then insert a new one
                ParamToModify.value.pop(position)
                ParamToModify.value.insert(position, New_val)
    elif isinstance(ParamToModify, boolParameter):
        if ParameterReadIn.sValue == "0": New_val = False
        else: New_val = True
        if New_val == ParamToModify.value:
           model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)
           return   #We have nothing to change - user provide value that was the same as the existing value (likely, the default value)
        ParamToModify.value = New_val     #set the new value
        ParamToModify.Provided = True      #set provided to true because we are using a user provide value now
        ParamToModify.Valid = True      #set Valid to true because it passed the validation tests
    elif isinstance(ParamToModify, strParameter):
        New_val = str(ParameterReadIn.sValue)
        if New_val == ParamToModify.value: return   #We have nothing to change - user provide value that was the same as the existing value (likely, the default value)
        ParamToModify.value = New_val     #set the new value
        ParamToModify.Provided = True      #set provided to true because we are using a user provide value now
        ParamToModify.Valid = True      #set Valid to true because it passed the validation tests

    model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)
    
def CovertUnits(ParamToModify, strUnit: str,  model) -> str:
    """
    CovertUnits gets called if a unit version is needed: either currency or standard units like F to C or m to ft

    Args:
        ParamToModify (Parameter): The Parameter that will be modified (assuming it passes validation and conversion)
        strUnit (str): A string containing the value to be converted along with the units it is current in.  The ubnits to convert to are set by the PreferredUnits of ParamToModify
        model (Model):  The container class of the application, giving access to everything else, including the logger

    Returns:
        str: The new value as a string (without the units, because they are already held in PreferredUnits of ParamToModify)
    """
    model.logger.info("Init " + str(__name__) + ": " + sys._getframe(  ).f_code.co_name + " for " + ParamToModify.Name)
    
    #deal with the currency case
    if ParamToModify.UnitType == Units.CURRENCY:
        prefFactor = 1.0
        PrefperYear = ""
        CurrperYear = ""
        prefType = ParamToModify.PreferredUnits.value
        parts = strUnit.split(' ')
        val = parts[0].strip()
        currType = parts[1].strip()
        if prefType == currType:    #user has provide a currents that is the curreny expected, so just strip off the currency
            strUnit = str(val)
            ParamToModify.UnitsMatch = True
            ParamToModify.CurrentUnits = currType
            return strUnit
            
        if prefType.endswith("/yr"):  #handle the /yr situation
            PrefperYear = "/yr"
            prefType = prefType.replace("/yr", "")
        if currType.endswith("/yr"):
            CurrperYear = "/yr"
            currType = currType.replace("/yr", "")
            
        if prefType.endswith("/kwh"):  #handle the /yr situation
            PrefperYear = "/kwh"
            prefType = prefType.replace("/kwh", "")
        if currType.endswith("/kwh"):
            CurrperYear = "/kwh"
            currType = currType.replace("/kwh", "")

        if prefType.startswith("MUSD") and currType.startswith("USD"):     # if the type are not equal, the user provided that is not the preferred type.  Let's try to deal with first the simple case where the require units are MUSD (or KUSD), and the user provided USD (or KUSD)
            ParamToModify.UnitsMatch = False
            ParamToModify.CurrentUnits = currType + CurrperYear
            val = float(val) / 1000000.0
            strUnit = str(val)
            prefType = prefType.replace("M","", 1)
        elif prefType.startswith("KUSD") and currType.startswith("USD"):
            ParamToModify.UnitsMatch = False
            ParamToModify.CurrentUnits = currType + CurrperYear
            val = float(val) / 1000.0
            strUnit = str(val)
            prefType = prefType.replace("K","", 1)
        elif prefType.startswith("USD") and currType.startswith("MUSD"):
            ParamToModify.CurrentUnits = currType + CurrperYear
            ParamToModify.UnitsMatch = False
            val = float(val) * 1000000.0
            strUnit = str(val)
            currType = prefType.replace("M","", 1)
        elif prefType.startswith("USD") and currType.startswith("KUSD"):
            ParamToModify.UnitsMatch = False
            ParamToModify.CurrentUnits = currType + CurrperYear
            val = float(val) / 1000.0
            strUnit = str(val)
            currType = prefType.replace("K","", 1)

        if prefType != currType:      #Now lets deal with the case where the units still don't match.  Could be a straight EUR to USD conversion, but the units need to be MEUR to MUSD.
            cc = CurrencyCodes()
            symbol = cc.get_symbol(currType)     #if we have a symbol for a currency type, then the type is known to the library.  If we don't try dsome tricks to make it into something it does do recognize
            if symbol == None:
                if currType.startswith('M') or currType.startswith('m') or currType.startswith('K') or currType.startswith('k'):   # maybe they put a K or k in front of a currency type (i,e. KUSD) to denote kilo or an M or m (MUSD) to denote million (but note that some currency symbols start with M or K, so we can't assume anything)
                    if currType.startswith('M'): currType2 = currType.replace("M","", 1)
                    if currType.startswith('m'): currType2 = currType.replace("m","", 1)
                    x = cc.get_symbol(currType2)   #check to see if we get a symbol from that type.  If we do, then we know they used MUSD
                    if x == None:
                        if currType.startswith('K'): currType2 = currType.replace("K","", 1)
                        if currType.startswith('k'): currType2 = currType.replace("k","", 1)
                        x = cc.get_symbol(currType)
                        if x == None:    #No idea what they did!!!
                            print("Error: GEOPHIRES failed to convert your currency for " + ParamToModify.Name + " to something it understands. You gave " + strUnit + " - Are these currency units defined for forex-python?  or perhaps the currency server is down?  Please change your units to " + ParamToModify.PreferredUnits.value + "to contine. Cannot continue unless you do.  Exiting.")
                            model.logger.critical("Error: GEOPHIRES failed to convert your currency for " + ParamToModify.Name + " to something it understands. You gave " + strUnit + " - Are these currency units defined for forex-python?  or perhaps the currency server is down?  Please change your units to " + ParamToModify.PreferredUnits.value + "to contine. Cannot continue unless you do.  Exiting.")
                            sys.exit()
                        else:
                            currType  = currType2
                            prefFactor = 1/1000.0
                    else:
                        currType  = currType2
                        prefFactor = 1/1000000.0

            if prefType.startswith("MUSD"):     # User has used the MUSD as the shorthand preferred unit.  This means nothing to the exchange rate library, change it to something that the library understands, and set a multiplier factor
                prefFactor = 1000000.0 * prefFactor
                prefType = prefType.replace("M","", 1)
            elif prefType.startswith("KUSD"):
                prefFactor = 1000.0 * prefFactor
                prefType = prefType.replace("K","", 1)
            try:
                cr = CurrencyRates()
                conv_rate = cr.get_rate(currType, prefType)
            except BaseException as ex:
                print (str(ex))
                print("Error: GEOPHIRES failed to convert your currency for " + ParamToModify.Name + " to something it understands. You gave " + strUnit + " - Are these currency units defined for forex-python?  or perhaps the currency server is down?  Please change your units to " + ParamToModify.PreferredUnits.value + "to contine. Cannot continue unless you do.  Exiting.")
                model.logger.critical(str(ex))
                model.logger.critical("Error: GEOPHIRES failed to convert your currency for " + ParamToModify.Name + " to something it understands. You gave " + strUnit + " - Are these currency units defined for forex-python?  or perhaps the currency server is down?  Please change your units to " + ParamToModify.PreferredUnits.value + "to contine. Cannot continue unless you do.  Exiting.")
                sys.exit()                
            New_val = (conv_rate * float(val)) / prefFactor
            strUnit = str(New_val)
            ParamToModify.UnitsMatch = False
            ParamToModify.CurrentUnits = parts[1]
        else:
            if len(PrefperYear) > 0: prefType = prefType + PrefperYear   #set it back the way it was
            if len(CurrperYear) > 0: currType = currType + CurrperYear
            parts = strUnit.split(' ')
            strUnit = parts[0]

    else:  #must be something other than boolean, string, or currency
        if isinstance(strUnit, pint.Quantity):
            val = ParamToModify.value
            currType = str(strUnit)
        else: 
            parts = strUnit.split(' ')
            val = parts[0].strip()
            currType = parts[1].strip()
        #check to see if the units provided (CurrentUnits) are the same as the preferred units.  In that case, we don't need to do anything.
        try:
            Old_valQ = ureg.Quantity(0.000, str(ParamToModify.CurrentUnits.value))      #Make a Pint Quanity out of the old value: the amount of the unit doesn't matter, just the units, so I set the amount to 0
            New_valQ = ureg.Quantity(float(val), currType)      #Make a Pint Quanity out of the new value
        except BaseException as ex:
            print (str(ex))
            print("Error: GEOPHIRES failed to initialize your units for " + ParamToModify.Name + " to something it understands. You gave " + strUnit + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?  Cannot continue.  Exiting.")
            model.logger.critical(str(ex))
            model.logger.critical("Error: GEOPHIRES failed to initialize your units for " + ParamToModify.Name + " to something it understands. You gave " + strUnit + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?  Cannot continue.  Exiting.")
            sys.exit()

        if Old_valQ.units != New_valQ.units:    #do the transformation only if the units don't match
            ParamToModify.CurrentUnits = LookupUnits(currType, ParamToModify.UnitType)
            try:
                New_valQ.ito(Old_valQ) #ParamToModify.PreferredUnits.value)    #update The quanity to the preferred units so we don't have to change the underlying calculations.  This assumes that PInt recognizes our unit.  If we have a new unit, we have to add it to the Pint configuration text file
            except BaseException as ex:
                print (str(ex))
                print("Error: GEOPHIRES failed to convert your units for " + ParamToModify.Name + " to something it understands. You gave " + strUnit + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?  Cannot continue.  Exiting.")
                model.logger.critical(str(ex))
                model.logger.critical("Error: GEOPHIRES failed to convert your units for " + ParamToModify.Name + " to something it understands. You gave " + strUnit + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?  Cannot continue.  Exiting.")
                sys.exit()

            strUnit =str(New_valQ.magnitude)      #set sValue to the value based on the new units - don't add units to it - it should just be a raw number
            ParamToModify.UnitsMatch = False
        else: #if we come here, we must have a unit declarred, but the unit must be the same as the preferred unit, so we need to just get ride of the extra text after the space
            parts = strUnit.split(' ')
            strUnit = parts[0]

    model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)
    return strUnit

def CovertUnitsBack(ParamToModify, model):
    """
    CovertUnitsBack: Converts units back to what the user specified they as.  It does this so that the user can see them in the report as the ubnits they specified.  We know that because CurrentUnits contains the desired units

    Args:
        ParamToModify (Parameter): The Parameter that will be modified.
        model (Model):  The container class of the application, giving access to everything else, including the logger
    """
    model.logger.info("Init " + str(__name__) + ": " + sys._getframe(  ).f_code.co_name + " for " + ParamToModify.Name)
    
    #deal with the currency case
    if ParamToModify.UnitType == Units.CURRENCY:
        prefType = ParamToModify.PreferredUnits.value
        currType = ParamToModify.CurrentUnits

        #Let's try to deal with first the simple conversion where the require units are MUSD (or KUSD), and the user provided USD (or KUSD)
        if prefType.startswith("MUSD") and currType.startswith("USD"):
            ParamToModify.value = ParamToModify.value * 1000000.0
            model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)
            return
        elif prefType.startswith("KUSD") and currType.startswith("USD"):
            ParamToModify.value = ParamToModify.value * 1000.0
            model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)
            return
        elif prefType.startswith("USD") and currType.startswith("MUSD"):
            ParamToModify.value = ParamToModify.value / 1000000.0
            model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)
            return
        elif prefType.startswith("USD") and currType.startswith("KUSD"):
            ParamToModify.value = ParamToModify.value / 1000.0
            model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)
            return

        #Now lets deal with the case where the units still don't match.  Could be a straight EUR to USD conversion, but the units need to be MEUR to MUSD.
        prefFactor = 1.0
        PrefperYear = ""
        CurrperYear = ""
        val = ParamToModify.value

        #handle the /yr situation
        if prefType.endswith("/yr"):
            PrefperYear = "/yr"
            prefType = prefType.replace("/yr", "")
        if currType.endswith("/yr"):
            CurrperYear = "/yr"
            currType = currType.replace("/yr", "")
        
        #handle the /kwh situation
        if prefType.endswith("/kwh"):
            PrefperYear = "/kwh"
            prefType = prefType.replace("/kwh", "")
        if currType.endswith("/kwh"):
            CurrperYear = "/kwh"
            currType = currType.replace("/kwh", "")

            #start the currency conversion process
        cc = CurrencyCodes()
        symbol = cc.get_symbol(currType)     #if we have a symbol for a currency type, then the type is known to the library.  If we don't try dsome tricks to make it into something it does do recognize
        if symbol == None:
            if currType.startswith('M') or currType.startswith('m') or currType.startswith('K') or currType.startswith('k'):   # maybe they put a K or k in front of a currency type (i,e. KUSD) to denote kilo or an M or m (MUSD) to denote million (but note that some currency symbols start with M or K, so we can't assume anything)
                if currType.startswith('M'): currType2 = currType.replace("M","", 1)
                if currType.startswith('m'): currType2 = currType.replace("m","", 1)
                x = cc.get_symbol(currType2)   #check to see if we get a symbol from that type.  If we do, then we know they used MUSD
                if x == None:
                    if currType.startswith('K'): currType2 = currType.replace("K","", 1)
                    if currType.startswith('k'): currType2 = currType.replace("k","", 1)
                    x = cc.get_symbol(currType)
                    if x == None:    #No idea what they did!!!
                        print("Error: GEOPHIRES failed to convert your currency for " + ParamToModify.Name + " to something it understands. You gave " + currType + " - Are these currency units defined for forex-python?  or perhaps the currency server is down?  Please change your units to " + ParamToModify.PreferredUnits.value + "to contine. Cannot continue unless you do.  Exiting.")
                        model.logger.critical("Error: GEOPHIRES failed to convert your currency for " + ParamToModify.Name + " to something it understands. You gave " + currType + " - Are these currency units defined for forex-python?  or perhaps the currency server is down?  Please change your units to " + ParamToModify.PreferredUnits.value + "to contine. Cannot continue unless you do.  Exiting.")
                        sys.exit()
                    else:
                        currType  = currType2
                        prefFactor = 1/1000.0
                else:
                    currType  = currType2
                    prefFactor = 1/1000000.0

        if prefType.startswith("MUSD"):     # User has used the MUSD as the shorthand preferred unit.  This means nothing to the exchange rate library, change it to something that the library understands, and set a multiplier factor
            prefFactor = 1000000.0 * prefFactor
            prefType = prefType.replace("M","", 1)
        elif prefType.startswith("KUSD"):
            prefFactor = 1000.0 * prefFactor
            prefType = prefType.replace("K","", 1)
        try:
            cr = CurrencyRates()
            conv_rate = cr.get_rate(currType, prefType)
        except BaseException as ex:
            print (str(ex))
            print("Error: GEOPHIRES failed to convert your currency for " + ParamToModify.Name + " to something it understands. You gave " + currType + " - Are these currency units defined for forex-python?  or perhaps the currency server is down?  Please change your units to " + ParamToModify.PreferredUnits.value + "to contine. Cannot continue unless you do.  Exiting.")
            model.logger.critical(str(ex))
            model.logger.critical("Error: GEOPHIRES failed to convert your currency for " + ParamToModify.Name + " to something it understands. You gave " + currType + " - Are these currency units defined for forex-python?  or perhaps the currency server is down?  Please change your units to " + ParamToModify.PreferredUnits.value + "to contine. Cannot continue unless you do.  Exiting.")
            sys.exit()                
        New_val = (conv_rate * float(val)) / prefFactor
        ParamToModify.value - New_val
        ParamToModify.UnitsMatch = False
        model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)
        return

    else:  #must be something other than currency
        if isinstance(ParamToModify.CurrentUnits, pint.Quantity):
            val = ParamToModify.CurrentUnits.magnitude
            currType = str(ParamToModify.CurrentUnits.units)
        else:
            if " " in ParamToModify.CurrentUnits.value:
                parts = ParamToModify.CurrentUnits.value.split(' ')
                val = parts[0].strip()
                currType = parts[1].strip()
            else:
                val = ParamToModify.value
                currType = ParamToModify.CurrentUnits.value

        try:
            if isinstance(ParamToModify.PreferredUnits, pint.Quantity): prefQ = ParamToModify.PreferredUnits
            else: prefQ = ureg.Quantity(float(val), str(ParamToModify.PreferredUnits.value))      #Make a Pint Quanity out of the old value
            if isinstance(ParamToModify.CurrentUnits, pint.Quantity): currQ = ParamToModify.CurrentUnits
            else: currQ = ureg.Quantity(float(val), currType)      #Make a Pint Quanity out of the new value
        except BaseException as ex:
            print (str(ex))
            print("Error: GEOPHIRES failed to initialize your units for " + ParamToModify.Name + " to something it understands. You gave " + currType + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?  Cannot continue.  Exiting.")
            model.logger.critical(str(ex))
            model.logger.critical("Error: GEOPHIRES failed to initialize your units for " + ParamToModify.Name + " to something it understands. You gave " + currType + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?  Cannot continue.  Exiting.")
            sys.exit()
        try:
            currQ = prefQ.to(currQ) #update The quanity back to the current units (the units that we started with) units so the display will be in the right units
        except BaseException as ex:
            print (str(ex))
            print("Error: GEOPHIRES failed to convert your units for " + ParamToModify.Name + " to something it understands. You gave " + currType + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?  Cannot continue.  Exiting.")
            model.logger.critical(str(ex))
            model.logger.critical("Error: GEOPHIRES failed to convert your units for " + ParamToModify.Name + " to something it understands. You gave " + currType + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?  Cannot continue.  Exiting.")
            sys.exit()

        #rest the vakue
        ParamToModify.value = currQ.magnitude
    model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe(  ).f_code.co_name)

def LookupUnits(sUnitText:str, uType:Enum)->Enum:
    """
    LookupUnits Given a unit class and a text string, this will return the string from the Enumneration if it is there (or return noting if it is not)

    Args:
        sUnitText (str): The units desired to be checked (e.g., "ft", "degF")
        uType (Enum): The UnitClass

    Returns:
        Enum: The Enumerated Text as string
    """
    if uType == Units.LENGTH: MyEnum = LengthUnit
    elif uType == Units.AREA: MyEnum = AreaUnit
    elif uType == Units.VOLUME: MyEnum = VolumeUnit
    elif uType == Units.DENSITY: MyEnum = DensityUnit
    elif uType == Units.TEMPERATURE: MyEnum = TemperatureUnit
    elif uType == Units.PRESSURE: MyEnum = PressureUnit
    elif uType == Units.TIME: MyEnum = TimeUnit
    elif uType == Units.FLOWRATE: MyEnum = FlowRateUnit
    elif uType == Units.TEMP_GRADIENT: MyEnum = TemperatureGradientUnit
    elif uType == Units.DRAWDOWN: MyEnum = DrawdownUnit
    elif uType == Units.IMPEDANCE: MyEnum = ImpedanceUnit
    elif uType == Units.PRODUCTIVITY_INDEX: MyEnum = ProductivityIndexUnit
    elif uType == Units.INJECTIVITY_INDEX: MyEnum = InjectivityIndexUnit
    elif uType == Units.HEAT_CAPACITY: MyEnum = HeatCapacityUnit
    elif uType == Units.THERMAL_CONDUCTIVITY: MyEnum = ThermalConductivityUnit
    elif uType == Units.CURRENCY: MyEnum = CurrencyUnit
    elif uType == Units.PERCENT: MyEnum = PercentUnit
    elif uType == Units.ELECTRICITY: MyEnum = ElectricityUnit
    elif uType == Units.HEAT: MyEnum = HeatUnit
    elif uType == Units.AVAILABILITY: MyEnum = AvailabilityUnit

    for item in MyEnum:
        if item.value == sUnitText:
            return item
    return None

def ConvertOutputUnits(oparam:OutputParameter, model):
    """
    ConvertOutputUnits Given an output paremeter, convert the value(s) from what they contain (as calculated by GEOPHIRES) to what the user specified as what they want for outputs.  Conversion happens inline.

    Args:
        oparam (OutputParemeter): The parameter you want to be converted (value or list of values).  Because Parameters know the PreferredUnits and CurrentUnits, this routine knows what to do.
        model (Model):  The container class of the application, giving access to everything else, including the logger

    Returns:
        None
    """
    if isinstance(oparam.value, str): return   #strings have no units
    elif isinstance(oparam.value, bool): return   #booleans have no units
    for UnitName in model.outputs.ParameterDict.items():
        if oparam.UnitType.name == UnitName[0]:
            desiredType = model.outputs.ParameterDict[UnitName[0]].value
            if oparam.PreferredUnits.value != desiredType:
                if isinstance(oparam.value, float) or isinstance(oparam.value, int): #this is a simple unit conversion
                    try:
                        fromQ = ureg.Quantity(oparam.value, str(oparam.PreferredUnits.value))      #Make a Pint Quanity out of the from value
                        toQ = ureg.Quantity(0, desiredType)      #Make a Pint Quanity out of the new value
                    except BaseException as ex:
                        print (str(ex))
                        print("Warning: GEOPHIRES failed to initialize your units for " + oparam.Name + " to something it understands. You gave " + desiredType + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?  continuing without output conversion.")
                        model.logger.warning(str(ex))
                        model.logger.warning("Warning: GEOPHIRES failed to initialize your units for " + oparam.Name + " to something it understands. You gave " + desiredType + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?    continuing without output conversion.")
                        return
                    try:
                        toQ = fromQ.to(toQ) #update The quanity to the units that the user wanted
                    except BaseException as ex:
                        print (str(ex))
                        print("Warning: GEOPHIRES failed to convert your units for " + oparam.Name + " to something it understands. You gave " + desiredType + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?    continuing without output conversion.")
                        model.logger.warning(str(ex))
                        model.logger.warning("Warning: GEOPHIRES failed to convert your units for " + oparam.Name + " to something it understands. You gave " + desiredType + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?   continuing without output conversion.")
                        return

                    #rest the value and current units
                    oparam.value = toQ.magnitude
                    oparam.CurrentUnits = LookupUnits(desiredType, oparam.UnitType)
                if isinstance(oparam.value, array):
                    i = 0
                    for arrayval in oparam.value:
                        try:
                            fromQ = ureg.Quantity(oparam.value[i], str(oparam.PreferredUnits.value))      #Make a Pint Quanity out of the from value
                            toQ = ureg.Quantity(0, desiredType)      #Make a Pint Quanity out of the new value
                        except BaseException as ex:
                            print (str(ex))
                            print("Warning: GEOPHIRES failed to initialize your units for " + oparam.Name + " to something it understands. You gave " + desiredType + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?  continuing without output conversion.")
                            model.logger.warning(str(ex))
                            model.logger.warning("Warning: GEOPHIRES failed to initialize your units for " + oparam.Name + " to something it understands. You gave " + desiredType + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?    continuing without output conversion.")
                            return
                        try:
                            toQ = fromQ.to(toQ) #update The quanity to the units that the user wanted
                        except BaseException as ex:
                            print (str(ex))
                            print("Warning: GEOPHIRES failed to convert your units for " + oparam.Name + " to something it understands. You gave " + desiredType + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?    continuing without output conversion.")
                            model.logger.warning(str(ex))
                            model.logger.warning("Warning: GEOPHIRES failed to convert your units for " + oparam.Name + " to something it understands. You gave " + desiredType + " - Are the units defined for Pint library, or have you defined them in the user defined units file (GEOPHIRES3_newunits)?   continuing without output conversion.")
                            return

                        #rest the value and current units
                        oparam.value[i] = toQ.magnitude
                        oparam.CurrentUnits = LookupUnits(desiredType, oparam.UnitType)
                        i = i +1