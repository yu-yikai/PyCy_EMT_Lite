function export_reference(repositoryRoot)
%EXPORT_REFERENCE Export the third original CompareCircuits electrical T group.
% Requires MATLAB, Simulink and Simscape. All five native networks still run.
%   addpath('validation/cases/transformer_t_equivalent'); export_reference(pwd)
% Physical protocol frozen at 0ec7239 before candidate implementation: use
% the official MLX's step@2s / Rc=1e5 setup, not the SLX fallback@100s/Rc1e4.
if nargin==0
    repositoryRoot=fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));
end
referenceRoot=fullfile(repositoryRoot,'local_reference','transformer_t_equivalent');
modelDirectory=fullfile(referenceRoot,'simulink');
rawDirectory=fullfile(referenceRoot,'raw_results');
normalizedDirectory=fullfile(referenceRoot,'normalized_results');
refinedDirectory=fullfile(referenceRoot,'refined_results');
for directory={modelDirectory,rawDirectory,normalizedDirectory,refinedDirectory}
    if ~isfolder(directory{1}), mkdir(directory{1}); end
end
previousFileGenConfig=Simulink.fileGenControl('getConfig');
restore=onCleanup(@() Simulink.fileGenControl('setConfig','config',previousFileGenConfig)); %#ok<NASGU>
Simulink.fileGenControl('set','CacheFolder',fullfile(referenceRoot,'cache'), ...
    'CodeGenFolder',fullfile(referenceRoot,'codegen'),'createDir',true);
modelName='CompareCircuits';
modelFile=fullfile(modelDirectory,[modelName '.slx']);
if ~isfile(modelFile)
    openExample('simscape/ComparisonOfMutualInductorAndIdealTransformerExample','workDir',modelDirectory);
end
addpath(modelDirectory);
diary(fullfile(referenceRoot,'export_reference.log'));
diaryCleanup=onCleanup(@() diary('off')); %#ok<NASGU>
expectedSources={ ...
    'CompareCircuits.slx','9df7b95e3d0c5b842c1699631e49a5587179088b6afe9281914c52b60964e07b'; ...
    'ComparisonOfMutualInductorAndIdealTransformerExample.mlx','8a6e3f0f1f55dc015619d8462592be4c4ac1910a022fd7315fc6a6ef8ee877b6'; ...
    'ElectricalEquivalentCircuitMutualInductor.slx','eb5ff69d07d15aed0e74183ec6c05c1fea57fad0937a65bbb1c2ab57166146cd'; ...
    'ElectricalEquivalentCircuitSimplifiedMutualInductor.slx','0f47e478f52e4adee90f3ee35518e9dff2eda2232c213305cf8a75fcf0689cc3'; ...
    'ElectricalEquivalentCircuitTransformer.slx','e64bffb228e8f11daf0ffb6475615a82f7e4e20668808bcd3d5edcfe921cf672'; ...
    'MagneticEquivalentCircuit.slx','b6e4b137ee8405d9cf8333cb9d90133c70a15b0f1c1d05454fdcd8f20230706b'; ...
    'MagneticEquivalentCircuitIdealTransformer.slx','6cb185d3d40bdf8974ca606018d9f5cf98e1780d8796abf24a671793204cbc55'};
sources=checkSources(modelDirectory,expectedSources);
if ~bdIsLoaded(modelName), open_system(modelFile); end
sources=checkSources(modelDirectory,expectedSources);
fprintf('MATLAB %s\nUnmodified model and all five support files verified.\n',version);

% Bind every case-sensitive physical/harness variable from the official MLX.
% In particular R1 differs from r1, l1 from L1, and Rc is 1e5, not 1e4.
variables=struct('R1',1e6,'R2',1e6,'Rc',.1e6,'N1',100,'N2',500);
variables.ratio=variables.N1/variables.N2;
variables.l1=variables.N1^2/variables.R1;
variables.l2=variables.N2^2/variables.R2;
variables.Lm=variables.N1^2/variables.Rc;
variables.L1=variables.N1^2*(1/variables.Rc+1/variables.R1);
variables.L2=variables.N2^2*(1/variables.Rc+1/variables.R2);
variables.M=variables.N1*variables.N2/variables.Rc;
variables.k=1/sqrt((1+variables.Rc/variables.R1)*(1+variables.Rc/variables.R2));
variables.r1=1; variables.r2=1; variables.vStep=1; variables.tStep=2;
maxSteps=[.001,.0005]; elapsed=zeros(1,2); initial=zeros(2,3);
for runIndex=1:2
    in=Simulink.SimulationInput(modelName);
    names=fieldnames(variables);
    for k=1:numel(names), in=in.setVariable(names{k},variables.(names{k})); end
    in=in.setModelParameter('Solver','ode15s','RelTol','1e-9','AbsTol','1e-11', ...
        'MaxStep',sprintf('%.17g',maxSteps(runIndex)),'StopTime','8', ...
        'SimscapeLogType','all','SimscapeLogName','simlog','SimscapeLogLimitData','off');
    timer=tic;
    out=sim(in);
    elapsed(runIndex)=toc(timer);
    values=out.simlog.Subsystem_Reference2.l1.i_L.series.values('A'); initial(runIndex,1)=values(1);
    values=out.simlog.Subsystem_Reference2.l2.i_L.series.values('A'); initial(runIndex,2)=values(1);
    values=out.simlog.Subsystem_Reference2.Lm.i_L.series.values('A'); initial(runIndex,3)=values(1);
    assert(all(initial(runIndex,:)==0),'Native T initial inductor currents differ from the frozen zero state.');
    physical=extractSignals(out);
    if runIndex==1
        save(fullfile(rawDirectory,'simulink_output.mat'),'out','-v7.3');
        writetable(physical,fullfile(rawDirectory,'simscape_native.csv'));
        baseline=normalize(physical);
        writetable(baseline,fullfile(normalizedDirectory,'reference.csv'));
    else
        save(fullfile(refinedDirectory,'simulink_output.mat'),'out','-v7.3');
        writetable(physical,fullfile(refinedDirectory,'simscape_native.csv'));
        refined=normalize(physical);
        writetable(refined,fullfile(refinedDirectory,'reference.csv'));
    end
    fprintf('Native max step %.4g s: %d samples, %.6f s elapsed; three zero initial currents.\n', ...
        maxSteps(runIndex),height(physical),elapsed(runIndex));
