function export_reference(repositoryRoot)
%EXPORT_REFERENCE Run the unchanged original three-phase transformer chain.
% Requires MATLAB R2025a, Simulink, Simscape and Simscape Electrical.
%   addpath('validation/cases/three_phase_transformer_chain'); export_reference(pwd)
% Acceptance was frozen at 4edd4a1; native node spelling corrected at c88c2bb.
% Solver-only addendum 926138d follows resource/minimum-step diagnostics.
% Candidate-step addendum 08a0156 records the preserved initial 1us FAIL.
% Only runtime solver/output logging changes are made through SimulationInput.
if nargin==0
    repositoryRoot=fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));
end
assert(strcmp(version('-release'),'2025a'),'Use the inspected R2025a reference installation.');
referenceRoot=fullfile(repositoryRoot,'local_reference','three_phase_transformer_chain');
originalRoot=fullfile(repositoryRoot,'local_reference','three_phase_transformer');
protocolRoot=fullfile(repositoryRoot,'validation','cases','three_phase_transformer_chain');
modelDirectory=fullfile(referenceRoot,'simulink');
runId=char(datetime('now','TimeZone','UTC','Format','yyyyMMdd''T''HHmmssSSS''Z'''));
runDirectory=fullfile(referenceRoot,'export_runs',runId);
inputDirectory=fullfile(runDirectory,'inputs');
for directory={modelDirectory,inputDirectory}
    if ~isfolder(directory{1}), mkdir(directory{1}); end
end
diary(fullfile(runDirectory,'export_reference.log'));
diaryCleanup=onCleanup(@() diary('off')); %#ok<NASGU>
previousPath=path;
pathCleanup=onCleanup(@() path(previousPath)); %#ok<NASGU>
previousFileGenConfig=Simulink.fileGenControl('getConfig');
fileGenCleanup=onCleanup(@() Simulink.fileGenControl('setConfig','config',previousFileGenConfig)); %#ok<NASGU>
Simulink.fileGenControl('set','CacheFolder',fullfile(runDirectory,'cache'), ...
    'CodeGenFolder',fullfile(runDirectory,'codegen'),'createDir',true);

% Pin both the independently inspected original and pre-candidate protocol.
modelName='ee_delta_transmission';
modelFile=fullfile(modelDirectory,[modelName '.slx']);
modelHash='02be3b7168ed504a6a585c3aa29aba3369b294d6bed2a517d6408a1931abe4ca';
originalFile=fullfile(originalRoot,'simulink',[modelName '.slx']);
assert(strcmp(sha256File(originalFile),modelHash),'Inspected original model bytes changed.');
if ~isfile(modelFile), copyfile(originalFile,modelFile); end
assert(strcmp(sha256File(modelFile),modelHash),'Reference model bytes differ from the original.');
protocolFiles={'manifest.json','parameters.json'};
protocolHashes={ ...
    '69ce525611621836336e321975b8d0e8261042cdfc10a6e67290e1b1a3e5ffd5', ...
    'e9838207cf7bbd90cd7922269cdc0e5753de0ef89d7fc6356c7cf1a4ff851f69'};
for k=1:numel(protocolFiles)
    file=fullfile(protocolRoot,protocolFiles{k});
    assert(strcmp(protocolLFHash(file),protocolHashes{k}),'Frozen protocol text changed.');
    copyfile(file,fullfile(inputDirectory,protocolFiles{k}));
end
addendumFile=fullfile(protocolRoot,'reference_solver_addendum.md');
addendumHash='10835fdcd754f5b9ef719e89c024eeb0e22e1a727dbcdf1ea93b6154f0d48968';
assert(strcmp(protocolLFHash(addendumFile),addendumHash),'Frozen solver addendum text changed.');
copyfile(addendumFile,fullfile(inputDirectory,'reference_solver_addendum.md'));
solverAddendum=struct('file','reference_solver_addendum.md', ...
    'commit','926138d43f5ee9091df782c461207b8eb0d6b8d5', ...
    'lf_sha256',addendumHash,'raw_sha256',sha256File(addendumFile), ...
    'text',readUTF8(addendumFile));
