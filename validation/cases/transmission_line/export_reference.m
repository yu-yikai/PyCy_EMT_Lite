function export_reference(repositoryRoot)
%EXPORT_REFERENCE Run the official finite 50-T RLCG ladder at two tolerances.
% Requires MATLAB, Simulink and Simscape. This is not a Bergeron reference.
%   addpath('validation/cases/transmission_line'); export_reference(pwd)
% Only solver/logging overrides are applied through SimulationInput. The
% official source, 50 sections, zero initial state and 50-ohm load are kept.
if nargin==0
    repositoryRoot=fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));
end
referenceRoot=fullfile(repositoryRoot,'local_reference','transmission_line');
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
modelName='TransmissionLine';
modelFile=fullfile(modelDirectory,[modelName '.slx']);
if ~isfile(modelFile)
    openExample('simscape/TransmissionLineExample','workDir',modelDirectory);
end
addpath(modelDirectory);
diary(fullfile(referenceRoot,'export_reference.log'));
diaryCleanup=onCleanup(@() diary('off')); %#ok<NASGU>
modelSHA256=sha256File(modelFile);
assert(strcmp(modelSHA256,'844a8501b9e25a4fe881ecfc7ea14d7d1b0e9bdba38986572ba1a910551d86fe'), ...
    'Model differs from the inspected R2025a reference; inspect before exporting.');
libraryFile=which('TransmissionLine_lib');
sectionSource=fullfile(matlabroot,'toolbox','physmod','simscape', ...
    'supporting_files','example_libraries','+TransmissionLine','t_section.ssc');
librarySHA256=sha256File(libraryFile);
sectionSHA256=sha256File(sectionSource);
assert(strcmp(librarySHA256,'c9de97cb0b86024c03fe16ec4f1ba979be896b4a0ccda8fac066fdb84c899444'));
assert(strcmp(sectionSHA256,'e6bae69228f1b4c2d568097ca973ff2b13e8ab2cccdb07cfbaeae7b22492ae73'));
checkLoadedLibrary(libraryFile,librarySHA256);
if ~bdIsLoaded(modelName), open_system(modelFile); end
assert(strcmpi(char(java.io.File(get_param(modelName,'FileName')).getCanonicalPath()), ...
    char(java.io.File(modelFile).getCanonicalPath())));
assert(strcmp(get_param(modelName,'Dirty'),'off'),'Reference model has unsaved changes.');
checkLoadedLibrary(libraryFile,librarySHA256);
fprintf('MATLAB %s\nModel SHA256 %s\n',version,modelSHA256);
% Explicitly bind the seven original PreLoadFcn defaults. Changing a base
% workspace variable does not mark an already loaded model dirty, so neither
% its file checksum nor Dirty alone protects the electrical parameter set.
% These bindings preserve, rather than change, the inspected physical protocol.
modelVariables=struct('length',5,'nSegments',50,'segmentLength',.1, ...
    'R',.0067,'C',100e-12,'Z',50,'G',5e-6);

% The current definition is frozen separately from PyCy, before viewing any
% candidate data. Refinement goals are 1% of the candidate absolute limits:
% <=0.5mV / 10uA, and NRMSE<=3e-5 on the 10V / .2A engineering bases.
maxSteps=[10e-12,5e-12];
elapsed=zeros(1,2);
initialCurrent=zeros(1,2); initialVoltage=zeros(1,2);
for runIndex=1:2
    in=Simulink.SimulationInput(modelName);
    variableNames=fieldnames(modelVariables);
    for variableIndex=1:numel(variableNames)
        name=variableNames{variableIndex};
        in=in.setVariable(name,modelVariables.(name));
    end
    in=in.setModelParameter('Solver','ode15s','RelTol','1e-8','AbsTol','1e-10', ...
        'MaxStep',sprintf('%.17g',maxSteps(runIndex)),'StopTime','50e-9', ...
        'SimscapeLogType','all','SimscapeLogName','simlog','SimscapeLogLimitData','off');
    timer=tic;
    out=sim(in);
    elapsed(runIndex)=toc(timer);
    [initialCurrent(runIndex),initialVoltage(runIndex)]=inspectInitialState(out);
    assert(initialCurrent(runIndex)==0 && initialVoltage(runIndex)==0);
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
    fprintf('Reference max step %.3g s: %d samples, %.6f s elapsed, zero initial state.\n', ...
        maxSteps(runIndex),height(physical),elapsed(runIndex));
