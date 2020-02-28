# Plotter.py
#
# Barry Whiteside
# Mullard Space Science Laboratory - UCL
#
# PanCam Data Processing Tools


import matplotlib.pyplot as plt
from matplotlib import gridspec
import matplotlib.dates as mdates
import matplotlib
import pandas as pd
from pandas.plotting import register_matplotlib_converters
import numpy as np
from pathlib import Path
import logging

import PC_Fns

logger = logging.getLogger(__name__)


register_matplotlib_converters()
myFmt = mdates.DateFormatter('%H:%M')

HK_Plot_Location = 'HK Plots'
# Voltage limits for calibrated plots
# Initialised as lists for dashed lines
Lim_VREF_Low = [3.1]
Lim_VREF_High = [3.6]
Lim_6V0_Low = [5.5]
Lim_6V0_High = [6.3]
Lim_1V5_Low = [1.4]
Lim_1V5_High = [1.6]


class plotter_Error(Exception):
    """error for unexpected things"""
    pass


def all_plots(proc_dir: Path):
    """Generates one of each defined plots.

    Arguments:
        proc_dir {Path} -- Dir containing generated .pickle files.

    Generates:
        HK Plots {Folder} -- Located in proc_dir containing the following if available:
            FW.png           -- Plot of Filter Wheel Status
            HK_OVER.png      -- Overview of PanCam HK
            INT_TEMP_CAL.png -- Plot of calibrated temperatures
            INT_TEMP_RAW.png -- Plot of RAW temperatures and heater status
            VOLT_CAL.png     -- Plot of the calibrated voltages and limits
            VOLT_RAW.png     -- Plot of the raw voltages
    """

    HK_Overview(proc_dir)
    HK_Voltages(proc_dir)
    HK_Temperatures(proc_dir)
    FW(proc_dir)

    Rover_Temperatures(proc_dir)
    Rover_Power(proc_dir)

    psu(proc_dir)

    HRC_CS(proc_dir)


def MakeHKPlotsDir(PROC_DIR):
    """Checks to see if the 'HK Plots' directory has been generated, if not creates it"""
    HK_DIR = PROC_DIR / HK_Plot_Location
    if HK_DIR.is_dir():
        logger.info("'HK Plots' Directory already exists")
    else:
        logger.info("Generating 'HK Plots' directory")
        HK_DIR.mkdir()
    return HK_DIR


def zero_to_nan(values):
    """Replace every 0 with 'nan' and return a copy."""
    # Taken from https://stackoverflow.com/questions/18697417/not-plotting-zero-in-matplotlib-or-change-zero-to-none-python
    List = [float('nan') if x == 0 else x for x in values]
    List_Low = [float('nan') if x == 0 else x-15 for x in values]
    List_High = [float('nan') if x == 0 else x+15 for x in values]
    return List, List_Low, List_High


def format_axes(fig, integers=False):
    """Shows the grid, hides the xlabel and sets the y scale to integers for each subplot within a figure.

    Arguments:
        fig {matplotlib.fig} -- A matplotlib figure object.

    Keyword Arguments:
        integers {bool} -- If set to True, the y-axis ticks are forced to integers. (default: {False})
    """

    for i, ax in enumerate(fig.axes):
        ax.grid(True)
        ax.tick_params(labelbottom=False)
        if integers:
            ax.yaxis.set_major_locator(
                matplotlib.ticker.MaxNLocator(integer=True))


def add_text(axes: matplotlib.axes, text: str):
    """Adds axes text to the subplot

    Arguments:
        axes {matplotlib.axes} -- matplotlib.axes object for text to be added.
        text {str} -- String containing text to be added.
    """

    axes.text(.99, .9, text,
              color='0.25',
              fontweight='bold',
              horizontalalignment='right',
              transform=axes.transAxes)


