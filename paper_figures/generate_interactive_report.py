"""Generate interactive HTML report with embedded figures and navigation."""
from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER_FIGURES_OUTPUT = ROOT / "paper_figures" / "output"
PRESENTATIONS_DIR = ROOT / "presentations"


def image_to_base64(image_path: Path) -> str:
    """Convert image to base64 for embedding in HTML."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def generate_interactive_html():
    """Generate self-contained interactive HTML report."""

    # Collect all PNG figures
    figures = []
    for png_file in sorted(PAPER_FIGURES_OUTPUT.glob("fig*.png")):
        fig_num = png_file.stem.split("_")[0].replace("fig", "")
        fig_name = png_file.stem.replace(f"fig{fig_num}_", "").replace("_", " ").title()

        # Embed image as base64
        img_data = image_to_base64(png_file)

        figures.append({
            "num": fig_num,
            "name": fig_name,
            "filename": png_file.name,
            "data": img_data,
        })

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HW-1 Project Interactive Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}

        header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}

        nav {{
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 2px solid #dee2e6;
            position: sticky;
            top: 0;
            z-index: 100;
        }}

        nav h2 {{
            margin-bottom: 15px;
            color: #495057;
            font-size: 1.2em;
        }}

        .nav-buttons {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .nav-btn {{
            background: white;
            border: 2px solid #667eea;
            color: #667eea;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 0.9em;
            font-weight: 600;
        }}

        .nav-btn:hover {{
            background: #667eea;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}

        .nav-btn.active {{
            background: #667eea;
            color: white;
        }}

        main {{
            padding: 40px;
        }}

        .figure-section {{
            display: none;
            animation: fadeIn 0.5s;
        }}

        .figure-section.active {{
            display: block;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .figure-header {{
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 3px solid #667eea;
        }}

        .figure-header h2 {{
            color: #2c3e50;
            font-size: 2em;
            margin-bottom: 10px;
        }}

        .figure-header .meta {{
            color: #6c757d;
            font-size: 0.9em;
        }}

        .figure-image {{
            width: 100%;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
            transition: transform 0.3s;
        }}

        .figure-image:hover {{
            transform: scale(1.02);
            cursor: zoom-in;
        }}

        .figure-description {{
            background: #f8f9fa;
            padding: 25px;
            border-radius: 12px;
            line-height: 1.8;
            color: #495057;
        }}

        .figure-description h3 {{
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}

        .figure-description p {{
            margin-bottom: 15px;
        }}

        .figure-description ul {{
            margin-left: 25px;
            margin-bottom: 15px;
        }}

        .figure-description li {{
            margin-bottom: 8px;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}

        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            border: 2px solid #e9ecef;
            text-align: center;
            transition: all 0.3s;
        }}

        .stat-card:hover {{
            border-color: #667eea;
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.2);
        }}

        .stat-card .number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}

        .stat-card .label {{
            color: #6c757d;
            font-size: 0.9em;
        }}

        footer {{
            background: #2c3e50;
            color: white;
            padding: 30px;
            text-align: center;
        }}

        footer p {{
            margin-bottom: 10px;
        }}

        .lightbox {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            cursor: zoom-out;
        }}

        .lightbox.active {{
            display: flex;
        }}

        .lightbox img {{
            max-width: 95%;
            max-height: 95%;
            border-radius: 8px;
            box-shadow: 0 0 50px rgba(255,255,255,0.3);
        }}

        .download-btn {{
            background: #28a745;
            color: white;
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            margin-top: 20px;
            transition: all 0.3s;
        }}

        .download-btn:hover {{
            background: #218838;
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(40, 167, 69, 0.4);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>HW-1 Quasi-Passive Biped Robot</h1>
            <p>Interactive Figure Report | V01-V24 Development Journey</p>
            <p style="margin-top: 10px; font-size: 0.9em;">Generated: 2026-06-05 | Total Figures: {len(figures)}</p>
        </header>

        <nav>
            <h2>Navigate Figures</h2>
            <div class="nav-buttons" id="navButtons">
                <!-- Buttons generated by JavaScript -->
            </div>
        </nav>

        <main id="mainContent">
            <!-- Figure sections generated by JavaScript -->
        </main>

        <footer>
            <p><strong>Project:</strong> hw-1 Quasi-Passive Biped Robot</p>
            <p><strong>Author:</strong> 段泽琪 (学号: 2024211317)</p>
            <p><strong>Institution:</strong> 工业设计博士</p>
            <p style="margin-top: 15px; opacity: 0.8;">All figures generated at 300 DPI | IEEE/Elsevier compatible</p>
        </footer>
    </div>

    <div class="lightbox" id="lightbox">
        <img id="lightboxImg" src="" alt="Zoomed figure">
    </div>

    <script>
        const figures = {json.dumps(figures, ensure_ascii=False)};

        const descriptions = {{
            "1": {{
                "title": "Version Evolution Timeline",
                "description": "Development progress from V01 (Compass Gait) to V24 (Sim-to-Real). Top panel shows performance maturity index progression. Bottom panel shows category distribution across versions.",
                "highlights": [
                    "V05: Passive limit cycle proof via Poincaré analysis",
                    "V10: Rolling foot biomimetic gait (lowest CoT = 0.048)",
                    "V13: Event-driven FSM control with phase detection",
                    "V18-V20: 3D lateral stability exploration (negative results)",
                    "V24: Sim-to-real transfer and hardware deployment"
                ]
            }},
            "2": {{
                "title": "Parameter Space Stability Domain",
                "description": "Heatmap showing gait stability (steps before failure) as a function of hip and ankle spring stiffness. Reveals optimal parameter regions and design tradeoffs.",
                "highlights": [
                    "White star indicates globally optimal parameters",
                    "Blue circle (V10) and red square (V13) show actual designs",
                    "Contour lines mark stability thresholds (10, 50, 80 steps)",
                    "Narrow stability basin demonstrates sensitivity to parameter choices"
                ]
            }},
            "3": {{
                "title": "Energy Efficiency Analysis",
                "description": "Cost of Transport comparison across quasi-passive versions. Demonstrates mechanical energy decomposition and KE-PE exchange during periodic gait.",
                "highlights": [
                    "V10 achieves lowest CoT of 0.048 (comparable to humans)",
                    "Mechanical energy remains nearly constant during steady gait",
                    "V11 terrain case shows larger fluctuations due to irregularities",
                    "Energy efficiency validates quasi-passive design philosophy"
                ]
            }},
            "4": {{
                "title": "Phase Portrait and Limit Cycle",
                "description": "Hip and knee joint phase space trajectories showing periodic motion. Red circles indicate touchdown events (Poincaré section). Demonstrates orbital stability.",
                "highlights": [
                    "Closed trajectories confirm limit cycle behavior",
                    "Poincaré section shows consistent touchdown states",
                    "Configuration space projection reveals coupled coordination",
                    "Phase portraits validate passive dynamics exploitation"
                ]
            }},
            "5": {{
                "title": "V22 Hardware Design Specifications",
                "description": "Mechanical schematic showing 5-link bipedal structure with total leg length 1.0 m. Details mass distribution and actuator specifications.",
                "highlights": [
                    "74% mass concentrated at hip (top-heavy design)",
                    "Dynamixel MX-64AR motors (4 units, 6 Nm each)",
                    "Total cost <8000 RMB (low-cost research platform)",
                    "Ready for fabrication with CAD files and BOM"
                ]
            }},
            "6": {{
                "title": "Friction Compensation Analysis",
                "description": "Complete analysis of motor friction problem (V16) and compensation solution (V13.7). Demonstrates failure bands, compensation effectiveness, and stability restoration.",
                "highlights": [
                    "V16: Motor friction τ_C > 0.5 Nm destroys limit cycle",
                    "V13.7: Feedforward compensation restores 180-step stability",
                    "Phase portrait shows degradation and restoration",
                    "Floquet analysis confirms compensation brings |λ| < 1",
                    "Energy dissipation prevented by compensation strategy"
                ]
            }},
            "7": {{
                "title": "State Estimation Robustness",
                "description": "V17 sensor noise tolerance analysis. Shows Kalman filter effectiveness with encoder quantization and contact detection timing requirements.",
                "highlights": [
                    "System tolerates up to 5× baseline noise with encoders",
                    "12-bit MX-64AR encoder quantization: σ ≈ 0.75 mrad",
                    "Contact detection delay <15 ms required for 80%+ success",
                    "Kalman filtering prevents drift over 50+ gait cycles",
                    "State estimation enables closed-loop phase-based control"
                ]
            }},
            "8": {{
                "title": "3D Lateral Stability Failure Analysis",
                "description": "Systematic analysis of V18-V20 negative results. Demonstrates fundamental limits of passive lateral stability in compass-gait morphology.",
                "highlights": [
                    "V18: All passive configurations failed within 2 steps",
                    "V19: Active hip abduction up to 30 Nm insufficient",
                    "V20: Step width control failed regardless of target",
                    "Root cause: Unstable eigenvalues |λ| > 1.3 in lateral/yaw modes",
                    "Negative result demonstrates physical limits, not implementation flaws"
                ]
            }},
            "9": {{
                "title": "Poincaré Convergence Proof",
                "description": "V5 limit cycle stability proof via Poincaré analysis. Shows exponential convergence from multiple initial conditions with Floquet multiplier analysis.",
                "highlights": [
                    "Five initial conditions converge to same limit cycle",
                    "Poincaré map demonstrates fixed point convergence",
                    "Exponential convergence rate: λ ≈ 0.3 per step",
                    "All Floquet multipliers inside unit circle (|λ| < 1)",
                    "Periodic energy exchange confirms passive dynamics"
                ]
            }}
        }};

        // Generate navigation buttons
        const navButtons = document.getElementById('navButtons');
        figures.forEach((fig, index) => {{
            const btn = document.createElement('button');
            btn.className = 'nav-btn' + (index === 0 ? ' active' : '');
            btn.textContent = `Fig ${{fig.num}}: ${{fig.name}}`;
            btn.onclick = () => showFigure(index);
            navButtons.appendChild(btn);
        }});

        // Generate figure sections
        const mainContent = document.getElementById('mainContent');
        figures.forEach((fig, index) => {{
            const section = document.createElement('section');
            section.className = 'figure-section' + (index === 0 ? ' active' : '');
            section.id = `figure-${{fig.num}}`;

            const desc = descriptions[fig.num] || {{}};

            section.innerHTML = `
                <div class="figure-header">
                    <h2>Figure ${{fig.num}}: ${{desc.title || fig.name}}</h2>
                    <div class="meta">
                        <strong>Filename:</strong> ${{fig.filename}} |
                        <strong>Resolution:</strong> 300 DPI |
                        <strong>Format:</strong> PNG
                    </div>
                </div>

                <img class="figure-image"
                     src="data:image/png;base64,${{fig.data}}"
                     alt="Figure ${{fig.num}}"
                     onclick="openLightbox(this.src)">

                <div class="figure-description">
                    <h3>Description</h3>
                    <p>${{desc.description || 'No description available.'}}</p>

                    ${{desc.highlights ? `
                        <h3>Key Highlights</h3>
                        <ul>
                            ${{desc.highlights.map(h => `<li>${{h}}</li>`).join('')}}
                        </ul>
                    ` : ''}}
                </div>
            `;

            mainContent.appendChild(section);
        }});

        function showFigure(index) {{
            // Update active button
            document.querySelectorAll('.nav-btn').forEach((btn, i) => {{
                btn.classList.toggle('active', i === index);
            }});

            // Update active section
            document.querySelectorAll('.figure-section').forEach((section, i) => {{
                section.classList.toggle('active', i === index);
            }});

            // Scroll to top
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        function openLightbox(src) {{
            const lightbox = document.getElementById('lightbox');
            const lightboxImg = document.getElementById('lightboxImg');
            lightboxImg.src = src;
            lightbox.classList.add('active');
        }}

        document.getElementById('lightbox').onclick = function() {{
            this.classList.remove('active');
        }};

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {{
            const currentIndex = Array.from(document.querySelectorAll('.figure-section'))
                .findIndex(s => s.classList.contains('active'));

            if (e.key === 'ArrowRight' && currentIndex < figures.length - 1) {{
                showFigure(currentIndex + 1);
            }} else if (e.key === 'ArrowLeft' && currentIndex > 0) {{
                showFigure(currentIndex - 1);
            }} else if (e.key === 'Escape') {{
                document.getElementById('lightbox').classList.remove('active');
            }}
        }});
    </script>
</body>
</html>"""

    output_path = ROOT / "presentations" / "interactive_report.html"
    output_path.write_text(html_content, encoding="utf-8")

    print(f"[OK] Interactive HTML report: {output_path}")
    print(f"     Size: {output_path.stat().st_size / (1024*1024):.2f} MB")
    print(f"     Figures embedded: {len(figures)}")
    print(f"\n     Open in browser: file:///{output_path.as_posix()}")

    return output_path


if __name__ == "__main__":
    print("=" * 70)
    print("INTERACTIVE HTML REPORT GENERATOR")
    print("=" * 70)
    print("\nGenerating self-contained HTML report with embedded figures...\n")

    generate_interactive_html()

    print("\n" + "=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