end
convergence=refinementCheck(baseline,refined);
writeJSON(fullfile(referenceRoot,'reference_convergence.json'),convergence);
assert(convergence.passed,'Native 1ms/0.5ms refinement exceeds the frozen self-convergence limits.');
% Independent algebraic sign/ratio audit, using actual native quantities.
audit=struct('primary_kcl_max_abs_a',max(abs(baseline.i_source_to_transformer ...
    -baseline.i_magnetizing-baseline.i_load/variables.ratio)), ...
    'ideal_ratio_max_abs_v',max(abs(baseline.v_primary_core-variables.ratio*baseline.v_secondary_core)), ...
    'load_ohm_max_abs_a',max(abs(baseline.v_load/variables.r2-baseline.i_load)), ...
    'initial_inductor_current_a',initial);
writeJSON(fullfile(referenceRoot,'native_physics_audit.json'),audit);
metadata=struct('schema_version',1,'origin','Unmodified MathWorks five-network model; third pure electrical T group exported', ...
    'export_time_utc',char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd HH:mm:ss Z')), ...
    'source_url','https://www.mathworks.com/help/simscape/ug/comparison-of-mutual-inductor-and-ideal-transformer.html', ...
    'example_id','simscape/ComparisonOfMutualInductorAndIdealTransformerExample', ...
    'model_name',modelName,'model_sha256',sources(1).sha256,'source_files',sources, ...
    'export_script_sha256',sha256File([mfilename('fullpath') '.m']), ...
    'matlab_version',version,'required_products',{{'MATLAB','Simulink','Simscape'}}, ...
    'physical_parameter_source','Official MLX experiment, not SLX PostLoad fallback. Explicit case-sensitive SimulationInput bindings.', ...
    'workspace_variable_bindings',variables,'freeze_commit','0ec7239', ...
    'solver','ode15s','relative_tolerance',1e-9,'absolute_tolerance',1e-11,'local_solver','off', ...
    'max_step_s',maxSteps(1),'refined_max_step_s',maxSteps(2),'stop_time_s',8, ...
    'source',struct('before_v',0,'after_v',1,'step_s',2,'series_resistance_ohm',1), ...
    'load_resistance_ohm',1,'turns_ratio_primary_to_secondary',.2, ...
    'T_inductance_h',struct('primary_leakage',.01,'secondary_leakage',.25,'magnetizing',.1), ...
    'initial_inductor_currents_a',initial,'winding_resistance_ohm',0,'inductor_parallel_conductance_s',0, ...
    'magnetizing_branch_location','Core primary after l1; connected core primary to primary electrical reference.', ...
    'signal_mapping',struct('v_source','Controlled_Voltage_Source3.v', ...
        'v_primary_core','Subsystem_Reference2.Ideal_Transformer.v1', ...
        'v_secondary_core','Subsystem_Reference2.Ideal_Transformer.v2','v_load','Resistor5.v', ...
        'i_source_to_transformer','-Controlled_Voltage_Source3.i','i_load','Resistor5.i', ...
        'i_magnetizing','Subsystem_Reference2.Lm.i_L'), ...
    'current_directions','Source toward l1/core; ideal secondary toward l2/load; Lm core toward ground. Native ideal-transformer secondary input current is -i_load.', ...
    'voltage_reference','Primary and secondary negative winding terminals are explicitly connected to their original electrical references.', ...
    'event_guard_s',.001,'comparison_windows_s',[0,1.999;2.001,8], ...
    'normalization','Native timestamps and values preserved; last sample at duplicate times. No resampling, fitted time/phase shift or amplitude scaling.', ...
    'topology_changes','none','physical_parameter_changes','none relative to the official MLX experiment', ...
    'simulation_changes','ode15s1e-9/1e-11 max1ms and independent0.5ms refinement; explicit original variables; full logging.', ...
    'reference_self_convergence',convergence,'native_physics_audit',audit, ...
    'samples',height(baseline),'refined_samples',height(refined),'simulation_elapsed_seconds',elapsed, ...
    'scope','Linear zero-state step response of explicit T network. Does not certify physical DC transformer operation, saturation, hysteresis or existing example09 aggregate topology.', ...
    'redistribution','Original MathWorks model/script and generated data remain local; no redistribution permission asserted.');
