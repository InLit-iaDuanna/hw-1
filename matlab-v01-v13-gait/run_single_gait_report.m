function result = run_single_gait_report(cfg)
%RUN_SINGLE_GAIT_REPORT Read one version dataset and export a MATLAB report.
thisDir = fileparts(mfilename('fullpath'));
outRoot = fullfile(thisDir, 'out');
outDir = fullfile(outRoot, cfg.id);
if ~exist(outDir, 'dir')
    mkdir(outDir);
end

if ~isfile(cfg.dataCsv)
    error('Data CSV not found: %s', cfg.dataCsv);
end

T = readtable(cfg.dataCsv, 'VariableNamingRule', 'preserve');
paramsText = "";
if isfield(cfg, 'paramsJson') && isfile(cfg.paramsJson)
    paramsText = string(fileread(cfg.paramsJson));
end

matPath = fullfile(outDir, cfg.id + "_data.mat");
tablePath = fullfile(outDir, cfg.id + "_data_table.csv");
reportPath = fullfile(outDir, cfg.id + "_report.png");
if isfile(matPath)
    delete(matPath);
end
save(matPath, 'T', 'cfg', 'paramsText', '-v7');
writetable(T, tablePath);

switch string(cfg.kind)
    case "energy"
        plot_energy_report(T, cfg, reportPath);
    case "atlas"
        plot_atlas_report(T, cfg, reportPath);
    otherwise
        plot_timeseries_report(T, cfg, reportPath);
end

result = struct();
result.version = string(cfg.id);
result.title = string(cfg.title);
result.kind = string(cfg.kind);
result.rows = height(T);
result.columns = width(T);
result.hasTime = hasVar(T, "time");
result.hasHipX = hasVar(T, "hip_x");
result.hasContacts = hasVar(T, "left_contact") && hasVar(T, "right_contact");
result.matFile = string(matPath);
result.reportFile = string(reportPath);

fprintf('  MAT:    %s\n', matPath);
fprintf('  CSV:    %s\n', tablePath);
fprintf('  Report: %s\n', reportPath);
end

function plot_timeseries_report(T, cfg, reportPath)
time = getTime(T);
names = string(T.Properties.VariableNames);

fig = makeFigure();
tiledlayout(fig, 2, 2, 'Padding', 'compact', 'TileSpacing', 'compact');

ax = nexttile;
hold on; grid on;
if hasVar(T, "hip_x")
    plot(time, getVar(T, "hip_x"), 'LineWidth', 1.6, 'DisplayName', 'hip x');
    ylabel('hip x / m');
else
    plotFallbackNumeric(T, time);
    ylabel('value');
end
xlabel('time / s');
title('Hip Forward Trajectory');
styleAxes(ax);

ax = nexttile;
hold on; grid on;
if hasVar(T, "left_contact") && hasVar(T, "right_contact")
    stairs(time, getVar(T, "left_contact"), 'LineWidth', 1.4, 'DisplayName', 'left foot');
    stairs(time, -getVar(T, "right_contact"), 'LineWidth', 1.4, 'DisplayName', 'right foot');
    yticks([-1 0 1]);
    yticklabels({'right', 'none', 'left'});
    legend('Location', 'best');
    title('Foot Contact Timing');
else
    plotFallbackNumeric(T, time);
    title('Key Variables');
end
xlabel('time / s');
styleAxes(ax);

ax = nexttile;
hold on; grid on;
angleVars = names(contains(names, "theta") | contains(names, "hip") | contains(names, "knee") | contains(names, "ankle"));
angleVars = angleVars(angleVars ~= "hip_x" & angleVars ~= "hip_z" & ~contains(angleVars, "_vel") & ~contains(angleVars, "_tau") & ~contains(angleVars, "clearance"));
plotSomeVars(T, time, angleVars, 5);
xlabel('time / s');
ylabel('angle / rad');
title('Joint Angles');
styleAxes(ax);

ax = nexttile;
hold on; grid on;
if plotPhasePortrait(T)
    title('Phase Portrait');
