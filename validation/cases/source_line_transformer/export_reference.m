function export_reference(repositoryRoot,runId,baselineMat)
%EXPORT_REFERENCE Export unchanged SPS source-line-transformer reference.
% Physical/accuracy protocol frozen independently at 65d89bb before candidate.
% Only SimulationInput runtime solver and state-output settings are changed.
if nargin==0
    repositoryRoot=fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));
end
if nargin<2
    runId=char(datetime('now','TimeZone','UTC','Format','yyyyMMdd''T''HHmmssSSS''Z'''));
end
if nargin<3, baselineMat=''; end
freezeCommit='65d89bb577c07656142f13c062907a5d7d600aba';
guardCommit='436c26642aff420d9e209b19bbf6043ca8e5b55c';
guardHash='86929b4960c62e6403c888b57fe14508855ada98a93dfbe57e44f454a7aa041b';
protocolHashes={'b95012206a51341838fdfc580e1b665577e0ca39c823330f7cde1cc2ed120174','a8ce291205ad8dc6a4bd4882be690853ab956597f708619da3851429da215d37','4b301512d3292657945be5d37028dea8b439b5520c9fd6ea5013bac40568c608'};
assert(~strcmp(freezeCommit,'UNFROZEN'),'Draft only: freeze the protocol before any native run.');
assert(strcmp(version('-release'),'2025a'),'Use the inspected R2025a installation.');
referenceRoot=fullfile(repositoryRoot,'local_reference','source_line_transformer');
researchRoot=fullfile(repositoryRoot,'local_reference','d0_research');
originalRun=fullfile(researchRoot,'default_runs','20261106T044524416Z');
protocolRoot=fullfile(repositoryRoot,'validation','cases','source_line_transformer');
runDirectory=fullfile(referenceRoot,'export_runs',runId);
inputDirectory=fullfile(runDirectory,'inputs');
assert(~isfolder(inputDirectory),'A historical export run must not be reused.');
mkdir(inputDirectory);
diary(fullfile(runDirectory,'export_reference.log'));
diaryCleanup=onCleanup(@() diary('off')); %#ok<NASGU>
previousPath=path; previousDirectory=pwd;
pathCleanup=onCleanup(@() path(previousPath)); %#ok<NASGU>
directoryCleanup=onCleanup(@() cd(previousDirectory)); %#ok<NASGU>
previousFileGenConfig=Simulink.fileGenControl('getConfig');
fileGenCleanup=onCleanup(@() Simulink.fileGenControl('setConfig','config',previousFileGenConfig)); %#ok<NASGU>
Simulink.fileGenControl('set','CacheFolder',fullfile(runDirectory,'cache'), ...
    'CodeGenFolder',fullfile(runDirectory,'codegen'),'createDir',true);

modelName='power_gui';
modelHash='a46b7c34658c65ce58c6e51a6d167244c06f4e839063c00bd1ff75c78bdc5a08';
originalFile=fullfile(researchRoot,'simulink',[modelName '.slx']);
modelDirectory=fullfile(referenceRoot,'simulink');
if ~isfolder(modelDirectory), mkdir(modelDirectory); end
modelFile=fullfile(modelDirectory,[modelName '.slx']);
assert(strcmp(sha256File(originalFile),modelHash),'Inspected original bytes changed.');
if ~isfile(modelFile), copyfile(originalFile,modelFile); end
assert(strcmp(sha256File(modelFile),modelHash),'Reference copy differs from original.');
inventoryFile=fullfile(researchRoot,'evidence_inventory_final.json');
inventoryHash='9297e7ef3f59aed86f9791c9e4ee7c98f15f0a09dc467481947d6e2e2a8c6e4f';
assert(strcmp(sha256File(inventoryFile),inventoryHash),'Frozen research inventory changed.');
verifyInventory(researchRoot,inventoryFile);
protocolFiles={'manifest.json','parameters.json','acceptance_plan.md'};
protocol=struct('file',{},'raw_sha256',{},'lf_sha256',{},'text',{});
for k=1:numel(protocolFiles)
    file=fullfile(protocolRoot,protocolFiles{k});
    assert(strcmp(protocolLFHash(file),protocolHashes{k}),'Frozen protocol text changed.');
    copyfile(file,fullfile(inputDirectory,protocolFiles{k}));
    protocol(k)=struct('file',protocolFiles{k},'raw_sha256',sha256File(file), ...
        'lf_sha256',protocolHashes{k},'text',readUTF8(file));
