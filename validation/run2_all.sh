#!/usr/bin/env bash
# Run 2, everything in sequence (nothing else on the CPU). Log: validation/cache/run2_log.txt
export NUDGE_APP=validation/app_v2 NUDGE_RUN=run2 PYTHONIOENCODING=utf-8
PY=validation/.venv/Scripts/python; L=validation/cache/run2_log.txt
f() { grep --line-buffered -v "WARNING\|No runtime\|ScriptRunContext\|: part [0-9] of\|Checking \"" ; }
echo "== Run 2 start $(date '+%d %b %H:%M')" >> $L
for step in sample a null d; do echo "-- $step $(date +%H:%M)" >> $L; $PY validation/run2.py $step 2>&1 | f >> $L; done
echo "-- C function path $(date +%H:%M)" >> $L; $PY -c "import sys; sys.path.insert(0,'validation'); import part_c; part_c.run_all()" 2>&1 | f >> $L
echo "-- C page layer $(date +%H:%M)" >> $L; (cd validation && ../$PY apptest_page.py 2>&1 | f >> ../$L)
echo "-- C4 timing $(date +%H:%M)" >> $L; $PY validation/time_c4.py 2>&1 | f >> $L
echo "-- B $(date +%H:%M)" >> $L; $PY validation/run2.py b 2>&1 | f >> $L
for spec in "2 100000" "2 200000" "12 100000"; do echo "-- timing $spec $(date +%H:%M)" >> $L; $PY validation/run2.py timing $spec 2>&1 | f >> $L; done
echo "== Run 2 end $(date '+%d %b %H:%M')" >> $L
