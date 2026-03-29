#!/usr/bin/env bash
# Test all 8 combinations of JPEG validation flags.
# Each run streams /dev/video0 for up to 5 minutes.
# PASS = survived the full timeout.  FAIL = pipeline crashed early.

set -euo pipefail

TIMEOUT=300
DEVICE=/dev/video0
SCRIPT="$(dirname "$0")/gst_uvc_single_cam.py"

# ── test cases: label + flags ────────────────────────────────────────
LABELS=()
FLAGS=()

LABELS+=("all checks ON");             FLAGS+=("")
LABELS+=("--no-check-soi");            FLAGS+=("--no-check-soi")
LABELS+=("--no-check-eoi");            FLAGS+=("--no-check-eoi")
LABELS+=("--no-check-walk");           FLAGS+=("--no-check-walk")
LABELS+=("--no-check-soi --no-check-eoi");   FLAGS+=("--no-check-soi --no-check-eoi")
LABELS+=("--no-check-soi --no-check-walk");  FLAGS+=("--no-check-soi --no-check-walk")
LABELS+=("--no-check-eoi --no-check-walk");  FLAGS+=("--no-check-eoi --no-check-walk")
LABELS+=("all checks OFF");            FLAGS+=("--no-check-soi --no-check-eoi --no-check-walk")

TOTAL=${#LABELS[@]}

# ── results arrays ───────────────────────────────────────────────────
RESULTS=()
DURATIONS=()

echo "=== Validation Flag Test Suite ==="
echo "Device:  $DEVICE"
echo "Timeout: ${TIMEOUT}s per test"
echo "Script:  $SCRIPT"
echo ""

for i in $(seq 0 $((TOTAL - 1))); do
    label="${LABELS[$i]}"
    flags="${FLAGS[$i]}"
    echo "──────────────────────────────────────────────"
    echo "[$(( i + 1 ))/$TOTAL] Flags: $label"

    start_ts=$(date +%s)

    # shellcheck disable=SC2086
    set +e
    timeout "$TIMEOUT" python3 "$SCRIPT" "$DEVICE" $flags 2>&1
    rc=$?
    set -e

    end_ts=$(date +%s)
    elapsed=$(( end_ts - start_ts ))

    # exit 124 = timeout killed the process (survived full duration)
    if [ "$rc" -eq 0 ] || [ "$rc" -eq 124 ]; then
        RESULTS+=("PASS")
        echo ""
        echo "      Result: PASS (ran ${elapsed}s, exit $rc)"
    else
        RESULTS+=("FAIL")
        echo ""
        echo "      Result: FAIL (crashed at ${elapsed}s, exit $rc)"
    fi
    DURATIONS+=("$elapsed")
    echo ""
done

# ── summary table ────────────────────────────────────────────────────
echo "=== Summary ==="
printf "  %-45s  %-6s  %s\n" "FLAGS" "RESULT" "DURATION"
for i in $(seq 0 $((TOTAL - 1))); do
    printf "  %-45s  %-6s  %ss\n" "${LABELS[$i]}" "${RESULTS[$i]}" "${DURATIONS[$i]}"
done
