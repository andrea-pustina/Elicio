import subprocess


def execute_cmd(array_cmd, cwd='.'):
    p = subprocess.Popen(array_cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = p.communicate()
    return output, error


def execute_cmd_shell(cmd, cwd='.', verbose=True):
    if verbose:
        p = subprocess.Popen(cmd, cwd=cwd, shell=True)
        p.wait()
        print('\n\n')
        print(p.stderr)
    else:
        p = subprocess.Popen(cmd, cwd=cwd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        p.wait()

    return p
