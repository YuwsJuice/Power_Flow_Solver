function power_system_ui 
    minWidth  = 650;
    minHeight = 450;

    fig = figure( ...
        'Name',        'Cirnos Perfect Power Flow Solver', ...
        'Position',    [100 100 1200 700], ...
        'NumberTitle', 'off', ...
        'MenuBar',     'none', ...
        'Resize',      'on', ...
        'Color',       [1 1 1], ...
        'DeleteFcn',   @(~,~) cleanupTimer() ...
    );
    fig.ResizeFcn = @(src,~) enforceMinSize(src, minWidth, minHeight);

    bottomPanel = uipanel(fig, ...
        'Units',           'normalized', ...
        'Position',        [0, 0, 1, 0.10], ...
        'BackgroundColor', [0.95 0.95 0.95], ...
        'BorderType',      'none' ...
    );

    % Use a single baseline and height for all text/edit/popup/button
    ctrlY = 0.10;   % 10% up from bottom of panel
    ctrlH = 0.80;   % 80% of panel height

    % 1) "Tolerance:" label

    uicontrol(bottomPanel, ...
        'Style',              'text', ...
        'String',             'Tolerance:', ...
        'FontSize',           10, ...
        'HorizontalAlignment','right', ...
        'Units',              'normalized', ...
        'Position',           [0.02, ctrlY, 0.12, ctrlH], ...
        'BackgroundColor',    [0.95 0.95 0.95] ...
    );

    tolEdit = uicontrol(bottomPanel, ...
        'Style',    'edit', ...
        'String',   '1e-10', ...
        'FontSize', 10, ...
        'Units',    'normalized', ...
        'Position', [0.15, 0.65, 0.05 0.30] ...
    );

    uicontrol(bottomPanel, ...
        'Style',              'text', ...
        'String',             'Max Iter:', ...
        'FontSize',           10, ...
        'HorizontalAlignment','right', ...
        'Units',              'normalized', ...
        'Position',           [0.26, ctrlY, 0.12, ctrlH], ...
        'BackgroundColor',    [0.95 0.95 0.95] ...
    );

    % 4) Max Iter edit‐box
    maxIterEdit = uicontrol(bottomPanel, ...
        'Style',         'edit', ...
        'String',        '100', ...
        'FontSize',      10, ...
        'Units',         'normalized', ...
        'Position',      [0.4 0.65, 0.05 0.30] ...
    );

    % 5) "Solver:" label
    uicontrol(bottomPanel, ...
        'Style',              'text', ...
        'String',             'Solver:', ...
        'FontSize',           10, ...
        'HorizontalAlignment','right', ...
        'Units',              'normalized', ...
        'Position',           [0.50, ctrlY, 0.08, ctrlH], ...
        'BackgroundColor',    [0.95 0.95 0.95] ...
    );

    solverPopup = uicontrol(bottomPanel, ...
        'Style',    'popupmenu', ...
        'String',   {'NR','GS'}, ...
        'FontSize', 10, ...
        'Units',    'normalized', ...
        'Position', [0.59, 0.65, 0.07 0.30] ...
    );

    iterText = uicontrol(bottomPanel, ...
        'Style',             'text', ...
        'String',            'Iterations: N/A', ...
        'FontSize',          10, ...
        'HorizontalAlignment','left', ...
        'Units',             'normalized', ...
        'Position',          [0.74, ctrlY, 0.16, ctrlH], ...
        'BackgroundColor',   [0.95 0.95 0.95] ...
    );

    runBtn = uicontrol(bottomPanel, ...
        'Style',       'pushbutton', ...
        'String',      'RUN', ...
        'FontSize',    11, ...
        'FontWeight',  'bold', ...
        'Units',       'normalized', ...
        'Position',    [0.91, ctrlY, 0.08, ctrlH], ...
        'BackgroundColor',[0.20 0.20 0.20], ...
        'ForegroundColor',[1 1 1], ...
        'Callback',    @(~,~) runFlowCallback() ...
    );

    tabgp = uitabgroup(fig, ...
        'Units','normalized', ...
        'Position',[0 0.10 1 0.90] ...
    );
    homeTab     = uitab(tabgp, 'Title','Home');
    dataTab     = uitab(tabgp, 'Title','Data');
    resultsTab  = uitab(tabgp, 'Title','Results');
    examplesTab = uitab(tabgp, 'Title','Examples');
    helpTab     = uitab(tabgp, 'Title','Help');
    tabgp.SelectedTab = homeTab;

    Npix = 16;
    hexData = cell(Npix, Npix);
    for r = 1:Npix
        for c = 1:Npix
            frac = ((r-1)/(Npix-1) + (c-1)/(Npix-1)) / 2;
            lvl = round(frac * 255);
            hexData{r,c} = sprintf('#%02X%02X%02X', lvl, lvl, lvl);
        end
    end
    rgbArray = zeros(Npix, Npix, 3);
    for r = 1:Npix
        for c = 1:Npix
            hx = hexData{r,c};
            rVal = hex2dec(hx(2:3));
            gVal = hex2dec(hx(4:5));
            bVal = hex2dec(hx(6:7));
            rgbArray(r,c,:) = [rVal, gVal, bVal]/255;
        end
    end
    photoAx = axes(homeTab, ...
        'Units', 'normalized', ...
        'Position', [0.02 0.05 0.50 0.90], ...
        'Visible', 'off' ...
    );
    imshow(rgbArray, 'Parent', photoAx, 'InitialMagnification','fit','Interpolation','nearest');
    axis(photoAx, 'image');
    exBg = get(homeTab,'BackgroundColor');
    uicontrol(homeTab, ...
        'Style',      'text', ...
        'String',     'POWER FLOW SOLVER', ...
        'FontSize',   28, ...
        'FontWeight','bold', ...
        'Units',      'normalized', ...
        'Position',   [0.55 0.75 0.40 0.15], ...
        'BackgroundColor',exBg, ...
        'HorizontalAlignment','left' ...
    );
    uicontrol(homeTab, ...
        'Style',      'text', ...
        'String',     {'Enter data on the “Data” tab, select solver, then click','“Run” to compute.'}, ...
        'FontSize',   10, ...
        'Units',      'normalized', ...
        'Position',   [0.55 0.65 0.40 0.10], ...
        'BackgroundColor',exBg, ...
        'HorizontalAlignment','left' ...
    );

    initBusData = {
        1,'Slack',1.00,0,  0, 0,   0,  0, 0, 0, NaN, NaN;
        2,'PQ',   1.00,0,  0, 0,   0, 0, 0, 0, NaN, NaN;
        3, 'PV',  1.00,0,  0. 0.   0.  0. 0. 0, NaN, NaN
    };
    initBranchData = {
        1,2,0,0,0,0,0;
        1,3,0,0,0,0,0;
        2,3,0,0,0,0,0
    };
    dataBg = get(dataTab,'BackgroundColor');
    dataPanel = uipanel(dataTab, ...
        'Units','normalized', ...
        'Position',[0.01 0.02 0.98 0.96], ...
        'BackgroundColor', dataBg, ...
        'BorderType','line' ...
    );
    
    % Bus Data label
    uicontrol(dataPanel, ...
        'Style',      'text', ...
        'String',     'Bus Data', ...
        'FontSize',   12, ...
        'FontWeight','bold', ...
        'Units',      'normalized', ...
        'Position',   [0.01 0.95 0.30 0.03], ...
        'BackgroundColor', dataBg, ...
        'HorizontalAlignment','left' ...
    );
    
    % Create grouped headers for bus table with merged groups
    % Define group names and their column spans
    busGroupHeaders = {
        'Bus', 4;       % Spans 4 columns (Bus, Type, V, Phase)
        'Generation', 2; % Spans 2 columns (Pgen, Qgen)
        'Load', 2;      % Spans 2 columns (Pload, Qload)
        'Shunt', 2;     % Spans 2 columns (G, B)
        'PV Buses', 2   % Spans 2 columns (Qmin, Qmax)
    };
    
    % Create detailed headers for bus table
    busDetailedHeaders = {
        'Bus', 'Type', 'V (pu)', 'Phase (deg)', ...
        'Pgen (MW)', 'Qgen (MVAr)', ...
        'Pload (MW)', 'Qload (MVAr)', ...
        'G (pu)', 'B (pu)', ...
        'Qmin', 'Qmax'
    };
    
    % Create custom column names with merged group headers for bus table
    busColumnNames = cell(1, length(busDetailedHeaders));
    colIndex = 1;
    
    for g = 1:size(busGroupHeaders, 1)
        groupName = busGroupHeaders{g,1};
        groupSpan = busGroupHeaders{g,2};
        
        % For the first column in the group
        busColumnNames{colIndex} = sprintf(...
            '<html><div style="text-align:center;"><b>%s</b><br>%s</div></html>', ...
            groupName, busDetailedHeaders{colIndex});
        
        % For subsequent columns in the group
        for s = 2:groupSpan
            colIndex = colIndex + 1;
            busColumnNames{colIndex} = sprintf(...
                '<html><div style="text-align:center;"><b>&nbsp;</b><br>%s</div></html>', ...
                busDetailedHeaders{colIndex});
        end
        
        colIndex = colIndex + 1;
    end
    
    % Set bus table column widths as requested
    busColWidths = {70, 84, 70, 98, 112, 98, 98, 112, 70, 70, 98, 98};
    
    % Bus Table with merged group headers
    busTable = uitable(dataPanel, ...
        'Data',            initBusData, ...
        'ColumnName',      busColumnNames, ...
        'ColumnFormat',    {'numeric',{'Slack','PV','PQ'}, ...
                            'numeric','numeric','numeric','numeric','numeric','numeric','numeric','numeric','numeric','numeric'}, ...
        'ColumnEditable',  true, ...
        'Tag',             'busTable', ...
        'CellSelectionCallback', @(src,evt) storeSelection(src,evt), ...
        'CellEditCallback',      @busCellEditCallback, ...
        'FontSize',        10, ...
        'Units',           'normalized', ...
        'Position',        [0.01 0.55 0.98 0.40], ...
        'RowStriping',     'on' ...
    );
    busTable.ColumnWidth = busColWidths;
    
    % Add/Delete Bus buttons panel
    busBtnPanel = uipanel(dataPanel, ...
        'Units','normalized', ...
        'Position',[0 0.49 1 0.06], ...
        'BackgroundColor',[0.95 0.95 0.95], ...
        'BorderType','none' ...
    );
    uicontrol(busBtnPanel, ...
        'Style','pushbutton', ...
        'String','➕ Add Bus', ...
        'FontSize',10, ...
        'Units','normalized', ...
        'Position',[0.01 0.15 0.20 0.70], ...
        'Callback',@(~,~) addRow(busTable,'bus') ...
    );
    uicontrol(busBtnPanel, ...
        'Style','pushbutton', ...
        'String','🗑️ Delete Bus', ...
        'FontSize',10, ...
        'Units','normalized', ...
        'Position',[0.23 0.15 0.20 0.70], ...
        'Callback',@(~,~) deleteRow(busTable) ...
    );
    
    % Toggle button for Bus advanced columns