candidateStepFile=fullfile(protocolRoot,'candidate_step_addendum.md');
candidateStepHash='43d1085cb735fcf2347cdf6591cb786144ed3b5f37d7c672135118e41dfd815f';
assert(strcmp(protocolLFHash(candidateStepFile),candidateStepHash),'Frozen candidate-step addendum text changed.');
copyfile(candidateStepFile,fullfile(inputDirectory,'candidate_step_addendum.md'));
candidateStepAddendum=struct('file','candidate_step_addendum.md', ...
    'commit','08a01562d7e9dc557b472202f15e2b25894261a2', ...
    'lf_sha256',candidateStepHash,'raw_sha256',sha256File(candidateStepFile), ...
    'text',readUTF8(candidateStepFile));
copyfile([mfilename('fullpath') '.m'],fullfile(inputDirectory,'export_reference.m'));
copyfile(modelFile,fullfile(inputDirectory,[modelName '.slx']));
auditFiles={'source_parameter_audit.md','source_parameter_audit_native.json', ...
    'winding_reference_audit.md','winding_reference_audit.json'};
for k=1:numel(auditFiles)
    copyfile(fullfile(originalRoot,auditFiles{k}),fullfile(inputDirectory,auditFiles{k}));
end
copyfile(fullfile(originalRoot,'default_probe','provenance.json'), ...
    fullfile(inputDirectory,'original_default_provenance.json'));
manifest=jsondecode(fileread(fullfile(inputDirectory,'manifest.json')));
assert(numel(manifest.signals)==19 && isequal(manifest.windows_seconds,[0,4e-5;4e-5,.05]));

addpath(modelDirectory);
assert(strcmpi(canonical(which([modelName '.slx'])),canonical(modelFile)), ...
    'A different same-name model resolves on MATLAB path.');
wasLoaded=bdIsLoaded(modelName);
if wasLoaded, checkLoaded(modelName,modelFile); end
modelCleanup=onCleanup(@() closeOwnedModel(modelName,wasLoaded)); %#ok<NASGU>
fprintf('MATLAB %s\nRun %s\nOriginal SHA-256 %s\n',version,runId,modelHash);
fprintf('Two full-network native runs; physical parameters and initialization unchanged.\n');

settings=struct('name',{'baseline','refined'},'relative_tolerance',{1e-9,1e-10}, ...
    'absolute_tolerance',{1e-8,1e-8},'max_step_s',{25e-6,12.5e-6});
audited=jsondecode(fileread(fullfile(inputDirectory,'original_default_provenance.json')));
for runIndex=1:2
    destination=fullfile(runDirectory,settings(runIndex).name);
    mkdir(destination);
    in=Simulink.SimulationInput(modelName);
    in=in.setModelParameter('Solver','daessc', ...
        'RelTol',sprintf('%.17g',settings(runIndex).relative_tolerance), ...
        'AbsTol',sprintf('%.17g',settings(runIndex).absolute_tolerance), ...
        'MaxStep',sprintf('%.17g',settings(runIndex).max_step_s), ...
        'InitialStep','1e-10','StopTime','0.05','ReturnWorkspaceOutputs','on', ...
        'SimscapeLogType','all','SimscapeLogName','simlog','SimscapeLogLimitData','off');
    timer=tic;
    out=sim(in);
    settings(runIndex).elapsed_seconds=toc(timer);
    save(fullfile(destination,'simulink_output.mat'),'in','out','-v7.3');
    settings(runIndex).actual_solver=out.SimulationMetadata.ModelInfo.SolverInfo;
    assert(strcmp(settings(runIndex).actual_solver.Solver,'daessc'),'Actual solver differs.');
    checkLoaded(modelName,modelFile);
    assert(strcmp(sha256File(modelFile),modelHash),'Original model changed during simulation.');
    parameters=physicalParameters(modelName);
    ids=fieldnames(audited.actual_dialog_parameters);
    for k=1:numel(ids)
        assert(isequal(parameters.(ids{k}).values,audited.actual_dialog_parameters.(ids{k}).values), ...
            'Actual physical dialog parameters differ from the original default audit.');
    end
    [native,normalized,audit]=extractSignals(out,manifest);
    assert(all(audit.initial_source_current_a==0),'Three native source currents must start at zero.');
    settings(runIndex).native_audit=audit;
    settings(runIndex).samples=height(normalized);
    settings(runIndex).model_dirty=get_param(modelName,'Dirty');
    settings(runIndex).loaded_model_path=get_param(modelName,'FileName');
    writetable(native,fullfile(destination,'simscape_native.csv'));
    writetable(normalized,fullfile(destination,'reference.csv'));
    writeJSON(fullfile(destination,'actual_physical_parameters.json'),parameters);
    writeJSON(fullfile(destination,'run_settings.json'),settings(runIndex));
    fprintf('%s: %d native samples; %.6f seconds; initial source I=[%g %g %g] A.\n', ...
        settings(runIndex).name,height(native),settings(runIndex).elapsed_seconds, ...
        audit.initial_source_current_a);
    if runIndex==1, baseline=normalized; else, refined=normalized; end
