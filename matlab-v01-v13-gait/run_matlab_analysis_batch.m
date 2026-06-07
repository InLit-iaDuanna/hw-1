%% Batch Process All Python Exports
% Automatically generate MATLAB reports from all Python-exported data
%
% Usage:
%   cd('D:\Dunna\Documents\hw-1\matlab-v01-v13-gait')
%   run_matlab_analysis_batch
%
% Prerequisites:
%   1. Run sync_data.ps1 first to export Python data
%   2. Ensure python_exports/ directory exists with .mat files

thisDir = fileparts(mfilename('fullpath'));
pythonExportDir = fullfile(thisDir, 'python_exports');
outputRoot = fullfile(thisDir, 'out');

if ~exist(pythonExportDir, 'dir')
    error('Python exports directory not found: %s\nRun sync_data.ps1 first!', pythonExportDir);
end

% Version list
versions = {'v01', 'v02', 'v03', 'v04', 'v05', 'v06', 'v07', 'v08', 'v09', 'v10', 'v11', 'v12', 'v13'};

fprintf('========================================\n');
fprintf('MATLAB Report Generation from Python\n');
fprintf('========================================\n\n');

successCount = 0;
failCount = 0;
failedVersions = {};

for i = 1:numel(versions)
    versionId = versions{i};
    matFile = fullfile(pythonExportDir, versionId, sprintf('%s_python_export.mat', versionId));

    if ~isfile(matFile)
        fprintf('[%s] SKIP: No exported data found\n', versionId);
        continue;
    end

    try
        fprintf('[%s] Processing...\n', versionId);
        outputDir = fullfile(outputRoot, versionId);
        generate_matlab_report_from_python(versionId, matFile, outputDir);
        successCount = successCount + 1;
        fprintf('[%s] ✓ Success\n\n', versionId);
    catch ME
        failCount = failCount + 1;
        failedVersions{end+1} = versionId;
        fprintf('[%s] ✗ Failed: %s\n\n', versionId, ME.message);
    end
end

fprintf('========================================\n');
fprintf('Batch processing complete\n');
fprintf('========================================\n');
fprintf('Success: %d\n', successCount);
fprintf('Failed:  %d\n', failCount);

if ~isempty(failedVersions)
    fprintf('\nFailed versions: %s\n', strjoin(failedVersions, ', '));
end

fprintf('\nOutput directory: %s\n', outputRoot);
fprintf('========================================\n');
