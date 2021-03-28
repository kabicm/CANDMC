# This files generates bash scripts that launch jobs on piz daint according to params.ini format.

import os
import configparser
import ast
import sys
import numpy as np
import csv
import struct
from numpy import genfromtxt
import configparser
import math
import argparse
from datetime import datetime

path_to_launch = './launch/'
path_to_params = './scripts/params.ini'
cholesky_section = 'candmc'
output_path = 'benchmarks'

def createBashPreface(P, algorithm):
    numNodes = math.ceil(P/2)
    time = datetime.now().time()
    return '#!/bin/bash -l \n\
#SBATCH --job-name=candmc-%s-p%d \n\
#SBATCH --time=00:30:00 \n\
#SBATCH --nodes=%d \n\
#SBATCH --output=%s/%s-p%d-%s.txt \n\
#SBATCH --constraint=mc \n\
#SBATCH --account=g34 \n\n\
export OMP_NUM_THREADS=18 \n\n' % (algorithm, P, numNodes, output_path, algorithm, P, time)

# parse params.ini
def readConfig(section):
    config = configparser.ConfigParser()
    config.read(path_to_params)
    if not config.has_section(section):
        print("Please add a %s section", (section))
        raise Exception()

    P_info = []
    try:
        P = ast.literal_eval(config[section]['P'])
        for p in P:
            numP = p[0]
            for i in range(1, len(p)):
                P_info.append((numP, p[i]))
    except:
        print("Please add at least one number of processors P=[] (%s)" %(section))
        raise

    try:
        N = ast.literal_eval(config[section]['N'])
    except:
        print("Please add at least one matrix size N=[] (%s)" %(section))
        raise
    try:
        b = ast.literal_eval(config[section]['b'])
    except:
        print("Please add at least one tile size b_sm=[] (%s)" %(section))
        raise

    try:
        reps = ast.literal_eval(config[cholesky_section]['r'])
    except:
        print("No number of repetitions found, using default 5. If you do not want this, add r= and the number of reps")
        reps = 5

    if len(P) == 0 or len(N) ==0 or len(b) == 0:
        print("One of the arrays in params.ini is empty, please add values")
        raise Exception()
    
    return P_info, N, b, reps
    


def generateLaunchFile(P, N, B, r, algorithm, pivot):
    for p in P:
        filename = path_to_launch + 'launch_%s_%d.sh' %(algorithm, p[0])
        with open(filename, 'w') as f:
            f.write(createBashPreface(p[0], algorithm))
            for n in N:
                for b in B:
                    numNodes = math.ceil(p[0]/2)
                    # next we iterate over all possibilities and write the bash script
                    if pivot == 'both':
                        cmd = 'srun -N %d -n %d ./bin/benchmarks/lu_25d_tp_bench -n %d -num_iter %d -b_sm %d -b_lrg %d -c_rep %d \nsrun -N %d -n %d ./bin/benchmarks/lu_25d_pp_bench -n %d -num_iter %d -b_sm %d -b_lrg %d -c_rep %d \n' % (numNodes, p[0], n, r, b[0], b[1], p[1], numNodes, p[0], n, r, b[0], b[1], p[1])
                    elif pivot == 'tour':
                        cmd = 'srun -N %d -n %d ./bin/benchmarks/lu_25d_tp_bench -n %d -num_iter %d -b_sm %d -b_lrg %d -c_rep %d \n' % (numNodes, p[0], n, r, b[0], b[1], p[1])
                    elif pivot == 'part':
                        cmd = 'srun -N %d -n %d ./bin/benchmarks/lu_25d_pp_bench -n %d -num_iter %d -b_sm %d -b_lrg %d -c_rep %d \n' % (numNodes, p[0], n, r, b[0], b[1], p[1])
                    else:
                        print('Please use an existing strategy (tour, part) or do not give a strategy at all')
                        raise Exception()

                    f.write(cmd)
    return

# We use the convention that we ALWAYS use n nodes and 2n ranks
# We might want to change that in future use
if __name__ == "__main__":

    # create a launch directory if it doesn't exist yet
    os.makedirs("launch", exist_ok=True)

    parser = argparse.ArgumentParser(description='Create sbatch files for launch on Piz Daint. \n \
    For every number of processors in params.ini, exactly one script is created \n \
    After creation, use the launch on daint script to launch all')
    parser.add_argument('--dir', metavar='dir', type=str, required=False,
                    help='path to the output file', default='benchmarks')


    parser.add_argument('--pivot', metavar='pivot', type=str, required=False,
                    help='tour tournament part for partial pivoting, both for both',  default='tour')
    args = vars(parser.parse_args())

    # parse the output directory path, and make the directories
    if args['dir'] is not None:
        output_path = args['dir']
        if output_path[-1] == '/':
            output_path = output_path[:-1]
        os.makedirs(output_path, exist_ok=True)

    # create a launch directory if it doesn't exist yet

    try:
        P, Ns, b, reps = readConfig(cholesky_section)
        generateLaunchFile(P, Ns, b, reps, cholesky_section, args['pivot'])
        print("successfully generated launch files for candmc")
    except:
        pass