end

refinement=refinementCheck(baseline,refined,manifest);
writeJSON(fullfile(runDirectory,'self_refinement.json'),refinement);
assert(refinement.passed,'Native self-refinement failed the frozen one-tenth limits.');
checkLoaded(modelName,modelFile);
assert(strcmp(sha256File(originalFile),modelHash) && strcmp(sha256File(modelFile),modelHash), ...
    'Original/source copy model bytes changed.');
metadata=struct('schema_version',1,'case_id',manifest.case_id,'reference_id',manifest.reference_id, ...
    'origin','Unmodified complete MathWorks R2025a ee_delta_transmission physical network', ...
    'export_time_utc',char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd HH:mm:ss Z')), ...
    'export_run_id',runId,'export_run_directory',runDirectory, ...
    'source_url',manifest.reference_source, ...
    'acquisition_url','https://www.mathworks.com/help/releases/R2025a/exampledata/simscapeelectrical/main/ee_delta_transmission.slx', ...
    'model_name',modelName,'model_path',modelFile,'model_sha256',modelHash, ...
    'original_model_path',originalFile,'model_was_loaded_before_export',wasLoaded, ...
    'loaded_model_path',get_param(modelName,'FileName'),'model_dirty_after_runs',get_param(modelName,'Dirty'), ...
    'matlab_version',version,'installed_products',ver, ...
    'required_products',{{'MATLAB','Simulink','Simscape','Simscape Electrical'}}, ...
    'freeze_commit','4edd4a170c7630af81ec4bec44b4769aa176ffa8', ...
    'signal_name_correction_commit','c88c2bbe5f80430410707f20415d3cbb98924ec3', ...
    'frozen_protocol_lf_sha256',struct('manifest',protocolHashes{1},'parameters',protocolHashes{2}), ...
    'manifest_sha256',sha256File(fullfile(inputDirectory,'manifest.json')), ...
    'parameters_sha256',sha256File(fullfile(inputDirectory,'parameters.json')), ...
    'export_script_sha256',sha256File([mfilename('fullpath') '.m']), ...
    'solver_addendum',solverAddendum, ...
    'candidate_step_addendum',candidateStepAddendum, ...
    'solver','daessc','initial_step_s',1e-10,'stop_time_s',.05,'runs',settings, ...
    'comparison_windows_s',manifest.windows_seconds,'reference_self_refinement',refinement, ...
    'signal_mapping',signalMapping(manifest), ...
    'normalization','Keep common native timestamps; last sample at duplicate times only. Source I negated into supply; T2 i2 negated into load; three Delta Reference I summed. No time/phase/amplitude fitting.', ...
    'topology_changes','none','physical_parameter_changes','none','initial_state_changes','none', ...
    'runtime_changes','SimulationInput solver tolerances/steps/stop time and existing full Simscape output logging only.', ...
    'input_snapshot_files',fileHashes(inputDirectory), ...
    'baseline_files',fileHashes(fullfile(runDirectory,'baseline')), ...
    'refined_files',fileHashes(fullfile(runDirectory,'refined')), ...
    'redistribution','Original model and generated vendor output remain ignored local data; no redistribution permission asserted.');
writeJSON(fullfile(runDirectory,'provenance.json'),metadata);

% Publish the tested baseline for the common runner; authoritative runs remain separate.
publishFiles(fullfile(runDirectory,'baseline'),fullfile(referenceRoot,'raw_results'));
publishFiles(fullfile(runDirectory,'refined'),fullfile(referenceRoot,'refined_results'));
normalizedDirectory=fullfile(referenceRoot,'normalized_results');
if ~isfolder(normalizedDirectory), mkdir(normalizedDirectory); end
copyfile(fullfile(runDirectory,'baseline','reference.csv'),fullfile(normalizedDirectory,'reference.csv'));
copyfile(fullfile(runDirectory,'self_refinement.json'),fullfile(referenceRoot,'self_refinement.json'));
copyfile(fullfile(runDirectory,'provenance.json'),fullfile(referenceRoot,'provenance.json'));
fprintf('Export complete: 19 signals, both frozen windows, all one-tenth self-refinement limits passed.\n');
fprintf('Baseline CSV SHA-256 %s\n',sha256File(fullfile(normalizedDirectory,'reference.csv')));
end

