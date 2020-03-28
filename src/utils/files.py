import shutil as shutil
import os
import subprocess
import glob


def count_lines(file_path):
    return sum(1 for line in open(file_path))


def copy_file(src, dst):
    shutil.copyfile(src, dst)


def copy_and_overwrite_dir(from_path, to_path):
    if os.path.exists(to_path):
        shutil.rmtree(to_path)
    shutil.copytree(from_path, to_path)


def change_permission(path, permissions):
    subprocess.call(['chmod', '-R', permissions, path])


def create_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def get_files_into_dir(path, regex='*', full_path=False):
    files_full_path = glob.glob(path + '/' + regex)

    if full_path:
        return files_full_path
    else:
        return [path.split("/")[-1] for path in files_full_path]


def get_file_absolute_path(rel_path):
    return os.path.abspath(rel_path)


def get_all_subfiles(path):
    """
    return also files in subfolders
    :param path:
    :return:
    """

    list_of_files = list()
    for (dirpath, dirnames, filenames) in os.walk(path):
        list_of_files += [os.path.join(dirpath, file) for file in filenames]
    return list_of_files
