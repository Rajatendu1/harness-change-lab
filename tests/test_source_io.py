import io
import os
from pathlib import Path
import socket
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from harnesslab.source_io import import_sources, export_sources
from harnesslab.source_bundle import pack_sources, unpack_sources


class SourceIOTests(unittest.TestCase):
    def test_nested_roundtrip_without_metadata_or_outside_files(self):
        with tempfile.TemporaryDirectory() as directory:
            sources={'src/a.py':b'x=1\n','README.md':b'hello'}
            self.assertEqual(import_sources(pack_sources(sources),expected_names=sources,root=directory),'source-import-ok')
            raw=export_sources(expected_names=['src/a.py'],root=directory)
            self.assertEqual(unpack_sources(raw,expected_names=['src/a.py']),{'src/a.py':b'x=1\n'})
            self.assertEqual((Path(directory)/'src/a.py').stat().st_mode&0o777,0o600)

    def test_nonempty_import_refused_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'a').write_bytes(b'original')
            with self.assertRaises(ValueError):
                import_sources(pack_sources({'a':b'new'}),expected_names=['a'],root=root)
            self.assertEqual((root/'a').read_bytes(),b'original')

    def test_invalid_archive_validated_before_any_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            raw=pack_sources({'a':b'valid','other':b'unexpected'})
            with self.assertRaises(ValueError): import_sources(raw,expected_names=['a'],root=directory)
            self.assertEqual(os.listdir(directory),[])

    def test_root_and_intermediate_symlinks_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'outside').mkdir(); (root/'outside/a').write_bytes(b'private-dummy')
            (root/'link').symlink_to(root/'outside',target_is_directory=True)
            for base,name in ((root/'link','a'),(root,'link/a')):
                with self.assertRaises(OSError): export_sources(root=base,expected_names=[name])
            with self.assertRaises(OSError):
                import_sources(pack_sources({'a':b'new'}),expected_names=['a'],root=root/'link')
            self.assertEqual((root/'outside/a').read_bytes(),b'private-dummy')

    def test_symlink_hardlink_fifo_socket_outputs_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'original').write_bytes(b'x')
            (root/'a').symlink_to(root/'original')
            with self.assertRaises(OSError): export_sources(root=root,expected_names=['a'])
            (root/'a').unlink(); os.link(root/'original',root/'a')
            with self.assertRaises(ValueError): export_sources(root=root,expected_names=['a'])
            (root/'a').unlink(); os.mkfifo(root/'a')
            with self.assertRaises(ValueError): export_sources(root=root,expected_names=['a'])
            (root/'a').unlink()
            with socket.socket(socket.AF_UNIX) as sock:
                sock.bind(str(root/'a'))
                with self.assertRaises(OSError): export_sources(root=root,expected_names=['a'])

    def test_missing_duplicate_and_path_escape_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'a').write_bytes(b'x')
            with self.assertRaises(OSError): export_sources(root=root,expected_names=['missing'])
            for names in (['a','a'],['../a'],['/a'],[]):
                with self.assertRaises(ValueError): export_sources(root=root,expected_names=names)

    def test_collection_file_and_aggregate_bytes_capped(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'a').write_bytes(b'1234'); (root/'b').write_bytes(b'5678')
            with patch('harnesslab.source_io.MAX_FILE',3):
                with self.assertRaises(ValueError): export_sources(root=root,expected_names=['a'])
            with patch('harnesslab.source_io.MAX_BYTES',7):
                with self.assertRaises(ValueError): export_sources(root=root,expected_names=['a','b'])

    def test_import_io_failure_not_success_or_rollback_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('harnesslab.source_io.os.mkdir',side_effect=OSError('fixed ENOSPC fixture')):
                with self.assertRaises(OSError):
                    import_sources(pack_sources({'src/a':b'x'}),expected_names=['src/a'],root=directory)