def HK_Voltages(PROC_DIR, Interact=False):
    """"Produces a calibrated and uncalibrated voltage plots from pickle files"""

    logger.info("Producing Voltage Plots")

    HK_DIR = MakeHKPlotsDir(PROC_DIR)

    # Search for PanCam RAW Processed Files
    RawPikFile = PC_Fns.Find_Files(
        PROC_DIR, "*RAW_HKTM.pickle", SingleFile=True)
    if not RawPikFile:
        logger.warning("No file found - ABORTING")
        return

    RAW = pd.read_pickle(RawPikFile[0])

    fig = plt.figure(figsize=(14.0, 9.0))
    gs = gridspec.GridSpec(3, 1, height_ratios=[1, 1, 1], figure=fig)
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharex=ax0)
    ax2 = fig.add_subplot(gs[2], sharex=ax0)

    ax0.plot(RAW.DT, RAW.Volt_Ref.astype('int64'), 'r-', label='VRef RAW')
    ax0.set_ylabel('VRef RAW [ENG]')

    ax1.plot(RAW.DT, RAW.Volt_6V0.astype('int64'), 'b-', label='6V RAW')
    ax1.set_ylabel('6V RAW [ENG]')

    ax2.plot(RAW.DT, RAW.Volt_1V5.astype('int64'), 'g-', label='1V5 RAW')
    ax2.set_ylabel('1V5 RAW [ENG]')
    ax2.set_xlabel('Date Time')

    format_axes(fig, integers=True)
    ax2.tick_params(labelbottom=True)

    fig.tight_layout()
    fig.savefig(HK_DIR / 'VOLT_RAW.png')

    if Interact:
        plt.show(block=False)

    # Search for PanCam CAL Processed Files
    CalPikFile = PC_Fns.Find_Files(
        PROC_DIR, "*Cal_HKTM.pickle", SingleFile=True)
    if not CalPikFile:
        logger.warning("No file found - ABORTING")
        return

    Cal = pd.read_pickle(CalPikFile[0])

    fig2 = plt.figure(figsize=(14.0, 9.0))
    gs2 = gridspec.GridSpec(3, 1, height_ratios=[1, 1, 1], figure=fig2)
    ax3 = fig2.add_subplot(gs2[0])
    ax4 = fig2.add_subplot(gs2[1], sharex=ax3)
    ax5 = fig2.add_subplot(gs2[2], sharex=ax3)

    ax3.plot(Cal.DT, Cal.Volt_Ref, 'r-', label='VREF')
    ax3.plot([Cal['DT'].iloc[0], Cal['DT'].iloc[-1]],
             Lim_VREF_Low*2, 'darkred', linestyle='dashed')
    ax3.plot([Cal['DT'].iloc[0], Cal['DT'].iloc[-1]],
             Lim_VREF_High*2, 'darkred', linestyle='dashed')
    ax3.set_ylabel('VRef [V]')

    ax4.plot(Cal.DT, Cal.Volt_6V0, 'b-', label='6V0')
    ax4.plot([Cal['DT'].iloc[0], Cal['DT'].iloc[-1]],
             Lim_6V0_Low*2, 'darkblue', linestyle='dashed')
    ax4.plot([Cal['DT'].iloc[0], Cal['DT'].iloc[-1]],
             Lim_6V0_High*2, 'darkblue', linestyle='dashed')
    ax4.set_ylabel('6V [V]')

    ax5.plot(Cal.DT, Cal.Volt_1V5, 'g-', label='1V5')
    ax5.plot([Cal['DT'].iloc[0], Cal['DT'].iloc[-1]],
             Lim_1V5_Low*2, 'darkgreen', linestyle='dashed')
    ax5.plot([Cal['DT'].iloc[0], Cal['DT'].iloc[-1]],
             Lim_1V5_High*2, 'darkgreen', linestyle='dashed')
    ax5.set_ylabel('1V5 [V]')
    ax5.set_xlabel('Date Time')

    format_axes(fig2)
    ax5.tick_params(labelbottom=True)

    fig2.tight_layout()
    fig2.savefig(HK_DIR / 'VOLT_CAL.png')

    if Interact:
        plt.show(block=True)

    plt.close(fig)
    plt.close(fig2)

    logger.info("Producing Voltage Plots Completed")