busToggleBtn = uicontrol( ...
    'Parent',    busBtnPanel, ...                 % specify parent panel
    'Style',     'pushbutton', ...
    'String',    'Show Bus Advanced', ...
    'FontSize',  10, ...
    'Units',     'normalized', ...
    'Position',  [0.45 0.15 0.25 0.70], ...
    'Callback',  @toggleBusAdvanced, ...
    'UserData',  0, ...                           % 0 = hidden, 1 = shown
    'Visible',   'off' ...                        % hide this button by default
);

    % Branch Data label
    uicontrol(dataPanel, ...
        'Style',      'text', ...
        'String',     'Branch Data', ...
        'FontSize',   12, ...
        'FontWeight','bold', ...
        'Units',      'normalized', ...
        'Position',   [0.01 0.46 0.30 0.03], ...
        'BackgroundColor', dataBg, ...
        'HorizontalAlignment','left' ...
    );
    
    % Create grouped headers for branch table with merged groups
    % Define group names and their column spans
    branchGroupHeaders = {
        'Branch', 2;    % Spans 2 columns (From Bus, To Bus)
        'Impedance', 2; % Spans 2 columns (R, X)
        'Advanced', 3   % Spans 3 columns (Half B, Tap Ratio, Shift Angle)
    };
    
    % Create detailed headers for branch table
    branchDetailedHeaders = {
        'From Bus', 'To Bus', ...
        'R', 'X', ...
        'Half B (pu)', 'Tap Ratio', 'Shift Angle (deg)'
    };
    
    % Create custom column names with merged group headers for branch table
    branchColumnNames = cell(1, length(branchDetailedHeaders));
    colIndex = 1;
    
    for g = 1:size(branchGroupHeaders, 1)
        groupName = branchGroupHeaders{g,1};
        groupSpan = branchGroupHeaders{g,2};
        
        % For the first column in the group
        branchColumnNames{colIndex} = sprintf(...
            '<html><div style="text-align:center;"><b>%s</b><br>%s</div></html>', ...
            groupName, branchDetailedHeaders{colIndex});
        
        % For subsequent columns in the group
        for s = 2:groupSpan
            colIndex = colIndex + 1;
            branchColumnNames{colIndex} = sprintf(...
                '<html><div style="text-align:center;"><b>&nbsp;</b><br>%s</div></html>', ...
                branchDetailedHeaders{colIndex});
        end
        
        colIndex = colIndex + 1;
    end
    
    % Set branch table column widths as requested
    branchColWidths = {112, 112, 80, 80, 112, 112, 160};
    
    % Branch Table with merged group headers
    branchTable = uitable(dataPanel, ...
        'Data',            initBranchData, ...
        'ColumnName',      branchColumnNames, ...
        'ColumnFormat',    repmat({'numeric'},1,7), ...
        'ColumnEditable',  true, ...
        'Tag',             'branchTable', ...
        'CellSelectionCallback', @(src,evt) storeSelection(src,evt), ...
        'FontSize',        10, ...
        'Units',           'normalized', ...
        'Position',        [0.01 0.06 0.98 0.40], ...
        'RowStriping',     'on' ...
    );
    branchTable.ColumnWidth = branchColWidths;
    
    % Add/Delete Branch buttons panel
    branchBtnPanel = uipanel(dataPanel, ...
        'Units','normalized', ...
        'Position',[0 0 1 0.06], ...
        'BackgroundColor',[0.95 0.95 0.95], ...
        'BorderType','none' ...
    );
    uicontrol(branchBtnPanel, ...
        'Style','pushbutton', ...
        'String','➕ Add Branch', ...
        'FontSize',10, ...
        'Units','normalized', ...
        'Position',[0.01 0.15 0.20 0.70], ...
        'Callback',@(~,~) addRow(branchTable,'branch') ...
    );
    uicontrol(branchBtnPanel, ...
        'Style','pushbutton', ...
        'String','🗑️ Delete Branch', ...
        'FontSize',10, ...
        'Units','normalized', ...
        'Position',[0.23 0.15 0.20 0.70], ...
        'Callback',@(~,~) deleteRow(branchTable) ...
    );
    
