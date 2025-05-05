
" By running this file you will be able to run all endpoints tests"
import subprocess
subprocess.run(["pytest", "tests/", "--disable-warnings"])