end
guardName='native_state_guard_addendum.md'; guardFile=fullfile(protocolRoot,guardName);
assert(strcmp(protocolLFHash(guardFile),guardHash),'Frozen native-state guard addendum changed.');
copyfile(guardFile,fullfile(inputDirectory,guardName));
protocol(end+1)=struct('file',guardName,'raw_sha256',sha256File(guardFile),'lf_sha256',guardHash,'text',readUTF8(guardFile));
guardAddendum=struct('file',guardName,'commit',guardCommit,'lf_sha256',guardHash, ...
    'raw_sha256',sha256File(guardFile),'text',readUTF8(guardFile));
copyfile([mfilename('fullpath') '.m'],fullfile(inputDirectory,'export_reference.m'));
copyfile(modelFile,fullfile(inputDirectory,[modelName '.slx']));
copyfile(inventoryFile,fullfile(inputDirectory,'research_inventory.json'));
copyfile(fullfile(researchRoot,'power_gui_static_audit.json'),fullfile(inputDirectory,'original_static_audit.json'));
copyfile(fullfile(researchRoot,'power_gui_independent_feasibility.json'),fullfile(inputDirectory,'independent_feasibility.json'));
copyfile(fullfile(originalRun,'actual_dialog_parameters.json'),fullfile(inputDirectory,'original_dialog_parameters.json'));
copyfile(fullfile(originalRun,'provenance.json'),fullfile(inputDirectory,'original_default_provenance.json'));
copyfile(fullfile(originalRun,'detailed_analysis','power_analyze_detailed.json'),fullfile(inputDirectory,'original_native_detailed.json'));
copyfile(fullfile(originalRun,'detailed_analysis','power_analyze_detailed.mat'),fullfile(inputDirectory,'original_native_analysis.mat'));
manifest=jsondecode(readUTF8(fullfile(inputDirectory,'manifest.json')));
parameters=jsondecode(readUTF8(fullfile(inputDirectory,'parameters.json')));
assert(strcmp(manifest.case_id,'source_line_transformer'));
oracle=parameters.independent_reference_accuracy_oracle;
assert(strcmp(oracle.source_report_sha256,sha256File(fullfile(inputDirectory,'independent_feasibility.json'))));
staticAudit=jsondecode(readUTF8(fullfile(inputDirectory,'original_static_audit.json')));
loaded=load(fullfile(inputDirectory,'original_native_analysis.mat'),'network'); original=loaded.network;
originalDialogs=jsondecode(readUTF8(fullfile(inputDirectory,'original_dialog_parameters.json')));
dependencies=checkDependencies(staticAudit.direct_root_block_library_dependencies);
cachedBaseline=struct('reused',false);
if ~isempty(baselineMat)
    assert(strcmp(sha256File(baselineMat),'15a9a5c9d1acf78415346a549d1964c0c948fd786d1df9699679caa550c039ba'), ...
        'Only the audited original completed baseline MAT may be reused.');
    sourceRun=fileparts(fileparts(baselineMat));
    generationScript=fullfile(sourceRun,'inputs','export_reference.m');
    assert(strcmp(sha256File(generationScript),'47d39e6c2cd3a1edf2dbb04f8f0781ced3c887ef55559fb05ffe28b1477f1217'));
    copyfile(generationScript,fullfile(inputDirectory,'baseline_generation_export_reference.m'));
    for k=1:3
        file=fullfile(sourceRun,'inputs',protocolFiles{k});
        assert(strcmp(protocolLFHash(file),protocolHashes{k}));
        copyfile(file,fullfile(inputDirectory,['baseline_generation_' protocolFiles{k}]));
    end
    cachedBaseline=struct('reused',true,'source_run_id','20261106T052652719Z', ...
        'source_mat',canonical(baselineMat),'source_mat_sha256',sha256File(baselineMat), ...
        'generation_script_sha256',sha256File(generationScript), ...
        'description','Completed original native baseline reused read-only; no repeated baseline simulation');
end

addpath(modelDirectory);
assert(strcmpi(canonical(which([modelName '.slx'])),canonical(modelFile)),'A different same-name model resolves.');
assert(~bdIsLoaded(modelName),'Use an independent batch; do not reuse a preloaded model.');
modelCleanup=onCleanup(@() closeOwned(modelName)); %#ok<NASGU>
settings=struct('name',{'baseline','refined'},'relative_tolerance',{1e-9,1e-10}, ...
    'absolute_tolerance',{1e-9,1e-10},'max_step_s',{10e-6,5e-6});
