import subprocess

def run_cmd(*args):
    print(f"Running: {' '.join(args)}")
    res = subprocess.run(args, capture_output=True, text=True)
    print(f"RC: {res.returncode}")
    if res.stdout:
        print(f"STDOUT: {res.stdout.strip()}")
    if res.stderr:
        print(f"STDERR: {res.stderr.strip()}")
    print("-" * 40)

run_cmd("VBoxManage", "list", "vms")
run_cmd("VBoxManage", "createvm", "--name", "testvm123", "--ostype", "Linux_64", "--register")
run_cmd("VBoxManage", "list", "vms")
run_cmd("VBoxManage", "startvm", "testvm123", "--type", "headless")
run_cmd("VBoxManage", "unregistervm", "testvm123", "--delete")
