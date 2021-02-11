% connection strength heatmaps % better to choose from testLearnFF 
function outputLearnFF(isuffix, osuffix, mix)
	if nargin < 3
		mix = true;
	end
	st = 2; %0 for temporal, 1 for spatial, 2 for both
	%iV1 = randi(768,1);
	rng(1390845)
	ns = 1;
	if ~isempty(isuffix)
	    isuffix = ['_', isuffix];
	end
	if ~isempty(osuffix)
	    osuffix = ['_', osuffix];
	end
	thres = 0.0
	%iV1 = 218 
	nstep = 1000
	dt = 1.0;
	nbins = 20;
	nit = 20;

	f_sLGN = ['sLGN', osuffix, '.bin']
	LGN_V1_id_fn = ['LGN_V1_idList', isuffix, '.bin']
	fLGN_vpos = ['LGN_vpos', isuffix, '.bin'];
	
	fid = fopen(fLGN_vpos, 'r');
	nLGN = fread(fid, 1, 'uint') % # ipsi-lateral LGN 
	nLGN_I = fread(fid, 1, 'uint') % # ipsi-lateral LGN 
	doubleOnOff = fread(fid, 1, 'int');
	fclose(fid);
	
	% read the constants first only 
	fid = fopen(f_sLGN, 'r');
	nt = fread(fid, 1, 'uint');
	nV1 = fread(fid, 1, 'uint');
	max_LGNperV1 = fread(fid, 1, 'uint')
	sRatio = fread(fid, 1, 'float')
	nLearnFF = fread(fid, 1, 'uint')
	gmaxLGN = fread(fid, nLearnFF, 'float')
	gmax0 = gmaxLGN(1)*sRatio; % TODO, separate E and I
	fclose(fid);

	% read connection id
	sid = fopen(LGN_V1_id_fn, 'r');
	LGN_V1_ID = zeros(max_LGNperV1, nV1);
	nLGN_V1 = zeros(nV1,1);
	fread(sid, 1, 'uint'); % nV1
	for i = 1:nV1
	    nLGN_V1(i) = fread(sid, 1, 'uint');
	    assert(nLGN_V1(i) <= max_LGNperV1);
	    if nLGN_V1(i) > 0
	        LGN_V1_ID(1:nLGN_V1(i),i) = fread(sid, nLGN_V1(i), 'uint')  + 1;
	    end
	end
	fclose(sid);

	if ~exist('V1_pick', 'var') 
		V1_pick = randi(768,[ns,1]);
	end
	disp(V1_pick); 
	for iq = 1:ns
	    iV1 = V1_pick(iq)
	    %disp(nLGN_V1(iV1));
	    %disp(LGN_V1_ID(1:nLGN_V1(iV1),iV1)');
	    
	    if st == 2 || st == 1
	        fid = fopen(fLGN_vpos, 'r');
	        fseek(fid, (8+2*nLGN)*4, 0);
	        LGN_type = fread(fid, nLGN, 'uint');
	        fclose(fid);
	        types = unique(LGN_type);
	        ntype = length(types)
	    
	        sLGN = zeros(nLGN, 3);
	        
	        fid = fopen(f_sLGN, 'r');
	        fseek(fid, 6*4, 0); % skip till time
	    
	        % skip times
	        %ht = round(nt/2);
	        %it = [0, ht-1, nt-1 - (ht+1)]
	        qt = int32(floor(linspace(1, nt, nit)));
	        it = diff([0, qt])-1;
	        for j = 1:nit
	            if it(j) > 0
	                fseek(fid, max_LGNperV1*nV1*int64(it(j))*4, 0); % skip till time
	            end
	            data = fread(fid, [max_LGNperV1, nV1], 'float');
	            sLGN(LGN_V1_ID(1:nLGN_V1(iV1),iV1),j) = data(1:nLGN_V1(iV1),iV1);
	        end
	        fclose(fid);
	        
			if doubleOnOff == 0
	        	f = figure('PaperPosition',[0, 0, nit, (2-mix)]);
				set(f, 'PaperUnit', 'inches');
				nLGN_1D = sqrt(double(nLGN))
	    	    sLGN = reshape(sLGN, [nLGN_1D, nLGN_1D, nit]);
				gmax = max(abs(sLGN(:)));
	    	    if mix
	    	        clims = [-1, 1];
	    	        for i = 1:nit
	    	            subplot(1,nit+1,i)
	    	            stmp = sLGN(:,:,i);
	    	            offPick = LGN_type == 5;
	    	            stmp(offPick) = -stmp(offPick);
	    	            stmp = stmp./gmax;
	    	            stmp(abs(stmp)<thres) = 0;
	    	            imagesc(stmp, clims);
	    	            colormap('jet');
	    	            daspect([1,1,1]);
						axis image
	    	            %set(gca,'YDir','normal')
	    	            title(['t', num2str(qt(i)/1000),'-n',num2str(sum(sum(sLGN(:,:,i)>thres))),'-p',num2str(gmax/gmax0*100,'%.1f'),'%'], 'FontSize', 6);
	    	            if i == nit
							ax = subplot(1, nit+1, nit+1);
	    	            	im = imagesc(stmp, clims);
							im.Visible = 0;
							ax.Visible = 0;
	    	                colorbar;
	    	            	colormap('jet');
	    	            end
	    	        end
	    	    else
	    	        clims = [0, 1];
	    	        for itype = 1:ntype
	    	            for i = 1:nit
	    	                subplot(ntype,nit+1,(itype-1)*(nit+1) + i)
	    	                stmp = sLGN(:,:,i);
	    	                stmp(LGN_type ~= types(itype)) = 0;
	    	                stmp = stmp./gmax;
	    	                stmp(stmp<thres) = 0;
	    	                imagesc(stmp, clims);
	    	            	daspect([1,1,1]);
							axis image
	    	                %set(gca,'YDir','normal')
	    	                if itype == 1
	    	            		title(['t', num2str(qt(i)/1000),'-n',num2str(sum(sum(sLGN(:,:,i)>thres))),'-p',num2str(gmax/gmax0*100,'%.1f'),'%'], 'FontSize', 6);
	    	                end
	    	                if i == 1
	    	                    ylabel(['type: ', num2str(types(itype))]);
	    	                end
	    	                if i == nit
								ax = subplot(1, nit+1, nit+1);
	    	            		im = imagesc(stmp, clims);
								im.Visible = 0;
								ax.Visible = 0;
	    	            		colormap('jet');
	    	                    colorbar;
	    	                end
	    	            end
	    	        end
	    	    end
			else
	        	f = figure('PaperPosition',[0, 0, nit, 2]);
				set(f, 'PaperUnit', 'inches');
				assert(doubleOnOff == 1);	
				nLGN_1D = sqrt(double(nLGN/2))
				sLGN = reshape(sLGN, [nLGN_1D, nLGN_1D*2, nit]);
				gmax = max(abs(sLGN(:)));
	    	    clims = [0, 1];
	    	    for itype = 1:ntype
	    	        for i = 1:nit
	    	            subplot(ntype,nit+1,(itype-1)*(nit+1) + i)
	    	            stmp = sLGN(:,itype:2:(nLGN_1D*2),i);
	    	            stmp = stmp./gmax;
	    	            stmp(stmp<thres) = 0;
	    	            imagesc(stmp, clims);
	    	        	daspect([1,1,1]);
						axis image
	    	            %set(gca,'YDir','normal')
	    	            if itype == 1
	    	        		title(['t', num2str(qt(i)/1000),'-n',num2str(sum(stmp>0)),'-p',num2str(gmax/gmax0*100,'%.1f'),'%'], 'FontSize', 6);
	    	            end
	    	            if i == 1
	    	                ylabel(['type: ', num2str(types(itype))]);
	    	            end
	    	            if i == nit
							ax = subplot(1, nit+1, nit+1);
	    	        		im = imagesc(stmp, clims);
							im.Visible = 0;
							ax.Visible = 0;
	    	        		colormap('jet');
	    	                colorbar;
	    	            end
	    	        end
	    	    end
			end
			set(f, 'OuterPosition', [.1, .1, nit+2, 4]);
			set(f, 'innerPosition', [.1, .1, nit+2, 4]);
			if mix && doubleOnOff ~= 1
	        	saveas(f, ['sLGN_V1-',num2str(iV1), osuffix, '-mix'], 'fig');
	        	saveas(f, ['sLGN_V1-',num2str(iV1), osuffix, '-mix','.png']);
			else
	        	saveas(f, ['sLGN_V1-',num2str(iV1), osuffix, '-sep'], 'fig');
	        	saveas(f, ['sLGN_V1-',num2str(iV1), osuffix, '-sep','.png']);
			end
	    end
	    if st == 2 || st == 0
	        if ~exist('nstep', 'var')
	            nstep = 100;
	        end
	        if nstep > nt
	            nstep = nt;
	        end
	        tstep = int64(round(nt/nstep))
	        it = 1:tstep:nt;
	        nstep = length(it)
	        tLGN = zeros(max_LGNperV1, nstep);
	        
	        fid = fopen(f_sLGN, 'r');
	        fseek(fid, 6*4, 0); % skip till time
	        
	        for j = 1:nstep
	            if j > 1
	                fseek(fid, max_LGNperV1*nV1*int64(tstep-1)*4, 0); % skip till time
	            end
	            data = fread(fid, [max_LGNperV1, nV1], 'float');
	            tLGN(:,j) = data(:,iV1);
	        end
	        fclose(fid);
	        
	        qt = int32(floor(linspace(1,nstep,nit)));
	        f = figure('PaperPosition',[.1 .1 8 6]);
	    	subplot(1,3,[1,2])
	        plot(it*dt, tLGN./gmax*100, '-');
	        ylabel('% of max strength');
	        xlabel('ms');
	        edges = linspace(0,100,nbins);
	        for i = 1:nit
	            subplot(nit,3,3*i)
	            histogram(tLGN(:,qt(i))./gmax*100, 'BinEdges', edges);
	        end
			set(f, 'OuterPosition', [.1, .1, 8, 6]);
			set(f, 'innerPosition', [.1, .1, 8, 6]);
	        saveas(f, ['tLGN_V1-',num2str(iV1), osuffix], 'fig');
	        saveas(f, ['tLGN_V1-',num2str(iV1), osuffix, '.png']);
	    end
	end
end
