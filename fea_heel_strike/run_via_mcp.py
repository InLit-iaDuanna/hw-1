"""
Run heel-strike FEA via Abaqus MCP server.
This script is called from Claude Code MCP integration.
"""

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_SCRIPT = os.path.join(SCRIPT_DIR, "build_heel_strike_model.py")
POST_SCRIPT = os.path.join(SCRIPT_DIR, "postprocess_heel_strike.py")


def get_build_script_content():
    """Return the build script content for MCP execute_script."""
    with open(BUILD_SCRIPT) as f:
        return f.read()


def get_post_script_content():
    """Return the post-processing script content for MCP execute_script."""
    with open(POST_SCRIPT) as f:
        return f.read()


if __name__ == "__main__":
    print("Heel-Strike FEA Project")
    print("=" * 40)
    print()
    print("Usage:")
    print("  1. Start Abaqus/CAE with MCP plugin loaded")
    print("  2. Run build script:  abaqus cae noGUI=build_heel_strike_model.py")
    print("  3. Submit job:        abaqus job=Job_HeelStrike cpus=4")
    print("  4. Post-process:      abaqus cae noGUI=postprocess_heel_strike.py")
    print()
    print("Or via MCP (Claude Code):")
    print("  - check_abaqus_connection")
    print("  - execute_script(build_heel_strike_model.py)")
    print("  - submit_job('Job_HeelStrike')")
    print("  - execute_script(postprocess_heel_strike.py)")
    print()
    print("Files:")
    print(f"  Build:       {BUILD_SCRIPT}")
    print(f"  Post:        {POST_SCRIPT}")
    print(f"  Conditions:  {os.path.join(SCRIPT_DIR, 'impact_conditions.py')}")
    print(f"  Output dir:  {os.path.join(SCRIPT_DIR, 'out')}")