else
    plotFallbackNumeric(T, time);
    title('Data Preview');
    xlabel('time / s');
end
styleAxes(ax);

sgtitle(sprintf('%s | %s', cfg.id, cfg.title), 'Interpreter', 'none', 'FontName', 'Microsoft YaHei');
exportgraphics(fig, reportPath, 'Resolution', 180);
close(fig);
end

function plot_energy_report(T, cfg, reportPath)
fig = makeFigure();
tiledlayout(fig, 2, 2, 'Padding', 'compact', 'TileSpacing', 'compact');

labels = categorical(string(T.label));
labels = reordercats(labels, string(T.label));

ax = nexttile;
bar(labels, getOptionalVar(T, "CoT"));
title('Cost of Transport');
ylabel('CoT');
grid on;
styleAxes(ax);

ax = nexttile;
bar(labels, getOptionalVar(T, "active_input_energy_j"));
title('Active Input Energy');
ylabel('J');
grid on;
styleAxes(ax);

ax = nexttile;
bar(labels, getOptionalVar(T, "distance_m"));
title('Forward Distance');
ylabel('m');
grid on;
styleAxes(ax);

ax = nexttile;
hold on; grid on;
if hasVar(T, "alternating_touchdowns")
    bar(labels, getVar(T, "alternating_touchdowns"));
    ylabel('count');