function [native,normalized,audit]=extractSignals(out,manifest)
% These original physical log paths and signs were independently audited.
nodes={out.simlog.Voltage_Source.V,out.simlog.Wye_Delta_Transformer.N2.V, ...
    out.simlog.Load.N.V,out.simlog.Voltage_Source.I, ...
    out.simlog.Wye_Delta_Transformer.i2,out.simlog.Delta_Wye_Transformer.i2, ...
    out.simlog.Delta_Reference.I};
prefixes={'source_v','delta_v','load_v','source_I','up_i2','down_i2','reference_I'};
time=nodes{1}.series.time;
assert(time(1)==0 && time(end)==.05 && all(diff(time)>=0),'Unexpected native time range.');
values=zeros(numel(time),21); names={'time'};
for k=1:numel(nodes)
    assert(isequal(nodes{k}.series.time,time),'Native signal time vectors must agree exactly.');
    if k<=3, unit='V'; else, unit='A'; end
    samples=nodes{k}.series.values(unit);
    assert(isequal(size(samples),[numel(time),3]) && all(isfinite(samples),'all'), ...
        'Each native signal must be a finite three-phase vector.');
    values(:,3*k-2:3*k)=samples;
    for phase='abc', names{end+1}=[prefixes{k} '_' phase]; end %#ok<AGROW>
end
native=array2table([time,values],'VariableNames',names);
% Manifest order is six quantities for each phase, then total reference current.
normalizedValues=zeros(numel(time),19);
for phase=1:3
    normalizedValues(:,6*phase-5:6*phase)= ...
        [values(:,phase),values(:,3+phase),values(:,6+phase), ...
        -values(:,9+phase),values(:,12+phase),-values(:,15+phase)];
end
normalizedValues(:,19)=sum(values(:,19:21),2);
normalized=array2table([time,normalizedValues], ...
    'VariableNames',[{'time'},{manifest.signals.reference}]);
[~,lastIndex]=unique(time,'last');
normalized=normalized(lastIndex,:);
assert(all(diff(normalized.time)>0),'Normalized time must increase strictly.');
audit=struct('initial_source_current_a',values(1,10:12), ...
    'common_native_time',true,'native_samples',numel(time), ...
    'duplicate_times_removed',numel(time)-height(normalized), ...
    'max_abs_delta_reference_total_a',max(abs(normalizedValues(:,19))), ...
    'max_abs_delta_mean_voltage_v',max(abs(mean(values(:,4:6),2))));
end

function report=refinementCheck(baseline,refined,manifest)
report=struct('method','Absolute-time union of both native grids and exact integral of squared piecewise-linear differences; no shift or fit', ...
    'limit_fraction',.1,'passed',true);
for windowIndex=1:size(manifest.windows_seconds,1)
    first=manifest.windows_seconds(windowIndex,1); last=manifest.windows_seconds(windowIndex,2);
    time=unique([first;last;baseline.time(baseline.time>=first & baseline.time<=last); ...
        refined.time(refined.time>=first & refined.time<=last)]);
    result=struct('window_s',[first,last],'passed',true);
    worstAbsolute=0; worstNRMSE=0;
    for k=1:numel(manifest.signals)
        spec=manifest.signals(k); column=spec.reference;
        difference=interp1(baseline.time,baseline.(column),time,'linear') ...
            -interp1(refined.time,refined.(column),time,'linear');
        assert(all(isfinite(difference)),'Refinement comparison produced nonfinite data.');
        maximum=max(abs(difference));
        a=difference(1:end-1); b=difference(2:end);
        rmse=sqrt(sum(diff(time).*(a.^2+a.*b+b.^2)/3)/(last-first));
        nrmse=rmse/spec.scale;
        absoluteLimit=spec.max_abs_error/10; nrmseLimit=spec.max_nrmse/10;
        passed=maximum<absoluteLimit && nrmse<nrmseLimit;
        result.signals.(column)=struct('rmse',rmse,'nrmse',nrmse, ...
            'max_abs_difference',maximum,'scale',spec.scale, ...
            'max_abs_limit',absoluteLimit,'max_nrmse_limit',nrmseLimit,'passed',passed);
        result.passed=result.passed && passed;
        worstAbsolute=max(worstAbsolute,maximum/absoluteLimit);
        worstNRMSE=max(worstNRMSE,nrmse/nrmseLimit);
    end
    report.windows(windowIndex)=result;
    report.passed=report.passed && result.passed;
    fprintf('Self-refinement [%g,%g]s: pass=%d; worst abs/limit %.6g, NRMSE/limit %.6g.\n', ...
        first,last,result.passed,worstAbsolute,worstNRMSE);
