#!/usr/bin/python3

import sys
import subprocess
import threading
import time
import queue
import os

try:
    import matlab.engine
except ImportError:
    print("MATLAB engine could not be found. Converter and plotter tools may not function properly. See README.md for details on how to install this component.\n")
    matlab_available = False
else:
    matlab_available = True

class SiGPyC_Controller():

    def __init__(self, test_mode=False):

        # Class variables used for the subprocesses run, if any, of the tools
        # run when their checkboxes are selected
        self.usrp_proc = None
        self.controller_proc = None
        self.converter_proc = None
        self.plotter_proc = None
        self.iperf_client_proc = None
        self.iperf_server_proc = None

        # iperf-specific variables. The client_addr and server_addr variables
        # are self-explanatory and are set from the GUI's lineedit boxes.
        # Rate and mem_addr are for the other inputs to the client call
        # iperf -c [IP] -u -b[100]M -S [0x00]  -t10000000000
        self.iperf_client_addr = None
        self.iperf_server_addr = None
        self.iperf_rate = None
        self.iperf_mem_addr = None

        # The arguments to give to subprocess.Popen() to run iperf
        self.iperf_client_args = ["iperf", "-c", str(self.iperf_client_addr), "-u", "-b"+str(self.iperf_rate)+"M", "-S", str(self.iperf_mem_addr), "-t10000000000"]
        self.iperf_server_args = ["iperf", "-s", "-u", "-t100000000000000"]

        # Default run time length
        self.run_time = 0.5

        # Output/conversion file name
        self.file_name = ""

        # Path of project directory for use in calls to scripts in utils/
        self.working_dir = os.getcwd()

        # Each of these targets a local test script that prints a
        # self-identification message, then runs time.sleep() for a certain
        # amount of seconds
        if test_mode == True:
            self.usrp_control_args = ["python3", self.working_dir + "/tests/usrp_sim.py"]
            self.sg_controller_args = ["python3", self.working_dir + "/tests/sg_sim.py"]
            self.matlab_converter_args = ["python3", self.working_dir + "/tests/converter_sim.py"]
            self.matlab_plotter_args = ["python3", self.working_dir + "/tests/plotter_sim.py"]
            self.iperf_client_args = ["python3", self.working_dir + "/tests/iperf_sim.py", str(self.iperf_client_addr)]

        # Run the real arguments in the intended environment using
        # subprocess.Popen()
        else:
            self.usrp_control_args = ["python", self.working_dir + "/utils/writeIQ.py", "123", str(self.run_time)]
            self.sg_controller_args = ["python3", self.working_dir + "/utils/ramp_control.py", str(self.run_time)]

        if matlab_available == True:
            print("Starting Matlab engine for Python... ")
            self.engine = matlab.engine.start_matlab()
            print("Done\n")

            print("Pre-cleaning workspace...")
            self.engine.close('all', nargout=0)
            self.engine.clear('all', nargout=0)
            print("Done\n")
            print("Setting up Matlab engine workspace...")
            cur_dir = os.getcwd()
            self.engine.addpath(self.engine.genpath(cur_dir))
            print("Done\n")
        else:
            print("MATLAB not previously found during import step. Skipping setup...\n")


    # Runs a subprocess for the USRP based on the usrp_control_args variable
    def start_usrp(self):
        print("Running USRP...\n")
        self.usrp_control_args = ["python", self.working_dir + "/utils/writeIQ.py", self.file_name, str(self.run_time)]
        self.usrp_proc = subprocess.Popen(self.usrp_control_args, stdin=subprocess.PIPE, stderr=None, shell=False)
        while self.usrp_proc.poll() is None:
            continue
        print("Done sensing medium\n")

        return
    # Runs a subprocess for the SGControl tool based on the sg_controller_args
    # variable
    def start_controller(self, args):
        print("Running interference...\n")
        self.controller_proc = subprocess.Popen(self.sg_controller_args, stdin=subprocess.PIPE, stderr=None, shell=False)
        while self.controller_proc.poll() is None:
            continue
        print("Done injecting interference\n")

        return

    # Runs the USRP and SGControl tools simultaneously if and only if both boxes
    # are checked
    def start_usrp_controller(self):
        print("Running USRP with interference injected...\n")
        self.usrp_control_args = ["python", self.working_dir + "/utils/writeIQ.py", self.file_name, str(self.run_time)]
        self.usrp_proc = subprocess.Popen(self.usrp_control_args, stdin=subprocess.PIPE, stderr=None, shell=False)
        self.controller_proc = subprocess.Popen(self.sg_controller_args, stdin=subprocess.PIPE, stderr=None, shell=False)

        while True:

            self.usrp_proc.poll()
            self.controller_proc.poll()
            # Make sure the sequence won't continue until both tools have
            # finished
            if self.usrp_proc.returncode is not None and self.controller_proc.returncode is not None:
                break

        print("Done sensing with added interference\n")
        return

    # Runs the USRP and iperf tools simultaneously if and only if both boxes
    # are checked
    def start_usrp_iperf(self):
        print("Running USRP with interference injected...\n")

        # Only run with the client option if something is provided. If not, the iperf client will be run elsewhere
        if self.iperf_client_addr:
            self.iperf_client_proc = subprocess.Popen(self.iperf_client_args, stdin=subprocess.PIPE, stderr=None, shell=False)

        self.iperf_server_proc = subprocess.Popen(self.iperf_server_args, stdin=subprocess.PIPE, stderr=None, shell=False)
        self.usrp_control_args = ["python", self.working_dir + "/utils/writeIQ.py", self.file_name, str(self.run_time)]
        self.usrp_proc = subprocess.Popen(self.usrp_control_args, stdin=subprocess.PIPE, stderr=None, shell=False)

        while True:

            self.usrp_proc.poll()
            # Make sure the sequence won't continue until all tools have
            # finished
            if self.usrp_proc.returncode is not None:
                break

        if self.iperf_client_addr:
            self.iperf_client_proc.kill()

        self.iperf_server_proc.kill()

        print("Done sensing with iperf\n")
        return

    def start_converter(self):
        print("Running converter tool...\n")
        print(self.file_name)
        if matlab_available == True:
            self.engine.workspace['fileName'] = self.file_name + ".bin"
            self.engine.workspace['duration'] = self.run_time
            self.engine.displayTimingInformation(nargout=0)
            print("Done conversion\n")
        else:
            print("Nothing converted. Is the MATLAB engine installed?")

    def start_plotter(self):
        print("Running plotter...\n")
        if matlab_available == True:
            self.engine.Load_and_Eval(nargout=0)
            print("Done plotting\n")
        else:
            print("Nothing plotted. Is the MATLAB engine installed?")

    # Runs the iperf client and server processes
    def start_iperf(self):
        print("Running iperf...\n")
        self.iperf_client_proc = subprocess.Popen(self.iperf_client_args, stdin=subprocess.PIPE, stderr=None, shell=False)
        self.iperf_server_proc = subprocess.Popen(self.iperf_server_args, stdin=subprocess.PIPE, stderr=None, shell=False)

        while True:

            self.iperf_client_proc.poll()
            self.iperf_server_proc.poll()
            # Make sure the sequence won't continue until both tools have
            # finished. Is it necessary that we wait for the server, or is the
            # time given to it just to ensure that we had time to run the client
            # manually?
            if self.iperf_client_proc.returncode is not None and self.iperf_server_proc.returncode is not None:
                break

        print("Done running iperf\n")
        return
