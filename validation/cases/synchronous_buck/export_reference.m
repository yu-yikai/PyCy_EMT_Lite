function export_reference(repositoryRoot,runDirectory,stage,protocolFile,protocolHash)
% One original 10 ms run. The parent freezes the protocol before launching.
assert(startsWith(canonical(runDirectory),[canonical(fullfile(repositoryRoot,'local_reference','b2_protocol_research')) filesep]));
assert(isfolder(runDirectory) && ~isfolder(fullfile(runDirectory,'inputs')));
assert(strcmp(sha256File(protocolFile),protocolHash),'Frozen protocol changed.');
assert(any(strcmp(stage,{'baseline','refined'})));
modelName='SynchronousBuckConverter';
expectedModelHash='ea8344f62e2a691456363f0391389cd1675bfe246bd71dc8f15a3b838ca6ab42';
source=fullfile(repositoryRoot,'local_reference','synchronous_buck','simulink',[modelName '.slx']);
assert(strcmp(sha256File(source),expectedModelHash) && ~bdIsLoaded(modelName));
inputDirectory=fullfile(runDirectory,'inputs');mkdir(inputDirectory);
copyfile(source,fullfile(inputDirectory,[modelName '.slx']));
copyfile([mfilename('fullpath') '.m'],fullfile(inputDirectory,'export_reference.m'));
protocolDirectory=fullfile(repositoryRoot,'validation','cases','synchronous_buck');
protocolSnapshots=struct('file',{},'sha256_raw',{},'sha256_lf',{});
for name={'acceptance_plan.md','manifest.json','parameters.json'}
    protocolSource=fullfile(protocolDirectory,name{1});
    copyfile(protocolSource,fullfile(inputDirectory,name{1}));
    protocolSnapshots(end+1)=struct('file',name{1},'sha256_raw',sha256File(protocolSource), ...
        'sha256_lf',sha256LFFile(protocolSource)); %#ok<AGROW>
end
assert(strcmp(canonical(protocolFile),canonical(fullfile(protocolDirectory,'acceptance_plan.md'))));
parameters=jsondecode(fileread(fullfile(inputDirectory,'parameters.json')));
settings=parameters.reference_solver;selected=settings.(stage);
assert(strcmp(settings.solver,'ode23tb') && strcmp(settings.auto_scale_abs_tol,'off'));
assert(strcmp(parameters.reference_model_sha256,expectedModelHash) && parameters.stop_second==0.01);
previousPath=path;pathCleanup=onCleanup(@() path(previousPath)); %#ok<NASGU>
previousConfig=Simulink.fileGenControl('getConfig');
fileGenCleanup=onCleanup(@() Simulink.fileGenControl('setConfig','config',previousConfig)); %#ok<NASGU>
Simulink.fileGenControl('set','CacheFolder',fullfile(runDirectory,'cache'), ...
    'CodeGenFolder',fullfile(runDirectory,'codegen'),'createDir',true);
addpath(inputDirectory);
assert(strcmp(canonical(which([modelName '.slx'])),canonical(fullfile(inputDirectory,[modelName '.slx']))));
% Opening resolves original SIDs and reads config; only sim(in) drives execution.
open_system(fullfile(inputDirectory,[modelName '.slx']));
modelCleanup=onCleanup(@() closeOwned(modelName)); %#ok<NASGU>
assert(strcmp(get_param(modelName,'Dirty'),'off'));
original=modelConfiguration(modelName);
blockTolerances=struct('sid',{},'path',{},'absolute_tolerance',{});
for sid=[81,84]
    block=Simulink.ID.getFullName(sprintf('%s:%d',modelName,sid));
    try
        tolerance=get_param(block,'AbsTol');
    catch err
        tolerance=struct('unavailable',true,'identifier',err.identifier,'message',err.message);
    end
    blockTolerances(end+1)=struct('sid',sid,'path',block,'absolute_tolerance',tolerance); %#ok<AGROW>
end
scope25=Simulink.ID.getFullName([modelName ':25']);
scope123=Simulink.ID.getFullName([modelName ':123']);
scopeSettings=struct('scope25',scope25,'scope123',scope123, ...
    'scope25_DataLogging',get_param(scope25,'DataLogging'), ...
    'scope25_DataLoggingSaveFormat',get_param(scope25,'DataLoggingSaveFormat'), ...
    'scope123_DataLogging',get_param(scope123,'DataLogging'));
scopeInventory=struct('sid',{},'path',{},'parameters',{});
for sid=[25,123,125]
    block=Simulink.ID.getFullName(sprintf('%s:%d',modelName,sid));values=struct;
    for name={'DataLogging','DataLoggingSaveFormat','DataLoggingVariableName', ...
            'DataLoggingLimitDataPoints','DataLoggingMaxPoints','DataLoggingDecimateData','DataLoggingDecimation'}
        try
            values.(name{1})=get_param(block,name{1});
        catch err
            values.(name{1})=struct('unavailable',true,'identifier',err.identifier,'message',err.message);
        end
    end
    scopeInventory(end+1)=struct('sid',sid,'path',block,'parameters',values); %#ok<AGROW>