attempt=struct('status','started_not_published','run_id',runId,'freeze_commit',freezeCommit, ...
    'protocol',protocol,'model_sha256',modelHash,'matlab_version',version, ...
    'installed_products',ver,'settings',settings,'input_snapshot',fileHashes(inputDirectory));
writeJSON(fullfile(runDirectory,'export_attempt.json'),attempt);
fprintf('MATLAB %s\nRun %s\nUnchanged original power_gui; native states, no Scope logging edits.\n',version,runId);
for runIndex=1:2
    destination=fullfile(runDirectory,settings(runIndex).name); mkdir(destination);
    in=Simulink.SimulationInput(modelName);
    in=in.setModelParameter('Solver','ode15s','SolverType','Variable-step', ...
        'RelTol',sprintf('%.17g',settings(runIndex).relative_tolerance), ...
        'AbsTol',sprintf('%.17g',settings(runIndex).absolute_tolerance), ...
        'AutoScaleAbsTol','off','MaxStep',sprintf('%.17g',settings(runIndex).max_step_s), ...
        'InitialStep','1e-9','StartTime','0','StopTime','0.05', ...
        'ReturnWorkspaceOutputs','on','SaveTime','on','TimeSaveName','tout', ...
        'SaveState','on','StateSaveName','xout','SaveFormat','Dataset', ...
        'Decimation','1','LimitDataPoints','off','Refine','1');
    if runIndex==1 && cachedBaseline.reused
        loaded=load(baselineMat,'in','out'); expected=in; in=loaded.in; out=loaded.out;
        assertSameInput(in,expected);
        copyfile(baselineMat,fullfile(destination,'simulink_output.mat'));
        settings(runIndex).elapsed_seconds=out.SimulationMetadata.TimingInfo.TotalElapsedWallTime;
        settings(runIndex).native_generation=cachedBaseline;
        open_system(modelFile); % Query cached data's unchanged model, no simulation.
    else
        timer=tic; out=sim(in); settings(runIndex).elapsed_seconds=toc(timer);
        save(fullfile(destination,'simulink_output.mat'),'in','out','-v7.3');
        settings(runIndex).native_generation=struct('reused',false,'source_run_id',runId, ...
            'generation_script_sha256',sha256File([mfilename('fullpath') '.m']));
    end
    settings(runIndex).actual_solver=out.SimulationMetadata.ModelInfo.SolverInfo;
    assert(strcmp(settings(runIndex).actual_solver.Solver,'ode15s'));
    checkModel(modelName,modelFile,originalFile,modelHash);
    stateBlock=stateBlockAudit(out,modelName);
    dialogs=physicalParameters(modelName);
    assert(isequal({dialogs.values},{originalDialogs.values}),'Actual physical dialog parameters changed.');
    cd(destination);
    network=power_analyze(modelName,'detailed');
    save(fullfile(destination,'native_analysis.mat'),'network','-v7.3');
    assertSameNetwork(network,original);
    [native,inputs,outputs,normalized,audit]=extractSignals(out,network,manifest,stateBlock);
    assert(max(diff(native.time))<=settings(runIndex).max_step_s*(1+1e-10),'Native knot gap exceeds the frozen MaxStep.');
    writetable(native,fullfile(destination,'native_states.csv'));
    writetable(inputs,fullfile(destination,'native_source_inputs.csv'));
    writetable(outputs,fullfile(destination,'native_projected_outputs.csv'));
    writetable(normalized,fullfile(destination,'reference.csv'));
    writeJSON(fullfile(destination,'native_mapping.json'),struct( ...
        'states',{network.states},'inputs',{network.sourcenames},'outputs',{network.outstr}, ...
        'C',network.C,'D',network.D,'source',network.source,'x0',network.x0, ...
        'rlcnames',{network.rlcnames},'rlc',network.rlc,'unit',network.unit));
    writeJSON(fullfile(destination,'actual_dialog_parameters.json'),dialogs);
    accuracy=independentAccuracy(normalized,manifest,oracle.peak_phasors,parameters.physical_parameters.source.frequency_hz);
    accuracy.run_name=settings(runIndex).name;
    writeJSON(fullfile(destination,'independent_accuracy.json'),accuracy);
    settings(runIndex).audit=audit;
    settings(runIndex).independent_accuracy=accuracy;
    settings(runIndex).samples=height(native);
    settings(runIndex).model_dirty=get_param(modelName,'Dirty');
    settings(runIndex).loaded_path=get_param(modelName,'FileName');
    settings(runIndex).output_names=who(out);
    settings(runIndex).native_files=fileHashes(destination);
    writeJSON(fullfile(destination,'run_settings.json'),settings(runIndex));
    checkModel(modelName,modelFile,originalFile,modelHash,true);
    assert(accuracy.passed,'Native samples/PWL curves failed the frozen independent physical reference budget.');
    fprintf('%s: %d native knots, %.6f s; max step %.9g s; original steady initial state retained.\n', ...
        settings(runIndex).name,height(native),settings(runIndex).elapsed_seconds,max(diff(native.time)));
    if runIndex==1, baseline=normalized; else, refined=normalized; end
    if runIndex==1, closeOwned(modelName); end % Next real run loads original bytes afresh.