end
convergence=refinementCheck(baseline,refined);
writeJSON(fullfile(referenceRoot,'reference_convergence.json'),convergence);
assert(convergence.passed,'Reference 10ps/5ps refinement exceeds the declared self-convergence limits.');

% Original PlotV source is preserved. Its S2.T_5.p2 output is boundary15,
% although the legend says Segment25. The root is S1->S2->S3->S4->S5 and each
% subsystem contains 10 serial T sections, so boundary25 is S3.T_5.p2.
plotSource=fullfile(modelDirectory,'TransmissionLinePlotV.m');
copyfile(plotSource,fullfile(rawDirectory,'TransmissionLinePlotV_original.m'));
officialLabels=table(baseline.time,baseline.v_source,baseline.v_boundary_15,baseline.v_load, ...
    'VariableNames',{'time','official_Source','official_Segment25_actual15','official_Load'});
writetable(officialLabels,fullfile(rawDirectory,'official_plot_label_evidence.csv'));
metadata=struct('schema_version',1,'origin','MathWorks official model with tighter solver overrides; unmodified 50-T circuit', ...
    'export_time_utc',char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd HH:mm:ss Z')), ...
    'source_url','https://www.mathworks.com/help/simscape/ug/transmission-line.html', ...
    'example_id','simscape/TransmissionLineExample','model_name',modelName, ...
    'matlab_version',version,'required_products',{{'MATLAB','Simulink','Simscape'}}, ...
    'model_sha256',modelSHA256,'section_source_sha256',sectionSHA256,'section_library_sha256',librarySHA256, ...
    'section_source_file',sectionSource,'section_library_file',libraryFile, ...
    'original_workspace_variable_bindings',modelVariables, ...
    'solver','ode15s','relative_tolerance',1e-8,'absolute_tolerance',1e-10,'local_solver','off', ...
    'max_step_s',maxSteps(1),'refined_max_step_s',maxSteps(2),'stop_time_s',50e-9, ...
    'source',struct('waveform','10*sin(2*pi*200e6*t)','amplitude_v',10,'frequency_hz',200e6, ...
        'phase_rad',0,'series_resistance_ohm',0), ...
    'load_resistance_ohm',50,'segments',50,'total_length_m',5,'segment_length_m',.1, ...
    'per_m',struct('R_ohm',.0067,'L_h',250e-9,'G_s',5e-6,'C_f',100e-12), ...
    'each_T',struct('half_arm_R_ohm',.000335,'half_arm_L_h',12.5e-9, ...
        'shunt_R_ohm',2e6,'shunt_C_f',10e-12,'capacitor_ESR_ohm',0), ...
    'initial_state',struct('inductors',100,'capacitors',50,'current_max_abs_a',max(initialCurrent), ...
        'voltage_max_abs_v',max(initialVoltage),'DoDC','off'), ...
    'signal_mapping',struct('v_source','AC_Voltage.v','v_boundary_15','S2.T_5.p2.v', ...
        'v_boundary_25','S3.T_5.p2.v','v_load','Load.v', ...
        'i_source_to_line','-AC_Voltage.i','i_load','Load.i'), ...
    'voltage_reference','All voltages relative to the common electrical reference n=0.', ...
    'current_direction','Source to first line section; output line to 50-ohm load.', ...
    'plot_label_issue','Official S2.T_5.p2.v is labelled Segment25 but is boundary15; true boundary25 is S3.T_5.p2.v. Original script and mislabelled trace preserved.', ...
    'plot_source_sha256',sha256File(plotSource), ...
    'normalization','Native timestamps/values retained, last at duplicate times; no fitted shifts, scaling or resampling.', ...
    'topology_changes','none','electrical_parameter_changes','none','solver_changes','ode15s, RelTol1e-8/AbsTol1e-10, MaxStep10ps and independent5ps refinement', ...
    'reference_self_convergence',convergence,'samples',height(baseline),'refined_samples',height(refined), ...
    'simulation_elapsed_seconds',elapsed,'scope','Finite lumped 50-T RLCG ladder, not Bergeron or distributed-delay validation.', ...
    'redistribution','Original MathWorks model, source and data remain local; no redistribution permission asserted.');
