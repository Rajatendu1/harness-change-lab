import os
from pathlib import Path
import socket
import tempfile
import unittest

from harnesslab.protected_score import _files


class CandidateSnapshotTests(unittest.TestCase):
    def test_regular_tree_and_bookkeeping_pruning(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'src').mkdir(); (root/'src'/'a.py').write_bytes(b'x=1\n')
            (root/'.git').mkdir(); os.mkfifo(root/'.git'/'ignored-fifo')
            (root/'.aider-cache').mkdir(); os.mkfifo(root/'.aider-cache'/'ignored-fifo')
            self.assertEqual(_files(root),{'src/a.py':b'x=1\n'})

    def test_fifo_and_socket_refused_without_reading(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); os.mkfifo(root/'fifo')
            with self.assertRaises(ValueError): _files(root)
            (root/'fifo').unlink()
            with socket.socket(socket.AF_UNIX) as sock:
                sock.bind(str(root/'socket'))
                with self.assertRaises(ValueError): _files(root)

    def test_file_directory_and_root_links_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'target').mkdir()
            (root/'link').symlink_to(root/'target',target_is_directory=True)
            with self.assertRaises(ValueError): _files(root)
            with self.assertRaises(ValueError): _files(root/'link')
            (root/'link').unlink(); (root/'a').write_bytes(b'x')
            (root/'link').symlink_to(root/'a')
            with self.assertRaises(ValueError): _files(root)

    def test_hardlinks_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'a').write_bytes(b'x')
            os.link(root/'a',root/'b')
            with self.assertRaises(ValueError): _files(root)

    def test_aggregate_size_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            # Sparse files keep fixture disk small but read as zero bytes.
            for index in range(9):
                with (root/str(index)).open('wb') as stream: stream.truncate(8*1024*1024)
            with self.assertRaises(ValueError): _files(root)

    def test_per_file_size_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with (root/'big').open('wb') as stream: stream.truncate(8*1024*1024+1)
            with self.assertRaises(ValueError): _files(root)