end
in=Simulink.SimulationInput(modelName);
in=in.setModelParameter('Solver','ode23tb','SolverType','Variable-step', ...
    'StartTime','0','StopTime',sprintf('%.17g',parameters.stop_second), ...
    'MaxStep',sprintf('%.17g',selected.max_step_s),'RelTol',sprintf('%.17g',selected.relative_tolerance), ...
    'AbsTol',sprintf('%.17g',selected.absolute_tolerance),'AutoScaleAbsTol','off', ...
    'ReturnWorkspaceOutputs','on','SaveTime','on','TimeSaveName','tout', ...
    'SaveState','on','StateSaveName','xout','SaveFormat','Dataset', ...
    'Decimation','1','LimitDataPoints','off');
in=in.setBlockParameter(scope25,'DataLogging','on');
in=in.setBlockParameter(scope25,'DataLoggingSaveFormat','Dataset');
in=in.setBlockParameter(scope123,'DataLogging','on');
for k=1:numel(scopeInventory)
    in=in.setBlockParameter(scopeInventory(k).path,'DataLoggingLimitDataPoints','off', ...
        'DataLoggingDecimation','1');
end
before=struct('purpose','Original Buck full-window reference refinement; no candidate', ...
    'stage',stage,'protocol_source',protocolFile,'protocol_sha256',protocolHash, ...
    'protocol_snapshots',protocolSnapshots, ...
    'model_sha256',expectedModelHash,'matlab_version',version, ...
    'original_model_config',original,'requested_solver_settings',selected, ...
    'original_controller_block_tolerances',blockTolerances, ...
    'simulation_input_model_parameters',in.ModelParameters, ...
    'simulation_input_block_parameters',in.BlockParameters,'original_scope_settings',scopeSettings, ...
    'original_scope_inventory',scopeInventory, ...
    'inputs',fileHashes(inputDirectory));
writeJSON(fullfile(runDirectory,'attempt.json'),before);
save(fullfile(runDirectory,'simulation_input.mat'),'in','-v7.3');
timer=tic;out=sim(in);elapsedSeconds=toc(timer);
% Always preserve the complete native result before any assertion/extraction.
save(fullfile(runDirectory,'simulink_output.mat'),'in','out','-v7.3');
metadata=struct('stage',stage,'elapsed_seconds',elapsedSeconds, ...
    'outputs',{who(out)},'actual_solver',out.SimulationMetadata.ModelInfo.SolverInfo, ...
    'execution_info',out.SimulationMetadata.ExecutionInfo,'timing_info',out.SimulationMetadata.TimingInfo, ...
    'stored_config_after_sim',modelConfiguration(modelName), ...
    'source_model_sha256',sha256File(source), ...
    'copy_model_sha256',sha256File(fullfile(inputDirectory,[modelName '.slx'])), ...
    'model_dirty_after_sim',get_param(modelName,'Dirty'), ...
    'raw_mat_sha256',sha256File(fullfile(runDirectory,'simulink_output.mat')));
writeJSON(fullfile(runDirectory,'after_simulation.json'),metadata);
assert(strcmp(metadata.execution_info.StopEvent,'ReachedStopTime'));
assert(isempty(metadata.execution_info.ErrorDiagnostic));
assert(strcmp(metadata.actual_solver.Solver,'ode23tb'));
assert(abs(metadata.actual_solver.MaxStepSize-selected.max_step_s)<eps(selected.max_step_s));
for k=1:numel(protocolSnapshots)
    assert(strcmp(sha256LFFile(fullfile(protocolDirectory,protocolSnapshots(k).file)),protocolSnapshots(k).sha256_lf));
end
assert(strcmp(metadata.source_model_sha256,expectedModelHash) && strcmp(metadata.copy_model_sha256,expectedModelHash));
assert(strcmp(metadata.model_dirty_after_sim,'off') && isequal(metadata.stored_config_after_sim,original));
close_system(modelName,0);
extractNative(fullfile(runDirectory,'simulink_output.mat'),fullfile(runDirectory,'extracted'));
writeJSON(fullfile(runDirectory,'completion.json'),struct('stage',stage, ...
    'simulation_and_extraction_complete',true,'closed_without_saving',true, ...
    'candidate_created',false,'physical_or_control_parameters_changed',false));
end

function result=modelConfiguration(modelName)
names={'Solver','SolverType','RelTol','AbsTol','AutoScaleAbsTol','InitialStep','MinStep','MaxStep', ...
    'StartTime','StopTime','SolverResetMethod','ZeroCrossControl','ZeroCrossAlgorithm','ZCThreshold', ...
    'MaxConsecutiveZCs','MaxNumMinSteps','ConsecutiveZCsStepRelTol','MaxConsecutiveMinStep', ...
    'OutputOption','OutputTimes','Refine'};
result=struct;
for k=1:numel(names)
    try
        result.(names{k})=get_param(modelName,names{k});
    catch err
        result.(names{k})=struct('unavailable',true,'identifier',err.identifier,'message',err.message);
    end
