#!/bin/bash

# --mail-type ALL 
# --mail-user milton.gomez@unil.ch

#SBATCH --chdir /work/FAC/FGSE/IDYST/tbeucler/default/milton/repos/
#SBATCH --job-name AIFS_ens_gen
#SBATCH --output /work/FAC/FGSE/IDYST/tbeucler/default/milton/repos/neural_weather_models/AIFS-ens/logs/AIFS_gen-%j.out
#SBATCH --error /work/FAC/FGSE/IDYST/tbeucler/default/milton/repos/neural_weather_models/AIFS-ens/logs/AIFS_gen-%j.err

#SBATCH --partition gpu
#SBATCH --gres gpu:1
#SBATCH --gres-flags enforce-binding

#SBATCH --ntasks 1 
#SBATCH --cpus-per-task 8
#SBATCH --mem 64G
#SBATCH --time 72:00:00 
#SBATCH --export NONE

# clearing modules and loading python
module purge
module load gcc cuda apptainer

# add bindpaths
export APPTAINER_BINDPATH="/users,/scratch,/work"

echo "Starting run at: `date`"

container_path="/work/FAC/FGSE/IDYST/tbeucler/default/dawn_containers/AIFS/aifs-ens.sif"
script_path="/work/FAC/FGSE/IDYST/tbeucler/default/milton/repos/neural_weather_models/AIFS-ens/date_maker.py"

echo "Running script"

# Run the script inside the container
#apptainer exec --nv $container_path bash -c "/usr/bin/which python"
apptainer exec --nv $container_path python $script_path
