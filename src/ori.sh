#!/bin/bash
source /home/zhaobenyan/miniconda3/etc/profile.d/conda.sh
eval "$(conda shell.bash hook)"
conda activate neuro
set -e

cd ${data_fdr} #进入$HOME/model/patchfast
pwd
patch_cfg=${fig_fdr}/${trial_suffix}-ori_${ori}.cfg
#patch_cfg=$HOME/dataset/merge_test/repeat_test-ori_1.cfg  ori:in $( seq 1 $nOri )

echo $ori

BIN_DIR=${fdr0}/bin
date
if [ "$plotOnly" = False ]; then
	echo ${BIN_DIR}/${patch} -c ${patch_cfg}
	${patch} -c ${patch_cfg}
	date
fi

usePrefData=False
collectMeanDataOnly=False

if [ "$fitTC" = True ]; then
	OPstatus=0
else
	OPstatus=1
fi


plot_fig(){
	pid=""
	echo python ${fig_fdr}/plotLGN_response_${trial_suffix}.py ${trial_suffix}_${ori} ${LGN_V1_suffix} ${data_fdr} ${fig_fdr}
	python ${fig_fdr}/plotLGN_response_${trial_suffix}.py ${trial_suffix}_${ori} ${LGN_V1_suffix} ${data_fdr} ${fig_fdr} &
	pid+="${!} "

	echo python ${fig_fdr}/plotV1_response_${trial_suffix}.py ${trial_suffix} ${res_suffix} ${LGN_V1_suffix} ${V1_connectome_suffix} ${res_fdr} ${setup_fdr} ${data_fdr} ${fig_fdr} ${TF} ${ori} ${nOri} ${readNewSpike} ${usePrefData} ${collectMeanDataOnly} ${OPstatus}
	python ${fig_fdr}/plotV1_response_${trial_suffix}.py ${trial_suffix} ${res_suffix} ${LGN_V1_suffix} ${V1_connectome_suffix} ${res_fdr} ${setup_fdr} ${data_fdr} ${fig_fdr} ${TF} ${ori} ${nOri} ${readNewSpike} ${usePrefData} ${collectMeanDataOnly} ${OPstatus} &
	pid+="${!} "

	echo python ${fig_fdr}/plotFrameOutput_${trial_suffix}.py ${trial_suffix}_${ori} ${res_suffix} ${LGN_V1_suffix} ${V1_connectome_suffix} ${res_fdr} ${setup_fdr} ${data_fdr} ${fig_fdr}
	python ${fig_fdr}/plotFrameOutput_${trial_suffix}.py ${trial_suffix}_${ori} ${res_suffix} ${LGN_V1_suffix} ${V1_connectome_suffix} ${res_fdr} ${setup_fdr} ${data_fdr} ${fig_fdr}
	pid+="${!} "

	if [ "${plotTC}" = True ]; then
		echo python ${fig_fdr}/getTuningCurve_${trial_suffix}.py ${trial_suffix} ${res_suffix} ${LGN_V1_suffix} ${V1_connectome_suffix} ${res_fdr} ${setup_fdr} ${data_fdr} ${fig_fdr} ${nOri} ${fitTC} ${fitDataReady}
		python ${fig_fdr}/getTuningCurve_${trial_suffix}.py ${trial_suffix} ${res_suffix} ${LGN_V1_suffix} ${V1_connectome_suffix} ${res_fdr} ${setup_fdr} ${data_fdr} ${fig_fdr} ${nOri} ${fitTC} ${fitDataReady} &
		pid+="${!} "
	fi

	if [ "${singleOri}" = True ]; then
		if [ "${generate_V1_connection}" = True ]; then
			echo python ${fig_fdr}/connections_${V1_connectome_suffix}.py ${trial_suffix}_${ori} ${res_suffix} ${LGN_V1_suffix} ${V1_connectome_suffix} ${res_fdr} ${setup_fdr} ${data_fdr} ${fig_fdr}
			python ${fig_fdr}/connections_${V1_connectome_suffix}.py ${trial_suffix}_${ori} ${res_suffix} ${LGN_V1_suffix} ${V1_connectome_suffix} ${res_fdr} ${setup_fdr} ${data_fdr} ${fig_fdr}
			pid+="$(echo $!) "
		fi
	fi
	wait $pid
}

if [ "$plotdw" = True ]; then
	plot_fig
fi

date
conda activate base