end
end
function closeOwned(modelName)
if bdIsLoaded(modelName),close_system(modelName,0);end
end
function result=canonical(file)
result=char(java.io.File(file).getCanonicalPath());
end
function entries=fileHashes(directory)
files=dir(directory);files=files(~[files.isdir]);entries=struct('file',{},'bytes',{},'sha256',{});
for k=1:numel(files)
    entries(k)=struct('file',files(k).name,'bytes',files(k).bytes,'sha256',sha256File(fullfile(directory,files(k).name)));
end
end
function checksum=sha256File(file)
fid=fopen(file,'rb');assert(fid>=0);cleanup=onCleanup(@() fclose(fid)); %#ok<NASGU>
digest=java.security.MessageDigest.getInstance('SHA-256');digest.update(typecast(fread(fid,Inf,'*uint8'),'int8'));
checksum=lower(reshape(dec2hex(typecast(digest.digest(),'uint8'),2).',1,[]));
end
function writeJSON(file,value)
fid=fopen(file,'w','n','UTF-8');assert(fid>=0);cleanup=onCleanup(@() fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(value,PrettyPrint=true));
end

function extractNative(matFile,destination)
% Cached-only repair is possible: no model load, configuration, or simulation.
assert(~isfolder(destination),'Do not overwrite an earlier extraction.');mkdir(destination);
sourceHash=sha256File(matFile);loaded=load(matFile,'out');out=loaded.out;
groups=struct('index',{},'name',{},'block_paths',{},'rows',{},'width',{}, ...
    'time_first',{},'time_last',{},'negative_time_increments',{},'duplicate_time_increments',{}, ...
    'first_values',{},'last_values',{},'csv',{},'sha256',{});
for k=1:numElements(out.xout)
    state=out.xout.get(k);time=state.Values.Time(:);data=reshape(state.Values.Data,numel(time),[]);
    assert(~isempty(time) && all(isfinite(time)) && all(isfinite(data),'all'));
    assert(all(diff(time)>=0),'Preserve and report invalid axes; never silently reorder.');
    name=sprintf('native_state_%02d.csv',k);
    columns=[{'time'},arrayfun(@(j) sprintf('value_%02d',j),1:size(data,2),'UniformOutput',false)];
    writetable(array2table([time,data],'VariableNames',columns),fullfile(destination,name));
    groups(k)=struct('index',k,'name',state.Name,'block_paths',{convertToCell(state.BlockPath)}, ...
        'rows',numel(time),'width',size(data,2),'time_first',time(1),'time_last',time(end), ...
        'negative_time_increments',nnz(diff(time)<0),'duplicate_time_increments',nnz(diff(time)==0), ...
        'first_values',data(1,:),'last_values',data(end,:),'csv',name, ...
        'sha256',sha256File(fullfile(destination,name)));
end
writematrix(out.tout,fullfile(destination,'native_time.csv'));
writematrix(out.Isrc_sps,fullfile(destination,'source_current_native.csv'));
writematrix(out.Control,fullfile(destination,'duty_native.csv'));
writetable(table(out.Vout_sps{1}.Values.Time,out.Vout_sps{1}.Values.Data, ...
    'VariableNames',{'time','v_out'}),fullfile(destination,'output_voltage_native.csv'));
writetable(table(out.Vout_sps{2}.Values.Time,out.Vout_sps{2}.Values.Data, ...
    'VariableNames',{'time','i_pulse_load'}),fullfile(destination,'pulse_load_native.csv'));
assert(out.Isrc_sps(1,1)==0 && out.Isrc_sps(end,1)==0.01);
assert(out.Control(1,1)==0 && out.Control(end,1)==0.01);
assert(out.Vout_sps{1}.Values.Time(1)==0 && out.Vout_sps{1}.Values.Time(end)==0.01);
assert(out.Vout_sps{2}.Values.Time(1)==0 && out.Vout_sps{2}.Values.Time(end)==0.01);
writeJSON(fullfile(destination,'state_inventory.json'),groups);
writeJSON(fullfile(destination,'extraction_metadata.json'),struct('source_mat',matFile, ...
    'source_mat_sha256',sourceHash,'outputs',{who(out)},'state_groups',numel(groups), ...
    'total_saved_state_width',sum([groups.width]),'native_duplicates_preserved',true, ...
    'discrete_axes_preserved_without_extension',true,'resampled',false,'sim_invoked',false));
assert(strcmp(sourceHash,sha256File(matFile)));
end

function checksum=sha256LFFile(file)
text=fileread(file);text=strrep(text,sprintf('\r\n'),sprintf('\n'));text=strrep(text,sprintf('\r'),sprintf('\n'));
bytes=unicode2native(text,'UTF-8');digest=java.security.MessageDigest.getInstance('SHA-256');digest.update(typecast(uint8(bytes),'int8'));
checksum=lower(reshape(dec2hex(typecast(digest.digest(),'uint8'),2).',1,[]));
end
