================================================================================
ANIMATION RENDERING PERFORMANCE REPORT
================================================================================

Total versions tested: 6
Successful: 6
Failed: 0

--------------------------------------------------------------------------------
DETAILED RESULTS
--------------------------------------------------------------------------------

Version: V10
  Success: YES
  Wall Time: 12.12 s
  Simulation Duration: 4.00 s
  Frame Count: 240
  Target FPS: 60
  Render Speed: 19.8 fps
  Realtime Factor: 0.33x
  File Size: 0.69 MB
  Efficiency: 0.06 MB/s

Version: V13.6
  Success: YES
  Wall Time: 12.62 s
  Simulation Duration: 11.99 s
  Frame Count: 719
  Target FPS: 60
  Render Speed: 57.0 fps
  Realtime Factor: 0.95x
  File Size: 0.79 MB
  Efficiency: 0.06 MB/s

Version: V13.7
  Success: YES
  Wall Time: 12.25 s
  Simulation Duration: 11.99 s
  Frame Count: 719
  Target FPS: 60
  Render Speed: 58.7 fps
  Realtime Factor: 0.98x
  File Size: 0.84 MB
  Efficiency: 0.07 MB/s

Version: V14
  Success: YES
  Wall Time: 12.65 s
  Simulation Duration: 4.00 s
  Frame Count: 240
  Target FPS: 60
  Render Speed: 19.0 fps
  Realtime Factor: 0.32x
  File Size: 0.71 MB
  Efficiency: 0.06 MB/s

Version: V16
  Success: YES
  Wall Time: 12.14 s
  Simulation Duration: 3.55 s
  Frame Count: 212
  Target FPS: 60
  Render Speed: 17.5 fps
  Realtime Factor: 0.29x
  File Size: 0.83 MB
  Efficiency: 0.07 MB/s

Version: V17
  Success: YES
  Wall Time: 12.10 s
  Simulation Duration: 11.99 s
  Frame Count: 719
  Target FPS: 60
  Render Speed: 59.4 fps
  Realtime Factor: 0.99x
  File Size: 0.71 MB
  Efficiency: 0.06 MB/s

================================================================================
KEY FINDINGS
================================================================================

Fastest Rendering: V17 (12.10s)
Slowest Rendering: V14 (12.65s)
Speed Difference: 1.05x

Smallest File: V10 (0.69 MB)
Largest File: V13.7 (0.84 MB)

Average Wall Time: 12.31s
Average Render Speed: 38.6 fps
Average File Size: 0.76 MB

================================================================================
PARALLEL RENDERING ANALYSIS
================================================================================

Threads: 1
  Wall Time: 73.95s
  Speedup: 1.00x
  Efficiency: 100.0%
  Tasks Completed: 6/6

Threads: 2
  Wall Time: 42.68s
  Speedup: 1.73x
  Efficiency: 86.6%
  Tasks Completed: 6/6

Threads: 4
  Wall Time: 31.64s
  Speedup: 2.34x
  Efficiency: 58.4%
  Tasks Completed: 6/6

RECOMMENDATIONS:
  Optimal Thread Count: 1 (efficiency: 100.0%)

================================================================================
OPTIMIZATION RECOMMENDATIONS
================================================================================

Performance Analysis:

Short animations (< 6s simulation): avg 12.30s wall time
Long animations (>= 6s simulation): avg 12.32s wall time

Observation: Wall time is roughly constant regardless of simulation duration.
This suggests rendering overhead dominates (initialization, frame processing).

Slow rendering versions (< 30 fps):
  - V10: 19.8 fps, 240 frames, 12.12s
  - V14: 19.0 fps, 240 frames, 12.65s
  - V16: 17.5 fps, 212 frames, 12.14s

Fast rendering versions (>= 30 fps):
  - V13.6: 57.0 fps, 719 frames, 12.62s
  - V13.7: 58.7 fps, 719 frames, 12.25s
  - V17: 59.4 fps, 719 frames, 12.10s

RECOMMENDATIONS:

1. Reduce initialization overhead:
   - Pre-load models and renderer objects
   - Batch multiple animations in one run

2. For slow versions (V10, V14, V16):
   - These have shorter simulations but similar wall time
   - Consider extending simulation duration to amortize startup cost
   - Or batch render multiple scenarios together

3. Optimize frame rendering loop:
   - Profile annotation functions (PIL/ImageDraw operations)
   - Cache font objects and reduce text rendering calls
   - Pre-compute interpolation arrays instead of per-frame np.interp

4. Parallel rendering:
   - Current wall time ~12s per version
   - Use --parallel flag to test multi-threaded rendering
   - Expected speedup: 2-3x with 4 threads

5. Resolution/quality trade-offs:
   - Test 1080p rendering to compare file size vs time
   - Consider variable frame rate (30fps for previews, 60fps for final)


================================================================================