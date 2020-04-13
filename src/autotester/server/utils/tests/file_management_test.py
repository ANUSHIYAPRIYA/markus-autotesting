from autotester.server.utils.file_management import (
    clean_dir_name,
    random_tmpfile_name,
    recursive_iglob,
    copy_tree,
    ignore_missing_dir_error,
    move_tree,
    fd_lock,
    fd_open,
)
import os.path
import tempfile
import shutil
from autotester.config import config
import pytest
import fakeredis

from autotester.server.utils import string_management
from autotester.server.utils.redis_management import get_test_script_key

FILES_DIRNAME = config["_workspace_contents", "_files_dir"]
CURRENT_TEST_SCRIPT_HASH = config["redis", "_current_test_script_hash"]


@pytest.fixture
def empty_dir():
    with tempfile.TemporaryDirectory() as empty_directory:
        yield empty_directory


@pytest.fixture
def dir_has_onefile():
    with tempfile.TemporaryDirectory() as dir:
        with tempfile.NamedTemporaryFile(dir=dir) as file:
            yield dir, file.name


@pytest.fixture
def dir_has_onedir():
    with tempfile.TemporaryDirectory() as dir:
        with tempfile.TemporaryDirectory(dir=dir) as sub_dir:
            yield dir, sub_dir


@pytest.fixture
def nested_fd():
    with tempfile.TemporaryDirectory() as root_dir:
        with tempfile.TemporaryDirectory(dir=root_dir) as sub_dir1:
            with tempfile.TemporaryDirectory(dir=sub_dir1) as sub_dir2:
                with tempfile.NamedTemporaryFile(dir=sub_dir2) as file:
                    yield root_dir, sub_dir1, sub_dir2, file.name


def list_of_fd(file_or_dir):
    dir = []
    files = []
    for i in file_or_dir:
        dir.append(i[1]) if i[0] == "d" else files.append(i[1])
    return dir, files


def test_clean_dir_name():
    a = "markus/address"
    b = a.replace("/", "_")
    assert clean_dir_name(a) == b


def test_random_tmpfile_name():
    tmp_file_1 = random_tmpfile_name()
    tmp_file_2 = random_tmpfile_name()
    assert not tmp_file_1 == tmp_file_2


class TestRecursiveIglob:
    def test_empty_dir(self, empty_dir):
        """
        When the Directory is empty
        """
        file_or_dir = list(recursive_iglob(empty_dir))
        dir, files = list_of_fd(file_or_dir)
        assert not dir and not files

    def test_dir_has_onefile(self, dir_has_onefile):
        """
        When the Directory has only one file
        """
        root_dir, file = dir_has_onefile
        file_or_dir = list(recursive_iglob(root_dir))
        dir, files = list_of_fd(file_or_dir)
        assert not dir
        assert len(files) == 1 and file in files
        assert os.path.exists(files[0])

    def test_dir_has_onedir(self, dir_has_onedir):
        """
        When the Dirctory has only one sub directory
        """
        root_dir, sub_dir = dir_has_onedir
        file_or_dir = list(recursive_iglob(root_dir))
        dir, files = list_of_fd(file_or_dir)
        assert not files
        assert len(dir) == 1 and sub_dir in dir
        assert os.path.exists(dir[0])

    def test_dir_has_nestedfd(self, nested_fd):
        """
        When the files are nested in subdirectories more than 2 directories deep
        """
        root_dir, sub_dir1, sub_dir2, file = nested_fd
        file_or_dir = list(recursive_iglob(root_dir))
        dir, files = list_of_fd(file_or_dir)
        assert all(os.path.exists(d) for d in dir)
        assert all(os.path.exists(f) for f in files)
        assert sub_dir1 in dir and sub_dir2 in dir
        assert file in files


class TestCopyTree:
    def test_empty_dir(self, empty_dir, dir_has_onefile):
        """
        When the Source Directory is empty
        """
        source_dir = empty_dir
        dest_dir, file = dir_has_onefile
        list_fd_bef_copy = os.listdir(dest_dir)
        copy_tree(source_dir, dest_dir)
        list_fd_after_copy = os.listdir(dest_dir)
        assert len(list_fd_bef_copy) == len(list_fd_after_copy)

    def test_dir_has_onefile(self, dir_has_onefile, empty_dir):
        """
        When the Source Directory has only one file
        """
        source_dir, source_file = dir_has_onefile
        dest_dir = empty_dir
        copy_tree(source_dir, dest_dir)
        copied_file = os.path.join(dest_dir, os.path.basename(source_file))
        assert os.path.exists(copied_file)

    def test_dir_has_onedir(self, dir_has_onedir, empty_dir):
        """
        When the Source Dirctory has only one sub directory
        """
        source_dir, sub_dir = dir_has_onedir
        dest_dir = empty_dir
        copy_tree(source_dir, dest_dir)
        copied_dir = os.path.join(dest_dir, os.path.basename(sub_dir))
        assert os.path.exists(copied_dir)

    def test_dir_has_nestedfd(self, empty_dir, nested_fd):
        """
        When the files are nested in subdirectories more than 2 directories deep
        """
        dest_dir = empty_dir
        source_dir, sub_dir1, sub_dir2, source_file = nested_fd
        copy_tree(source_dir, dest_dir)
        copied_dir1 = os.path.join(dest_dir, os.path.basename(sub_dir1))
        copied_dir2 = os.path.join(copied_dir1, os.path.basename(sub_dir2))
        copied_file = os.path.join(copied_dir2, os.path.basename(source_file))
        assert os.path.exists(copied_dir1)
        assert os.path.exists(copied_dir2)
        assert os.path.exists(copied_file)


