import traceback
from tests.test_optimizer import test_compute_salaries_clamping, test_compute_salaries_rounding, test_run_optimizer_basic_execution

print("Running test_compute_salaries_clamping")
try:
    test_compute_salaries_clamping()
    print("PASS")
except Exception as e:
    print("FAIL:", e)
    traceback.print_exc()

print("Running test_compute_salaries_rounding")
try:
    test_compute_salaries_rounding()
    print("PASS")
except Exception as e:
    print("FAIL:", e)
    traceback.print_exc()

print("Running test_run_optimizer_basic_execution")
try:
    test_run_optimizer_basic_execution()
    print("PASS")
except Exception as e:
    print("FAIL:", e)
    traceback.print_exc()