writeJSON(fullfile(referenceRoot,'provenance.json'),metadata);
fprintf('Export complete: seven native signals, self-convergence passed, all five original networks ran.\n');
end

function physical=extractSignals(out)
% Paths/signs were checked from original physical connections and cached logs:
% i_source_to_transformer = l1.i_L, i_load = l2.i_L = original third yout.
physical=table(out.simlog.Controlled_Voltage_Source3.v.series.time, ...
    out.simlog.Controlled_Voltage_Source3.v.series.values('V'), ...
    out.simlog.Subsystem_Reference2.Ideal_Transformer.v1.series.values('V'), ...
    out.simlog.Subsystem_Reference2.Ideal_Transformer.v2.series.values('V'), ...
    out.simlog.Resistor5.v.series.values('V'), ...
    -out.simlog.Controlled_Voltage_Source3.i.series.values('A'), ...
    out.simlog.Resistor5.i.series.values('A'), ...
    out.simlog.Subsystem_Reference2.Lm.i_L.series.values('A'), ...
    'VariableNames',{'time','v_source','v_primary_core','v_secondary_core','v_load', ...
    'i_source_to_transformer','i_load','i_magnetizing'});
end

function physical=normalize(physical)
[~,lastIndex]=unique(physical.time,'last');
physical=physical(lastIndex,:); assert(all(diff(physical.time)>0));
end

function report=refinementCheck(baseline,refined)
windows=[0,1.999;2.001,8]; scales=[1,1,5,.2,1,.2,1];
limits=[.005,.005,.025,.001,.001,.0002,.001]/10;
columns=baseline.Properties.VariableNames(2:end);
report=struct('method','Absolute-time linear interpolation on native time union in both frozen windows; no shift or scaling', ...
    'baseline_max_step_s',.001,'refined_max_step_s',.0005,'passed',true);
for windowIndex=1:size(windows,1)
    first=windows(windowIndex,1); last=windows(windowIndex,2);
    time=unique([first;last;baseline.time(baseline.time>=first & baseline.time<=last); ...
        refined.time(refined.time>=first & refined.time<=last)]);
    result=struct('window_s',[first,last],'passed',true);
    for k=1:numel(columns)
        difference=interp1(baseline.time,baseline.(columns{k}),time,'linear') ...
            -interp1(refined.time,refined.(columns{k}),time,'linear');
        maximum=max(abs(difference));
        rmse=sqrt(trapz(time,difference.^2)/(last-first));
        passed=maximum<limits(k);
        result.signals.(columns{k})=struct('rmse',rmse,'nrmse',rmse/scales(k), ...
            'max_abs_difference',maximum,'scale',scales(k),'max_abs_limit',limits(k),'passed',passed);
        result.passed=result.passed && passed;
    end
    report.windows(windowIndex)=result;
    report.passed=report.passed && result.passed;
end
end

function sources=checkSources(modelDirectory,expected)
sources=struct('file',{},'path',{},'sha256',{});
for k=1:size(expected,1)
    file=fullfile(modelDirectory,expected{k,1}); checksum=sha256File(file);
    assert(strcmp(checksum,expected{k,2}),'Source bytes differ from the inspected official R2025a artifact.');
    sources(k)=struct('file',expected{k,1},'path',file,'sha256',checksum);
    [~,modelName,extension]=fileparts(file);
    if strcmp(extension,'.slx')
        assert(strcmpi(char(java.io.File(which([modelName '.slx'])).getCanonicalPath()), ...
            char(java.io.File(file).getCanonicalPath())),'A different same-name model resolves on MATLAB path.');
        if bdIsLoaded(modelName)
            assert(strcmpi(char(java.io.File(get_param(modelName,'FileName')).getCanonicalPath()), ...
                char(java.io.File(file).getCanonicalPath())),'A different same-name model is already loaded.');
            assert(strcmp(get_param(modelName,'Dirty'),'off'),'Loaded reference/support model has unsaved changes.');
        end
    end
end
end

function checksum=sha256File(fileName)
fid=fopen(fileName,'rb'); assert(fid>=0,'Cannot open source artifact for SHA-256.');
cleanup=onCleanup(@() fclose(fid)); %#ok<NASGU>
bytes=fread(fid,Inf,'*uint8'); digest=java.security.MessageDigest.getInstance('SHA-256');
digest.update(typecast(bytes,'int8'));
checksum=lower(reshape(dec2hex(typecast(digest.digest(),'uint8'),2).',1,[]));
end

function writeJSON(path,value)
fid=fopen(path,'w','n','UTF-8'); assert(fid>=0);
fprintf(fid,'%s\n',jsonencode(value,PrettyPrint=true)); fclose(fid);
end
