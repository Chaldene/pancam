# -*- coding: utf-8 -*-
"""
main.py

Barry Whiteside
Mullard Space Science Laboratory - UCL

PanCam Data Processing Tools
Created 31 Oct 2019
"""

from pathlib import Path
import logging
import shutil
import json

import plotter
import hk_cal
import hk_raw
import image_browse
import rover_ha
import rover
import swis
import hs
import labview
import tc_cal
import pancam_fns

logger, status = pancam_fns.setup_logging()

if __name__ == '__main__':

    status.info("Running main.py")

    # Select Folder to Process
    top_dir = Path(
        input("Type the path to the folder where the RAW log or archive files are stored: "))
    if (not top_dir.is_dir()) or top_dir == Path("."):
        logging.error("Non-Valid path provided - exiting")
        quit()

    # Determine if working with archived folder
    arch = input("Is the folder in a tar.bz2 archive? [Y/N (Default)]: ")
    if arch == 'Y' or arch == 'y':
        file_arch = input("Input the archive full filename: ")
        file_path = top_dir / file_arch

        if file_path.suffixes != ['.tar', '.bz2']:
            logger.error("Not a valid archive format - exiting")
            quit()

        logger.info("Unpacking archive to: %s", top_dir)
        shutil.unpack_archive(file_path, top_dir, 'bztar')

        # New top dir
        top_dir = top_dir / file_path.stem[:-4]

        arch_logs = False

    else:
        arch_user = input(
            "Do you want to archive the files after processing? [Y/N (Default)]: ")
        if arch_user == 'Y' or arch_user == 'y':
            arch_logs = True
        else:
            arch_logs = False

    # Test if processed directory folder exists, if not create it.
    proc_dir = top_dir / 'PROC'
    if not proc_dir.is_dir():
        MakeDir = True
        proc_dir.mkdir()

    # Create file handler logger
    pancam_fns.setup_proc_logging(logger, proc_dir)
    logger.info('\n\n\n\n')
    logger.info("main.py")

    # Check for a config.json and determine type else create one
    config_file = top_dir / "config.json"
    source = None
    model = None
    if config_file.exists():
        # Read source type
        with open(config_file, 'r') as f:
            try:
                config = json.load(f)
            except:
                config = {}

            if 'Source' in config:
                source = config['Source']

                # Check rover source contains required fields
                if (config['Source'] == 'Rover') & ('Source Details' in config):
                    try:
                        model = config['Source Details']['Model']
                    except:
                        model = None

    else:
        config_file.touch()
        config = {}

    # Cycle through processing types
    if not source:
        # First check if SWIS as multiple folders
        instances = swis.create_instances(top_dir)
        if instances:
            status.info("SWIS Instances Found")
            source = "SWIS"

        elif labview.hk_extract(top_dir, archive=arch_logs):
            status.info("LabView Type Found")
            source = "LabView"

        elif rover.TM_extract(top_dir):
            status.info("Rover Type Found")
            source = "Rover"

            # Idnetify Rover model
            model = rover.type(top_dir)

            # Version of RVSW
            version = rover.sw_ver(top_dir)

            source_details = {"Type": "Rover",
                              "Model": model,
                              "RMSW Ver": version}

            config.update({"Source Details": source_details})

        elif swis.nsvf_parse(top_dir):
            status.info("Single SWIS Type Found")
            source = "Single SWIS"

        else:
            status.error("No Source Type could be determined - Aborting")
            source = "Undetermined"

        # Write type to config_file
        if config:
            config.update({"Source": source})
        else:
            config = {"Source": source}

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4, sort_keys=True)

    if source == 'SWIS':
        for inst in instances:
            proc_dir = inst / "PROC"
            status.info("Analysing %s", inst.name)
            swis.hk_extract(inst)
            swis.hs_extract(inst)
            hs.decode(proc_dir, True)
            hs.verify(inst)
            hk_raw.decode(proc_dir, source)
            hk_cal.cal_HK(proc_dir)
            tc_cal.decode_all(proc_dir)
            plotter.all_plots(proc_dir)
            swis.sci_extract(inst)
            swis.sci_compare(inst)
            image_browse.Img_RAW_Browse(proc_dir)

    elif source == 'LabView':
        # LabView Files
        labview.hs_extract(top_dir, archive=arch_logs)
        hs.decode(proc_dir)
        hs.verify(proc_dir)
        labview.tc_extract(top_dir)
        if hs.all_default_image_dim(proc_dir):
            labview.sci_extract(top_dir, archive=arch_logs)
            labview.bin_move(top_dir, archive=arch_logs)
        else:
            labview.bin_move(top_dir, archive=arch_logs, comp_spw=False)
        labview.psu_extract(top_dir, archive=arch_logs)
        labview.create_spw_images(proc_dir)
        if arch_logs:
            labview.create_archive(top_dir)

    elif source == "Rover":
        # Rover files
        rover.TC_extract(top_dir)
        rover.TM_extract(top_dir)
        rover_ha.HaScan(top_dir)
        rover_ha.RestructureHK(proc_dir)
        rover_ha.compareHaCSV(proc_dir)
        rover.NavCamBrowse(top_dir)

    elif source == "Single SWIS":
        swis.nsvf_lb_extract(top_dir)
        swis.nsvf_tc_extract(top_dir)
        swis.hk_extract(proc_dir)
        hs.decode(proc_dir, spw_header=True)
        hs.verify(proc_dir)
        swis.sci_extract(proc_dir, True)
        swis.sci_compare(proc_dir)

    elif source == "Undetermined":
        quit()

    # Process secondary files
    hk_raw.decode(proc_dir, source, model)
    image_browse.Img_RAW_Browse(proc_dir)
    hk_cal.cal_HK(proc_dir)
    tc_cal.decode_all(proc_dir)

    # Produce Plots
    plotter.all_plots(proc_dir)

logger.info("main.py completed")
