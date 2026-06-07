# -*- coding: mbcs -*-
#
# Abaqus/CAE Release 2026 replay file
# Internal Version: 2025_09_23-22.43.03 RELr428 206049
# Run by duanj on Tue Jun  2 12:36:22 2026
#

# from driverUtils import executeOnCaeGraphicsStartup
# executeOnCaeGraphicsStartup()
#: Executing "onCaeGraphicsStartup()" in the site directory ...
from abaqus import *
from abaqusConstants import *
session.Viewport(name='Viewport: 1', origin=(1.075, 1.075), width=158.24, 
    height=106.64)
session.viewports['Viewport: 1'].makeCurrent()
from driverUtils import executeOnCaeStartup
executeOnCaeStartup()
#: Executing "onCaeStartup()" in the home directory ...
#: =======================================================
#: Abaqus MCP Plugin v4.0.0 (File IPC)
#: =======================================================
#: Home:   C:\Users\duanj\.abaqus-mcp
#: Abaqus: True
#: Start:  mcp_start()     (background, recommended)
#:         mcp_loop()      (blocking)
#: Stop:   mcp_stop()
#: Status: mcp_status()
#: =======================================================
execfile('_test_axi2.py', __main__.__dict__)
#: 模型 "AxiTest" 已创建.
print('RT script done')
#: RT script done