end
end

function parameters=physicalParameters(modelName)
parameters=struct;
for sid=[26,27,28,29,32]
    blockPath=Simulink.ID.getFullName(sprintf('%s:%d',modelName,sid));
    descriptors=get_param(blockPath,'DialogParameters'); names=fieldnames(descriptors);
    values=struct;
    for k=1:numel(names)
        value=get_param(blockPath,names{k});
        if ischar(value), values.(names{k})=value; end
    end
    parameters.(sprintf('SID%d',sid))=struct('path',blockPath,'values',values);
end
end

function mapping=signalMapping(manifest)
paths={'Voltage_Source.V','Wye_Delta_Transformer.N2.V','Load.N.V', ...
    '-Voltage_Source.I','Wye_Delta_Transformer.i2','-Delta_Wye_Transformer.i2'};
mapping=struct;
for phase=1:3
    for k=1:6
        spec=manifest.signals(6*phase-6+k);
        mapping.(spec.reference)=sprintf('%s phase %d',paths{k},phase);
    end
end
mapping.i_delta_reference_total='sum(Delta_Reference.I,2)';
end

function checkLoaded(modelName,modelFile)
assert(bdIsLoaded(modelName),'Reference model is not loaded after simulation.');
assert(strcmpi(canonical(get_param(modelName,'FileName')),canonical(modelFile)), ...
    'A different same-name model is loaded.');
assert(strcmp(get_param(modelName,'Dirty'),'off'),'Loaded reference has unsaved changes.');
end

function closeOwnedModel(modelName,wasLoaded)
if ~wasLoaded && bdIsLoaded(modelName), close_system(modelName,0); end
end

function value=canonical(fileName)
value=char(java.io.File(fileName).getCanonicalPath());
end

function entries=fileHashes(directory)
files=dir(directory); files=files(~[files.isdir]);
entries=struct('file',{},'bytes',{},'sha256',{});
for k=1:numel(files)
    entries(k)=struct('file',files(k).name,'bytes',files(k).bytes, ...
        'sha256',sha256File(fullfile(directory,files(k).name)));
end
end

function publishFiles(source,destination)
if ~isfolder(destination), mkdir(destination); end
files=dir(source); files=files(~[files.isdir]);
for k=1:numel(files), copyfile(fullfile(source,files(k).name),fullfile(destination,files(k).name)); end
end

function checksum=sha256File(fileName)
fid=fopen(fileName,'rb'); assert(fid>=0,'Cannot open artifact for SHA-256.');
cleanup=onCleanup(@() fclose(fid)); %#ok<NASGU>
digest=java.security.MessageDigest.getInstance('SHA-256');
while true
    bytes=fread(fid,8*1024*1024,'*uint8');
    if isempty(bytes), break; end
    digest.update(typecast(bytes,'int8'));
end
checksum=lower(reshape(dec2hex(typecast(digest.digest(),'uint8'),2).',1,[]));
end

function checksum=protocolLFHash(fileName)
% Git text can be checked out with CRLF; preserve all other protocol bytes.
fid=fopen(fileName,'rb'); assert(fid>=0);
cleanup=onCleanup(@() fclose(fid)); %#ok<NASGU>
bytes=fread(fid,Inf,'*uint8');
isCRLF=bytes==13 & [bytes(2:end)==10;false];
bytes=bytes(~isCRLF);
digest=java.security.MessageDigest.getInstance('SHA-256');
digest.update(typecast(bytes,'int8'));
checksum=lower(reshape(dec2hex(typecast(digest.digest(),'uint8'),2).',1,[]));
end

function value=readUTF8(fileName)
fid=fopen(fileName,'rb'); assert(fid>=0);
cleanup=onCleanup(@() fclose(fid)); %#ok<NASGU>
value=native2unicode(fread(fid,Inf,'*uint8').','UTF-8');
end

function writeJSON(fileName,value)
fid=fopen(fileName,'w','n','UTF-8'); assert(fid>=0);
cleanup=onCleanup(@() fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(value,PrettyPrint=true));
end