else
    plotFallbackNumeric(T, (1:height(T))');
end
title('Touchdowns / Stability Indicator');
styleAxes(ax);

sgtitle(sprintf('%s | %s', cfg.id, cfg.title), 'Interpreter', 'none', 'FontName', 'Microsoft YaHei');
exportgraphics(fig, reportPath, 'Resolution', 180);
close(fig);
end

function plot_atlas_report(T, cfg, reportPath)
fig = makeFigure();
tiledlayout(fig, 2, 2, 'Padding', 'compact', 'TileSpacing', 'compact');

labels = categorical(string(T.slice));
labels = reordercats(labels, string(T.slice));

ax = nexttile;
bar(labels, parsePercentColumn(T, "success_rate"));
title('Success Rate by Parameter Slice');
ylabel('success rate');
ylim([0 1]);
grid on;
styleAxes(ax);

ax = nexttile;
bar(labels, getOptionalVar(T, "n_success"));
title('Successful Runs');
ylabel('count');
grid on;
styleAxes(ax);

ax = nexttile;
hold on; grid on;
plot(1:height(T), getOptionalVar(T, "cot_min"), '-o', 'LineWidth', 1.2, 'DisplayName', 'min CoT');
plot(1:height(T), getOptionalVar(T, "cot_median"), '-o', 'LineWidth', 1.2, 'DisplayName', 'median CoT');
xticks(1:height(T));
xticklabels(string(T.slice));
title('CoT Range');
ylabel('CoT');
legend('Location', 'best');
styleAxes(ax);

ax = nexttile;
axis off;
summaryText = sprintf(['Atlas summary\n' ...
    'Total slices: %d\n' ...
    'Best success rate: %.2f%%\n' ...
    'Best median CoT: %.3f\n' ...
    'Use V13 to define design tolerance before hardware.'], ...
    height(T), max(parsePercentColumn(T, "success_rate")) * 100, min(getOptionalVar(T, "cot_median")));
text(0.05, 0.88, summaryText, 'Units', 'normalized', 'FontSize', 14, 'FontName', 'Microsoft YaHei', 'VerticalAlignment', 'top');

sgtitle(sprintf('%s | %s', cfg.id, cfg.title), 'Interpreter', 'none', 'FontName', 'Microsoft YaHei');
exportgraphics(fig, reportPath, 'Resolution', 180);
close(fig);
end

function fig = makeFigure()
fig = figure('Color', 'w', 'Position', [80, 80, 1500, 980], 'Visible', 'off');
set(fig, 'DefaultAxesFontName', 'Microsoft YaHei');
end

function styleAxes(ax)
set(ax, ...
    'Color', 'w', ...
    'XColor', [0.1 0.1 0.1], ...
    'YColor', [0.1 0.1 0.1], ...
    'GridColor', [0.75 0.75 0.75], ...
    'MinorGridColor', [0.86 0.86 0.86], ...
    'FontName', 'Microsoft YaHei', ...
    'FontSize', 11, ...
    'LineWidth', 0.8);
end

function tf = hasVar(T, name)
tf = ismember(char(name), T.Properties.VariableNames);
end

function x = getVar(T, name)
x = T.(char(name));
end

function x = getOptionalVar(T, name)
if hasVar(T, name)
    x = T.(char(name));
else
    x = nan(height(T), 1);
end
end

function values = parsePercentColumn(T, name)
raw = T.(char(name));
if isnumeric(raw)
    values = raw;
    if any(values > 1, 'all')
        values = values / 100;
    end
else
    values = str2double(erase(string(raw), "%")) / 100;
end
values(~isfinite(values)) = 0;
end

function time = getTime(T)
if hasVar(T, "time")
    time = getVar(T, "time");
else
    time = (0:height(T)-1)';
end
end

function plotSomeVars(T, time, vars, maxCount)
count = 0;
for i = 1:numel(vars)
    v = char(vars(i));
    if ismember(v, T.Properties.VariableNames) && isnumeric(T.(v))
        plot(time, T.(v), 'LineWidth', 1.2, 'DisplayName', friendlyVarName(v));
        count = count + 1;
    end
    if count >= maxCount
        break;
    end
end
if count == 0
    plotFallbackNumeric(T, time);
else
    legend('Location', 'best', 'Interpreter', 'none');
end
end

function plotFallbackNumeric(T, time)
names = T.Properties.VariableNames;
count = 0;
for i = 1:numel(names)
    v = names{i};
    if isnumeric(T.(v))
        plot(time, T.(v), 'LineWidth', 1.1, 'DisplayName', friendlyVarName(v));
        count = count + 1;
    end
    if count >= 3
        break;
    end
end
if count > 0
    legend('Location', 'best', 'Interpreter', 'none');
end
end

function ok = plotPhasePortrait(T)
ok = true;
if hasVar(T, "left_hip") && hasVar(T, "left_hip_vel")
    plot(getVar(T, "left_hip"), getVar(T, "left_hip_vel"), 'LineWidth', 1.3, 'DisplayName', 'left hip');
    if hasVar(T, "right_hip") && hasVar(T, "right_hip_vel")
        plot(getVar(T, "right_hip"), getVar(T, "right_hip_vel"), 'LineWidth', 1.3, 'DisplayName', 'right hip');
    end
    xlabel('hip angle / rad');
    ylabel('hip angular velocity / rad/s');
    legend('Location', 'best');
elseif hasVar(T, "theta_stance") && hasVar(T, "omega_stance")
    plot(getVar(T, "theta_stance"), getVar(T, "omega_stance"), 'LineWidth', 1.3, 'DisplayName', 'stance');
    xlabel('stance angle / rad');
    ylabel('stance angular velocity / rad/s');
elseif hasVar(T, "theta") && hasVar(T, "theta_dot")
    plot(getVar(T, "theta"), getVar(T, "theta_dot"), 'LineWidth', 1.3);
    xlabel('phase angle / rad');
    ylabel('angular velocity / rad/s');
elseif hasVar(T, "left_angle") && hasVar(T, "left_omega")
    plot(getVar(T, "left_angle"), getVar(T, "left_omega"), 'LineWidth', 1.3);
    xlabel('left leg angle / rad');
    ylabel('left leg angular velocity / rad/s');
else
    ok = false;
end
end

function label = friendlyVarName(v)
switch string(v)
    case "left_hip"
        label = 'left hip';
    case "left_knee"
        label = 'left knee';
    case "left_ankle"
        label = 'left ankle';
    case "right_hip"
        label = 'right hip';
    case "right_knee"
        label = 'right knee';
    case "right_ankle"
        label = 'right ankle';
    otherwise
        label = v;
end
end