def HK_Temperatures(PROC_DIR, Interact=False):
    """"Produces a calibrated and uncalibrated temperature plots from pickle files"""

    logger.info("Producing Temperature Plots")

    HK_DIR = MakeHKPlotsDir(PROC_DIR)

    # Search for PanCam RAW Processed Files
    RawPikFile = PC_Fns.Find_Files(
        PROC_DIR, "*RAW_HKTM.pickle", SingleFile=True)
    if not RawPikFile:
        logger.warning("No file found - ABORTING")
        return

    RAW = pd.read_pickle(RawPikFile[0])

    fig = plt.figure(figsize=(14.0, 9.0))
    gs = gridspec.GridSpec(4, 1, height_ratios=[2, 1, 0.5, 0.5], figure=fig)
    gs.update(hspace=0.0)
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharex=ax0)
    ax2 = fig.add_subplot(gs[2], sharex=ax0)
    ax3 = fig.add_subplot(gs[3], sharex=ax0)

    # RAW Plot and Heater Set-Point
    ax0.plot(RAW.DT, RAW.Temp_LFW.astype('int64'),  label='LFW')
    ax0.plot(RAW.DT, RAW.Temp_RFW.astype('int64'),  label='RFW')
    ax0.plot(RAW.DT, RAW.Temp_HRC.astype('int64'),  label='HRC')
    ax0.plot(RAW.DT, RAW.Temp_LWAC.astype('int64'), label='LWAC')
    ax0.plot(RAW.DT, RAW.Temp_RWAC.astype('int64'), label='RWAC')
    ax0.plot(RAW.DT, RAW.Temp_HRCA.astype('int64'), label='ACT')

    # Heater set-point and 15 values shaded either side
    HSP, HSP_L, HSP_H = zero_to_nan(RAW.Stat_Temp_Se.astype('int64'))
    ax0_HSP = ax0.plot(RAW.DT, HSP, '--', color='k', label='HTR Set Point')
    ax0.fill_between(RAW.DT, HSP_L, HSP_H,
                     color=ax0_HSP[0].get_color(), alpha=0.2)

    ax0.legend(loc='lower center', bbox_to_anchor=(
        0.5, 1.0), ncol=4, borderaxespad=0, frameon=False)
    add_text(ax0, 'Internal Temps')
    ax0.set_ylabel('RAW [ENG]')

    # LDO Temperature
    ax1.plot(RAW.DT, RAW.Temp_LDO.astype('int64'), '-k', label='LDO')
    add_text(ax1, 'LDO Temp')
    ax1.set_ylabel('LDO RAW [ENG]')
    ax1.yaxis.tick_right()
    ax1.yaxis.set_label_position('right')

    ax2.plot(RAW.DT, RAW.Stat_Temp_He.astype('int64'), label='HTR')
    ax2.set_ylim([-0.5, 3.2])
    ax2.set_yticks([0, 1, 2, 3])
    ax2.set_yticklabels(['None', 'WACL', 'WACR', 'HRC'])
    add_text(ax2, 'HTR')

    ax3.plot(RAW.DT, RAW.Stat_Temp_On.astype('int64'), label='HTR On')
    ax3.plot(RAW.DT, RAW.Stat_Temp_Mo.astype('int64'), label='AUTO')
    ax3.legend(loc='center right', bbox_to_anchor=(
        1.0, 0.5), ncol=1, borderaxespad=0, frameon=False)
    ax3.set_ylim([-0.1, 1.1])
    ax3.get_yaxis().set_visible(False)
    ax3.set_xlabel('Date Time')

    format_axes(fig, integers=False)
    ax3.tick_params(labelbottom=True)

    fig.tight_layout()
    fig.savefig(HK_DIR / 'INT_TEMP_RAW.png')

    if Interact:
        plt.show(block=False)

    # Search for PanCam CAL Processed Files
    CalPikFile = PC_Fns.Find_Files(
        PROC_DIR, "*Cal_HKTM.pickle", SingleFile=True)
    if not CalPikFile:
        logger.warning("No file found - ABORTING")
        return

    Cal = pd.read_pickle(CalPikFile[0])

    # Calibrated Temperatures
    fig2 = plt.figure(figsize=(14.0, 9.0))
    gs2 = gridspec.GridSpec(2, 1, height_ratios=[3, 1], figure=fig2)
    ax3 = fig2.add_subplot(gs2[0])
    ax4 = fig2.add_subplot(gs2[1], sharex=ax3)

    ax3.plot(Cal.DT, Cal.Temp_LFW,  label='LFW')
    ax3.plot(Cal.DT, Cal.Temp_RFW,  label='RFW')
    ax3.plot(Cal.DT, Cal.Temp_HRC,  label='HRC')
    ax3.plot(Cal.DT, Cal.Temp_LWAC, label='LWAC')
    ax3.plot(Cal.DT, Cal.Temp_RWAC, label='RWAC')
    ax3.plot(Cal.DT, Cal.Temp_HRCA, label='ACT')
    ax3.set_ylabel('Temp [$^\circ$C]')
    ax3.legend(loc='lower center', bbox_to_anchor=(
        0.5, 1.0), ncol=5, borderaxespad=0, frameon=False)

    ax4.plot(Cal.DT, Cal.Temp_LDO, '-k', label='LDO')
    ax4.set_ylabel('LDO Temp [$^\circ$C]')
    ax4.set_xlabel('Date Time')
    # ax4.xaxis.set_major_formatter(myFmt)

    format_axes(fig2)
    ax4.tick_params(labelbottom=True)

    fig2.tight_layout()
    fig2.savefig(HK_DIR / 'INT_TEMP_CAL.png')

    if Interact:
        plt.show(block=True)

    plt.close(fig)
    plt.close(fig2)

    logger.info("Producing Temperature Plots Completed")


