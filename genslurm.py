import os
current_dir = os.path.dirname(os.path.abspath(__file__))
param_file = os.path.join(current_dir, 'params.csv')
results_file= os.path.join(current_dir,'results.csv')
slurms =[]


with open(param_file, 'r') as file:
    lines = file.readlines()


slurm_scripts=[] 

for idx, line in enumerate(lines):
    slurms.append(f'script{idx}.slurm')
    first_line = line.strip().split(',')
    job_name, partition,nodes, ntasks, mem, gpu, threads, nx, ny, nz, rt = first_line

    slurm_scripts.append( f"""#!/bin/bash
#SBATCH --job-name {job_name}        
#SBATCH --array 1              
#SBATCH --ntasks-per-node {ntasks}                        
#SBATCH --time 00:15:00             
#SBATCH --mem {mem}                        
#SBATCH --partition {partition}            
#SBATCH --nodes {nodes} 
#SBATCH --gpus {gpu}  
# Load packages
module load intel/20.0.4 hpcg

export OMP_PROC_BIND=TRUE
export OMP_PLACES=cores
export OMP_NUM_THREADS={threads}  
# Task {idx}           

RESULTS_CSV=$SLURM_SUBMIT_DIR/results.csv

if test -f $RESULTS_CSV; then
echo Using parameter file $RESULTS_CSV
else
echo Error $RESULTS_CSV not found
exit 1
fi



srun --mpi=pmi2 --partition  {partition} --gpu={gpu} --nodes={nodes} --ntasks={ntasks} --mem={mem} xhpcg {nx} {ny} {nz} {rt} 


if [ ! -f "$RESULTS_CSV" ]; then
        echo "GFLOP/s, Execution Time, Optimization Phase Time, Raw SpMV, Raw MG" > "$RESULTS_CSV"
fi

LOG_FILES=($SLURM_SUBMIT_DIR/HPCG-Benchmark_3.*.txt)

if [ ${{#LOG_FILES[@]}} -eq 0 ]; then
            echo "No log files found matching pattern: $SLURM_SUBMIT_DIR/HPCG-Benchmark_*.txt"
                exit 1
fi


for LOG_FILE in "${{LOG_FILES[@]}}"; do
        echo "$LOG_FILE"

        # Extract performance data from the benchmark log
        GFLOP=$(grep -oP 'GFLOP/s Summary::Raw Total=\K[\d\.]+' "$LOG_FILE")
        echo GFLOP got: $GFLOP
        EXEC_TIME=$(grep -oP 'Final Summary::Results are valid but execution time \(sec\) is=\K[\d\.]+' "$LOG_FILE")
        OPT_PHASE_TIME=$(grep -oP 'User Optimization Overheads::Optimization phase time \(sec\)=\K[\d\.]+' "$LOG_FILE")
        SPMV_TIME=$(grep -oP 'Benchmark Time Summary::SpMV=\K[\d\.]+' "$LOG_FILE")
        MG_TIME=$(grep -oP 'Benchmark Time Summary::MG=\K[\d\.]+' "$LOG_FILE")

        # Append the extracted data to results.csv
        echo "GFLOPS:$GFLOP, EXEC_Time:$EXEC_TIME, optPhaseTime:$OPT_PHASE_TIME, SPMVTime:$SPMV_TIME, MGTime:$MG_TIME" >> "$RESULTS_CSV"
        echo "Results for this run:"
        echo "GFLOP/s: $GFLOP"
        echo "Execution Time: $EXEC_TIME"
        echo "Optimization Phase Time: $OPT_PHASE_TIME"
        echo "Raw SpMV Time: $SPMV_TIME"
        echo "Raw MG Time: $MG_TIME"
        echo "Results written to $RESULTS_CSV"

done
# Delete them so we dont redo values
for LOG_FILE in "${LOG_FILES[@]}"; do
        if [ -f "$LOG_FILE" ]; then
                rm -f "$LOG_FILE"
        fi
done

    """)
for idx, file in enumerate(slurms):
    output = os.path.join(current_dir, file)
    with open(output, 'w') as f:
        f.write(slurm_scripts[idx])
    os.chmod(output, 0o755)
    os.system(f"sbatch {file}")


