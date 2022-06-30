import sys
import Model
import Outputs
import numpy as np


NL="\n"

class OutputsCCUS(Outputs):
    """description of class"""
    def PrintOutputs(self, model:Model):
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe(  ).f_code.co_name)

        # Do the original output
#        super().PrintOutputs(reserv, wellbores, surfaceplant, economics, model)   # initialize the parent parameters and variables MIR no need to do this, it has already run
        if np.sum(model.economics.CCUSRevenue.value) == 0: return   #don't bother if we have nothing to report.

        #now do CCUS output, which will append to the original output
        #---------------------------------------
        #write results to output file and screen
        #---------------------------------------
        try:
            with open('HDR.out','a', encoding='UTF-8') as f:
                f.write(NL)
                f.write(NL)
                f.write("                                ***CCUS ECONOMICS***"+ NL);
                f.write(NL)
                f.write(NL)
 #               f.write(f"      Adjusted CAPEX (after incentives, grants, etc)    {model.economics.AdjustedCAPEX.value:10.2f} M$" + NL)
 #               f.write(f"      Adjusted OPEX (after incentives, grants, etc)     {model.economics.AdjustedOPEX.value:10.2f} M$" + NL)
 #               f.write(f"      NPV                                               {model.economics.AddOnNPV.value:10.2f} M$" + NL)
                f.write("                                        ******************************" + NL)
                f.write("                                        *      CCUS PROFILE          *" + NL)
                f.write("                                        ******************************" + NL)
                f.write("Year           CCUS             Annual Cash Cumm. Cash" + NL);
                f.write("Since     Price   Revenue            Flow       Flow" + NL);
                f.write("Start    ($/lb)   ($M)               ($M)       ($M)" + NL);
                i = 0
                ii=0
                for ii in range(0, model.surfaceplant.plantlifetime.value, 1):
                    #running years...
                    f.write(f"   {i+1:3.0f}    {model.economics.CCUSPrice.value[ii]:5.3f}   {model.economics.CCUSRevenue.value[ii]:5.2f}             {model.economics.CashFlow.value[i]:5.2f}     {model.economics.CummCashFlow.value[i]:5.2f}"    + NL)
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