branchToggleBtn = uicontrol( ...
    'Parent',    branchBtnPanel, ...              % specify parent panel
    'Style',     'pushbutton', ...
    'String',    'Show Branch Advanced', ...
    'FontSize',  10, ...
    'Units',     'normalized', ...
    'Position',  [0.45 0.15 0.25 0.70], ...
    'Callback',  @toggleBranchAdvanced, ...
    'UserData',  0, ...                           % 0 = hidden, 1 = shown
    'Visible',   'off' ...                        % hide this button by default
);

    % Define advanced columns to hide
    advancedBusCols = 9:12;    % Columns: G, B, Qmin, Qmax
    advancedBranchCols = 5:7;  % Columns: Half B, Tap Ratio, Shift Angle
    
    % Store original widths for restoration
    originalBusWidths = busColWidths(advancedBusCols);
    originalBranchWidths = branchColWidths(advancedBranchCols);
    
    % Hide advanced columns initially
    busTable.ColumnWidth(advancedBusCols) = {0};
    branchTable.ColumnWidth(advancedBranchCols) = {0};

    % Toggle callback for Bus advanced columns
    function toggleBusAdvanced(src, ~)
        state = src.UserData;
        if state == 0 % Currently hidden, show columns
            busTable.ColumnWidth(advancedBusCols) = originalBusWidths;
            src.String = 'Hide Bus Advanced';
            src.UserData = 1;
        else % Currently shown, hide columns
            busTable.ColumnWidth(advancedBusCols) = {0};
            src.String = 'Show Bus Advanced';
            src.UserData = 0;
        end
    end

    % Toggle callback for Branch advanced columns
    function toggleBranchAdvanced(src, ~)
        state = src.UserData;
        if state == 0 % Currently hidden, show columns
            branchTable.ColumnWidth(advancedBranchCols) = originalBranchWidths;
            src.String = 'Hide Branch Advanced';
            src.UserData = 1;
        else % Currently shown, hide columns
            branchTable.ColumnWidth(advancedBranchCols) = {0};
            src.String = 'Show Branch Advanced';
            src.UserData = 0;
        end
    end


    %% Results Tab
    resBg = get(resultsTab,'BackgroundColor');
    resPanel = uipanel(resultsTab, ...
        'Units','normalized', ...
        'Position',[0.01 0.02 0.98 0.96], ...
        'BackgroundColor', resBg, ...
        'BorderType','line' ...
    );
    txtNoResults = uicontrol(resPanel, ...
        'Style',           'text', ...
        'String',          'Nothing here yet. Run Power Flow to see results.', ...
        'FontSize',        14, ...
        'FontWeight',      'bold', ...
        'ForegroundColor', [0.5 0.5 0.5], ...
        'HorizontalAlignment','center', ...
        'Units',           'normalized', ...
        'Position',        [0.05 0.60 0.90 0.05], ...
        'BackgroundColor', resBg, ...
        'Tag',             'txtNoResults' ...
    );
    uicontrol(resPanel, ...
        'Style','text', ...
        'String','Branch Results', ...
        'FontSize',12, ...
        'FontWeight','bold', ...
        'Units','normalized', ...
        'HorizontalAlignment','left', ...
        'Position',[0.01 0.95 0.30 0.03], ...
        'BackgroundColor', resBg ...
    );
    resultBranchTable = uitable(resPanel, ...
        'Data',       {}, ...
        'ColumnName', {}, ...
        'FontSize',   10, ...
        'Units',      'normalized', ...
        'Position',   [0.01 0.55 0.98 0.40], ...
        'Tag',        'resultBranchTable', ...
        'RowStriping','on' ...
    );
    resultBranchTable.ColumnWidth = repmat({135},1,8);
    uicontrol(resPanel, ...
        'Style','text', ...
        'String','Bus Results', ...
        'FontSize',12, ...
        'FontWeight','bold', ...
        'Units','normalized', ...
        'HorizontalAlignment','left', ...
        'Position',[0.01 0.50 0.30 0.03], ...
        'BackgroundColor', resBg ...
    );
    resultBusTable = uitable(resPanel, ...
        'Data',       {}, ...
        'ColumnName', {}, ...
        'FontSize',   10, ...
        'Units',      'normalized', ...
        'Position',   [0.01 0.00 0.98 0.50], ...
        'Tag',        'resultBusTable', ...
        'RowStriping','on' ...
    );
    resultBusTable.ColumnWidth = repmat({120},1,9);


    
    %% Examples Tab
    exampleCases = struct();
exampleCases(1).name = '3-Bus System';
exampleCases(1).bus = {
    1, 'Slack', 1.025, 0, 0, 0, 0, 0, 0, 0, NaN, NaN;
    2, 'PQ',    1.0,   0, 0, 0, 400, 200, 0, 0, NaN, NaN;
    3, 'PV',    1.03,  0, 300, 0, 0, 0, 0, 0, NaN, NaN
};
exampleCases(1).branch = {
    1, 2, 0, 0.025, 0, 0, 0;
    1, 3, 0, 0.05,  0, 0, 0;
    2, 3, 0, 0.025, 0, 0, 0
};
    exampleCases(2).name = '4-Bus System';
    exampleCases(2).bus = {
        1, 'Slack', 1.00, 0,  0, 0,  0,  0, 0, 0, NaN, NaN;
        2, 'PV',    1.02, 0, 40, 0, 10,  5, 0, 0, NaN, NaN;
        3, 'PQ',    1.00, 0,  0, 0, 60, 20, 0, 0, NaN, NaN;
        4, 'PQ',    1.00, 0,  0, 0, 20, 10, 0, 0, NaN, NaN
    };
    exampleCases(2).branch = {
        1, 2, 0.01,  0.03,  0.02, 0, 0;
        1, 3, 0.02,  0.04,  0.01, 0, 0;
        2, 3, 0.012, 0.036, 0.015, 0, 0;
        2, 4, 0.015, 0.045,  0.02, 0, 0;
        3, 4, 0.01,  0.03, 0.025, 0, 0
    };
    exampleCases(3).name = '2-Bus System';
    exampleCases(3).bus = {
        1, 'Slack', 1.0, 0, 0, 0, 0, 0, 0, 0, NaN, NaN;
        2, 'PQ',    NaN, NaN, 0, 0, 100, 50, 0, 0, NaN, NaN
    };
    exampleCases(3).branch = {
    1, 2, 0.12, 0.16, 0, 0, 0
};
% Create main panels for Examples tab
exBg = get(examplesTab,'BackgroundColor');
mainExPanel = uipanel(examplesTab, ...
    'Units','normalized', ...
    'Position',[0.01 0.02 0.98 0.96], ...
    'BackgroundColor', exBg, ...
    'BorderType','none' ...
);

