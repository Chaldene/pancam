# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 17:18:02 2019

@author: ucasbwh
"""

### File for generating Rover TM csv in generic python format

import pandas as pd
from pathlib import Path
from bitstruct import unpack_from as upf
#import binascii  # Used if wanting to output ascii to terminal

def TM_convert(TMfiles, PROC_DIR):
   
    print("---Processing Rover TM Files")    
    DF = pd.DataFrame()
    DRS = pd.DataFrame()
    DRT = pd.DataFrame()

    # Read CSV files and parse
    for file in TMfiles:
        DT = pd.read_csv(file, sep=';', header=0, index_col=False)
        DL = DT[DT['NAME'].str.contains("AB.TM.TM_RMI00040")]
        if not DL.empty:
            DG = DL.RAW_DATA.apply(lambda x: x[38:-4])
            DG = DG.apply(lambda x: bytearray.fromhex(x))
            DG = DG.apply(lambda x: pd.Series(list(x)))
            DG = DG.astype(pd.Int64Dtype())
            DG['DT'] = pd.to_datetime(DL['GROUND_REFERENCE_TIME'], format='%d/%m/%Y %H:%M:%S.%f')
            DF = DF.append(DG, ignore_index=True)
            
        # Rover HK both low and high speed
        DP = DT[ (DT['NAME'] == "AB.TM.MRSP8001") | (DT['NAME'] == "AB.TM.MRSP8002")].copy()
        if not DP.empty:
            DG = DP.RAW_DATA.apply(lambda x: x[2:])
            DG = DG.apply(lambda x: bytearray.fromhex(x))
            #PanCam Current
            OffBy, OffBi, Len = 85, 4, 'u12'
            DP['RAW_Inst_Curr'] = DG.apply(lambda x: upf(Len, x, offset=8*OffBy+OffBi)[0])
            DP['Inst_Curr'] = DP['RAW_Inst_Curr'] * 1.1111/4095
            #PanCam Heater
            OffBy, OffBi, Len = 57, 4, 'u12'
            DP['RAW_HTR_Curr'] = DG.apply(lambda x: upf(Len, x, offset=8*OffBy+OffBi)[0])
            DP['HTR_Curr'] = DP['RAW_HTR_Curr'] * 1.1111/4095
            #PanCam Heater Status
            OffBy, OffBi, Len = 51, 2, 'u1'
            DP['HTR_ST'] = DG.apply(lambda x: upf(Len, x, offset=8*OffBy+OffBi)[0])
            #PanCam Power Status
            OffBy, OffBi, Len = 77, 1, 'u1'
            DP['PWR_ST'] = DG.apply(lambda x: upf(Len, x, offset=8*OffBy+OffBi)[0])
            DP['DT'] = pd.to_datetime(DP['GROUND_REFERENCE_TIME'], format='%d/%m/%Y %H:%M:%S.%f')
            DRS = DRS.append(DP, ignore_index=True)

        # Rover HK Thermistors Only contained within low speed HK
        DK = DT.loc[DT['NAME'] == "AB.TM.MRSP8001"].copy()
        if not DK.empty:
            DW = DK.RAW_DATA.apply(lambda x: x[2:])
            DW = DW.apply(lambda x: bytearray.fromhex(x))
            #PIU Temp
            OffBy, OffBi, Len = 511, 3, 'u13'
            DK['RAW_PIU_T'] = DW.apply(lambda x: upf(Len, x, offset=8*OffBy+OffBi)[0])
            DK['PIU_T'] = DK['RAW_PIU_T']*0.18640 - 259.84097 #Calculated from thermistor curve provided
            #DCDC Temp
            OffBy, OffBi, Len = 559, 3, 'u13'
            DK['RAW_DCDC_T'] = DW.apply(lambda x: upf(Len, x, offset=8*OffBy+OffBi)[0])
            DK['DCDC_T'] = DK['RAW_DCDC_T']*0.18640 - 259.84097 #Calculated from thermistor curve provided
            DK['DT'] = pd.to_datetime(DK['GROUND_REFERENCE_TIME'], format='%d/%m/%Y %H:%M:%S.%f')
            DRT = DRT.append(DK, ignore_index=True)
            
    print("Number of PanCam TMs found: ", DF.shape[0])
    print("Number of Rover Status Entries found: ", DRS.shape[0])
    print("Number of Rover Temperature Entries found: ", DRT.shape[0])

    write_dts = DF['DT'].iloc[0].strftime('%y%m%d_%H%M%S_')

    DF.to_pickle(PROC_DIR / (write_dts + "TM.pickle") )
    print("PanCam TM pickled.")

    DRS.to_pickle(PROC_DIR / (write_dts + "RoverStatus.pickle") )
    print("Rover Status TM pickled.")

    DRT.to_pickle(PROC_DIR / (write_dts + "RoverTemps.pickle") )
    print("Rover Temperatures TM pickled.")
    


def TC_convert(TCfiles, PROC_DIR):
    
    print("---Processing Rover TC Files")
    
    TC = pd.DataFrame()
    
    # Read CSV file and parse
    for file in TCfiles:
        dt = pd.read_csv(file, sep=';', encoding = "ISO-8859-1" , header=0, dtype=object, index_col=False)
        dp = dt[dt['DESCRIPTION'].str.contains("Pan Cam", na=False) & dt['NAME'].str.contains("CRM", na=False)].copy()
        dm = dp['VARIABLE_PART'].str.split(',', -1, expand=True)
        
        TC = pd.concat([dp[['NAME', 'DESCRIPTION', 'GROUND_REFERENCE_TIME']], dm.loc[:,9:]], axis=1)
        TC['DT'] = pd.to_datetime(TC['GROUND_REFERENCE_TIME'], format='%d/%m/%Y %H:%M:%S.%f')
        TC['ACTION'] = TC['DESCRIPTION'].map(lambda x: x.lstrip('Pan Cam'))
        TC['LEVEL'] = 1
        
    print("Number of PanCam TCs found: ", TC.size)
    
    write_dts = TC['DT'].iloc[0].strftime('%y%m%d_%H%M%S_')
    TC.to_pickle(PROC_DIR / (write_dts  + "TC.pickle") )
    print("Rover TC pickled")        
    
    
        
if __name__ == "__main__":
    TMfiles = [r'C:\Users\ucasbwh\OneDrive - University College London\PanCam Documents\Rover Level Testing\Data\191107 - TVAC TP02 Testing\20191106_1734_ERJPMW_CRUISE_CHECKOUTS\20191106_1734_CRUISE_CHECKOUT-203\STDRawOcdsAnalysis.csv']
    TCfiles = [r"C:\Users\ucasbwh\OneDrive - University College London\PanCam Documents\Rover Level Testing\Data\191107 - TVAC TP02 Testing\20191106_1734_ERJPMW_CRUISE_CHECKOUTS\20191106_1734_CRUISE_CHECKOUT_TMTC-203\STDChronoAnalysis.csv"]
    Dir =      r"C:\Users\ucasbwh\OneDrive - University College London\PanCam Documents\Rover Level Testing\Data\191107 - TVAC TP02 Testing\20191106_1734_ERJPMW_CRUISE_CHECKOUTS\PROC"
    TM_convert(TMfiles, Dir)
    TC_convert(TCfiles, Dir)