def Rover_Temperatures(PROC_DIR, Interact=False):
    """"Produces a Rover temperature plot from pickle files"""

    logger.info("Producing Rover Temperature Plot")

    HK_DIR = MakeHKPlotsDir(PROC_DIR)

    # Search for PanCam Rover Status Processed Files
    RawPikFile = PC_Fns.Find_Files(
        PROC_DIR, "*RoverStatus.pickle", SingleFile=True)
    if not RawPikFile:
        logger.warning("No file found - ABORTING")
        return

    ROV = pd.read_pickle(RawPikFile[0])

    # Search for PanCam Rover Temperature Processed Files
    RawPikFile = PC_Fns.Find_Files(
        PROC_DIR, "*RoverTemps.pickle", SingleFile=True)
    if not RawPikFile:
        logger.warning("No file found - ABORTING")
        return

    TMP = pd.read_pickle(RawPikFile[0])

    # Rover Temperatures
    fig = plt.figure(figsize=(14.0, 9.0))
    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], figure=fig)
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharex=ax0)

    ax0.plot(TMP.DT, TMP.PIU_T.astype('int64'), label='PIU')
    ax0.plot(TMP.DT, TMP.DCDC_T.astype('int64'), label='DCDC')
    ax0.legend(loc='upper right', frameon=False)
    ax0.set_ylabel('Rover Monitored \n Temperature [$^\circ$C]')

    ax1.plot(ROV.DT, ROV.HTR_ST.astype('int64'), label='Heater Status')
    ax1.text(.99, .9, 'Rover Heater Status', color='0.25', fontweight='bold',
             horizontalalignment='right', transform=ax1.transAxes)
    ax1.yaxis.tick_right()
    ax1.yaxis.set_label_position('right')
    ax1.set_ylabel('LDO RAW [ENG]')
    ax1.set_ylim([-0.1, 1.1])
    ax1.get_yaxis().set_visible(False)
    ax1.set_xlabel('Date Time')

    format_axes(fig, integers=True)
    ax1.tick_params(labelbottom=True)

    fig.tight_layout()
    fig.savefig(HK_DIR / 'ROV_TEMPS.png')

    if Interact:
        plt.show()

    plt.close(fig)

    logger.info("Producing Rover Temperature Plot Completed")


def Rover_Power(PROC_DIR, Interact=False):
    """"Produces a Rover power consumption plot from pickle files"""

    logger.info("Producing Rover Power Plot")

    HK_DIR = MakeHKPlotsDir(PROC_DIR)

    # Search for PanCam Rover Status Processed Files
    RawPikFile = PC_Fns.Find_Files(
        PROC_DIR, "*RoverStatus.pickle", SingleFile=True)
    if not RawPikFile:
        logger.warning("No file found - ABORTING")
        return

    ROV = pd.read_pickle(RawPikFile[0])

    # Rover Current and Status Plot
    fig = plt.figure(figsize=(14.0, 9.0))
    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], figure=fig)
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharex=ax0)

    ax0.plot(ROV.DT, ROV.Inst_Curr, label='Instr.')
    ax0.plot(ROV.DT, ROV.HTR_Curr, label='HTR')
    ax0.legend(loc='upper right')
    ax0.set_ylabel('Current [A]')

    ax1.plot(ROV.DT, ROV.PWR_ST, label='Instr.')
    ax1.plot(ROV.DT, ROV.HTR_ST, label='HTR')
    add_text(ax1, 'Status')
    ax1.yaxis.tick_right()
    ax1.yaxis.set_label_position('right')
    ax1.set_ylabel('Status')
    ax1.set_ylim([-0.1, 1.1])
    ax1.get_yaxis().set_visible(False)
    ax1.set_xlabel('Date Time')

    format_axes(fig, integers=True)
    ax1.tick_params(labelbottom=True)

    fig.tight_layout()
    fig.savefig(HK_DIR / 'ROV_PWR.png')

    if Interact:
        plt.show(block=False)

    plt.close(fig)

    # Rover Status and Power Extract
    ACT = ROV[(ROV.PWR_ST > 0) | (ROV.HTR_ST > 0)]
    if not ACT.empty:
        fig2 = plt.figure(figsize=(14.0, 9.0))
        gs2 = gridspec.GridSpec(2, 1, height_ratios=[3, 1], figure=fig)
        ax2 = fig2.add_subplot(gs2[0])
        ax3 = fig2.add_subplot(gs2[1], sharex=ax2)

        ax2.plot(ACT.DT, ACT.Inst_Curr, label='Instr.')
        ax2.plot(ACT.DT, ACT.HTR_Curr, label='HTR')
        ax2.legend(loc='upper right')
        ax2.set_ylabel('Current [A]')

        ax3.plot(ACT.DT, ACT.PWR_ST, '.', label='Instr.')
        ax3.plot(ACT.DT, ACT.HTR_ST, '.', label='HTR')
        add_text(ax3, 'Status')
        ax3.yaxis.tick_right()
        ax3.yaxis.set_label_position('right')
        ax3.set_ylabel('Status')
        ax3.set_ylim([-0.1, 1.1])
        ax3.get_yaxis().set_visible(False)
        ax3.set_xlabel('Date Time')

        format_axes(fig2)
        ax3.tick_params(labelbottom=True)

        fig2.tight_layout()
        fig2.savefig(HK_DIR / 'ROV_PWR_EXT.png')

    if Interact:
        plt.show()

    plt.close(fig)

    logger.info("Producing Rover Power Plot Completed")


