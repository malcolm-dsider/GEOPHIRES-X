


        #print results to console screen
        print("")
        print("----------------------------")
        print("GEOPHIRES Simulation Results")
        print("----------------------------")
        print("")
        print("1. Simulation Metadata")
        print("----------------------")
        print(" GEOPHIRES Version = 2.0")
        print(" GEOPHIRES Build Date = 2018-01-02")
        currentdate = datetime.datetime.now().strftime("%Y-%m-%d")
        currenttime = datetime.datetime.now().strftime("%H:%M")
        print(" Simulation Date = "+ currentdate)
        print(" Simulation Time = "+ currenttime)
        print(" Calculation Time = "+"{0:.3f}".format((time.time()-tic)) +" s")
    
        print("")
        print("2. Summary of Simulation Results")
        print("--------------------------------")
        #say what type of end-use option
        if surfaceplant.enduseoption.value == EndUseOptions.ELECTRICITY:
            print(" End-Use Option = Electricity")
        elif surfaceplant.enduseoption.value == EndUseOptions.HEAT:
            print(" End-Use Option = Direct-Use Heat")
        elif surfaceplant.enduseoption.value == EndUseOptions.COGENERATION_BOTTOMING_EXTRA_HEAT: #topping cycle
            print(" End-Use Option = Cogeneration Topping Cycle")
            print(" Heat sales considered as extra income")
        elif surfaceplant.enduseoption.value == EndUseOptions.COGENERATION_BOTTOMING_EXTRA_ELECTRICTY: #topping cycle
            print(" End-Use Option = Cogeneration Topping Cycle")
            print(" Electricity sales considered as extra income")
        elif surfaceplant.enduseoption.value == EndUseOptions.COGENERATION_BOTTOMING_EXTRA_HEAT: #bottoming cycle  
            print(" End-Use Option = Cogeneration Bottoming Cycle")
            print(" Heat Sales considered as extra income")
        elif surfaceplant.enduseoption.value == EndUseOptions.COGENERATION_BOTTOMING_EXTRA_ELECTRICTY: #bottoming cycle  
            print(" End-Use Option = Cogeneration Bottoming Cycle")
            print(" Electricity sales considered as extra income")            
        elif surfaceplant.enduseoption.value == EndUseOptions.COGENERATION_PARALLEL_EXTRA_HEAT: #cogen split of mass flow rate
            print(" End-Use Option = Cogeneration Parallel Cycle")
            print(" Heat sales considered as extra income")
        elif surfaceplant.enduseoption.value == EndUseOptions.COGENERATION_PARALLEL_EXTRA_ELECTRICTY: #cogen split of mass flow rate
            print(" End-Use Option = Cogeneration Parallel Cycle")
            print(" Electricity sales considered as extra income")
        #say what type of power plant
        if surfaceplant.enduseoption.value != EndUseOptions.HEAT:
            print(" Power Plant Type = " + surfaceplant.pptype.value)
        
        #print(surfaceplant.NetElectricityProduced.value)
        if surfaceplant.enduseoption.value != EndUseOptions.HEAT:
            print(" Average Net Electricity Generation = " + "{0:.2f}".format(np.average(surfaceplant.NetElectricityProduced.value)) +" MWe" )
        if surfaceplant.enduseoption.value != EndUseOptions.ELECTRICITY:
            print(" Average Net Heat Production = " + "{0:.2f}".format(np.average(surfaceplant.HeatProduced.value)) +" MWth" )        
        
        #print LCOE/LCOH
        if surfaceplant.enduseoption.value == EndUseOptions.ELECTRICITY:
            print(" LCOE = " + "{0:.1f}".format((economics.Price)) +" cents/kWh")
        elif surfaceplant.enduseoption.value == EndUseOptions.HEAT:
            print(" LCOH = " + "{0:.1f}".format((economics.Price)) +" $/MMBTU")
        elif surfaceplant.enduseoption.value in [EndUseOptions.COGENERATION_TOPPING_EXTRA_HEAT, EndUseOptions.COGENERATION_BOTTOMING_EXTRA_HEAT, EndUseOptions.COGENERATION_PARALLEL_EXTRA_HEAT]: #heat sales is additional income revenuw stream
            print(" LCOE = " + "{0:.1f}".format((economics.Price)) +" cents/kWh")
            print(" Additional average annual revenue from heat sales = " + "{0:.1f}".format(np.average(economics.annualheatincome)) +" M$/year")
        elif surfaceplant.enduseoption.value in [EndUseOptions.COGENERATION_TOPPING_EXTRA_ELECTRICTY, EndUseOptions.COGENERATION_BOTTOMING_EXTRA_ELECTRICTY, EndUseOptions.COGENERATION_PARALLEL_EXTRA_ELECTRICTY]: #electricity sales is additional income revenuw stream
            print(" LCOH = " + "{0:.1f}".format((economics.Price)) +" $/MMBTU")
            print(" Additional average annual revenue from electricity sales = " + "{0:.1f}".format(np.average(surfaceplant.economics)) +" M$/year")    
        #say what type of economic model is used
        print(" Economic Model Used = " + model.econmodel + " Model")
        if model.econmodel == EconomicModel.FCR:
            print(" Fixed Charge Rate (FCR) = " + "{0:.2f}".format((model.FCR*100))+"%")
        elif model.econmodel == EconomicModel.STANDARDIZED_LEVELIZED_COST:
            print(" Discount Rate = " + "{0:.2f}".format((model.discountrate.value*100))+"%")                    
        
        print("")
        print("3. Reservoir Simulation Results")
        print("-------------------------------")
        print(" Reservoir Model = " + reserv.resoption + " Model")
        if reserv.resoption == ReservoirModel.SINGLE_FRACTURE:
            print(" m/A Drawdown Parameter = " + "{0:.5f}".format(reserv.drawdp) + " kg/s/m^2" )    
        elif reserv.resoption == ReservoirModel.ANNUAL_PERCENTAGE:
            print(" Annual Thermal Drawdown = " + "{0:.3f}".format(reserv.drawdp*100) + " %/year" )

        print(" Number of Production Wells = " + "{0:.0f}".format((wellbores.nprod.value)))
        print(" Number of Injection Wells = " + "{0:.0f}".format((wellbores.ninj.value)))
        print(" Number of Times Redrilling = " + "{0:.0f}".format((wellbores.redrill)))
        print(" Well Depth = " + "{0:.1f}".format((reserv.depth.value)) + " m")
        print(" Flow Rate per Production Well = " + "{0:.0f}".format((wellbores.prodwellflowrate.value))+" kg/s")
        print(" Initial Reservoir Temperature = " + "{0:.1f}".format(reserv.Trock.value) + "degrees C")
        print(" Maximum Production Temperature = " + "{0:.1f}".format(np.max(wellbores.ProducedTemperature.value)) +" " + surfaceplant.ProducedTemperature.PreferredUnits)
        print(" Average Production Temperature = " + "{0:.1f}".format(np.average(wellbores.ProducedTemperature.value)) +" " + surfaceplant.ProducedTemperature.PreferredUnits)
        print(" Minimum Production Temperature = " + "{0:.1f}".format(np.min(wellbores.ProducedTemperature.value)) +" " + surfaceplant.ProducedTemperature.PreferredUnits)
        print(" Initial Production Temperature = " + "{0:.1f}".format((wellbores.ProducedTemperature.value[0])) +" " + surfaceplant.ProducedTemperature.PreferredUnits)
        print(" Average Reservoir Heat Extraction = " + "{0:.2f}".format(np.average(surfaceplant.HeatExtracted.value)) +" " + surfaceplant.HeatExtracted.PreferredUnits)
        if wellbores.rameyoptionprod.value:
            print(" Production Wellbore Heat Transmission Model = Ramey Model")
            print(" Average Production Well Temperature Drop = " +"{0:.1f}".format(np.average(wellbores.ProdTempDrop.value))  + wellbores.ProdTempDrop.PreferredUnits.value)
        else:
            print(" Wellbore Heat Transmission Model = Constant Temperature Drop of " +"{0:.1f}".format(wellbores.tempdropprod.value)  +" "+wellbores.tempdropprod.PreferredUnits)
        if wellbores.impedancemodelused:
            print(" Total Average Pressure Drop = "+"{0:.1f}".format(np.average(wellbores.DP.value)) + " " + wellbores.DP.PreferredUnits)
            print("    Average Injection Well Pressure Drop = "+"{0:.1f}".format(np.average(wellbores.DP1.value)) + " " + wellbores.DP1.PreferredUnits)
            print("    Average Reservoir Pressure Drop = "+"{0:.1f}".format(np.average(wellbores.DP2.value)) + " " + wellbores.DP2.PreferredUnits)
            print("    Average Production Well Pressure Drop = "+"{0:.1f}".format(np.average(wellbores.DP3.value)) + " " + wellbores.DP3.PreferredUnits)
            print("    Average Buoyancy Pressure Drop = "+"{0:.1f}".format(np.average(wellbores.DP4.values)) + " " + wellbores.DP4.PreferredUnits)
        else:
            print(" Average Injection Well Pump Pressure Drop = "+"{0:.1f}".format(np.average(wellbores.DP1.value)) + " " + wellbores.DP1.PreferredUnits)
            if wellbores.productionwellpumping:
                print(" Average Production Well Pump Pressure Drop = "+"{0:.1f}".format(np.average(wellbores.DP3.value)) + " " + wellbores.DP3.PreferredUnits)
            
        print("")
        print("4. Surface Equipment Simulation Results")
        print("---------------------------------------")
        if surfaceplant.enduseoption.value != EndUseOptions.HEAT:
            print(" Maximum Total Electricity Generation = " + "{0:.2f}".format(np.max(surfaceplant.ElectricityProduced.value)) + " " + surfaceplant.ElectricityProduced.PreferredUnits)
            print(" Average Total Electricity Generation = " + "{0:.2f}".format(np.average(surfaceplant.ElectricityProduced.value)) + " " + surfaceplant.ElectricityProduced.PreferredUnits)
            print(" Minimum Total Electricity Generation = " + "{0:.2f}".format(np.min(surfaceplant.ElectricityProduced.value)) + " " + surfaceplant.ElectricityProduced.PreferredUnits)
            print(" Initial Total Electricity Generation = " + "{0:.2f}".format((surfaceplant.ElectricityProduced.value[0])) + " " + surfaceplant.ElectricityProduced.PreferredUnits)
            print(" Maximum Net Electricity Generation = " + "{0:.2f}".format(np.max(surfaceplant.NetElectricityProduced.value)) + " " + surfaceplant.NetElectricityProduced.PreferredUnits)
            print(" Average Net Electricity Generation = " + "{0:.2f}".format(np.average(surfaceplant.NetElectricityProduced.value)) + " " + surfaceplant.NetElectricityProduced.PreferredUnits)
            print(" Minimum Net Electricity Generation = " + "{0:.2f}".format(np.min(surfaceplant.NetElectricityProduced.value)) + " " + surfaceplant.NetElectricityProduced.PreferredUnits)
            print(" Initial Net Electricity Generation = " + "{0:.2f}".format((surfaceplant.NetElectricityProduced.value[0])) + " " + surfaceplant.NetElectricityProduced.PreferredUnits)
            print(" Average Annual Total Electricity Generation = " + "{0:.2f}".format(np.average(surfaceplant.TotalkWhProduced.value/1E6)) + " " + surfaceplant.NetElectricityProduced.PreferredUnits)
            print(" Average Annual Net Electricity Generation = " + "{0:.2f}".format(np.average(surfaceplant.NetkWhProduced.value/1E6)) + " " + surfaceplant.NetElectricityProduced.PreferredUnits)
        if surfaceplant.enduseoption.value != EndUseOptions.ELECTRICITY:
            print(" Maximum Net Heat Production = " + "{0:.2f}".format(np.max(surfaceplant.HeatProduced.value)) + " " + surfaceplant.HeatProduced.PreferredUnits)
            print(" Average Net Heat Production = " + "{0:.2f}".format(np.average(surfaceplant.HeatProduced.value)) + " " + surfaceplant.HeatProduced.PreferredUnits)
            print(" Minimum Net Heat Production = " + "{0:.2f}".format(np.min(surfaceplant.HeatProduced.value)) + " " + surfaceplant.HeatProduced.PreferredUnits)
            print(" Initial Net Heat Production = " + "{0:.2f}".format((surfaceplant.HeatProduced.value[0])) + " " + surfaceplant.HeatProduced.PreferredUnits)
            print(" Average Annual Heat Production = " + "{0:.2f}".format(np.average(surfaceplant.HeatkWhProduced.value/1E6)) + " " + surfaceplant.HeatkWhProduced.PreferredUnits)
        print(" Average Pumping Power = " + "{0:.2f}".format(np.average(wellbores.PumpingPower.value)) + " " + wellbores.PumpingPower.PreferredUnits)

        print("")
        print("5. Capital and O&M Costs")
        print("------------------------")
        print(" Total Capital Cost = " + "{0:.2f}".format(model.CCap.value) + " " + model.CCap.PreferredUnits)
        if not totalcapcost.Valid:        
            print("   Wellfield Cost = " + "{0:.2f}".format(wellbores.Cwell.value) + " " + wellbores.Cwell.PreferredUnits)  
            print("   Surface Plant Cost = " + "{0:.2f}".format(surfaceplant.Cplant.value) + " " + surfaceplant.Cplant.PreferredUnits)
            print("   Exploration Cost = " + "{0:.2f}".format(reserv.Cexpl.value) + " " + reserv.Cexpl.PreferredUnits)
            print("   Field Gathering System Cost = " + "{0:.2f}".format(surfaceplant.Cgath.value) + " " + surfaceplant.Cgath.PreferredUnits)
            if surfaceplant.pipinglength > 0:
                print("   Transmission Pipeline Cost = " + "{0:.2f}".format(surfaceplant.Cpiping.value) + " " + surfaceplant.Cpiping.PreferredUnits)
            print("   Stimulation Cost = " + "{0:.2f}".format(reserv.Cstim.value) + " " + reserv.Cstim.PreferredUnits)
        if surfaceplant.enduseoption.value == EndUseOptions.HEAT:
            print(" Total O&M Cost = " + "{0:.2f}".format(model.Coam.value+surfaceplant.averageannualpumpingcosts.value) + " " + surfaceplant.averageannualpumpingcosts.PreferredUnits)
        else:
            print(" Total O&M Cost = " + "{0:.2f}".format(model.Coam.value) + " " + model.Coam.PreferredUnits)
        if not oamtotalfixed.Valid:
            print("   Wellfield O&M Cost = " + "{0:.2f}".format(wellbores.Coamwell.value) + " " + wellbores.Coamwell.PreferredUnits)
            print("   Surface Plant O&M Cost = " + "{0:.2f}".format(surfaceplant.Coamplant.value) + " " + surfaceplant.Coamplant.PreferredUnits)
            print("   Make-Up Water O&M Cost = " + "{0:.2f}".format(surfaceplant.Coamwater.value) + " " + surfaceplant.Coamwater.PreferredUnits)
            if surfaceplant.enduseoption.value == EndUseOptions.HEAT:
                print("   Average annual pumping costs = " + "{0:.2f}".format(surfaceplant.averageannualpumpingcosts.value) + " " + surfaceplant.averageannualpumpingcosts.PreferredUnits)

        print("")
        print("6. Power Generation Profile")    
        print("---------------------------")

        if surfaceplant.enduseoption.value == EndUseOptions.ELECTRICITY:   #only electricity
            print('  YEAR   THERMAL     GEOFLUID       PUMP      NET      FIRST LAW')
            print('         DRAWDOWN    TEMPERATURE    POWER     POWER    EFFICIENCY')
            print('         (-)         ('+wellbores.ProducedTemperature.PreferredUnits+')        ('+wellbores.PumpingPower.PreferredUnits+')     ('+surfaceplant.NetElectricityProduced.PreferredUnits+')    ('+surfaceplant.FirstLawEfficiency.PreferredUnits+')')
            for i in range(0, surfaceplant.plantlifetime.value+1):
                print('  {0:2.0f}   {1:8.4f}     {2:8.2f}      {3:8.4f}  {4:8.4f}  {5:8.4f}'.format(i, wellbores.ProducedTemperature.value[i*economics.timestepsperyear.value]/wellbores.ProducedTemperature.value[0], wellbores.ProducedTemperature.value[i*economics.timestepsperyear.value], wellbores.PumpingPower.value[i*economics.timestepsperyear.value], surfaceplant.NetElectricityProduced.value[i*economics.timestepsperyear.value], surfaceplant.FirstLawEfficiency.value[i*economics.timestepsperyear.value]*100))
        elif surfaceplant.enduseoption.value == EndUseOptions.HEAT: #only direct-use
            print('  YEAR   THERMAL      GEOFLUID      PUMP      NET')
            print('         DRAWDOWN     TEMPERATURE   POWER     HEAT')
            print('         (-)          ('+wellbores.ProducedTemperature.PreferredUnits+')       ('+wellbores.PumpingPower.PreferredUnits+')     ('+surfaceplant.HeatProduced.PreferredUnits+')')
            for i in range(0, surfaceplant.plantlifetime.value+1):
                print('  {0:2.0f}   {1:8.4f}     {2:8.2f}      {3:8.4f}   {4:8.4f}'.format(i, wellbores.ProducedTemperature.value[i*economics.timestepsperyear.value]/wellbores.ProducedTemperature.value[0], wellbores.ProducedTemperature.value[i*economics.timestepsperyear.value], wellbores.PumpingPower.value[i*economics.timestepsperyear.value], surfaceplant.HeatProduced.value[i*economics.timestepsperyear.value]))
        elif surfaceplant.enduseoption.value not in [EndUseOptions.ELECTRICITY, EndUseOptions.HEAT]:  #both electricity and direct-use
            print('  YEAR   THERMAL      GEOFLUID      PUMP      NET       NET       FIRST LAW')
            print('         DRAWDOWN     TEMPERATURE   POWER     POWER     HEAT      EFFICIENCY')
            print('         (-)          ('+wellbores.ProducedTemperature.PreferredUnits+')       ('+wellbores.PumpingPower.PreferredUnits+')     ('+surfaceplant.NetElectricityProduced.PreferredUnits+')     ('+surfaceplant.HeatProduced.PreferredUnits+')    ('+surfaceplant.FirstLawEfficiency.PreferredUnits+')')
            for i in range(0, surfaceplant.plantlifetime.value+1):
                print('  {0:2.0f}    {1:8.4f}    {2:8.2f}      {3:8.4f}   {4:8.4f}  {5:8.4f}  {6:8.4f}'.format(i, wellbores.ProducedTemperature.value[i*economics.timestepsperyear.value]/wellbores.ProducedTemperature.value[0], wellbores.ProducedTemperature.value[i*economics.timestepsperyear.value], wellbores.PumpingPower.value[i*economics.timestepsperyear.value], surfaceplant.NetElectricityProduced.value[i*economics.timestepsperyear.value],surfaceplant.HeatProduced.value[i*economics.timestepsperyear.value],surfaceplant.FirstLawEfficiency.value[i*economics.timestepsperyear.value]*100))