% Left panel for example controls
leftPanel = uipanel(mainExPanel, ...
    'Units','normalized', ...
    'Position',[0 0 0.48 1], ...
    'BackgroundColor', exBg, ...
    'BorderType','none' ...
);

% Right panel for gradient display
rightPanel = uipanel(mainExPanel, ...
    'Units','normalized', ...
    'Position',[0.50 0 0.50 1], ...
    'BackgroundColor', exBg, ...
    'BorderType','none' ...
);


% Example controls in left panel
uicontrol(leftPanel, ...
    'Style',      'text', ...
    'String',     'Select an Example Case:', ...
    'FontSize',   12, ...
    'FontWeight','bold', ...
    'Units',      'normalized', ...
    'Position',   [0.02 0.90 0.40 0.06], ...
    'BackgroundColor', exBg, ...
    'HorizontalAlignment','left' ...
);

exampleNames = {exampleCases.name};
popupEx = uicontrol(leftPanel, ...
    'Style',      'popupmenu', ...
    'String',     exampleNames, ...
    'FontSize',   10, ...
    'Units',      'normalized', ...
    'Position',   [0.02 0.82 0.40 0.06] ...
);

uicontrol(leftPanel, ...
    'Style',      'pushbutton', ...
    'String',     'Load Example into Data Tab', ...
    'FontSize',   10, ...
    'FontWeight','bold', ...
    'Units',      'normalized', ...
    'Position',   [0.02 0.72 0.40 0.07], ...
    'Callback',   @(~,~) loadExampleCallback() ...
);

uicontrol(leftPanel, ...
    'Style',      'text', ...
    'String',     {'After loading, switch to “Data” to modify before running.'; ...
                   'Ensure formatting matches (bus numbers, column order).'}, ...
    'FontSize',   10, ...
    'Units',      'normalized', ...
    'HorizontalAlignment','left', ...
    'Position',   [0.02 0.50 0.96 0.20], ...
    'BackgroundColor', exBg ...
);

Npix = 16;
hexData = cell(Npix, Npix);
for r = 1:Npix
    for c = 1:Npix
        frac = ((r-1)/(Npix-1) + (c-1)/(Npix-1)) / 2;
        lvl = round(frac * 255);
        hexData{r,c} = sprintf('#%02X%02X%02X', lvl, lvl, lvl);
    end
end
rgbArray = zeros(Npix, Npix, 3);
for r = 1:Npix
    for c = 1:Npix
        hx = hexData{r,c};
        rVal = hex2dec(hx(2:3));
        gVal = hex2dec(hx(4:5));
        bVal = hex2dec(hx(6:7));
        rgbArray(r,c,:) = [rVal, gVal, bVal]/255;
    end
end
gradientAx = axes('Parent', rightPanel, ...
    'Units', 'normalized', ...
    'Position', [0.1 0.15 0.8 0.7], ...
    'Visible', 'off' ...
);
imshow(rgbArray, 'Parent', gradientAx, 'InitialMagnification','fit','Interpolation','nearest');
axis(gradientAx, 'image');

uicontrol(rightPanel, ...
    'Style',      'text', ...
    'String',     '', ...
    'FontSize',   14, ...
    'FontWeight','bold', ...
    'Units',      'normalized', ...
    'Position',   [0.1 0.88 0.8 0.08], ...
    'BackgroundColor', [0.92 0.92 0.92], ...
    'HorizontalAlignment','center' ...
);


helpLines = {
    'HOW TO USE THIS POWER SYSTEM UI'
    '========================================='
    ''
    '1) DATA TAB:'
    '   ---------'
    ''
    '   BUS DATA:'
    '     - Bus (Col 1): Positive integer (unique identifier).'
    '     - Type (Col 2): {Slack, PV, PQ}'
    '         * Slack: fixed voltage magnitude & angle.'
    '         * PV: fixed voltage magnitude; reactive limits apply.'
    '         * PQ: load bus (P & Q specified).'
    '     - V (pu): per‐unit voltage (> 0).'
    '     - Phase (deg): voltage angle.'
    '     - Pgen (MW), Qgen (MVAr): generator outputs.'
    '     - Pload (MW), Qload (MVAr): load values.'
    '     - G (pu), B (pu): shunt conductance/susceptance.'
    '     - Qmin, Qmax: only for PV buses.'
    ''
    '     Use "Add Bus" to append a new bus.'
    '     Select a row and click "Delete Bus" to remove a bus.'
    ''
    '   BRANCH DATA:'
    '     - From Bus, To Bus: existing bus numbers (no self‐loops).'
    '     - R (pu), X (pu): branch impedance values.'
    '     - Half B (pu): half‐line charging susceptance.'
    '     - Tap Ratio, Shift Angle: transformer settings.'
    ''
    '     Use "Add Branch" to append a new branch.'
    '     Select a row and click "Delete Branch" to remove a branch.'
    ''
    '2) TOL & MAX ITER (BOTTOM):'
    '   ------------------------'
    ''
    '   - Tolerance: algorithm stops when ΔV < tolerance.'
    '   - Max Iter: maximum number of iterations allowed.'
    ''
    '3) RUN POWER FLOW:'
    '   ----------------'
    ''
    '   - Select solver (NR or GS), then click "Run".'
    '   - Error messages will appear if inputs are invalid.'
    '   - On success, go to the "Results" tab:'
    '       * Branch Summary: Pij, Qij, Pji, Qji, losses, total losses.'
    '       * Bus Summary: V, angle, Pgen, Qgen, Pload, Qload, Qinj, Pbus_loss, total loss.'
    '   - Iteration count updates at the bottom of the window.'
    ''
    '4) RESULTS TAB:'
    '   -------------'
    ''
    '   - Placeholder until the power flow finishes.'
    '   - Two tables will appear; scroll to see all columns and rows.'
    ''
    'GENERAL NOTES:'
    '-------------'
    ''
    '   - All inputs must be numeric (except "Type").'
    '   - For PV buses: Qmin must be less than Qmax; if violated, bus converts to PQ automatically.'
    '   - Units: P in MW, Q in MVAr, V in per‐unit, angles in degrees.'
    '   - Tap Ratio and Shift Angle apply only to transformers.'
    '   - To reset inputs, delete all rows and re‐enter data.'
    '   - Close the window to exit the application.'
    ''
    '========================================='
    'HAPPY POWER-FLOWING!'
};