def HK_Overview(PROC_DIR, Interact=False):
    """"Produces an overview of the TCs, Power Status and Errors"""

    logger.info("Producing Overview Plot")

    HK_DIR = MakeHKPlotsDir(PROC_DIR)

    # Search for PanCam RAW Processed Files
    RawPikFile = PC_Fns.Find_Files(
        PROC_DIR, "*RAW_HKTM.pickle", SingleFile=True)
    if not RawPikFile:
        logger.info("No RAW_HKTM file found - ABORTING")
        return

    RAW = pd.read_pickle(RawPikFile[0])

    # Search for PanCam Rover Telecommands
    # May need to switch to detect if Rover TC or LabView TC
    TCPikFile = PC_Fns.Find_Files(
        PROC_DIR, "*Unproc_TC.pickle", SingleFile=True)
    if not TCPikFile:
        logger.info("No TC file found - Leaving Blank")
        TC = pd.DataFrame()
        TCPlot = False
    else:
        TCPlot = True

    if TCPlot:
        TC = pd.read_pickle(TCPikFile[0])

    # RAW Plot and Heater
    fig = plt.figure(figsize=(14.0, 9.0))
    gs = gridspec.GridSpec(5, 1, height_ratios=[
                           1, 0.5, 0.5, 0.5, 0.5], figure=fig)
    gs.update(hspace=0.0)
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharex=ax0)
    ax2 = fig.add_subplot(gs[2], sharex=ax0)
    ax3 = fig.add_subplot(gs[3], sharex=ax0)
    ax4 = fig.add_subplot(gs[4], sharex=ax0)

    # Action List
    if TCPlot:
        size = TC.shape[0]
        TC['LEVEL'] = 1
        markerline, stemline, baseline = ax0.stem(
            TC['DT'], TC['LEVEL'], linefmt='C3-', basefmt="k-", use_line_collection=True)
        plt.setp(markerline, mec="k", mfc="w", zorder=3)
        markerline.set_ydata(np.zeros(size))
        for i in range(0, size):
            ax0.annotate(TC.ACTION.iloc[i], xy=(TC.DT.iloc[i], TC.LEVEL.iloc[i]), xytext=(0, -2),
                         textcoords="offset points", va="top", ha="right", rotation=90)
    else:
        ax0.get_yaxis().set_visible(False)
    add_text(ax0, 'Action List')

    # Cam Power and Enable
    ax1.plot(RAW.DT, RAW.Stat_PIU_En.astype('int64'), label='ENA')
    ax1.plot(RAW.DT, RAW.Stat_PIU_Pw.astype('int64'), label='PWR')
    add_text(ax1, 'Cam ENA and PWR')
    ax1.legend(loc='center right', bbox_to_anchor=(
        1.0, 0.5), ncol=1, borderaxespad=0, frameon=False)
    ax1.set_ylim([-0.5, 3.4])
    ax1.set_yticks([0, 1, 2, 3])
    ax1.set_yticklabels(['None', 'WACL', 'WACR', 'HRC'])

    # PIU Errors
    ax2.plot(RAW.DT, RAW.ERR_1_CMD.astype('int64') != 0, '.', label='CMD')
    ax2.plot(RAW.DT, RAW.ERR_1_FW.astype('int64') != 0,  '.', label='FW')
    ax2.plot(RAW.DT, (RAW.ERR_2_LWAC.astype('int64') != 0) & (
        RAW.ERR_2_LWAC.astype('int64') != 0x4), '.', label='LWAC')
    ax2.plot(RAW.DT, (RAW.ERR_2_RWAC.astype('int64') != 0) & (
        RAW.ERR_2_RWAC.astype('int64') != 0x4), '.', label='RWAC')
    ax2.plot(RAW.DT, RAW.ERR_3_HRC.astype('int64') != 0,  '.', label='HRC')
    ax2.legend(loc='center right', bbox_to_anchor=(
        1.0, 0.5), ncol=1, borderaxespad=0, frameon=False)
    ax2.set_ylim([-0.1, 1.1])
    ax2.get_yaxis().set_visible(False)
    add_text(ax2, 'Errors excl. WAC CMD TO')

    ax3.plot(RAW.DT, RAW.ERR_2_LWAC.astype('int64')
             == 0x4, '.', label='LWAC', color='C2')
    ax3.plot(RAW.DT, RAW.ERR_2_RWAC.astype('int64')
             == 0x4, '.', label='RWAC', color='C3')
    ax3.legend(loc='center right', bbox_to_anchor=(
        1.0, 0.5), ncol=1, borderaxespad=0, frameon=False)
    ax3.set_ylim([-0.1, 1.1])
    ax3.get_yaxis().set_visible(False)
    add_text(ax3, 'WAC CMD TO Error')

    ax4.plot(RAW.DT, RAW.IMG_No)
    if ax4.get_ylim()[1] < 1:
        ax4.set_ylim([-0.1, 1.1])
    ax4.grid(True)
    add_text(ax4, 'Img #')
    ax4.set_xlabel('Date Time')

    format_axes(fig)
    ax4.tick_params(labelbottom=True)

    fig.tight_layout()
    fig.savefig(HK_DIR / 'HK_OVR.png')

    if Interact:
        plt.show(block=True)

    plt.close(fig)

    logger.info("Producing Overview Plot Completed")


