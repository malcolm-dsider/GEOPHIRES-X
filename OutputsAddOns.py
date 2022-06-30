import sys
import Outputs
import Model

NL="\n"

class OutputsAddOns(Outputs):
    """description of class"""
    def PrintOutputs(model:Model):
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe(  ).f_code.co_name)

        # Do the original output
        super().PrintOutputs(model)   # initialize the parent parameters and variables

        if model.economics.AddOnCAPEXTotal.value + model.economics.AddOnOPEXTotalPerYear.value == 0: return   #don't bother if we have nothing to report.

        #now do AddOn output, which will append to the original output
        #---------------------------------------
        #write results to output file and screen
        #---------------------------------------
        try:
            with open('HDR.out','a', encoding='UTF-8') as f:
                f.write(NL)
                f.write(NL)
                f.write("                                ***ADDON ECONOMICS***"+ NL)
                f.write(NL)
                f.write(f"      Adjusted CAPEX (after incentives, grants, etc)    {model.economics.AdjustedCAPEX.value:10.2f} M$" + NL)
                f.write(f"      Adjusted OPEX (after incentives, grants, etc)     {model.economics.AdjustedOPEX.value:10.2f} M$" + NL)
                f.write(f"      NPV                                               {model.economics.AddOnNPV.value:10.2f} M$" + NL)
                f.write(f"      IRR                                               {model.economics.AddOnIRR.value:10.2f} %" + NL)
                f.write(f"      VIR                                               {model.economics.AddOnVIR.value:10.2f}" + NL)
                f.write(f"      MOIC                                              {model.economics.AddOnMOIC.value:10.2f}" + NL)
                f.write(f"      Payback Period                                    {model.economics.AddOnPaybackPeriod.value:10.2f} Years" + NL)
                f.write(f"      Total Add-on CAPEX                                {model.economics.AddOnCAPEXTotal.value:10.2f} M$" + NL)
                f.write(f"      Total Add-on OPEX                                 {model.economics.AddOnOPEXTotalPerYear.value:10.2f} M$/year" + NL)
                f.write(f"      Total Add-on Net Elec                             {model.economics.AddOnElecGainedTotalPerYear.value:10.2f} M$/year" + NL)
                f.write(f"      Total Add-on Net Heat                             {model.economics.AddOnHeatGainedTotalPerYear.value:10.2f} M$/year" + NL)
                f.write(f"      Total Add-on Profit                               {model.economics.AddOnProfitGainedTotalPerYear.value:10.2f} M$/year" + NL)
                f.write(NL)
                f.write(NL)                
                f.write("                                        ******************************" + NL)
                f.write("                                        *  ECONOMIC PROFILE          *" + NL)
                f.write("                                        ******************************" + NL)
                f.write("Year        Electricity             Heat          Add-on      Annual Cash Cumm. Cash" + NL);
                f.write("Since     Price   Revenue      Price   Revenue   Revenue          Flow       Flow" + NL);
                f.write("Start    ($/MWh)   ($M)       ($/MWh)   ($M)      ($M)            ($M)       ($M)" + NL);
                i = 0
                for i in range(0, model.economics.ConstructionYears.value, 1):
                    #construction years...
                    f.write(f"   {i+1:3.0f}                                                           {model.economics.CashFlow.value[i]:5.2f}     {model.economics.CummCashFlow.value[i]:5.2f}"    + NL)
                    i = i + 1
                ii=0
                for ii in range(0, (model.economics.ConstructionYears.value + model.surfaceplant.plantlifetime.value - 1), 1):
                    #running years...
                    f.write(f"   {i+1:3.0f}    {model.economics.ElecPrice.value[ii]:5.3f}   {model.economics.ElecRevenue.value[ii]:5.2f}        {model.economics.HeatPrice.value[ii]:5.3f}   {model.economics.HeatRevenue.value[ii]:5.2f}     {model.economics.AddOnRevenue.value[ii]:5.2f}           {model.economics.CashFlow.value[i]:5.2f}     {model.economics.CummCashFlow.value[i]:5.2f}"    + NL)
                    i = i + 1
                    ii = ii + 1
                    
        except BaseException as e:
            print (str(e))
            model.logger.critical(str(e))
            tb = sys.exc_info()[2]
            print ("GEOPHIRES:   ...write file error")
            print ("GEOPHIRES:   ...Line %i" % tb.tb_lineno)
            model.logger.critical("GEOPHIRES:   ...write file error")
            model.logger.critical("GEOPHIRES:   ...Line %i" % tb.tb_lineno)

        model.logger.info("Complete "+ str(__class__) + ": " + sys._getframe(  ).f_code.co_name)