uicontrol(helpTab, ...
    'Style',               'edit', ...
    'String',              helpLines, ...
    'Units',               'normalized', ...
    'Position',            [0.02 0.02 0.96 0.96], ...
    'FontSize',            15, ...
    'HorizontalAlignment', 'left', ...
    'Enable',              'inactive', ...
    'Max',                 2, ...
    'BackgroundColor',     [1 1 1] ...
);

    %% Subfunctions

    function enforceMinSize(src, minW, minH)
        pos = src.Position;
        updated = false;
        if pos(3) < minW
            pos(3) = minW; updated = true;
        end
        if pos(4) < minH
            pos(4) = minH; updated = true;
        end
        if updated
            src.Position = pos;
        end
    end

    function storeSelection(src, event)
        if ~isempty(event.Indices)
            src.UserData.SelectedRows = unique(event.Indices(:,1));
        end
    end

    function busCellEditCallback(~, event)
        if event.Indices(2) == 2
            newType = event.NewData;
            row = event.Indices(1);
            data = busTable.Data;
            if ~strcmp(newType, 'PV')
                data{row,11} = NaN;
                data{row,12} = NaN;
                busTable.Data = data;
            end
        end
    end

    function addRow(tblHandle, tableType)
        currentData = tblHandle.Data;
        numCols = size(currentData,2);
        if strcmp(tableType,'bus')
            if isempty(currentData)
                newBusNum = 1;
            else
                existing = cell2mat(currentData(:,1));
                newBusNum = max(existing) + 1;
            end
            newRow = {newBusNum,'PQ',1,0,0,0,0,0,0,0,NaN,NaN};
        else
            newRow = repmat({0},1,numCols);
            newRow{3} = 0.01;
            newRow{4} = 0.05;
            newRow{6} = 1;
        end
        tblHandle.Data = [currentData; newRow];
    end

    function deleteRow(tblHandle)
        if isfield(tblHandle.UserData,'SelectedRows') && ~isempty(tblHandle.UserData.SelectedRows)
            rowsToDelete = tblHandle.UserData.SelectedRows;
            d = tblHandle.Data;
            d(rowsToDelete,:) = [];
            tblHandle.Data = d;
            tblHandle.UserData.SelectedRows = [];
        else
            d = tblHandle.Data;
            if ~isempty(d)
                tblHandle.Data = d(1:end-1,:);
            end
        end
    end

    function runFlowCallback()
        try
            tolVal = str2double(get(tolEdit,'String'));
            if isnan(tolVal) || tolVal <= 0
                errordlg('Tolerance must be positive','Input Error'); return;
            end
            maxIterVal = round(str2double(get(maxIterEdit,'String')));
            if isnan(maxIterVal) || maxIterVal <= 0
                errordlg('Max Iter must be positive integer','Input Error'); return;
            end
            solverIdx = get(solverPopup,'Value');  % 1=NR, 2=GS

            busCell   = busTable.Data;
            [busData, busOK] = validateBusData(busCell);
            if ~busOK, return; end
            branchCell = branchTable.Data;
            [branchData, branchOK] = validateBranchData(branchCell,busData.Bus);
            if ~branchOK, return; end

            if solverIdx == 1
                [Summary_line_flow,Bus_information,iterCount] = computePowerFlow_NR(busData,branchData,tolVal,maxIterVal);
            else
                [Summary_line_flow,Bus_information,iterCount] = computePowerFlow_GS(busData,branchData,tolVal,maxIterVal);
            end

            % Populate Branch Results
            branchOut = table2cell(Summary_line_flow);
            lastRow = size(branchOut,1);
            for c = 1:size(branchOut,2)
                if isnumeric(branchOut{lastRow,c}) && isnan(branchOut{lastRow,c})
                    if c==1
                        branchOut{lastRow,c} = '      Total:';
                    else
                        branchOut{lastRow,c} = '';
                    end
                end
            end
            resultBranchTable.Data       = branchOut;
            resultBranchTable.ColumnName = Summary_line_flow.Properties.VariableNames;

            % Populate Bus Results
            busOut = table2cell(Bus_information);
            lastB = size(busOut,1);
            for c = 1:size(busOut,2)
                if isnumeric(busOut{lastB,c}) && isnan(busOut{lastB,c})
                    if c==1
                        busOut{lastB,c} = '      Total:';
                    else
                        busOut{lastB,c} = '';
                    end
                end
            end
            resultBusTable.Data       = busOut;
            resultBusTable.ColumnName = Bus_information.Properties.VariableNames;

            set(iterText,'String',['Iterations: ' num2str(iterCount)]);
            set(txtNoResults,'Visible','off');
            tabgp.SelectedTab = resultsTab;

        catch ME
            errordlg(ME.message,'Power Flow Error','modal');
        end
    end

    function [busData, valid] = validateBusData(data)
        valid = false;
        n = size(data,1);
        if n==0
            errordlg('Bus table is empty!','Validation Error'); return;
        end
        Bus = zeros(n,1);
        Type = cell(n,1);
        V = zeros(n,1);
        Phase = zeros(n,1);
        Pgen = zeros(n,1);
        Qgen = zeros(n,1);
        Pload = zeros(n,1);
        Qload = zeros(n,1);
        G = zeros(n,1);
        B = zeros(n,1);
        Qmin = zeros(n,1);
        Qmax = zeros(n,1);
        busNums = zeros(n,1);
        for i = 1:n
            if ~isnumeric(data{i,1}) || data{i,1}<=0
                errordlg(sprintf('Bus number invalid (row %d)',i),'Validation Error'); return;
            end
            Bus(i) = data{i,1};
            busNums(i) = data{i,1};

            validTypes = {'Slack','PV','PQ'};
            if ~any(strcmp(data{i,2},validTypes))
                errordlg(sprintf('Invalid bus type (row %d)',i),'Validation Error'); return;
            end
            Type{i} = data{i,2};

            if ~isnumeric(data{i,3}) || data{i,3}<=0
                errordlg(sprintf('Voltage ≤ 0 (row %d)',i),'Validation Error'); return;
            end
            V(i) = data{i,3};

            Phase(i) = data{i,4};
            Pgen(i)  = data{i,5};
            Qgen(i)  = data{i,6};
            Pload(i) = data{i,7};
            Qload(i) = data{i,8};
            G(i)     = data{i,9};
            B(i)     = data{i,10};

            if strcmp(Type{i},'PV')
                Qmin(i) = data{i,11};
                Qmax(i) = data{i,12};
            else
                Qmin(i) = NaN;
                Qmax(i) = NaN;
            end
        end
        if numel(unique(busNums))~=numel(busNums)
            errordlg('Bus numbers must be unique!','Validation Error'); return;
        end
        busData = struct( ...
            'Bus',Bus, ...
            'Type',{Type}, ...
            'V',V, ...
            'Phase',Phase, ...
            'Pgen',Pgen, ...
            'Qgen',Qgen, ...
            'Pload',Pload, ...
            'Qload',Qload, ...
            'G',G, ...
            'B',B, ...
            'Qmin',Qmin, ...
            'Qmax',Qmax ...
        );
        valid = true;
    end

    function [branchData, valid] = validateBranchData(data, validBuses)
        valid = false;
        m = size(data,1);
        if m==0
            errordlg('Branch table is empty!','Validation Error'); return;
        end
        bus_i = zeros(m,1);
        bus_j = zeros(m,1);
        R = zeros(m,1);
        X = zeros(m,1);
        half_B = zeros(m,1);
        Tap = ones(m,1);
        Shift = zeros(m,1);
        for i = 1:m
            if ~isnumeric(data{i,1}) || ~ismember(data{i,1},validBuses)
                errordlg(sprintf('Invalid From Bus (row %d)',i),'Validation Error'); return;
            end
            bus_i(i) = data{i,1};

            if ~isnumeric(data{i,2}) || ~ismember(data{i,2},validBuses)
                errordlg(sprintf('Invalid To Bus (row %d)',i),'Validation Error'); return;
            end
            bus_j(i) = data{i,2};

            if bus_i(i)==bus_j(i)
                errordlg(sprintf('No self-loop (row %d)',i),'Validation Error'); return;
            end

            if ~isnumeric(data{i,3}) || data{i,3}<0
                errordlg(sprintf('R < 0 (row %d)',i),'Validation Error'); return;
            end
            R(i)=data{i,3};

            if ~isnumeric(data{i,4}) || data{i,4}<=0
                errordlg(sprintf('X ≤ 0 (row %d)',i),'Validation Error'); return;
            end
            X(i)=data{i,4};

            half_B(i) = data{i,5};
            if isnumeric(data{i,6}) && ~isempty(data{i,6}) && data{i,6}~=0
                Tap(i) = data{i,6};
            end
            Shift(i) = data{i,7};
        end
        branchData = struct( ...
            'bus_i',bus_i, ...
            'bus_j',bus_j, ...
            'R',R, ...
            'X',X, ...
            'half_B',half_B, ...
            'Tap',Tap, ...
            'Shift',Shift ...
        );
        valid = true;
    end

    %% Newton–Raphson solver
    function [Summary_line_flow, Bus_information, iterCount] = computePowerFlow_NR(busData, branchData, tol, maxIter)
        BusData    = struct2table(busData);
        BranchData = struct2table(branchData);
        BusData    = sortrows(BusData, 'Bus');
        N = height(BusData);
        S_base = 100;
        Y = zeros(N);

        % Build Ybus
        for k = 1:height(BranchData)
            a     = BranchData.Tap(k);
            shift = deg2rad(BranchData.Shift(k));
            [ax, ay] = pol2cart(shift, a);
            z = BranchData.R(k) + 1i*BranchData.X(k);
            % Off-diagonals
            Y(BranchData.bus_i(k),BranchData.bus_j(k)) = Y(BranchData.bus_i(k),BranchData.bus_j(k)) - 1/(conj(ax+1i*ay)*z);
            Y(BranchData.bus_j(k),BranchData.bus_i(k)) = Y(BranchData.bus_j(k),BranchData.bus_i(k)) - 1/((ax+1i*ay)*z);
            % Diagonals
            Y(BranchData.bus_i(k),BranchData.bus_i(k)) = Y(BranchData.bus_i(k),BranchData.bus_i(k)) + 1/(a^2*z) + 1i*BranchData.half_B(k);
            Y(BranchData.bus_j(k),BranchData.bus_j(k)) = Y(BranchData.bus_j(k),BranchData.bus_j(k)) + 1/z + 1i*BranchData.half_B(k);
        end
        for k = 1:N
            Y(k,k) = Y(k,k) + BusData.G(k) + 1i*BusData.B(k);
        end

        BusData_copy = BusData;
        iterCount = 0;
        while true
            V     = BusData_copy.V(:);
            Phase = BusData_copy.Phase(:);
            V(isnan(V))        = 1;
            Phase(isnan(Phase))= 0;

            Log_load    = strcmp(string(BusData_copy.Type),"Load") | strcmp(string(BusData_copy.Type),"PQ");
            Log_pv_load = strcmp(string(BusData_copy.Type),"PV")  | Log_load;

            P_variable     = BusData_copy.Bus(Log_pv_load);
            Delta_variable = P_variable;
            Q_variable     = BusData_copy.Bus(Log_load);
            V_variable     = Q_variable;

            P_sch = (BusData_copy.Pgen(Log_pv_load) - BusData_copy.Pload(Log_pv_load)) / S_base;
            Q_sch = (BusData_copy.Qgen(Log_load) - BusData_copy.Qload(Log_load)) / S_base;

            iteration = 0;
            while true
                iteration = iteration + 1;
                J1_full = zeros(N); J2_full = zeros(N);
                J3_full = zeros(N); J4_full = zeros(N);

                for i = 1:N
                    x=0; y=0; z=0; w=0;
                    for j = 1:N
                        if i~=j
                            J1_full(i,j) = V(i)*V(j)*abs(Y(i,j))*sin(Phase(i)-Phase(j)-angle(Y(i,j)));
                            w = w + J1_full(i,j);
                            J2_full(i,j) = V(i)*abs(Y(i,j))*cos(Phase(i)-Phase(j)-angle(Y(i,j)));
                            x = x + (V(j)/V(i))*J2_full(i,j);
                            J3_full(i,j) = -V(i)*V(j)*abs(Y(i,j))*cos(Phase(i)-Phase(j)-angle(Y(i,j)));
                            y = y - J3_full(i,j);
                            J4_full(i,j) = V(i)*abs(Y(i,j))*sin(Phase(i)-Phase(j)-angle(Y(i,j)));
                            z = z + (V(j)/V(i))*J4_full(i,j);
                        end
                    end
                    J1_full(i,i) = -w;
                    J2_full(i,i) = 2*V(i)*abs(Y(i,i))*cos(angle(Y(i,i))) + x;
                    J3_full(i,i) = y;
                    J4_full(i,i) = -2*V(i)*abs(Y(i,i))*sin(angle(Y(i,i))) + z;
                end

                P_size     = length(P_variable);
                Delta_size = P_size;
                Q_size     = length(Q_variable);
                V_size     = Q_size;

                J1 = zeros(P_size,Delta_size);
                J2 = zeros(P_size,V_size);
                P_cal = [];
                for i = 1:P_size
                    kBus = P_variable(i);
                    for j = 1:Delta_size
                        J1(i,j) = J1_full(kBus,Delta_variable(j));
                    end
                    for j = 1:V_size
                        J2(i,j) = J2_full(kBus,V_variable(j));
                    end
                    ptemp = 0;
                    for j = 1:N
                        ptemp = ptemp + V(kBus)*V(j)*abs(Y(kBus,j))*cos(Phase(kBus)-Phase(j)-angle(Y(kBus,j)));
                    end
                    P_cal = [P_cal; ptemp];
                end

                J3 = zeros(Q_size,Delta_size);
                J4 = zeros(Q_size,V_size);
                Q_cal = [];
                for i = 1:Q_size
                    kBus = Q_variable(i);
                    for j = 1:Delta_size
                        J3(i,j) = J3_full(Q_variable(i),Delta_variable(j));
                    end
                    for j = 1:V_size
                        J4(i,j) = J4_full(Q_variable(i),V_variable(j));
                    end
                    qtemp = 0;
                    for j = 1:N
                        qtemp = qtemp + V(kBus)*V(j)*abs(Y(kBus,j))*sin(Phase(kBus)-Phase(j)-angle(Y(kBus,j)));
                    end
                    Q_cal = [Q_cal; qtemp];
                end

                Jacobian = [J1 J2; J3 J4];
                residual = [P_sch - P_cal; Q_sch - Q_cal];
                mismatch = Jacobian \ residual;

                Phase(Delta_variable) = Phase(Delta_variable) + mismatch(1:Delta_size);
                V(V_variable)         = V(V_variable) + mismatch(Delta_size+1:Delta_size+V_size);

                if norm(mismatch) < tol || iteration >= maxIter
                    break;
                end
            end
            iterCount = iteration;

            % Compute line flows
            I_line_flow = table();
            S_line_flow = table();
            S_network   = zeros(N,1);
            for k = 1:height(BranchData)
                iBus  = BranchData.bus_i(k);
                jBus  = BranchData.bus_j(k);
                a     = BranchData.Tap(k);
                shift = deg2rad(BranchData.Shift(k));
                [ax, ay] = pol2cart(shift,a);
                [Vi_x, Vi_y] = pol2cart(Phase(iBus), V(iBus));
                [Vj_x, Vj_y] = pol2cart(Phase(jBus), V(jBus));
                R = BranchData.R(k);
                X = BranchData.X(k);
                y = 1/(R + 1i*X);

                if shift ~= 0
                    Iij = -(y/conj(ax + 1i*ay))*(Vj_x+1i*Vj_y) + (y/a^2)*(Vi_x+1i*Vi_y);
                    Iji = y*(Vj_x+1i*Vj_y) - (y/(ax + 1i*ay))*(Vi_x+1i*Vi_y);
                    Sij = (Vi_x+1i*Vi_y)*conj(Iij)*S_base;
                    Sji = (Vj_x+1i*Vj_y)*conj(Iji)*S_base;
                    Ii0 = NaN; Ij0 = NaN; Iij_line = NaN; Iji_line = NaN;
                    Si0 = NaN; Sj0 = NaN; Sij_line = NaN; Sji_line = NaN;
                else
                    Mid = y/a;
                    Half_i = 1i*BranchData.half_B(k) + y*(1-a)/a^2;
                    Half_j = 1i*BranchData.half_B(k) + y*(a-1)/a;

                    Iij_line = ((Vi_x+1i*Vi_y)-(Vj_x+1i*Vj_y))*Mid;
                    Ii0 = Half_i*(Vi_x+1i*Vi_y);
                    Iij = Iij_line + Ii0;
                    Sij_line = (Vi_x+1i*Vi_y)*conj(Iij_line)*S_base;
                    Si0 = (Vi_x+1i*Vi_y)*conj(Ii0)*S_base;
                    Sij = Sij_line + Si0;

                    Iji_line = ((Vj_x+1i*Vj_y)-(Vi_x+1i*Vi_y))*Mid;
                    Ij0 = Half_j*(Vj_x+1i*Vj_y);
                    Iji = Iji_line + Ij0;
                    Sji_line = (Vj_x+1i*Vj_y)*conj(Iji_line)*S_base;
                    Sj0 = (Vj_x+1i*Vj_y)*conj(Ij0)*S_base;
                    Sji = Sji_line + Sj0;
                end
                S_network(iBus) = S_network(iBus) + Sij;
                S_network(jBus) = S_network(jBus) + Sji;

                Total_pow2gnd = Si0 + Sj0;
                RX_loss       = Sij_line + Sji_line;
                Total_loss    = Sij + Sji;

                I_line_flow = [I_line_flow; {iBus,jBus,Iij_line,Ii0,Iij,Iji_line,Ij0,Iji}];
                S_line_flow = [S_line_flow; {iBus,jBus,Sij_line,Si0,Sij,Sji_line,Sj0,Sji,Total_pow2gnd,RX_loss,Total_loss}];
            end
            I_line_flow.Properties.VariableNames = {'i','j','Iij_line','Ii0','Iij','Iji_line','Ij0','Iji'};
            S_line_flow.Properties.VariableNames = {'i','j','Sij_line','Si0','Sij','Sji_line','Sj0','Sji','Si0_Sj0','Sij_line_Sji_line','Total_loss'};

            Summary_line_flow = table( ...
                S_line_flow.i, S_line_flow.j, ...
                real(S_line_flow.Sij), imag(S_line_flow.Sij), ...
                real(S_line_flow.Sji), imag(S_line_flow.Sji), ...
                real(S_line_flow.Total_loss), imag(S_line_flow.Total_loss), ...
                'VariableNames', {'i','j','Pij','Qij','Pji','Qji','P_loss','Q_loss'} ...
            );
            Summary_line_flow = [Summary_line_flow; { NaN, NaN, NaN, NaN, NaN, NaN, sum(Summary_line_flow.P_loss), sum(Summary_line_flow.Q_loss) }];

            Q_injected = zeros(N,1);
            P_bus_loss = zeros(N,1);
            for kBus = 1:N
                Q_injected(kBus) = S_base*BusData.B(kBus)*V(kBus)^2;
                P_bus_loss(kBus)= S_base*BusData.G(kBus)*V(kBus)^2;
            end

            P_load    = BusData.Pload;
            Q_load    = BusData.Qload;
            P_network = real(S_network);
            Q_network = imag(S_network);
            P_gen     = P_network + P_load + P_bus_loss;
            Q_gen     = Q_network + Q_load - Q_injected;

            Phase_deg = rad2deg(Phase);
            No_Bus    = BusData.Bus;

            Bus_information = table( ...
                No_Bus, V, Phase_deg, P_gen, Q_gen, P_load, Q_load, Q_injected, P_bus_loss, ...
                'VariableNames', {'Bus','V','Phase','Pgen','Qgen','Pload','Qload','Qinj','Pbus_loss'} ...
            );
            Bus_information = [Bus_information; { NaN,NaN,NaN,sum(P_gen),sum(Q_gen),sum(P_load),sum(Q_load),sum(Q_injected),sum(P_bus_loss) }];
            break;
        end
    end

    %% Gauss–Seidel solver
    function [Summary_line_flow, Bus_information, iterCount] = computePowerFlow_GS(busData, branchData, tol, maxIter)
        BusData    = struct2table(busData);
        BranchData = struct2table(branchData);
        BusData    = sortrows(BusData, 'Bus');
        N = height(BusData);
        S_base = 100;

        % Build Ybus
        Ybus = zeros(N);
        for k = 1:height(BranchData)
            a     = BranchData.Tap(k);
            shift = deg2rad(BranchData.Shift(k));
            [ax, ay] = pol2cart(shift, a);
            z = BranchData.R(k) + 1i*BranchData.X(k);

            Ybus(BranchData.bus_i(k),BranchData.bus_j(k)) = ...
                Ybus(BranchData.bus_i(k),BranchData.bus_j(k)) - 1/(conj(ax+1i*ay)*z);
            Ybus(BranchData.bus_j(k),BranchData.bus_i(k)) = ...
                Ybus(BranchData.bus_j(k),BranchData.bus_i(k)) - 1/((ax+1i*ay)*z);

            Ybus(BranchData.bus_i(k),BranchData.bus_i(k)) = ...
                Ybus(BranchData.bus_i(k),BranchData.bus_i(k)) + 1/(a^2*z) + 1i*BranchData.half_B(k);
            Ybus(BranchData.bus_j(k),BranchData.bus_j(k)) = ...
                Ybus(BranchData.bus_j(k),BranchData.bus_j(k)) + 1/z + 1i*BranchData.half_B(k);
        end
        for k = 1:N
            Ybus(k,k) = Ybus(k,k) + BusData.G(k) + 1i*BusData.B(k);
        end

        % Initialize voltages (complex)
        V = BusData.V .* exp(1i*deg2rad(BusData.Phase));
        for i = 1:N
            if isnan(V(i))
                V(i) = 1 + 0j;
            end
        end

        % Specified P & Q per-unit
        P_spec = (BusData.Pgen - BusData.Pload) / S_base;
        Q_spec = (BusData.Qgen - BusData.Qload) / S_base;

        isSlack = strcmp(string(BusData.Type),'Slack');
        isPV    = strcmp(string(BusData.Type),'PV');
        isPQ    = strcmp(string(BusData.Type),'PQ');

        iterCount = 0;
        while iterCount < maxIter
            iterCount = iterCount + 1;
            V_old = V;

            for i = 1:N
                if isSlack(i)
                    continue;
                end

                sumYV = 0;
                for j = 1:N
                    if j~=i
                        sumYV = sumYV + Ybus(i,j)*V(j);
                    end
                end

                if isPQ(i)
                    S = P_spec(i) + 1i*Q_spec(i);
                    V(i) = (1/Ybus(i,i)) * (conj(S)/conj(V(i)) - sumYV);

                elseif isPV(i)
                    S_temp = P_spec(i) + 1i*0;
                    V_temp = (1/Ybus(i,i))*(conj(S_temp)/conj(V(i)) - sumYV);
                    V(i) = BusData.V(i)*exp(1i*angle(V_temp));
                    Q_spec(i) = -imag(conj(V(i))*(Ybus(i,:)*V));
                end
            end

            if max(abs(V - V_old)) < tol
                break;
            end
        end

        % Post‐processing
        Phase = angle(V);
        I_line_flow = table();
        S_line_flow = table();
        S_network   = zeros(N,1);

        for k = 1:height(BranchData)
            iBus = BranchData.bus_i(k);
            jBus = BranchData.bus_j(k);
            a    = BranchData.Tap(k);
            shift = deg2rad(BranchData.Shift(k));
            [ax, ay] = pol2cart(shift,a);

            Vi = V(iBus);
            Vj = V(jBus);
            R  = BranchData.R(k);
            X  = BranchData.X(k);
            y  = 1/(R + 1i*X);

            if shift ~= 0
                Iij = -(y/conj(ax + 1i*ay))*Vj + (y/a^2)*Vi;
                Iji = y*Vj - (y/(ax + 1i*ay))*Vi;
                Sij = Vi*conj(Iij)*S_base;
                Sji = Vj*conj(Iji)*S_base;
                Ii0 = NaN; Ij0 = NaN; Iij_line = NaN; Iji_line = NaN;
                Si0 = NaN; Sj0 = NaN; Sij_line = NaN; Sji_line = NaN;
            else
                Mid    = y/a;
                Half_i = 1i*BranchData.half_B(k) + y*(1-a)/a^2;
                Half_j = 1i*BranchData.half_B(k) + y*(a-1)/a;

                Iij_line = (Vi - Vj)*Mid;
                Ii0      = Half_i*Vi;
                Iij      = Iij_line + Ii0;
                Sij_line = Vi*conj(Iij_line)*S_base;
                Si0      = Vi*conj(Ii0)*S_base;
                Sij      = Sij_line + Si0;

                Iji_line = (Vj - Vi)*Mid;
                Ij0      = Half_j*Vj;
                Iji      = Iji_line + Ij0;
                Sji_line = Vj*conj(Iji_line)*S_base;
                Sj0      = Vj*conj(Ij0)*S_base;
                Sji      = Sji_line + Sj0;
            end

            S_network(iBus) = S_network(iBus) + Sij;
            S_network(jBus) = S_network(jBus) + Sji;

            Total_pow2gnd = Si0 + Sj0;
            RX_loss       = Sij_line + Sji_line;
            Total_loss    = Sij + Sji;

            I_line_flow = [I_line_flow; {iBus,jBus,Iij_line,Ii0,Iij,Iji_line,Ij0,Iji}];
            S_line_flow = [S_line_flow; {iBus,jBus,Sij_line,Si0,Sij,Sji_line,Sj0,Sji,Total_pow2gnd,RX_loss,Total_loss}];
        end

        I_line_flow.Properties.VariableNames = {
            'i','j','Iij_line','Ii0','Iij','Iji_line','Ij0','Iji'
        };
        S_line_flow.Properties.VariableNames = {
            'i','j','Sij_line','Si0','Sij','Sji_line','Sj0','Sji','Si0_Sj0','Sij_line_Sji_line','Total_loss'
        };

        Summary_line_flow = table( ...
            S_line_flow.i, S_line_flow.j, ...
            real(S_line_flow.Sij), imag(S_line_flow.Sij), ...
            real(S_line_flow.Sji), imag(S_line_flow.Sji), ...
            real(S_line_flow.Total_loss), imag(S_line_flow.Total_loss), ...
            'VariableNames', {'i','j','Pij','Qij','Pji','Qji','P_loss','Q_loss'} ...
        );
        Summary_line_flow = [Summary_line_flow; { NaN,NaN,NaN,NaN,NaN,NaN,sum(Summary_line_flow.P_loss),sum(Summary_line_flow.Q_loss) }];

        Q_injected = zeros(N,1);
        P_bus_loss = zeros(N,1);
        for kBus = 1:N
            Q_injected(kBus) = S_base*BusData.B(kBus)*abs(V(kBus))^2;
            P_bus_loss(kBus)= S_base*BusData.G(kBus)*abs(V(kBus))^2;
        end

        P_load    = BusData.Pload;
        Q_load    = BusData.Qload;
        P_network = real(S_network);
        Q_network = imag(S_network);
        P_gen     = P_network + P_load + P_bus_loss;
        Q_gen     = Q_network + Q_load - Q_injected;

        Phase_deg = rad2deg(angle(V));
        No_Bus    = BusData.Bus;

        Bus_information = table( ...
            No_Bus, abs(V), Phase_deg, P_gen, Q_gen, P_load, Q_load, Q_injected, P_bus_loss, ...
            'VariableNames', {'Bus','V','Phase','Pgen','Qgen','Pload','Qload','Qinj','Pbus_loss'} ...
        );
        Bus_information = [Bus_information; { NaN,NaN,NaN,sum(P_gen),sum(Q_gen),sum(P_load),sum(Q_load),sum(Q_injected),sum(P_bus_loss) }];
    end

    function loadExampleCallback()
        idx = get(popupEx,'Value');
        selBus = exampleCases(idx).bus;
        selBr  = exampleCases(idx).branch;
        busTable.Data    = selBus;
        branchTable.Data = selBr;
        tabgp.SelectedTab = dataTab;
    end

    function cleanupTimer()
        % (Clean up if needed)
    end
end