def HRC_CS(PROC_DIR, Interact=False):
    """"Produces a plot of the HRC Camera Status from pickle files"""

    logger.info("Producing HRC Status Plots")

    HK_DIR = MakeHKPlotsDir(PROC_DIR)

    # Search for PanCam RAW Processed Files
    RawPikFile = PC_Fns.Find_Files(
        PROC_DIR, "*RAW_HKTM.pickle", SingleFile=True)
    if not RawPikFile:
        logger.warning("No file found - ABORTING")
        return

    RAW = pd.read_pickle(RawPikFile[0])

    if not 'HRC_ACK' in RAW:
        logger.info("No HRC data available")
        return

    if not 0x02 in RAW['HRC_ACK'].values:
        logger.info("No HRC CS response available")
        return

    # Search for PanCam Rover Telecommands
    # May need to switch to detect if Rover TC or LabView TC
    TCPikFile = PC_Fns.Find_Files(
        PROC_DIR, "*Unproc_TC.pickle", SingleFile=True)
    if not TCPikFile:
        logger.info("No TC file found - Leaving Blank")
        TC = pd.DataFrame()
        TCPlot = False
    else:
        TCPlot = True

    if TCPlot:
        TC = pd.read_pickle(TCPikFile[0])

    # Create plot structure
    fig = plt.figure(figsize=(14.0, 9))
    gs = gridspec.GridSpec(7, 1, height_ratios=[
                           1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], figure=fig)
    gs.update(hspace=0.0)
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharex=ax0)
    ax2 = fig.add_subplot(gs[2], sharex=ax0)
    ax3 = fig.add_subplot(gs[3], sharex=ax0)
    ax4 = fig.add_subplot(gs[4], sharex=ax0)
    ax5 = fig.add_subplot(gs[5], sharex=ax0)
    ax6 = fig.add_subplot(gs[6], sharex=ax0)

    # Action List
    if TCPlot:
        size = TC.shape[0]
        TC['LEVEL'] = 1

        markerline, stemline, baseline = ax0.stem(
            TC['DT'], TC['LEVEL'], linefmt='C3-', basefmt="k-", use_line_collection=True)
        plt.setp(markerline, mec="k", mfc="w", zorder=3)
        markerline.set_ydata(np.zeros(size))
        add_text('Action List')
        for i in range(0, size):
            ax0.annotate(TC.ACTION.iloc[i], xy=(TC.DT.iloc[i], TC.LEVEL.iloc[i]), xytext=(0, -2),
                         textcoords="offset points", va="top", ha="right", rotation=90)
    # remove y axis and spines
    ax0.get_yaxis().set_visible(False)

    # Encoder Value
    ax1.plot(RAW['DT'], RAW['HRC_ENC'], '.')
    add_text(ax1, 'Enc Value')

    # Enc and MM Flag
    ax2.plot(RAW['DT'], RAW['HRC_EPF'], label='Enc')
    ax2.plot(RAW['DT'], RAW['HRC_MMF'], '.', label='MM')
    ax2.legend(loc='center right', bbox_to_anchor=(
        1.0, 0.5), ncol=1, borderaxespad=0, frameon=False)
    add_text(ax2, 'ENC & MM')
    ax2.set_ylim([-0.1, 1.1])
    ax2.yaxis.tick_right()
    ax2.yaxis.set_label_position('right')
    ax2.get_yaxis().set_visible(False)

    # AF and AI Flag
    ax3.plot(RAW['DT'], RAW['HRC_AFF'], label='AF')
    ax3.plot(RAW['DT'], RAW['HRC_AIF'], label='AI')
    ax3.legend(loc='center right', bbox_to_anchor=(
        1.0, 0.5), ncol=1, borderaxespad=0, frameon=False)
    add_text(ax3, 'AF & AI')
    ax3.set_ylim([-0.1, 1.1])
    ax3.get_yaxis().set_visible(False)

    # Current Sharpness
    ax4.plot(RAW['DT'], RAW['HRC_CS'])
    add_text(ax4, 'Sharpness')

    # Image Counter
    ax5.plot(RAW['DT'], RAW['HRC_IFC'], '.')
    add_text(ax5, 'IMG Count')
    ax5.yaxis.tick_right()
    plt.setp(ax5.get_yticklabels(), visible=False)
    ax5.yaxis.set_label_position('right')

    # Sensor Temp
    ax6.plot(RAW['DT'], RAW['HRC_TP'])
    add_text(ax6, 'RAW Sensor Temp')

    # Re-adjust x-axis so that doesn't interfere with text
    xstart, xend = ax0.get_xlim()
    new_xlimits = (xstart, (xend - xstart)*1.1+xstart)
    ax0.set_xlim(new_xlimits)

    format_axes(fig)
    ax6.tick_params(labelbottom=True)

    fig.tight_layout()
    fig.savefig(HK_DIR / 'HRC_CS.png')

    if Interact:
        plt.show(block=True)

    plt.close(fig)

    logger.info("Producing HRC CS Plot Completed")


