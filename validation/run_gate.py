"""Run 2 Part A + null test again, through the app WITH the final 20% check (change C), same fresh seeds as Run 2."""
import sys
sys.argv = ['x']
import common, run2
assert 'merge' in str(common.APP)
run2.run_a(); run2.run_null()
