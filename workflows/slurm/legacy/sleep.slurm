#!/bin/bash

# --mail-type ALL 
# --mail-user milton.gomez@unil.ch

#SBATCH --chdir /work/FAC/FGSE/IDYST/tbeucler/default/milton/repos/
#SBATCH --job-name AIFS_testing
#SBATCH --output /work/FAC/FGSE/IDYST/tbeucler/default/milton/repos/neural_weather_models/AIFS-ens/logs/AIFS_testing-%j.out
#SBATCH --error /work/FAC/FGSE/IDYST/tbeucler/default/milton/repos/neural_weather_models/AIFS-ens/logs/AIFS_testing-%j.err

#SBATCH --partition gpu
#SBATCH --gres gpu:1
#SBATCH --gres-flags enforce-binding

#SBATCH --ntasks 1 
#SBATCH --cpus-per-task 8
#SBATCH --mem 64G
#SBATCH --time 01:00:00 
#SBATCH --export NONE

# Sleep for 1 hour to wait for other jobs to finish
sleep 1h