def FW(PROC_DIR, Interact=False):
    """"Produces a plot of the FW Status from pickle files"""

    logger.info("Producing FW Status Plots")

    HK_DIR = MakeHKPlotsDir(PROC_DIR)

    # Search for PanCam RAW Processed Files
    RawPikFile = PC_Fns.Find_Files(
        PROC_DIR, "*RAW_HKTM.pickle", SingleFile=True)
    if not RawPikFile:
        logger.warning("No file found - ABORTING")
        return

    RAW = pd.read_pickle(RawPikFile[0])

    # Search for PanCam Rover Telecommands
    # May need to switch to detect if Rover TC or LabView TC
    TCPikFile = PC_Fns.Find_Files(
        PROC_DIR, "*Unproc_TC.pickle", SingleFile=True)
    if not TCPikFile:
        logger.info("No TC file found - Leaving Blank")
        TC = pd.DataFrame()
        TCPlot = False
    else:
        TCPlot = True

    if TCPlot:
        TC = pd.read_pickle(TCPikFile[0])

    # Create plot structure
    fig = plt.figure(figsize=(14.0, 9))
    gs = gridspec.GridSpec(7, 1,
                           height_ratios=[1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
                           figure=fig)
    gs.update(hspace=0.0)
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharex=ax0)
    ax2 = fig.add_subplot(gs[2], sharex=ax0)
    ax3 = fig.add_subplot(gs[3], sharex=ax0)
    ax4 = fig.add_subplot(gs[4], sharex=ax0)
    ax5 = fig.add_subplot(gs[5], sharex=ax0)
    ax6 = fig.add_subplot(gs[6], sharex=ax0)

    # Action List
    if TCPlot:
        size = TC.shape[0]
        TC['LEVEL'] = 1

        markerline, stemline, baseline = ax0.stem(
            TC['DT'], TC['LEVEL'], linefmt='C3-', basefmt="k-", use_line_collection=True)
        plt.setp(markerline, mec="k", mfc="w", zorder=3)
        markerline.set_ydata(np.zeros(size))
        add_text(ax0, 'Action List')
        for i in range(0, size):
            ax0.annotate(TC.ACTION.iloc[i], xy=(TC.DT.iloc[i], TC.LEVEL.iloc[i]), xytext=(0, -2),
                         textcoords="offset points", va="top", ha="right", rotation=90)
    # remove y axis and spines
    ax0.get_yaxis().set_visible(False)

    # FW Running Flag
    ax1.plot(RAW['DT'], RAW['Stat_FWL_Op'], label='FWL')
    ax1.plot(RAW['DT'], RAW['Stat_FWR_Op'], label='FWR')
    ax1.legend(loc='center right', bbox_to_anchor=(
        1.0, 0.5), ncol=1, borderaxespad=0, frameon=False)
    add_text(ax1, 'Running')
    ax1.set_ylim([-0.1, 1.1])
    ax1.get_yaxis().set_visible(False)

    # FW Home Flag
    ax2.plot(RAW['DT'], RAW['Stat_FWL_Ho'], label='FWL')
    ax2.plot(RAW['DT'], RAW['Stat_FWR_Ho'], label='FWR')
    add_text(ax2, 'Home')
    ax2.set_ylim([-0.1, 1.1])
    ax2.yaxis.tick_right()
    ax2.get_yaxis().set_visible(False)

    # FW Index Flag
    ax3.plot(RAW['DT'], RAW['Stat_FWL_Id'], label='FWL')
    ax3.plot(RAW['DT'], RAW['Stat_FWR_Id'], label='FWR')
    add_text(ax3, 'Index')
    ax3.set_ylim([-0.1, 1.1])
    ax3.get_yaxis().set_visible(False)

    # FW Position
    ax4.plot(RAW['DT'], RAW['Stat_FWL_Po'], label='FWL')
    ax4.plot(RAW['DT'], RAW['Stat_FWR_Po'], label='FWR')
    add_text(ax4, 'Position')

    # Absolute Steps
    ax5.plot(RAW['DT'], RAW['FWL_ABS'], label='FWL')
    ax5.plot(RAW['DT'], RAW['FWR_ABS'], label='FWR')
    add_text(ax5, 'Absolute Steps')
    ax5.yaxis.tick_right()
    ax5.yaxis.set_label_position('right')

    # Relative Steps
    ax6.plot(RAW['DT'], RAW['FWL_REL'], label='FWL')
    ax6.plot(RAW['DT'], RAW['FWR_REL'], label='FWR')
    add_text(ax6, 'Relative Steps')
    ax6.set_xlabel('Date Time')

    # Re-adjust x-axis so that
    xlimits = ax0.get_xlim()
    new_xlimits = (xlimits[0], (xlimits[1] - xlimits[0])*1.1+xlimits[0])
    ax0.set_xlim(new_xlimits)

    format_axes(fig)
    ax6.tick_params(labelbottom=True)

    fig.tight_layout()
    fig.savefig(HK_DIR / 'FW.png')

    if Interact:
        plt.show(block=True)

    plt.close(fig)

    logger.info("Producing FW Status Plot Completed")