end
refinement=refinementCheck(baseline,refined,manifest);
writeJSON(fullfile(runDirectory,'self_refinement.json'),refinement);
assert(refinement.passed,'Native self-refinement failed a frozen one-tenth limit.');
dependenciesAfter=checkDependencies(staticAudit.direct_root_block_library_dependencies);
assert(isequal(dependencies,dependenciesAfter),'Resolved library identities changed.');
checkModel(modelName,modelFile,originalFile,modelHash,true);
metadata=struct('schema_version',1,'case_id',manifest.case_id,'reference_id',manifest.reference_id, ...
    'origin','Unmodified complete MathWorks R2025a installed SPS power_gui network', ...
    'export_run_id',runId,'export_run_directory',runDirectory, ...
    'export_time_utc',char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd HH:mm:ss Z')), ...
    'source_url',manifest.reference_source,'model_name',modelName,'model_path',modelFile, ...
    'original_model_path',originalFile,'model_sha256',modelHash, ...
    'loaded_model_path',get_param(modelName,'FileName'),'model_dirty_after_runs',get_param(modelName,'Dirty'), ...
    'research_inventory_sha256',inventoryHash,'freeze_commit',freezeCommit,'frozen_protocol',protocol, ...
    'native_state_guard_addendum',guardAddendum,'cached_baseline_source',cachedBaseline, ...
    'matlab_version',version,'installed_products',ver,'direct_library_dependencies',dependencies, ...
    'dependency_scope','Direct root-block SPS libraries pinned to inspected bytes; not an exhaustive MATLAB distribution inventory', ...
    'export_script_sha256',sha256File([mfilename('fullpath') '.m']), ...
    'export_script_lf_sha256',protocolLFHash([mfilename('fullpath') '.m']), ...
    'solver','ode15s','initial_step_s',1e-9,'auto_scale_absolute_tolerance','off', ...
    'start_time_s',0,'stop_time_s',.05,'runs',settings, ...
    'measurement_origin','Native xout state trajectories projected using actual verified native C/D and immutable original source input; not direct Scope logs', ...
    'normalization','Original common native time; last duplicate time only; declared current sign changes; no shift, amplitude fit or uniform resampling', ...
    'source_inputs','Two diagnostic current inputs are identically zero; AC source is its actual amplitude*sin(2*pi*frequency*time+phase*pi/180)', ...
    'initialization','Original native steady-state initialization; no model or block initial values changed', ...
    'topology_changes','none','physical_parameter_changes','none','initial_state_changes','none', ...
    'runtime_changes','SimulationInput stiff solver settings, time/state Dataset output capture only', ...
    'comparison_windows_s',manifest.windows_seconds,'reference_self_refinement',refinement, ...
    'input_snapshot_files',fileHashes(inputDirectory), ...
    'baseline_files',fileHashes(fullfile(runDirectory,'baseline')), ...
    'refined_files',fileHashes(fullfile(runDirectory,'refined')), ...
    'redistribution','Original model and generated vendor outputs remain ignored local data; no redistribution permission asserted');
