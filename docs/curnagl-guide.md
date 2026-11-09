# Curnagl guide (step by step)

Last updated: 2026-11-08. Practical commands for this project; see the DCSR documentation
for the cluster itself.

## Where each thing happens

| Task | Where |
|---|---|
| Edit files, `git add/commit/push` | WSL (Ubuntu), on the mounted repository `~/repos/AITCHazard_Mexico` |
| Run anything (`apptainer`, `sbatch`, `squeue`, `seff`) | Curnagl, after `ssh curnagl` |

`~/repos` in WSL is the Curnagl folder `/work/FAC/FGSE/IDYST/tbeucler/default/apereze/repos`
mounted with `sshfs` (alias `mirror`): there is a single copy of the repository. Before
copying files or committing, run `pwd` and check it ends in `AITCHazard_Mexico`.

## One-time setup (WSL)

```bash
cat >> ~/.ssh/config <<'EOF'
Host curnagl
    HostName curnagl.dcsr.unil.ch
    User apereze1
    IdentityFile ~/.ssh/curnagl
    ServerAliveInterval 60
EOF
chmod 600 ~/.ssh/config
ssh curnagl hostname
```

The shell alias `curnagl` only works when typed alone; `ssh curnagl`, `scp` and tunnels need
the `Host curnagl` entry above. If `code .` fails with `Invalid argument`, run
`wsl --shutdown` in Windows PowerShell, reopen Ubuntu and run `mirror` again.

## Variables used everywhere (Curnagl)

```bash
cd /work/FAC/FGSE/IDYST/tbeucler/default/apereze/repos/AITCHazard_Mexico
module load apptainer/1.4.1
BASE=/work/FAC/FGSE/IDYST/tbeucler/default/apereze
SIF=$BASE/aifs/aifs_single_v2_era5.sif
PYLIBS=$BASE/aifs/pylibs/aifs11
```

Run AIFS code with `apptainer exec --bind /work --env PYTHONPATH=$PYLIBS $SIF python ...`.
Without `PYTHONPATH=$PYLIBS` the AIFS 1.1 checkpoint does not load.

## Long tasks on the login node: `tmux`

```bash
tmux new -s name        # open
# Ctrl+b, then d        # leave it running
tmux attach -t name     # come back (after ssh curnagl)
```

The login node allows at most 32 GB and 4 cores per user: downloads and plots only.

## Jobs

| Action | Command |
|---|---|
| Submit | `sbatch slurm/block1_bench_day.slurm` (prints the JOB_ID) |
| Submit another day | `sbatch --export=BENCH_DAY=2005-07-17 slurm/block1_bench_day.slurm` |
| Queue | `squeue -u apereze1` (`PD` waiting, `R` running, gone = finished) |
| Log | `tail -f logs/<name>-<JOB_ID>.log` (`Ctrl+C` leaves, the job keeps running) |
| Resources used | `seff <JOB_ID>`, `sacct -j <JOB_ID> --format=JobID,Elapsed,MaxRSS,State` |
| Cancel | `scancel <JOB_ID>` |

SLURM scripts that use `#SBATCH --export=NONE` must `export SLURM_EXPORT_ENV=ALL` after
`module load`, otherwise `srun` does not find `apptainer`.

## Jupyter on a GPU node

```bash
sbatch --cpus-per-task=8 --mem=64G --time=02:00:00 slurm/jupyter_gpu.slurm
tail -f logs/AIFSAPE-<JOB_ID>.log      # prints the tunnel command and the URL
```

In a local WSL terminal run the printed `ssh -n -N -L 8080:<node_ip>:<port> curnagl`, then
in VS Code: Select Kernel → Existing Jupyter Server → `http://127.0.0.1:8080/?token=<TOKEN>`.
Finish with `scancel <JOB_ID>`.

## Copying files

- From Windows to the repository (WSL): `cp /mnt/c/Users/adolf/Downloads/<file> ~/repos/AITCHazard_Mexico/<folder>/`.
  Check `ls -t /mnt/c/Users/adolf/Downloads | head` first: repeated downloads get ` (1)`.
- From the repository to Windows: `cp ~/repos/AITCHazard_Mexico/outputs/.../*.png /mnt/c/Users/adolf/Downloads/`.
- When pasting commands, check that URLs did not turn into `[text](url)`.

## Common errors

| Message | Cause | Fix |
|---|---|---|
| `execve(): apptainer: No such file or directory` | `srun` without the module environment | `export SLURM_EXPORT_ENV=ALL` |
| `No module named 'torch_geometric.nn.conv.utils.inspector'` | Missing AIFS 1.1 overlay | `--env PYTHONPATH=$PYLIBS` |
| `cp: cannot create regular file 'notebooks/'` | Not in the repository folder | `cd ~/repos/AITCHazard_Mexico` |
| `Could not resolve host: [www...](...)` | URL pasted as Markdown | Paste the plain URL |