def test_ignore_missing_dir_error():
    dir = tempfile.mkdtemp()
    shutil.rmtree(dir)
    shutil.rmtree(dir, onerror=ignore_missing_dir_error)


class TestMoveTree:
    def test_empty_dir(self, empty_dir, dir_has_onedir):
        """
        When the Source Directory is empty
        """
        source_dir = tempfile.mkdtemp()
        dest_dir, sub_dir = dir_has_onedir
        list_fd_bef_move = os.listdir(dest_dir)
        move_tree(source_dir, dest_dir)
        list_fd_after_move = os.listdir(dest_dir)
        assert len(list_fd_bef_move) == len(list_fd_after_move)

    def test_dir_has_onefile(self, empty_dir):
        """
        When the Source Directory has only one file
        """
        source_dir = tempfile.mkdtemp()
        fd, source_file = tempfile.mkstemp(dir=source_dir)
        dest_dir = empty_dir
        move_tree(source_dir, dest_dir)
        moved_file = os.path.join(dest_dir, os.path.basename(source_file))
        assert os.path.exists(moved_file) and not os.path.exists(source_file)

    def test_dir_has_onedir(self, empty_dir, dir_has_onedir):
        """
        When the Dirctory has only one sub directory
        """
        source_dir = tempfile.mkdtemp()
        sub_dir = tempfile.mkdtemp(dir=source_dir)
        dest_dir = empty_dir
        move_tree(source_dir, dest_dir)
        moved_dir = os.path.join(dest_dir, os.path.basename(sub_dir))
        assert os.path.exists(moved_dir) and not os.path.exists(sub_dir)

    def test_dir_has_nestedfd(self, empty_dir, nested_fd):
        """
        When the files are nested in subdirectories more than 2 directories deep
        """
        dest_dir = empty_dir
        source_dir = tempfile.mkdtemp()
        sub_dir1 = tempfile.mkdtemp(dir=source_dir)
        sub_dir2 = tempfile.mkdtemp(dir=sub_dir1)
        fd, source_file = tempfile.mkstemp(dir=sub_dir2)
        move_tree(source_dir, dest_dir)
        moved_dir1 = os.path.join(dest_dir, os.path.basename(sub_dir1))
        moved_dir2 = os.path.join(moved_dir1, os.path.basename(sub_dir2))
        moved_file = os.path.join(moved_dir2, os.path.basename(source_file))
        assert os.path.exists(moved_dir1) and not os.path.exists(sub_dir1)
        assert os.path.exists(moved_dir2)
        assert os.path.exists(moved_file)


class TestFdOpen:
    def test_open_dir(self):
        with tempfile.TemporaryDirectory() as dir:
            dir_fd = os.open(dir, os.O_RDONLY)
            with fd_open(dir) as fdd:
                same_dir = os.path.sameopenfile(fdd, dir_fd)
            assert same_dir

    def test_open_file(self):
        with tempfile.NamedTemporaryFile() as file:
            file_fd = os.open(file.name, os.O_RDONLY)
            with fd_open(file.name) as fdf:
                same_file = os.path.sameopenfile(fdf, file_fd)
            assert same_file

    def test_close(self):
        with tempfile.TemporaryDirectory() as dir:
            with fd_open(dir) as fdd:
                dir_fd = fdd
            with pytest.raises(Exception):
                os.close(dir_fd)


def test_copy_test_script_files(dir_has_onefile):
    markus_address = "http://localhost:3000/csc108/en/main"
    assignment_id = 1
    tests_path, test_file = dir_has_onefile
    copy_test_script_files(markus_address, assignment_id, tests_path)
    test_script_outer_dir = test_script_directory(
        markus_address, assignment_id
    )
    test_script_dir = os.path.join(test_script_outer_dir, FILES_DIRNAME)
    copied_file = os.path.join(test_script_dir, test_file)
    assert os.path.exists(copied_file)


def copy_test_script_files(markus_address, assignment_id, tests_path):
    """
        Copy test script files for a given assignment to the tests_path
        directory if they exist. tests_path may already exist and contain
        files and subdirectories.
        """
    test_script_outer_dir = test_script_directory(
        markus_address, assignment_id
    )
    test_script_dir = os.path.join(test_script_outer_dir, FILES_DIRNAME)
    if os.path.isdir(test_script_dir):
        with fd_open(test_script_dir) as fd:
            with fd_lock(fd, exclusive=False):
                return copy_tree(test_script_dir, tests_path)
    return []


def test_script_directory(markus_address, assignment_id, set_to=None):
    key = get_test_script_key(markus_address, assignment_id)
    r = fakeredis.FakeStrictRedis()
    if set_to is not None:
        r.hset(CURRENT_TEST_SCRIPT_HASH, key, set_to)
    out = r.hget(CURRENT_TEST_SCRIPT_HASH, key)
    return string_management.decode_if_bytes(out)
