function [T, metadata] = load_python_data(matFilePath)
%LOAD_PYTHON_DATA Load Python-exported .mat file and convert to MATLAB table.
%
%   [T, metadata] = load_python_data(matFilePath)
%
%   Inputs:
%       matFilePath - Path to .mat file exported by python_to_matlab_exporter.py
%
%   Outputs:
%       T        - MATLAB table with time-series data
%       metadata - Struct with version info and parameters
%
%   Example:
%       [T, meta] = load_python_data('python_exports/v10/v10_python_export.mat');
%       plot(T.time, T.hip_x);
%       disp(meta.params);

    if ~isfile(matFilePath)
        error('MATLAB:load_python_data:FileNotFound', ...
            'File not found: %s', matFilePath);
    end

    % Load the .mat file
    raw = load(matFilePath);

    % Extract metadata
    metadata = struct();
    if isfield(raw, 'version')
        metadata.version = string(raw.version);
    end
    if isfield(raw, 'title')
        metadata.title = string(raw.title);
    end
    if isfield(raw, 'params')
        metadata.params = raw.params;
    end
    if isfield(raw, 'duration_s')
        metadata.duration_s = raw.duration_s;
    end
    if isfield(raw, 'forward_distance_m')
        metadata.forward_distance_m = raw.forward_distance_m;
    end
    if isfield(raw, 'left_touchdowns')
        metadata.left_touchdowns = raw.left_touchdowns;
    end
    if isfield(raw, 'right_touchdowns')
        metadata.right_touchdowns = raw.right_touchdowns;
    end

    % Extract data structure
    if ~isfield(raw, 'data')
        error('MATLAB:load_python_data:InvalidFormat', ...
            'Expected field "data" not found in .mat file');
    end

    dataStruct = raw.data;
    fieldNames = fieldnames(dataStruct);

    % Convert to table
    T = struct();
    for i = 1:numel(fieldNames)
        fieldName = fieldNames{i};
        fieldValue = dataStruct.(fieldName);

        % Ensure column vector
        if isnumeric(fieldValue) || islogical(fieldValue)
            if isrow(fieldValue)
                fieldValue = fieldValue';
            end
            T.(fieldName) = fieldValue;
        elseif iscell(fieldValue) || isstring(fieldValue)
            % Handle string/categorical columns
            T.(fieldName) = string(fieldValue);
            if isrow(T.(fieldName))
                T.(fieldName) = T.(fieldName)';
            end
        end
    end

    % Convert struct to table
    T = struct2table(T, 'AsArray', true);

    fprintf('Loaded %s: %d rows × %d columns\n', ...
        metadata.version, height(T), width(T));
end
