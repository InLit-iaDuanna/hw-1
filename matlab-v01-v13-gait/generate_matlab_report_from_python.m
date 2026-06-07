function generate_matlab_report_from_python(versionId, matFilePath, outputDir)
%GENERATE_MATLAB_REPORT_FROM_PYTHON Generate report from Python-exported data.
%
%   generate_matlab_report_from_python(versionId, matFilePath, outputDir)
%
%   Inputs:
%       versionId   - Version identifier (e.g., 'v10')
%       matFilePath - Path to Python-exported .mat file
%       outputDir   - Directory to save report PNG
%
%   Example:
%       generate_matlab_report_from_python('v10', ...
%           'python_exports/v10/v10_python_export.mat', ...
%           'out/v10');

    if nargin < 3
        outputDir = fullfile('out', versionId);
    end

    if ~exist(outputDir, 'dir')
        mkdir(outputDir);
    end

    % Load data using the loader function
    [T, metadata] = load_python_data(matFilePath);

    % Determine report type based on available columns
    hasTimeSeries = ismember('time', T.Properties.VariableNames);
    hasEnergy = ismember('CoT', T.Properties.VariableNames);
    hasAtlas = ismember('slice', T.Properties.VariableNames);

    reportPath = fullfile(outputDir, sprintf('%s_python_report.png', versionId));

    if hasAtlas
        plot_atlas_report_from_python(T, metadata, reportPath);
    elseif hasEnergy
        plot_energy_report_from_python(T, metadata, reportPath);
    elseif hasTimeSeries
        plot_timeseries_report_from_python(T, metadata, reportPath);
    else
        error('Unable to determine report type from data columns');
    end

    fprintf('Report saved: %s\n', reportPath);
end

function plot_timeseries_report_from_python(T, metadata, reportPath)
    time = get_time_vector(T);
    names = string(T.Properties.VariableNames);

    fig = make_figure();
    tiledlayout(fig, 2, 2, 'Padding', 'compact', 'TileSpacing', 'compact');

    % Panel 1: Hip trajectory
    ax = nexttile;
    hold on; grid on;
    if has_var(T, "hip_x")
        plot(time, T.hip_x, 'LineWidth', 1.6, 'Color', '#1c7ed6', 'DisplayName', 'hip x');
        ylabel('hip x / m');
        if isfield(metadata, 'forward_distance_m')
            text(0.03, 0.92, sprintf('Forward: %.2f m', metadata.forward_distance_m), ...
                'Units', 'normalized', 'VerticalAlignment', 'top', 'FontSize', 10, ...
                'BackgroundColor', [1 1 1 0.8]);
        end
    else
        plot_fallback_numeric(T, time);
        ylabel('value');
    end
    xlabel('time / s');
    title('Hip Forward Trajectory');
    style_axes(ax);

    % Panel 2: Contact timing
    ax = nexttile;
    hold on; grid on;
    if has_var(T, "left_contact") && has_var(T, "right_contact")
        stairs(time, T.left_contact, 'LineWidth', 1.4, 'Color', '#0b7285', 'DisplayName', 'left foot');
        stairs(time, -T.right_contact, 'LineWidth', 1.4, 'Color', '#c92a2a', 'DisplayName', 'right foot');
        yticks([-1 0 1]);
        yticklabels({'right', 'none', 'left'});
        legend('Location', 'best');
        title('Foot Contact Timing');
        if isfield(metadata, 'left_touchdowns') && isfield(metadata, 'right_touchdowns')
            text(0.03, 0.92, sprintf('L: %d / R: %d', metadata.left_touchdowns, metadata.right_touchdowns), ...
                'Units', 'normalized', 'VerticalAlignment', 'top', 'FontSize', 10, ...
                'BackgroundColor', [1 1 1 0.8]);
        end
    else
        plot_fallback_numeric(T, time);
        title('Key Variables');
    end
    xlabel('time / s');
    style_axes(ax);

    % Panel 3: Joint angles
    ax = nexttile;
    hold on; grid on;
    angle_vars = names(contains(names, "hip") | contains(names, "knee") | contains(names, "ankle"));
    angle_vars = angle_vars(angle_vars ~= "hip_x" & angle_vars ~= "hip_z" & ...
        ~contains(angle_vars, "_vel") & ~contains(angle_vars, "_tau"));
    plot_some_vars(T, time, angle_vars, 5);
    xlabel('time / s');
    ylabel('angle / rad');
    title('Joint Angles');
    style_axes(ax);

    % Panel 4: Phase portrait
    ax = nexttile;
    hold on; grid on;
    if plot_phase_portrait(T)
        title('Phase Portrait');
    else
        plot_fallback_numeric(T, time);
        title('Data Preview');
        xlabel('time / s');
    end
    style_axes(ax);

    titleText = sprintf('%s | %s (Python Export)', metadata.version, metadata.title);
    sgtitle(titleText, 'Interpreter', 'none', 'FontName', 'Microsoft YaHei');
    exportgraphics(fig, reportPath, 'Resolution', 180);
    close(fig);
end

function plot_energy_report_from_python(T, metadata, reportPath)
    fig = make_figure();
    tiledlayout(fig, 2, 2, 'Padding', 'compact', 'TileSpacing', 'compact');

    labels = categorical(string(T.label));
    labels = reordercats(labels, string(T.label));

    ax = nexttile;
    bar(labels, get_optional_var(T, "CoT"));
    title('Cost of Transport');
    ylabel('CoT');
    grid on;
    style_axes(ax);

    ax = nexttile;
    bar(labels, get_optional_var(T, "active_input_energy_j"));
    title('Active Input Energy');
    ylabel('J');
    grid on;
    style_axes(ax);

    ax = nexttile;
    bar(labels, get_optional_var(T, "distance_m"));
    title('Forward Distance');
    ylabel('m');
    grid on;
    style_axes(ax);

    ax = nexttile;
    bar(labels, get_optional_var(T, "alternating_touchdowns"));
    title('Touchdowns');
    ylabel('count');
    grid on;
    style_axes(ax);

    titleText = sprintf('%s | %s (Python Export)', metadata.version, metadata.title);
    sgtitle(titleText, 'Interpreter', 'none', 'FontName', 'Microsoft YaHei');
    exportgraphics(fig, reportPath, 'Resolution', 180);
    close(fig);
