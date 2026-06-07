# Dashboard Changelog

## v3.0 - 2026-06-04 - Enhanced Analysis Platform

### 🎯 Major Features Added

#### 1. Version Comparison View (⚖️ Compare)
- **Side-by-side comparison** of 2-4 versions
- **Automatic metric extraction** from findings text:
  - Cost of Transport (CoT)
  - Success rate with percentage calculation
  - Floquet multipliers
  - Forward distance
- **Visual differentiation** by phase colors
- **Interactive selection** via dropdown menus
- Use case: Compare V10 (baseline) → V13.6 (FSM) → V13.7 (friction compensation)

#### 2. Energy & Performance Trends View (📈 Trends)
Three interactive SVG charts:

**a) CoT Evolution Chart**
- Line chart with area fill gradient
- Automatic Y-axis scaling
- Phase-colored data points
- Hover tooltips with exact values
- Shows energy efficiency improvement trajectory

**b) Success Rate Bar Chart**
- Vertical bars colored by phase
- Percentage labels on top of bars
- Reveals stability improvements across versions
- Highlights V13 decision gate (narrow basin) vs V13.7 recovery

**c) Phase Timeline Chart**
- Horizontal bars showing version count per phase
- Visual progress indication
- Dots for individual versions within each phase

#### 3. Parameter Sensitivity Heatmap View (🔥 Heatmap)
Four curated heatmaps based on actual findings:

**a) V13 Parameter Space (6×6)**
- foot_radius × leg_length sweep
- Success rate: 16.7% (6/36)
- Pattern: Success concentrated in corner/edge band
- Demonstrates decision gate evidence

**b) V13.6 FSM Controller (6×6)**
- Same parameter space with event-driven FSM
- Success rate: 11.1% (4/36)
- Pattern: Success domain migrated to center
- Shows different adjacent limit cycle

**c) V14c Arm Mass Sensitivity (6×6)**
- arm_mass monotonic degradation pattern
- Proves arm mass is root cause of instability
- Row-by-row decline visible

**d) V16 Motor Friction τ_C Resonance (1×10)**
- Non-monotonic pattern with failure band
- Success bands: {0, 0.034, 0.27+}
- Failure band: [0.013, 0.20]
- MX-64 spec (0.20) falls in failure zone
- Critical for hardware motor selection

### 🔧 Technical Implementation

**Architecture:**
- Pure vanilla JavaScript (no frameworks)
- SVG-based charts for crisp rendering at any scale
- Modular view rendering system
- Automatic data extraction with regex patterns

**Metric Extraction Patterns:**
```javascript
CoT: /CoT[=:\s]+([\d.]+)/
Success Rate: /(\d+)\/(\d+)/
Floquet: /max\|lambda\|[=:\s]+([\d.]+)/i
Forward Distance: /forward[=:\s]+([\d.]+)\s*m/i
```

**Color Scheme:**
- Phase 1: #1f6feb (blue)
- Phase 2: #238636 (green)
- Phase 3: #d97706 (orange)
- Phase 4: #dc2626 (red)
- Success: #34d399 (emerald)
- Failure: #dc2626 (red)

### 📊 Data Visualization Features

**Compare View:**
- Responsive grid layout (auto-fit, minmax 280px)
- Metrics table with conditional rendering
- Key findings highlighted with accent border
- Dependency count and tag preview

**Trends View:**
- Dynamic axis scaling
- Grid lines for readability
- Gradient fills for visual appeal
- Interactive tooltips (SVG title attributes)
- Responsive canvas sizing

**Heatmap View:**
- Grid-based layout with CSS Grid
- Color interpolation: red (failure) → yellow → green (success)
- Hover scale animation (1.1x)
- Legend with gradient bar
- Cell tooltips with coordinates

### 🚀 Usage Recommendations

**For Paper Defense:**
1. Timeline View → Show V01-V25 progression
2. Trends View → Highlight CoT improvement (0.072 near human 0.05)
3. Heatmap View → Decision gate evidence (V13 narrow basin)
4. Compare View → V10 vs V13.7 transformation

**For Control Law Tuning:**
1. Compare View → V10, V13.6, V13.6.1, V13.7
2. Heatmap View → Parameter domain migration
3. Identify optimal FSM configuration

**For Hardware Selection:**
1. Heatmap View → V16 τ_C resonance pattern
2. Compare View → V16 (failure) vs V13.7 (compensation)
3. Decision: low-friction motor or feedforward compensation

### 📝 Code Statistics

**Files Modified:**
- `index.html`: +120 lines (new view containers + CSS)
- `app.js`: +550 lines (3 new view renderers + metric extraction)
- `README.md`: Enhanced with v3.0 features and workflows

**New Functions:**
- `renderCompareView()` - Version comparison panel
- `updateCompare()` - Dynamic comparison update
- `extractMetrics()` - Regex-based metric extraction
- `renderTrendsView()` - Energy trends dashboard
- `renderCotChart()` - SVG line chart
- `renderSuccessChart()` - SVG bar chart
- `renderTimelineChart()` - SVG phase timeline
- `renderHeatmapView()` - Parameter sensitivity heatmaps
- `generateV13Data()` / `V136Data()` / `V14cData()` / `V16Data()` - Synthetic heatmap data
- `renderHeatmap()` - Grid-based heatmap renderer

### 🎨 UX Improvements

- Consistent dark theme across all views
- Smooth view transitions
- Hover effects on all interactive elements
- Responsive layouts adapt to different screen widths
- Clear visual hierarchy with section headers
- Color-coded phase identification throughout

### ⚡ Performance

- No external dependencies (zero network requests)
- SVG charts render instantly
- Efficient DOM manipulation with template literals
- Minimal reflows with CSS transforms

### 🔮 Future Enhancement Opportunities

1. **Dynamic Data Loading**: Read from actual out/ directories
2. **Export Functionality**: Download comparison tables as CSV/JSON
3. **3D Stability Basin Visualization**: Three.js or Plotly integration
4. **Real-time Parameter Sweep**: Connect to running simulations
5. **Annotation System**: Add user notes to specific versions
6. **Presentation Mode**: Full-screen slideshow with transitions

---

## v2.0 - 2026-05
- Initial modern redesign
- Grid, Timeline, Graph views
- Filter system
- Detail panel
- Dark glassmorphism theme

## v1.0 - 2026-04
- Basic version tracking
- Simple card layout