writeJSON(fullfile(runDirectory,'provenance.json'),metadata);
publishFiles(fullfile(runDirectory,'baseline'),fullfile(referenceRoot,'raw_results'));
publishFiles(fullfile(runDirectory,'refined'),fullfile(referenceRoot,'refined_results'));
normalizedDirectory=fullfile(referenceRoot,'normalized_results');
if ~isfolder(normalizedDirectory), mkdir(normalizedDirectory); end
copyfile(fullfile(runDirectory,'baseline','reference.csv'),fullfile(normalizedDirectory,'reference.csv'));
copyfile(fullfile(runDirectory,'provenance.json'),fullfile(referenceRoot,'provenance.json'));
copyfile(fullfile(runDirectory,'self_refinement.json'),fullfile(referenceRoot,'self_refinement.json'));
fprintf('All frozen native self-refinement checks passed. Baseline CSV SHA-256 %s\n', ...
    sha256File(fullfile(normalizedDirectory,'reference.csv')));
end

function audit=stateBlockAudit(out,modelName)
assert(numElements(out.xout)==1,'Expected the original single 12-state native group.');
state=out.xout.get(1); blockPaths=convertToCell(state.BlockPath);
assert(numel(blockPaths)==1,'Expected original native state block.');
dirtyBefore=get_param(modelName,'Dirty');
feval(modelName,[],[],[],'compile'); % Read generated implementation; never integrates time.
cleanup=onCleanup(@() terminateCompiled(modelName)); %#ok<NASGU>
blockType=get_param(blockPaths{1},'BlockType');
descriptors=get_param(blockPaths{1},'ObjectParameters');
functionName=get_param(blockPaths{1},'FunctionName');
assert(strcmp(blockType,'S-Function') && strcmp(functionName,'sfun_spid_contc'));
assert(~isfield(descriptors,'AbsoluteTolerance'),'Unexpected native absolute-tolerance block override.');
functionFile=which(functionName); sourceFile=fullfile(fileparts(functionFile),[functionName '.c']);
assert(strcmp(sha256File(functionFile),'a87689e01299106db2e40956dcd024f770a309663bf91cd18a94aeb75c6976dd'));
assert(strcmp(sha256File(sourceFile),'eeddbcc6613837f74a8cbaf238d79d7c8ea6fe0094b8e845ef5f3fc558052074'));
source=fileread(sourceFile);
assert(~contains(source,'ssSetStateAbsTol') && ~contains(source,'ssGetStateAbsTol'));
expression=get_param(blockPaths{1},'Parameters');
assert(strcmp(expression,'S.Mg, [S.nb.x S.nb.u S.nb.y S.nb.s], S.x0, S.MgColNames'));
runtime=get_param(blockPaths{1},'RuntimeObject');
assert(runtime.NumContStates==12 && runtime.NumDialogPrms==4);
audit=struct('path',{blockPaths},'block_type',blockType,'function_name',functionName, ...
    'function_file',functionFile,'function_sha256',sha256File(functionFile), ...
    'source_file',sourceFile,'source_sha256',sha256File(sourceFile), ...
    'parameter_expression',expression,'sfunction_argument_count',runtime.NumDialogPrms, ...
    'compiled_continuous_states',runtime.NumContStates,'has_absolute_tolerance_field',false, ...
    'compiled_sample_time',get_param(blockPaths{1},'CompiledSampleTime'), ...
    'dirty_before_query',dirtyBefore,'dirty_after_compile',get_param(modelName,'Dirty'), ...
    'tolerance_evidence','No per-state override setter in inspected installed C; model-tolerance inheritance inferred from source/documentation, not a runtime per-state AbsTol read');
feval(modelName,[],[],[],'term');
audit.status_after_term=get_param(modelName,'SimulationStatus');
audit.dirty_after_term=get_param(modelName,'Dirty');
end

function terminateCompiled(modelName)
if bdIsLoaded(modelName) && ~strcmp(get_param(modelName,'SimulationStatus'),'stopped')
    feval(modelName,[],[],[],'term');
end
end

function assertSameInput(actual,expected)
assert(strcmp(actual.ModelName,expected.ModelName));
assert(numel(actual.ModelParameters)==numel(expected.ModelParameters));
for k=1:numel(expected.ModelParameters)
    assert(strcmp(actual.ModelParameters(k).Name,expected.ModelParameters(k).Name) ...
        && isequal(actual.ModelParameters(k).Value,expected.ModelParameters(k).Value), ...
        'Cached native baseline input differs from the frozen solver/state-capture configuration.');
end
end

