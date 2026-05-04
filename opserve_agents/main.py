#!/usr/bin/env python3
"""OPServe CLI entrypoint for local testing."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from opserve_agents.team import run_analysis


async def main():
    """Run OPServe analysis locally."""
    print("=" * 80)
    print("OPServe — Operational Intelligence Platform")
    print("=" * 80)
    print()

    project = "Project Atlas"
    use_mock = True

    print(f"Analyzing: {project}")
    print(f"Using mock data: {use_mock}")
    print()
    print("Pipeline: Context Collector → Workflow Mapper → Risk Agent → Impact Analyzer → Role Translator")
    print()

    results = await run_analysis([project], use_mock=use_mock)

    print()
    print("=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    print()

    result = results.get(project, {})

    if result.get("status") == "success":
        analysis = result.get("analysis", {})
        print(f"Project Health: {analysis.get('overall_project_health', 'Unknown')}")
        print()

        if "role_specific_outputs" in analysis:
            outputs = analysis["role_specific_outputs"]

            print("EXECUTIVE SUMMARY")
            print("-" * 80)
            exec_summary = outputs.get("executive", {})
            print(exec_summary.get("summary", "No summary"))
            if exec_summary.get("decision_needed"):
                print(f"Decision Needed: {exec_summary['decision_needed']}")
            print()

            print("OPERATIONS CHECKLIST")
            print("-" * 80)
            ops = outputs.get("operations", {})
            for item in ops.get("checklist", []):
                print(f"  - {item}")
            print()

            print("ENGINEERING NEXT STEPS")
            print("-" * 80)
            eng = outputs.get("engineering", {})
            for step in eng.get("technical_next_steps", []):
                print(f"  - {step}")
            print()

        print("FULL ANALYSIS")
        print("-" * 80)
        print(json.dumps(analysis, indent=2))

    else:
        error = result.get("error", "Unknown error")
        print(f"Analysis failed: {error}")
        print()
        print("Full result:")
        print(json.dumps(result, indent=2))

    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
