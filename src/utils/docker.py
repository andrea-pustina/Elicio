import src.utils.shell as shell
import time
import socket


def unblock_docker_volume(container_volume_path, container_name, docker_compose_path='', user='root'):
    """
    :param container_volume_path: the path of the volume into the container
    :param container_name: container name
    :param docker_compose_path:  path to the dir where is docker-compose.yml file
    :return: None
    """
    shell.execute_cmd(['docker-compose', 'exec', '-T', '--user', 'root', container_name, 'chown', '-R', '{}:{}'.format(user, user), container_volume_path], cwd=docker_compose_path)
    shell.execute_cmd(['docker-compose', 'exec', '-T', '--user', 'root', container_name, 'chmod', '-R', '777', container_volume_path], cwd=docker_compose_path)


def docker_compose(cmd, docker_compose_path):
    shell.execute_cmd_shell('docker-compose ' + cmd, cwd=docker_compose_path, verbose=False)


def wait_for_port(port, host='localhost', timeout=5.0):
    """Wait until a port starts accepting TCP connections.
    Args:
        port (int): Port number.
        host (str): Host address on which the port should exist.
        timeout (float): In seconds. How long to wait before raising errors.
    Raises:
        TimeoutError: The port isn't accepting connection after time specified in `timeout`.
    """
    start_time = time.perf_counter()
    while True:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                break
        except OSError as ex:
            time.sleep(0.01)
            if time.perf_counter() - start_time >= timeout:
                raise TimeoutError('Waited too long for the port {} on host {} to start accepting '
                                   'connections.'.format(port, host)) from ex

    time.sleep(1)