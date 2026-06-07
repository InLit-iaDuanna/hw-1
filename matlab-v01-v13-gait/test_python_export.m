%% Quick Test: Load and Visualize Python Export
% Test script to verify Python → MATLAB data flow
%
% Usage:
%   cd('D:\Dunna\Documents\hw-1\matlab-v01-v13-gait')
%   test_python_export

clear; close all; clc;

thisDir = fileparts(mfilename('fullpath'));
matFile = fullfile(thisDir, 'python_exports', 'v10', 'v10_python_export.mat');

if ~isfile(matFile)
    error('Test file not found: %s\nRun: .\\sync_data.ps1 v10', matFile);
end

fprintf('========================================\n');
fprintf('Testing Python → MATLAB Data Flow\n');
fprintf('========================================\n\n');

% Test 1: Load data
fprintf('[Test 1] Loading Python export...\n');
try
    [T, metadata] = load_python_data(matFile);
    fprintf('✓ Success: Loaded %d rows × %d columns\n\n', height(T), width(T));
catch ME
    fprintf('✗ Failed: %s\n', ME.message);
    return;
end

% Test 2: Display metadata
fprintf('[Test 2] Metadata:\n');
fprintf('  Version: %s\n', metadata.version);
fprintf('  Title: %s\n', metadata.title);
fprintf('  Duration: %.2f s\n', metadata.duration_s);
fprintf('  Distance: %.2f m\n', metadata.forward_distance_m);
fprintf('  Left touchdowns: %d\n', metadata.left_touchdowns);
fprintf('  Right touchdowns: %d\n\n', metadata.right_touchdowns);

% Test 3: Quick visualization
fprintf('[Test 3] Generating quick visualization...\n');
figure('Name', 'Python Export Test', 'Position', [100 100 1200 600]);

subplot(2,2,1);
plot(T.time, T.hip_x, 'LineWidth', 1.5, 'Color', '#1c7ed6');
xlabel('time / s');
ylabel('hip x / m');
title('Hip Forward Trajectory');
grid on;

subplot(2,2,2);
stairs(T.time, T.left_contact, 'LineWidth', 1.3, 'Color', '#0b7285');
hold on;
stairs(T.time, -T.right_contact, 'LineWidth', 1.3, 'Color', '#c92a2a');
xlabel('time / s');
yticks([-1 0 1]);
yticklabels({'right', 'none', 'left'});
title('Contact Timing');
grid on;

subplot(2,2,3);
plot(T.time, rad2deg(T.left_hip), 'LineWidth', 1.2, 'Color', '#0b7285', 'DisplayName', 'left hip');
hold on;
plot(T.time, rad2deg(T.right_hip), 'LineWidth', 1.2, 'Color', '#c92a2a', 'DisplayName', 'right hip');
xlabel('time / s');
ylabel('angle / deg');
title('Hip Angles');
legend('Location', 'best');
grid on;

subplot(2,2,4);
plot(T.left_hip, T.left_hip_vel, 'LineWidth', 1.2, 'Color', '#0b7285', 'DisplayName', 'left');
hold on;
plot(T.right_hip, T.right_hip_vel, 'LineWidth', 1.2, 'Color', '#c92a2a', 'DisplayName', 'right');
xlabel('hip angle / rad');
ylabel('hip angular velocity / rad/s');
title('Phase Portrait');
legend('Location', 'best');
grid on;

sgtitle(sprintf('%s | %s', metadata.version, metadata.title), 'Interpreter', 'none');
fprintf('✓ Visualization displayed\n\n');

% Test 4: Generate full report
fprintf('[Test 4] Generating full report...\n');
try
    outputDir = fullfile(thisDir, 'out', 'v10');
    generate_matlab_report_from_python('v10', matFile, outputDir);
    fprintf('✓ Report generated successfully\n\n');
catch ME
    fprintf('✗ Failed: %s\n\n', ME.message);
end

fprintf('========================================\n');
fprintf('All tests completed!\n');
fprintf('========================================\n');
