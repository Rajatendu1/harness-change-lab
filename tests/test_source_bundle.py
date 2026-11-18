import gzip
import io
import tarfile
import unittest
from unittest.mock import patch

from harnesslab.source_bundle import (overlay_candidate, pack_sources, source_name,
                                      unpack_sources, validate_sources)


def archive_entries(entries):
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as archive:
        for name,kind,data in entries:
            info=tarfile.TarInfo(name); info.type=kind
            if kind==tarfile.REGTYPE:
                info.size=len(data)
                archive.addfile(info,io.BytesIO(data))
            else:
                info.linkname='../../outside'
                archive.addfile(info)
    return buffer.getvalue()


class SourceBundleTests(unittest.TestCase):
    def test_roundtrip_exact_sources_without_metadata(self):
        sources={'src/a.py':b'x=1\n','README.md':b'\x00binary permitted'}
        raw=pack_sources(sources)
        self.assertEqual(unpack_sources(raw,expected_names=sources),sources)
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            self.assertTrue(all(x.uid==x.gid==x.mtime==0 and x.mode==0o600 for x in archive))

    def test_unsafe_names_rejected(self):
        for name in ('/absolute','../outside','a/../b','./a','a//b','a\\b','.git/config',
                     'src/.aider/secret','a/','a\x00b',''):
            with self.subTest(name=repr(name)),self.assertRaises(ValueError):
                source_name(name)

    def test_special_and_link_entries_rejected(self):
        for kind in (tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.FIFOTYPE,tarfile.CHRTYPE,
                     tarfile.BLKTYPE,tarfile.DIRTYPE):
            raw=archive_entries([('a.py',kind,b'')])
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                unpack_sources(raw,expected_names=['a.py'])

    def test_missing_duplicate_unexpected_and_path_traversal_rejected(self):
        for entries in ([('other.py',tarfile.REGTYPE,b'x')],
                        [('a.py',tarfile.REGTYPE,b'x'),('a.py',tarfile.REGTYPE,b'y')],
                        [('../a.py',tarfile.REGTYPE,b'x')],[]):
            with self.assertRaises(ValueError):
                unpack_sources(archive_entries(entries),expected_names=['a.py'])

    def test_compression_and_truncation_refused(self):
        raw=pack_sources({'a.py':b'x'*8192})
        for bad in (gzip.compress(raw),b'garbage',raw[:600]):
            with self.assertRaises(ValueError):
                unpack_sources(bad,expected_names=['a.py'])

    def test_transfer_file_and_aggregate_caps_enforced(self):
        raw=pack_sources({'a.py':b'1234','b.py':b'5678'})
        with patch('harnesslab.source_bundle.MAX_ARCHIVE',1):
            with self.assertRaises(ValueError): unpack_sources(raw,expected_names=['a.py','b.py'])
            with self.assertRaises(ValueError): pack_sources({'a.py':b'x'})
        with patch('harnesslab.source_bundle.MAX_FILE',3):
            with self.assertRaises(ValueError): unpack_sources(raw,expected_names=['a.py','b.py'])
            with self.assertRaises(ValueError): pack_sources({'a.py':b'1234'})
        with patch('harnesslab.source_bundle.MAX_BYTES',7):
            with self.assertRaises(ValueError): unpack_sources(raw,expected_names=['a.py','b.py'])
            with self.assertRaises(ValueError): validate_sources({'a.py':b'1234','b.py':b'5678'})

    def test_overlay_only_complete_declared_existing_files(self):
        base={'a.py':b'old','immutable.py':b'fixed'}
        self.assertEqual(overlay_candidate(base,{'a.py':b'new'},editable_names=['a.py']),
                         {'a.py':b'new','immutable.py':b'fixed'})
        self.assertEqual(base['a.py'],b'old')
        for proposed,editable in (({'new.py':b'x'},['new.py']),({'a.py':b'x'},['a.py','immutable.py']),
                                   ({'a.py':b'x','immutable.py':b'y'},['a.py'])):
            with self.assertRaises(ValueError): overlay_candidate(base,proposed,editable_names=editable)

    def test_file_directory_conflict_rejected(self):
        with self.assertRaises(ValueError): pack_sources({'a':b'x','a/b':b'y'})
        raw=archive_entries([('a',tarfile.REGTYPE,b'x'),('a/b',tarfile.REGTYPE,b'y')])
        with self.assertRaises(ValueError): unpack_sources(raw,expected_names=['a','a/b'])