end

function plot_atlas_report_from_python(T, metadata, reportPath)
    fig = make_figure();
    tiledlayout(fig, 2, 2, 'Padding', 'compact', 'TileSpacing', 'compact');

    labels = categorical(string(T.slice));
    labels = reordercats(labels, string(T.slice));

    ax = nexttile;
    bar(labels, parse_percent_column(T, "success_rate"));
    title('Success Rate by Parameter Slice');
    ylabel('success rate');
    ylim([0 1]);
    grid on;
    style_axes(ax);

    ax = nexttile;
    bar(labels, get_optional_var(T, "n_success"));
    title('Successful Runs');
    ylabel('count');
    grid on;
    style_axes(ax);

    ax = nexttile;
    hold on; grid on;
    plot(1:height(T), get_optional_var(T, "cot_min"), '-o', 'LineWidth', 1.2, 'DisplayName', 'min CoT');
    plot(1:height(T), get_optional_var(T, "cot_median"), '-o', 'LineWidth', 1.2, 'DisplayName', 'median CoT');
    xticks(1:height(T));
    xticklabels(string(T.slice));
    title('CoT Range');
    ylabel('CoT');
    legend('Location', 'best');
    style_axes(ax);

    ax = nexttile;
    axis off;
    summary_text = sprintf(['Python Export Summary\n' ...
        'Total slices: %d\n' ...
        'Best success: %.1f%%\n' ...
        'Best CoT: %.3f'], ...
        height(T), max(parse_percent_column(T, "success_rate")) * 100, ...
        min(get_optional_var(T, "cot_median")));
    text(0.05, 0.88, summary_text, 'Units', 'normalized', 'FontSize', 14, ...
        'FontName', 'Microsoft YaHei', 'VerticalAlignment', 'top');

    titleText = sprintf('%s | %s (Python Export)', metadata.version, metadata.title);
    sgtitle(titleText, 'Interpreter', 'none', 'FontName', 'Microsoft YaHei');
    exportgraphics(fig, reportPath, 'Resolution', 180);
    close(fig);
end

% Helper functions
function fig = make_figure()
    fig = figure('Color', 'w', 'Position', [80, 80, 1500, 980], 'Visible', 'off');
    set(fig, 'DefaultAxesFontName', 'Microsoft YaHei');
end

function style_axes(ax)
    set(ax, 'Color', 'w', 'XColor', [0.1 0.1 0.1], 'YColor', [0.1 0.1 0.1], ...
        'GridColor', [0.75 0.75 0.75], 'FontName', 'Microsoft YaHei', ...
        'FontSize', 11, 'LineWidth', 0.8);
end

function tf = has_var(T, name)
    tf = ismember(char(name), T.Properties.VariableNames);
end

function x = get_optional_var(T, name)
    if has_var(T, name)
        x = T.(char(name));
    else
        x = nan(height(T), 1);
    end
end

function values = parse_percent_column(T, name)
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

function time = get_time_vector(T)
    if has_var(T, "time")
        time = T.time;
    else
        time = (0:height(T)-1)';
    end
end

function plot_some_vars(T, time, vars, max_count)
    count = 0;
    colors = ['#1c7ed6'; '#0b7285'; '#c92a2a'; '#2f9e44'; '#f08c00'];
    for i = 1:numel(vars)
        v = char(vars(i));
        if has_var(T, v) && isnumeric(T.(v))
            color_idx = mod(count, size(colors, 1)) + 1;
            plot(time, T.(v), 'LineWidth', 1.2, 'DisplayName', v, ...
                'Color', colors(color_idx, :));
            count = count + 1;
        end
        if count >= max_count
            break;
        end
    end
    if count > 0
        legend('Location', 'best', 'Interpreter', 'none');
    end
end

function plot_fallback_numeric(T, time)
    names = T.Properties.VariableNames;
    count = 0;
    for i = 1:min(3, numel(names))
        v = names{i};
        if isnumeric(T.(v))
            plot(time, T.(v), 'LineWidth', 1.1, 'DisplayName', v);
            count = count + 1;
        end
    end
    if count > 0
        legend('Location', 'best', 'Interpreter', 'none');
    end
end

function ok = plot_phase_portrait(T)
    ok = true;
    if has_var(T, "left_hip") && has_var(T, "left_hip_vel")
        plot(T.left_hip, T.left_hip_vel, 'LineWidth', 1.3, 'Color', '#0b7285', 'DisplayName', 'left hip');
        if has_var(T, "right_hip") && has_var(T, "right_hip_vel")
            plot(T.right_hip, T.right_hip_vel, 'LineWidth', 1.3, 'Color', '#c92a2a', 'DisplayName', 'right hip');
        end
        xlabel('hip angle / rad');
        ylabel('hip angular velocity / rad/s');
        legend('Location', 'best');
    elseif has_var(T, "theta") && has_var(T, "theta_dot")
        plot(T.theta, T.theta_dot, 'LineWidth', 1.3);
        xlabel('angle / rad');
        ylabel('angular velocity / rad/s');
    else
        ok = false;
    end
end
