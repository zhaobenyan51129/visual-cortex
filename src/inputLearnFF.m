% essential input files
% suffix: theme string $lgn in lFF.slurm
% seed: for randomize LGN connecction
% std_ecc: initial connections weights to be gaussian distributed if nonzero
% suffix0: theme string %lgn0 in lFF.slurm
% stage: retinal wave stages, takes 2 or 3
function inputLearnFF(inputFn, suffix, seed, std_ecc, suffix0, stage, res_fdr, setup_fdr, squareOrCircle, sInput, relay, binary_thres)

	res_fdr = [res_fdr,'/'] %resourceFolder in cfg
	setup_fdr = [setup_fdr,'/'] %inputFolder in cfg

	con_std = 0

	if std_ecc > 0
		normed = true
	else
		normed = false
	end
	
	if stage == 2
		u0 = 1.0; % stage 2 always single_value
		u1 = 1.0;
	else
		u0 = 1.0; % uniform range
		u1 = 1.0;
		%#u0 = 0.666667; % uniform range
		%#u1 = 1.333333;
	end

	%%%% HERE %%%%%%%%
	if stage == 5
		nother = 1; % set the number of temporal-variable learning parameters, such as rLTD 
		set_other = [[0.32, 0.85]]; % rLTD
	else
		nother = 0;
	end
	same = false; % set true if all the V1 neurons have the same LGN connections
	if stage == 2 || stage == 5
		pCon = 0.9 % initial sparsity
		nLGN_1D = 16 % sqrt of the total number of On/Off LGN cells
		radiusRatio = 1.0
	end
	if stage == 3
		if relay
			%pCon = 0.8 % initial sparsity
			pCon = 0.8 % initial sparsity
			nLGN_1D = 16 % sqrt of the total number of On/Off LGN cells
			radiusRatio = 0.5
		else
			pCon = 0.8
			nLGN_1D = 8
			radiusRatio = 1.0
		end
    end
	%%%%%%%%

	if ~isempty(suffix0)
	    suffix0 = ['-', suffix0];
	end
	if ~isempty(suffix)
	    suffix = ['-', suffix];
	end

	fLGN_V1_ID = [setup_fdr, 'LGN_V1_idList', suffix, '.bin'];
	fLGN_V1_s = [setup_fdr, 'LGN_V1_sList', suffix, '.bin'];
	fV1_RFprop = [setup_fdr, 'V1_RFprop', suffix, '.bin'];
	fLGN_switch = [setup_fdr, 'LGN_switch', suffix, '.bin'];

	fV1_vposFn = [res_fdr, 'V1_vpos', suffix0, '.bin'];
	fV1_allpos = [res_fdr, 'V1_allpos', suffix0, '.bin'];
	fV1_feature = [res_fdr, 'V1_feature', suffix0, '.bin'];
	fLGN_vpos = [res_fdr, 'LGN_vpos', suffix0, '.bin'];
	fLGN_surfaceID = [res_fdr, 'LGN_surfaceID', suffix0, '.bin'];
	
	%parvoMagno = 1 % parvo
	parvoMagno = 2 % magno 
	%parvoMagno = 3 % both, don't use, only for testing purpose
	
	rng(seed);
	initialConnectionStrength = 1.0; % dont change, use sRatioLGN in .cfg file
	eiStrength = 0.000;
	ieStrength = 0.000;
	nblock = 32;
    blockSize = 32;
	mE = 24;
	mI = 8;
	%nblock = 1;
    %blockSize = 1024;
	%mE = 768;
	%mI = 256;
	nV1 = nblock*blockSize;
	doubleOnOff = 1;
	frameVisV1output = false; % if need framed V1 output, write visual pos to fV1_allpos



	fid = fopen([res_fdr, inputFn, '.cfg'], 'r');
	nStage = fread(fid, 1, 'uint')
    nOri = fread(fid, nStage, 'uint')
	nRep = fread(fid, nStage, 'uint')
	frameRate = fread(fid, 1, 'double')
	framesPerStatus = fread(fid, nStage, 'uint')
	framesToFinish = fread(fid, nStage, 'uint')
	max_ecc = fread(fid, 1, 'double')
	fclose(fid);

    if stage == 2 || stage == 3
		assert(nStage == 1);
	    %%%%% HERE %%%%%%%%
	    if stage == 2
	    	peakRate = 0.5; % active cell percentage during wave
	    	% corresponds to the parameters set in ext_input.py
	    end
	    if stage == 3
	    	peakRate = 1.0;
	    	absentRate = 1.0; % active cell percentage when being "absent"/not dominating
	    end
	    %%%%%%%%%%%%%
	    nStatus = nOri*nRep;
	    status = zeros(6,nStatus);
	    statusFrame = zeros(nStatus,1);

	    for i=1:nOri
	    	for j = 1:nRep
	    		statusFrame((i-1)*nRep + j) = framesPerStatus;
	    	end
	    	statusFrame(i*nRep) = statusFrame(i*nRep) + framesToFinish;
	    end
	    
	    statusFrame'
	    sum(statusFrame)
	    switch stage 
	    	case 2
	    		status(5,:) = peakRate;
	    		status(6,:) = peakRate;
	    	case 3
	    		%rands = rand(1,nStatus);
	    		%absentSeq = rands > 0;
                absentSeq = 3:3:nStatus;
	    		status(5,:) = peakRate;
	    		status(5,absentSeq) = absentRate;
	    		status(6,:) = 1.0;
	    	otherwise
	    		warning('unexpected stage')
	    end
	    reverse = zeros(nStatus,1);
    else
		assert(nStage == 2);
	    %%%%% HERE %%%%%%%%
	    assert(stage == 5);
	    peakRate = [0.5, 1.0]; % active cell percentage during wave
	    % corresponds to the parameters set in ext_input.py
	    absentRate = 1.0; % active cell percentage when being "absent"/not dominating
	    nStatus = sum(nOri.*nRep)
	    status = zeros(6,nStatus);
	    statusFrame = zeros(nStatus,1);
        others = zeros(nStatus,nother);
        iStatus = 0;
        for k = 1:length(nOri)
            for i=1:nother
                others(iStatus+1:iStatus+nOri(k)*nRep(k),i) = set_other(i, k);
            end
            iStatus = iStatus + nOri(k)*nRep(k);
        end
        others
	    %%%%%%%%%%%%%
        iFrame = 0;
        for k=1:length(nOri)
            for i=1:nOri(k)
	        	for j = 1:nRep(k)
                    jFrame = iFrame + (i-1)*nRep(k) + j;
	        		statusFrame(jFrame) = framesPerStatus(k);
                    if k == 2 && mod(j,3) == 0
                        status(5,jFrame) = absentRate;
                    else
	                    status(5,jFrame) = peakRate(k);
                    end
	    	        status(6,jFrame) = peakRate(k);
	        	end
	        	statusFrame(iFrame + i*nRep(k)) = statusFrame(iFrame + i*nRep(k)) + framesToFinish(k);
	        end
            iFrame = iFrame + nOri(k) * nRep(k);
        end
	    statusFrame'
	    sum(statusFrame)
	    reverse = zeros(nStatus,1);
    end

	nLGN = nLGN_1D*nLGN_1D;
	if doubleOnOff
	    nLGN = nLGN * 2;
	end
	
	fid = fopen(fLGN_surfaceID, 'w'); % format follows patch.cu, search for the same variable name
	if doubleOnOff
	    [LGN_idx, LGN_idy] = meshgrid(1:nLGN_1D*2, 1:nLGN_1D); % meshgrid gives coordinates of LGN on the surface memory
	else
	    [LGN_idx, LGN_idy] = meshgrid(1:nLGN_1D, 1:nLGN_1D); % meshgrid gives coordinates of LGN on the surface memory
	end
	% tranform the coords into row-first order
	LGN_idx = LGN_idx'-1; % index start with 0 in c/c++
	LGN_idy = LGN_idy'-1;
	if doubleOnOff 
	    fwrite(fid, 2*nLGN_1D-1, 'uint'); % width - 1, legacy problem, will add 1 after read
	    fwrite(fid, nLGN_1D-1, 'uint'); % height - 1
	else
	    fwrite(fid, nLGN_1D-1, 'uint'); % width - 1, legacy problem, will add 1 after read
	    fwrite(fid, nLGN_1D-1, 'uint'); % height - 1
	end
	assert(prod(size(LGN_idx)) == nLGN);
	fwrite(fid, LGN_idx(:), 'int');
	fwrite(fid, LGN_idy(:), 'int');
	fclose(fid);

	if doubleOnOff
		idx = LGN_idx;
		idx = ceil((idx+1)/2)-1;
	    LGN_x = (idx(:)-nLGN_1D/2+0.5)./nLGN_1D.*max_ecc./0.5;
	else
	    LGN_x = (LGN_idx(:)-nLGN_1D/2+0.5)./nLGN_1D.*max_ecc./0.5;
	end
	LGN_y = (LGN_idy(:)-nLGN_1D/2+0.5)./nLGN_1D.*max_ecc./0.5;
	LGN_vpos0 = [LGN_x(1:2:nLGN), LGN_y(1:2:nLGN)];

	%for i=1:nLGN_1D
	%	for j=1:nLGN_1D
	%		index = (i-1)*nLGN_1D + j;
	%		fprintf(['(', num2str(LGN_vpos0(index,1),'%1.1f'), ', ', num2str(LGN_vpos0(index,2),'%1.1f'),')']);
	%		if j==nLGN_1D
	%			fprintf('\n');
	%		else
	%			fprintf(', ');
	%		end
	%	end
	%end

    if squareOrCircle
		nLGN_square = sum(max(abs(LGN_vpos0), [], 2) <= max_ecc*radiusRatio)
	    nLGNperV1 = round(nLGN_square*2*pCon);
    else
	    nLGN_circ = sum(sum(LGN_vpos0.*LGN_vpos0,2) <= max_ecc*max_ecc*radiusRatio*radiusRatio)
	    nLGNperV1 = round(nLGN_circ*2*pCon);
    end
	if mod(nLGNperV1,2) == 1
		nLGNperV1 = nLGNperV1 + 1;
	end
	nLGNperV1
	% number of E and I connecitons based on LGN connections
	nI = int32(min(nLGNperV1/4, mI));
	nE = int32(min(nLGNperV1, mE));


	fid = fopen(fLGN_V1_ID, 'w'); % format follows read_listOfList in util/util.h
	fwrite(fid, nV1, 'uint');
	id = zeros(nLGNperV1,nV1);
	for i = 1:nV1
	    fwrite(fid, nLGNperV1, 'uint');
		if doubleOnOff 
			if i == 1 || ~same
				ids_on = randq(nLGN_1D*nLGN_1D, nLGNperV1/2, LGN_vpos0, max_ecc*radiusRatio, con_std, squareOrCircle); % index start from 0
			end
			idi	= zeros(nLGNperV1,1);
			current_id = 1;
			for j = 1:nLGN_1D
				idj = ids_on(ids_on >= nLGN_1D*(j-1) & ids_on < nLGN_1D*j);
				idi(current_id:current_id+length(idj)-1) = idj*2;
				current_id = current_id+length(idj);
			end
			if i == 1 || ~same
				ids_off = randq(nLGN_1D*nLGN_1D, nLGNperV1/2, LGN_vpos0, max_ecc*radiusRatio, con_std, squareOrCircle); % index start from 0
			end
			for j = 1:nLGN_1D
				idj = ids_off(ids_off >= nLGN_1D*(j-1) & ids_off < nLGN_1D*j);
				idi(current_id:current_id+length(idj)-1) = idj*2+1;
				current_id = current_id+length(idj);
			end
			id(:,i) = idi;
		else
			id(:,i) = randperm(nLGN, nLGNperV1)-1; % index start from 0
		end
	    fwrite(fid, id(:,i), 'uint');
	end
	fclose(fid);
	
	fid = fopen(fV1_allpos, 'w'); % format follows patch.cu, search for the same variable name
	% not necessarily a ring
	loop = linspace(0,pi,nV1+1);
	polar = loop(1:nV1)';
	ecc = zeros(nV1,1);
	V1_pos = [cos(polar).*ecc, sin(polar).*ecc];
	fwrite(fid, nblock, 'uint');
	fwrite(fid, blockSize, 'uint');
	fwrite(fid, 2, 'uint'); %posDim, don't change
	%
	fwrite(fid, -1, 'double'); % x0: min(x) = cos(pi);
	fwrite(fid, 2, 'double'); % xspan: max(x) - min(x) = cos(0)-cos(pi);
	fwrite(fid, -1, 'double'); % y0..
	fwrite(fid, 2, 'double'); % yspan..
	fwrite(fid, V1_pos, 'double'); % write V1_pos
	fwrite(fid, -1, 'double'); % vx0: min(vx)
	fwrite(fid, 2, 'double'); % vxspan: max(vx)-min(vx)
	fwrite(fid, -1, 'double'); % vy..
	fwrite(fid, 2, 'double'); % vyspan..
	fwrite(fid, V1_pos, 'double');  %supposedly vpos
	fclose(fid);
	
	
	fid = fopen(fV1_vposFn, 'w');
	fwrite(fid, nV1, 'uint');
	fwrite(fid, ecc, 'double');
	fwrite(fid, polar, 'double');
	fclose(fid);
	
	fid = fopen(fLGN_switch, 'w');
	fwrite(fid, nStatus, 'uint'); 
	fwrite(fid, status, 'float'); % activated percentage
	fwrite(fid, statusFrame, 'uint'); % duration
	fwrite(fid, reverse, 'int');
	fwrite(fid, nother, 'uint'); 
    if stage == 5
        fwrite(fid, others, 'float');
    end
	fclose(fid);
	
	fid = fopen(fLGN_vpos, 'w'); % format follows patch.cu, search for the same variable name
	fwrite(fid, nLGN, 'uint'); % # ipsi-lateral LGN 
	fwrite(fid, 0, 'uint'); % contra-lateral LGN all from one eye
	interDis = max_ecc/(nLGN_1D-1)
	fwrite(fid, max_ecc, 'float');
	% using uniform_retina, thus normalized to the central vision of a single eye
	fwrite(fid, -max_ecc, 'float'); % x0
	fwrite(fid, 2*max_ecc, 'float'); % xspan
	fwrite(fid, -max_ecc, 'float'); % y0
	fwrite(fid, 2*max_ecc, 'float'); % yspan
	
	disp([min(LGN_x), max(LGN_x)]);
	disp([min(LGN_y), max(LGN_y)]);
	fwrite(fid, LGN_x, 'float');
	fwrite(fid, LGN_y, 'float');
	
	% see preprocess/RFtype.h
	if parvoMagno == 1
	    LGN_type = randi(4,[nLGN,1])-1; % 0-3: L-on, L-off, M-on, M-off
	end
	if parvoMagno == 2
	    %LGN_type = 3+randi(2,[nLGN,1]); % 4:on center or 5: off center
	    %LGN_type = 4+zeros(nLGN,1); % 4:on center or 5: off center
	    if doubleOnOff
	        LGN_type = zeros(size(LGN_idx));
	        LGN_type(1:2:size(LGN_idx,1),:) = 4;
	        LGN_type(2:2:size(LGN_idx,1),:) = 5;
	    else
	        type0 = zeros(nLGN_1D, 1);
	        type0(1:2:nLGN_1D) = 4;
	        type0(2:2:nLGN_1D) = 5;
	        type1 = zeros(nLGN_1D, 1);
	        type1(1:2:nLGN_1D) = 5;
	        type1(2:2:nLGN_1D) = 4;
	        for i = 1:nLGN_1D
	            if mod(i,2) == 1
	                %LGN_type(:,i) = circshift(type, i);
	                LGN_type(:,i) = type0;
	            else
	                LGN_type(:,i) = type1;
	            end
	        end
	    end
	end
	if parvoMagno == 3
	    LGN_type = zeros(nLGN,1);
	    nParvo = randi(nLGN, 1)
	    nMagno = nLGN - nParvo
	    LGN_type(1:nParvo) = randi(4,[nParvo,1])-1; %
	    LGN_type((nParvo+1):nLGN) = 3 + randi(2,[nMagno,1]); %
	end

	%picked = zeros(2*nLGN_1D, nLGN_1D);
	%picked(id(:,1)) = 1;
	%for i=1:nLGN_1D
	%	for j=1:nLGN_1D*2
	%		index = (i-1)*2*nLGN_1D + j;
	%		if picked(index)
	%			fprintf([num2str(LGN_type(index),'%1.0f'), '(x)']);
	%		else
	%			fprintf([num2str(LGN_type(index),'%1.0f'), '   ']);
	%		end
	%		if j==nLGN_1D*2
	%			fprintf('\n');
	%		else
	%			fprintf(', ');
	%		end
	%	end
	%end
	
	fwrite(fid, LGN_type, 'uint');
	% in polar form
	LGN_ecc = sqrt(LGN_x.*LGN_x + LGN_y.*LGN_y); %degree
	LGN_polar = atan2(LGN_y, LGN_x); % [-pi, pi]
	fwrite(fid, LGN_polar, 'float');
	fwrite(fid, LGN_ecc, 'float');
	
	fwrite(fid, doubleOnOff, 'int'); % be read by outputLearnFF not used in patch.cu
	fclose(fid);
	
	if ~isempty(sInput)
		fid = fopen(sInput, 'r');
        nt = fread(fid, 1, 'uint');
		sampleInterval = fread(fid, 1, 'uint');
		nst = floor(nt/sampleInterval);
		dt_ = fread(fid, 1, 'float')
        nV1_ = fread(fid, 1, 'uint');
        assert(nV1_ == nV1);
        max_LGNperV1 = fread(fid, 1, 'uint');
		if max_LGNperV1 <= nLGNperV1
			disp(max_LGNperV1)
			disp(nLGNperV1)
			assert(nLGNperV1 == max_LGNperV1);	
		end
        fseek(fid, 3*4, 0); % skip till time
        fseek(fid, max_LGNperV1*nV1*int64(nst-1)*4, 0); % skip till time
        sLGN = fread(fid, [nV1_, max_LGNperV1], 'float')'; % transposed
        fclose(fid);
	else
		if normed
		    sLGN = zeros(nLGNperV1, nV1);
		    for i = 1:nV1
		        sLGN(:,i) = exp(-(LGN_ecc(id(:,i)+1) ./ (std_ecc)).^2);
		    end
		else
		    sLGN = (u0 + rand(nLGNperV1,nV1)*(u1-u0));
		end
		for i = 1:nV1
			ss = sLGN(:,i);
			if binary_thres > 0
				pick = (ss-min(ss))./(max(ss)-min(ss)) > binary_thres;
				ss(pick) = u1;
				ss(~pick) = u0;
			end	
			sLGN(:,i) = ss./sum(ss)*initialConnectionStrength*nLGNperV1;
		end
	end
	disp('min max LGN');
	disp(max(sLGN(:)));
	disp(min(sLGN(:)));
	fid = fopen(fLGN_V1_s, 'w'); % format follows function read_LGN in patch.h
	fwrite(fid, nV1, 'uint');
	fwrite(fid, nLGNperV1, 'uint');
	for i = 1:nV1
	    fwrite(fid, nLGNperV1, 'uint');
	    fwrite(fid, sLGN(1:nLGNperV1, i), 'float');
		if i == 1
			f = figure('PaperPosition',[0, 0, 3, 7]);
			set(f, 'PaperUnit', 'inches');
			s = zeros(nLGN,1);
	        s(id(1:nLGNperV1,i)+1) = sLGN(1:nLGNperV1,i);
	    	s = reshape(s, [nLGN_1D*2, nLGN_1D]);
	    	clims = [0, 1];
			for itype = 1:2
				stmp0 = s(itype:2:(nLGN_1D*2),:);
				local_max = max(abs(stmp0(:)));
				stmp = stmp0./local_max;
				subplot(2,1,itype)
	    		imagesc([1 nLGN_1D], [1,nLGN_1D],stmp', clims);
	    		daspect([1,1,1]);
	    		set(gca,'YDir','reverse')
				set(gca,'YTickLabel', []);
				set(gca,'XTickLabel', []);
	    	    colormap('gray');
			end
	        saveas(f, [setup_fdr,'sLGN_V1-init-',num2str(i), suffix, '-sep.png']);
		end
	end
	fclose(fid);
	
	% by setting useNewLGN to false, populate LGN.bin follow the format in patch.cu
	
	% not in use, only self block is included
	fNeighborBlock = [setup_fdr, 'neighborBlock', suffix, '.bin'];
	% not in use, may use if cortical inhibition is needed
	fV1_delayMat = [setup_fdr, 'V1_delayMat', suffix, '.bin']; % zeros
	fV1_conMat = [setup_fdr, 'V1_conMat', suffix, '.bin']; % zeros
	fV1_vec = [setup_fdr, 'V1_vec', suffix, '.bin']; % zeros
	
	fV1_gapMat = [setup_fdr, 'V1_gapMat', suffix, '.bin']; % zeros
	fV1_gapVec = [setup_fdr, 'V1_gapVec', suffix, '.bin']; % zeros
	
	nearNeighborBlock = nblock;
	cid = fopen(fV1_conMat, 'w');
	did = fopen(fV1_delayMat, 'w');
	gid = fopen(fV1_gapMat, 'w');
	fwrite(cid, nearNeighborBlock , 'uint');
	fwrite(gid, nearNeighborBlock , 'uint');
	fwrite(did, nearNeighborBlock , 'uint');
    for iblock = 1:nblock
	    conMat = zeros(blockSize,blockSize,nearNeighborBlock);
	    delayMat = zeros(blockSize,blockSize,nearNeighborBlock);
        for iNeighbor = 1:nearNeighborBlock
	                   %(post, pre)
	        conIE = zeros(mI,mE);
	        for i = 1:mI
	            ied = randperm(mE, nE);
	            conIE(i,ied) = ieStrength;
	        end
	        conEI = zeros(mE,mI);
	        for i = 1:mE
	            eid = randperm(mI, nI);
	            conEI(i,eid) = eiStrength;
	        end
	        conMat(1:mE,(mE+1):blockSize,iNeighbor) = conEI;
	        conMat((mE+1):blockSize,1:mE,iNeighbor) = conIE;
	        % not necessary to calc distance
	        for i = 1:blockSize
	            for j = 1:blockSize
                    id_i = (iblock-1)*blockSize + i;
                    id_j = (iNeighbor-1)*blockSize + j;
	                delayMat(i,j) = norm(V1_pos(id_i,:) - V1_pos(id_j,:), 2);
	                delayMat(j,i) = delayMat(i,j);
	            end
	        end
        end
	    fwrite(cid, conMat , 'float');
	    gapMat = zeros(mI,mI,nearNeighborBlock);
	    fwrite(gid, gapMat , 'float');
	    fwrite(did, delayMat , 'float');
    end
	fclose(cid);
	fclose(gid);
	fclose(did);
	
	fid = fopen(fNeighborBlock, 'w');
	nNearNeighborBlock = zeros(nblock,1)+nearNeighborBlock;
	nNeighborBlock = zeros(nblock,1)+nearNeighborBlock;
	fwrite(fid, nNearNeighborBlock, 'uint'); % number of near neighbor
	fwrite(fid, nNeighborBlock, 'uint'); % number of all (near + far[vec]) neighbor
	nBlockId = zeros(nearNeighborBlock, nblock);
    for i = 1:nblock
        nBlockId(:,i) = 0:(nearNeighborBlock-1);
    end
	fwrite(fid, nBlockId, 'uint'); % id of neighbor
	fclose(fid);
	
	
	fid = fopen(fV1_vec, 'w');
    connectlongRange = 0
	fwrite(fid, connectLongRange, 'uint');
	nVec = zeros(nV1,1);
	fwrite(fid, nVec, 'uint');
	fclose(fid);
	
	fid = fopen(fV1_gapVec, 'w');
	nGapVec = zeros(mI*nblock,1);
	fwrite(fid, nGapVec, 'uint');
	fclose(fid);
	
	fConnectome = [setup_fdr, 'connectome_cfg', suffix, '.bin'];
	fid = fopen(fConnectome, 'w');
	fwrite(fid,2,'uint');
	fwrite(fid,1,'uint');
	fwrite(fid,[mE,mI+mE],'uint');
	%fwrite(fid,[5,5,5,5],'float'); % synapse per cortical connection in float!
	%fwrite(fid,[10,10],'float'); % synapse per FF connection in float!
	fclose(fid);
	
	fConStats = [setup_fdr, 'conStats', suffix, '.bin'];
	fid = fopen(fConStats, 'w');
	fwrite(fid,2,'uint');
	fwrite(fid,nV1,'uint');
	fwrite(fid,ones(nV1,1),'float'); %excRatio
	fwrite(fid,zeros(nV1,2),'uint'); %preN
	fwrite(fid,zeros(nV1,2),'uint'); %preAvail
	fwrite(fid,zeros(nV1,2),'float'); %preNS
	fwrite(fid,1,'uint'); %nTypeI
	fwrite(fid,256,'uint'); %mI
	fwrite(fid,zeros(256,1),'uint'); %nGap
	fwrite(fid,zeros(256,1),'float'); %GapS
	fclose(fid);
	
	fid = fopen(fV1_feature, 'w');
	nFeature = 2;
	fwrite(fid,nFeature,'uint');
	fwrite(fid,rand(nV1,nFeature),'float');
	fclose(fid);
	
	fid = fopen(fV1_RFprop, 'w');
	fwrite(fid, nV1, 'uint');
	fwrite(fid, V1_pos, 'float');
	fwrite(fid, zeros(nV1,1)+max_ecc, 'float');
	fwrite(fid, zeros(nV1,1), 'float');
	fwrite(fid, zeros(nV1,1), 'float');
	fwrite(fid, ones(nV1,1), 'float');
	fclose(fid);
end
function ids = randq(m,n,pos,r0,stdev, squareOrCircle)
	r2 = sum(pos.*pos,2);
	ndiscard = m-n;
	id = 1:m;
    if squareOrCircle
	    ndm = sum(max(abs(pos),[],2)>r0);
		pick = max(abs(pos),[],2)<=r0;
    else
	    ndm = sum(r2>r0*r0);
		pick = r2<=r0*r0;
    end
	id_left = id(pick);
	if stdev <= 0
		ids = id_left(randperm(m-ndm,n));
	else
		 rands = rand(m-ndm, 1);
		[~, id0] = mink(rands ./ exp(-r2(pick)/(stdev*stdev)),n);
		ids = id_left(id0);
	end
	ids = ids-1; % index start from 0
	assert(all(ids >= 0));
end