def psu(proc_dir, Interact=False):

    logger.info("Producing PSU Plot")

    hk_dir = MakeHKPlotsDir(proc_dir)

    psupikfile = PC_Fns.Find_Files(proc_dir, "psu.pickle", SingleFile=True)

    if not psupikfile:
        logger.warning("No file found - ABORTING")
        return

    data = pd.read_pickle(psupikfile[0])

    fig = plt.figure(figsize=(14.0, 9.0))
    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], figure=fig)
    ax0 = fig.add_subplot(gs[0])
    ax1 = ax0.twinx()
    ax2 = fig.add_subplot(gs[1], sharex=ax0)

    ax0.plot(data['DT'], data['Voltage'], 'C0-', label='Instr.')
    ax0.plot(data['DT'], data['Htr. Voltage'], 'C0--', label='HTR')
    ax0.legend(loc='upper right')
    ax0.set_ylabel('Voltage - Zoom [V]')
    ax0.set_ylim(26, 30.0)

    ax1.plot(data['DT'], data['Current'], 'C2-', label='Instr.')
    ax1.plot(data['DT'], data['Htr. Current'], 'C2--', label='HTR')
    ax1.set_ylabel('Current [A]')
    ax1.set_ylim(-0.01, 0.35)
    ax1.spines['right'].set_color('C2')
    ax1.tick_params(axis='y', colors='C2')
    ax1.yaxis.label.set_color('C2')
    ax1.grid(color='lightgreen')

    ax2.plot(data['DT'], data['Voltage'], 'C0-', label='Instr.')
    ax2.plot(data['DT'], data['Htr. Voltage'], 'C0--', label='HTR')
    ax2.set_ylabel('Voltage [V]')
    ax2.set_xlabel('Date Time')

    format_axes(fig)
    ax0.grid(False)
    ax2.tick_params(labelbottom=True)

    fig.tight_layout()
    fig.savefig(hk_dir / 'PSU_Cur.png')

    if Interact:
        plt.show(block=False)

    fig2 = plt.figure(figsize=(14.0, 9.0))
    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], figure=fig2)
    ax3 = fig2.add_subplot(gs[0])
    ax4 = ax3.twinx()
    ax5 = fig2.add_subplot(gs[1], sharex=ax3)

    ax3.plot(data['DT'], data['Voltage'], 'C0-', label='Instr.')
    ax3.plot(data['DT'], data['Htr. Voltage'], 'C0--', label='HTR')
    ax3.legend(loc='upper right')
    ax3.set_ylabel('Voltage - Zoom [V]')
    ax3.set_ylim(26, 30.0)

    ax4.plot(data['DT'], data['Power'], 'C1-', label='Instr.')
    ax4.plot(data['DT'], data['Htr. Power'], 'C1--', label='HTR')
    ax4.set_ylabel('Power [W]')
    ax4.spines['right'].set_color('C1')
    ax4.tick_params(axis='y', colors='C1')
    ax4.yaxis.label.set_color('C1')
    ax4.grid(color='wheat')

    ax5.plot(data['DT'], data['Voltage'], 'C0-', label='Instr.')
    ax5.plot(data['DT'], data['Htr. Voltage'], 'C0--', label='HTR')
    ax5.set_ylabel('Voltage [V]')
    ax5.set_xlabel('Date Time')

    format_axes(fig2)
    ax3.grid(False)
    ax5.tick_params(labelbottom=True)

    fig2.tight_layout()
    fig2.savefig(hk_dir / 'PSU_Pwr.png')

    if Interact:
        plt.show(block=True)


if __name__ == "__main__":
    DIR = Path(
        input("Type the path to the PROC folder where the processed files are stored: "))

    logging.basicConfig(filename=(DIR / 'processing.log'),
                        level=logging.INFO,
                        format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
    logger.info('\n\n\n\n')
    logger.info("Running Plotter.py as main")
    logger.info("Reading directory: %s", DIR)

    #HK_Temperatures(DIR, True)
    # Rover_Temperatures(DIR)
    # Rover_Power(DIR)
    #HK_Overview(DIR, True)
    #HK_Voltages(DIR, True)
    #HRC_CS(DIR, True)
    #FW(DIR, Interact=True)
    psu(DIR, Interact=True)