function [native,inputs,outputs,normalized,audit]=extractSignals(out,network,manifest,stateBlock)
assert(numElements(out.xout)==1,'Expected the original single 12-state native group.');
state=out.xout.get(1); time=state.Values.Time(:);
x=reshape(state.Values.Data,numel(time),[]);
assert(isequal(size(x),[numel(time),12]) && all(isfinite(x),'all'));
assert(time(1)==0 && time(end)==.05 && all(diff(time)>=0));
assert(isequal(out.tout(:),time),'State and model native time grids must agree exactly.');
assert(isequal(x(1,:).',network.x0(:)),'Actual native t0 differs from unchanged native initialization.');
assert(isequal(network.source(1:2,4),[0;0]) && network.source(3,4)>0 && network.source(3,6)==60);
u=zeros(numel(time),3);
u(:,3)=network.source(3,4)*sin(2*pi*network.source(3,6)*time+network.source(3,5)*pi/180);
y=x*network.C.'+u*network.D.';
assert(isequal(y(:,3),x(:,10)) && isequal(y(:,4),x(:,12)));
assert(max(abs(y(:,5)-x(:,1)-x(:,2)))<1e-8 && max(abs(y(:,6)-(u(:,3)-x(:,10))/2))<1e-8);
native=array2table([time,x],'VariableNames',[{'time'},arrayfun(@(k) sprintf('state_%02d',k),1:12,'UniformOutput',false)]);
inputs=array2table([time,u],'VariableNames',{'time','diagnostic_i_b3','diagnostic_i_b1','source_voltage'});
outputs=array2table([time,y],'VariableNames',{'time','diagnostic_v_b3','diagnostic_v_b1','v_b1','v_b2','i_load','i_source'});
allSignals=array2table([time,x(:,10:12),x(:,9),x(:,1),-x(:,2),-x(:,3),x(:,4:8),y(:,6),y(:,5)], ...
    'VariableNames',{'time','v_sending','v_middle','v_receiving','v_load', ...
    'i_z1','i_zs','i_comp_sending','i_comp_receiving','i_line1','i_line2', ...
    'i_magnetizing','i_primary','i_source','i_load'});
columns=[{'time'},{manifest.signals.reference}];
assert(all(ismember(columns,allSignals.Properties.VariableNames)),'Protocol contains an unmapped reference column.');
normalized=allSignals(:,columns);
duplicates=find(diff(time)==0);
if ~isequal(normalized{duplicates,2:end},normalized{duplicates+1,2:end})
    fprintf('Repeated native times have different left/right normalized values; raw MAT retained.\n');
    disp(normalized(unique([duplicates;duplicates+1]),:));
    error('Distinct left/right native values at the same time cannot be merged.');
end
[~,lastIndex]=unique(time,'last'); normalized=normalized(lastIndex,:);
assert(all(diff(normalized.time)>0) && all(isfinite(normalized{:,:}),'all'));
audit=struct('native_state_block',stateBlock,'native_state_names',{network.states}, ...
    'native_samples',numel(time), ...
    'duplicates_removed',numel(time)-height(normalized),'max_native_step_s',max(diff(time)), ...
    'duplicate_values_verified_exactly_equal',true, ...
    'actual_initial_state',x(1,:),'native_initial_state',network.x0, ...
    'actual_t0_matches_native_x0',true,'source_current_initial_a',y(1,6), ...
    'load_current_initial_a',y(1,5),'normalized_columns',{columns});
end

function assertSameNetwork(network,original)
assert(strcmp(network.unit,'OMU'));
for name={'states','sourcenames','outstr','rlcnames','A','B','C','D','source','rlc','x0'}
    actual=network.(name{1}); expected=original.(name{1});
    if iscell(actual), actual=actual(:); expected=expected(:); end
    assert(isequal(actual,expected),'Native branch/state/source/projection metadata changed.');
end
end

function dialogs=physicalParameters(modelName)
dialogs=struct('sid',{},'path',{},'values',{});
for sid=[1,2,3,9,10,11,16,17,18,29]
    blockPath=Simulink.ID.getFullName(sprintf('%s:%d',modelName,sid));
    names=fieldnames(get_param(blockPath,'DialogParameters')); values=struct;
    for k=1:numel(names)
        value=get_param(blockPath,names{k});
        if ischar(value), values.(names{k})=value; end
    end
    dialogs(end+1)=struct('sid',sid,'path',blockPath,'values',values); %#ok<AGROW>
end
end

function dependencies=checkDependencies(expected)
dependencies=struct('name',{},'resolved_path',{},'sha256',{});
for k=1:numel(expected)
    file=which([expected(k).name '.slx']);
    assert(~isempty(file),'An inspected direct SPS library is missing.');
    hash=sha256File(file);
    assert(strcmp(hash,expected(k).sha256),'An inspected direct SPS library changed.');
    dependencies(k)=struct('name',expected(k).name,'resolved_path',canonical(file),'sha256',hash);
end
end

function verifyInventory(directory,file)
inventory=jsondecode(readUTF8(file));
for k=1:numel(inventory.files)
    entry=inventory.files(k);
    assert(strcmp(sha256File(fullfile(directory,entry.path)),entry.sha256),'Frozen research evidence changed.');
end
end

function checkModel(modelName,modelFile,originalFile,expectedHash,allowReadOnlyDirty)
if nargin<5, allowReadOnlyDirty=false; end
assert(bdIsLoaded(modelName));
assert(strcmpi(canonical(get_param(modelName,'FileName')),canonical(modelFile)));
if ~allowReadOnlyDirty
    assert(strcmp(get_param(modelName,'Dirty'),'off'),'Reference has unsaved changes before read-only native analysis.');
end
assert(strcmp(sha256File(originalFile),expectedHash) && strcmp(sha256File(modelFile),expectedHash));
end

function closeOwned(modelName)
if bdIsLoaded(modelName), close_system(modelName,0); end
end

function report=refinementCheck(baseline,refined,manifest)
report=struct('method','Exact squared-error integral of piecewise-linear native grid union; no shift or fit', ...
    'limit_fraction',.1,'passed',true);
for windowIndex=1:size(manifest.windows_seconds,1)
    first=manifest.windows_seconds(windowIndex,1); last=manifest.windows_seconds(windowIndex,2);
    assert(first>=baseline.time(1) && first>=refined.time(1) && last<=baseline.time(end) && last<=refined.time(end));
    time=unique([first;last;baseline.time(baseline.time>=first & baseline.time<=last); ...
        refined.time(refined.time>=first & refined.time<=last)]);
    result=struct('window_s',[first,last],'passed',true);
    for k=1:numel(manifest.signals)
        spec=manifest.signals(k); column=spec.reference;
        error=interp1(baseline.time,baseline.(column),time,'linear')-interp1(refined.time,refined.(column),time,'linear');
        assert(all(isfinite(error)));
        a=error(1:end-1); b=error(2:end);
        rmse=sqrt(sum(diff(time).*(a.^2+a.*b+b.^2)/3)/(last-first));
        maximum=max(abs(error)); nrmse=rmse/spec.scale;
        passed=maximum<=spec.max_abs_error/10 && nrmse<=spec.max_nrmse/10;
        result.signals.(column)=struct('rmse',rmse,'nrmse',nrmse,'max_abs_difference',maximum, ...
            'absolute_limit',spec.max_abs_error/10,'nrmse_limit',spec.max_nrmse/10,'passed',passed);
        result.passed=result.passed && passed;
    end
    report.windows(windowIndex)=result; report.passed=report.passed && result.passed;
    fprintf('Native self-refinement [%g,%g]s: pass=%d.\n',first,last,result.passed);
end
end

function report=independentAccuracy(native,manifest,phasors,frequency)
% Absolute native accuracy against frozen independent physical phasors.
% The L-infinity/scale bound proves the NRMSE limit; no integral is claimed.
omega=2*pi*frequency;
report=struct('method','Native knots and exact PWL-minus-sine stationary points; L-infinity/scale bounds NRMSE', ...
    'limit_fraction',.1,'continuous_nrmse_integral_evaluated',false,'passed',true);
for windowIndex=1:size(manifest.windows_seconds,1)
    first=manifest.windows_seconds(windowIndex,1); last=manifest.windows_seconds(windowIndex,2);
    result=struct('window_s',[first,last],'passed',true);
    inside=native.time>=first & native.time<=last;
    time=unique([first;native.time(inside);last]);
    for k=1:numel(manifest.signals)
        spec=manifest.signals(k); column=spec.reference; q=phasors.(column);
        sampleError=native.(column)(inside)-q.real*sin(omega*native.time(inside))-q.imag*cos(omega*native.time(inside));
        sampleMaximum=max(abs(sampleError));
        values=interp1(native.time,native.(column),time,'linear');
        [maximum,stationaryCount,roundoffGuard]=pwlSineMaximum(time,values,q.real,q.imag,omega);
        absoluteLimit=spec.max_abs_error/10; nrmseLimit=spec.max_nrmse/10;
        passed=sampleMaximum<=absoluteLimit && sampleMaximum/spec.scale<=nrmseLimit ...
            && maximum<=absoluteLimit && maximum/spec.scale<=nrmseLimit;
        result.signals.(column)=struct('sample_max_abs_error',sampleMaximum, ...
            'sample_nrmse_upper_bound',sampleMaximum/spec.scale,'pwl_max_abs_error_bound',maximum, ...
            'pwl_nrmse_upper_bound',maximum/spec.scale,'pwl_stationary_points',stationaryCount, ...
            'floating_roundoff_guard',roundoffGuard,'scale',spec.scale, ...
            'absolute_limit',absoluteLimit,'nrmse_bound_limit',nrmseLimit,'passed',passed);
        result.passed=result.passed && passed;
    end
    report.windows(windowIndex)=result; report.passed=report.passed && result.passed;
    fprintf('Independent native absolute accuracy [%g,%g]s: pass=%d (NRMSE guaranteed upper bound).\n', ...
        first,last,result.passed);
end
end

function [maximum,stationaryCount,roundoffGuard]=pwlSineMaximum(time,values,a,b,omega)
% Error extrema are endpoints or slope = omega*A*cos(omega*t+phase).
maximum=max(abs(values-a*sin(omega*time)-b*cos(omega*time)));
amplitude=hypot(a,b); phase=atan2(b,a); stationaryCount=0;
if amplitude>0
    for k=1:numel(time)-1
        slope=(values(k+1)-values(k))/(time(k+1)-time(k));
        ratio=slope/(omega*amplitude);
        if abs(ratio)>1, continue; end
        for angle=[acos(ratio),-acos(ratio)]
            firstTurn=ceil((omega*time(k)+phase-angle)/(2*pi));
            lastTurn=floor((omega*time(k+1)+phase-angle)/(2*pi));
            roots=(angle+2*pi*(firstTurn:lastTurn)-phase)/omega;
            roots=roots(roots>=time(k) & roots<=time(k+1));
            if isempty(roots), continue; end
            linear=values(k)+slope*(roots-time(k));
            errors=linear-a*sin(omega*roots)-b*cos(omega*roots);
            maximum=max(maximum,max(abs(errors)));
            stationaryCount=stationaryCount+numel(roots);
        end
    end
end
roundoffGuard=64*eps(max([1;abs(values);amplitude]));
maximum=maximum+roundoffGuard;
end

function entries=fileHashes(directory)
files=dir(directory); files=files(~[files.isdir]);
entries=struct('file',{},'bytes',{},'sha256',{});
for k=1:numel(files)
    entries(k)=struct('file',files(k).name,'bytes',files(k).bytes,'sha256',sha256File(fullfile(directory,files(k).name)));
end
end

function publishFiles(source,destination)
if ~isfolder(destination), mkdir(destination); end
files=dir(source); files=files(~[files.isdir]);
for k=1:numel(files), copyfile(fullfile(source,files(k).name),fullfile(destination,files(k).name)); end
end

function value=canonical(file)
value=char(java.io.File(file).getCanonicalPath());
end

function hash=sha256File(file)
fid=fopen(file,'rb'); assert(fid>=0); cleanup=onCleanup(@() fclose(fid)); %#ok<NASGU>
digest=java.security.MessageDigest.getInstance('SHA-256');
while true
    bytes=fread(fid,8*1024*1024,'*uint8'); if isempty(bytes), break; end
    digest.update(typecast(bytes,'int8'));
end
hash=lower(reshape(dec2hex(typecast(digest.digest(),'uint8'),2).',1,[]));
end

function hash=protocolLFHash(file)
fid=fopen(file,'rb'); assert(fid>=0); cleanup=onCleanup(@() fclose(fid)); %#ok<NASGU>
bytes=fread(fid,Inf,'*uint8');
bytes=bytes(~(bytes==13 & [bytes(2:end)==10;false]));
digest=java.security.MessageDigest.getInstance('SHA-256'); digest.update(typecast(bytes,'int8'));
hash=lower(reshape(dec2hex(typecast(digest.digest(),'uint8'),2).',1,[]));
end

function value=readUTF8(file)
fid=fopen(file,'rb'); assert(fid>=0); cleanup=onCleanup(@() fclose(fid)); %#ok<NASGU>
value=native2unicode(fread(fid,Inf,'*uint8').','UTF-8');
end

function writeJSON(file,value)
fid=fopen(file,'w','n','UTF-8'); assert(fid>=0); cleanup=onCleanup(@() fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(value,PrettyPrint=true));
end
