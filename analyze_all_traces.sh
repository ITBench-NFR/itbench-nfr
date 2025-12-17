#!/bin/bash

# Script to run analyze_traces.py for each observations_dump.json in ciso_traces_* folders

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYZE_SCRIPT="${SCRIPT_DIR}/analyze_traces.py"

# Check if the analyze script exists
if [[ ! -f "$ANALYZE_SCRIPT" ]]; then
    echo "Error: analyze_traces.py not found at $ANALYZE_SCRIPT"
    exit 1
fi

# Find all observations_dump.json files in ciso_traces_* directories
find "${SCRIPT_DIR}/../ciso_traces"_* -name "observations_dump.json" 2>/dev/null | while read -r json_file; do
    # Get the directory containing the JSON file
    dir=$(dirname "$json_file")
    output_file="${dir}/analysis.log"
    
    echo "Processing: $json_file"
    echo "Output: $output_file"
    
    # Run the analysis script and redirect output to analysis.log
    python3 "$ANALYZE_SCRIPT" "$json_file" > "$output_file" 2>&1
    
    if [[ $? -eq 0 ]]; then
        echo "  ✓ Done"
    else
        echo "  ✗ Failed"
    fi
    echo ""
done

echo "All analyses complete!"