writeJSON(fullfile(referenceRoot,'provenance.json'),metadata);
fprintf('Export completed: reference self-convergence passed, %d baseline samples.\n',height(baseline));
end

function physical=extractSignals(out)
physical=table(out.simlog.AC_Voltage.v.series.time, ...
    out.simlog.AC_Voltage.v.series.values('V'), ...
    out.simlog.S2.T_5.p2.v.series.values('V'), ...
    out.simlog.S3.T_5.p2.v.series.values('V'), ...
    out.simlog.Load.v.series.values('V'), ...
    -out.simlog.AC_Voltage.i.series.values('A'), ...
    out.simlog.Load.i.series.values('A'), ...
    'VariableNames',{'time','v_source','v_boundary_15','v_boundary_25','v_load','i_source_to_line','i_load'});
end

function physical=normalize(physical)
[~,lastIndex]=unique(physical.time,'last');
physical=physical(lastIndex,:);
assert(all(diff(physical.time)>0));
end

function [maxCurrent,maxVoltage]=inspectInitialState(out)
maxCurrent=0; maxVoltage=0;
for group=1:5
    for section=1:10
        groupName=['S' num2str(group)]; sectionName=['T_' num2str(section)];
        values=out.simlog.(groupName).(sectionName).l1.i.series.values('A');
        maxCurrent=max(maxCurrent,abs(values(1)));
        values=out.simlog.(groupName).(sectionName).l2.i.series.values('A');
        maxCurrent=max(maxCurrent,abs(values(1)));
        values=out.simlog.(groupName).(sectionName).c.v.series.values('V');
        maxVoltage=max(maxVoltage,abs(values(1)));
    end
end
end

function report=refinementCheck(baseline,refined)
time=unique([baseline.time;refined.time]);
columns=baseline.Properties.VariableNames(2:end);
scales=[10,10,10,10,.2,.2]; limits=[.0005,.0005,.0005,.0005,1e-5,1e-5];
report=struct('method','Absolute-time linear interpolation on union of native timestamps, no shift or amplitude fitting', ...
    'window_s',[0,50e-9],'baseline_max_step_s',10e-12,'refined_max_step_s',5e-12,'passed',true);
for k=1:numel(columns)
    difference=interp1(baseline.time,baseline.(columns{k}),time,'linear') ...
        -interp1(refined.time,refined.(columns{k}),time,'linear');
    rmse=sqrt(trapz(time,difference.^2)/(time(end)-time(1)));
    maximum=max(abs(difference));
    passed=rmse/scales(k)<=3e-5 && maximum<=limits(k);
    report.signals.(columns{k})=struct('rmse',rmse,'nrmse',rmse/scales(k),'max_abs_difference',maximum, ...
        'scale',scales(k),'max_nrmse',3e-5,'max_abs_limit',limits(k),'passed',passed);
    report.passed=report.passed && passed;
end
end

function checksum=sha256File(fileName)
fid=fopen(fileName,'rb'); assert(fid>=0,'Cannot open source file for SHA-256.');
cleanup=onCleanup(@() fclose(fid)); %#ok<NASGU>
bytes=fread(fid,Inf,'*uint8'); digest=java.security.MessageDigest.getInstance('SHA-256');
digest.update(typecast(bytes,'int8'));
checksum=lower(reshape(dec2hex(typecast(digest.digest(),'uint8'),2).',1,[]));
end

function writeJSON(path,value)
fid=fopen(path,'w','n','UTF-8'); assert(fid>=0);
fprintf(fid,'%s\n',jsonencode(value,PrettyPrint=true)); fclose(fid);
end

function checkLoadedLibrary(libraryFile,expectedSHA256)
if bdIsLoaded('TransmissionLine_lib')
    loadedLibraryFile=get_param('TransmissionLine_lib','FileName');
    assert(strcmpi(char(java.io.File(loadedLibraryFile).getCanonicalPath()), ...
        char(java.io.File(libraryFile).getCanonicalPath())), ...
        'A different same-name TransmissionLine_lib is loaded.');
    assert(strcmp(get_param('TransmissionLine_lib','Dirty'),'off'), ...
        'Loaded TransmissionLine_lib has unsaved changes.');
    assert(strcmp(sha256File(loadedLibraryFile),expectedSHA256), ...
        'Loaded TransmissionLine_lib differs from the inspected reference.');
end
end
