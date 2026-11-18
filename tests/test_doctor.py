import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from brightery_doctor import cli


class ParsingTests(unittest.TestCase):
    def test_cpu(self):
        c = cli.parse_cpu('cpu 10 2 3 4 5 6 7 8 9\n')
        self.assertEqual(c['total'], 45)
        self.assertEqual(c['iowait'], 5)

    def test_diskstats(self):
        row = '8 0 sda 10 0 20 30 40 0 50 60 0 70 80\n'
        d = cli.parse_disks(row, {'sda'})['sda']
        self.assertEqual(d['write_ops'], 40)
        self.assertEqual(d['weighted_ms'], 80)

    def test_sensitive_arguments_never_retained(self):
        raw = ('42 (chmod) D 1 0 0 0 0 0 0 0 0 0 11 12 0 0 0 0 0 0 100 0 0').encode()
        def fake_read(path, size=8192, binary=False):
            if path.endswith('/stat'):
                return raw.decode()
            if path.endswith('/cmdline'):
                return b'chmod\0-R\0--token=TOPSECRET\0/home/private\0'
            if path.endswith('/cgroup'):
                return '0::/system.slice/deploypro.service\n'
            return ''
        with mock.patch.object(cli, 'read', side_effect=fake_read):
            p = cli.parse_process(42)
        self.assertTrue(p['recursive_permissions'])
        self.assertEqual(p['service'], 'deploypro.service')
        self.assertNotIn('TOPSECRET', json.dumps(p))
        self.assertNotIn('/home/private', json.dumps(p))

    def test_terminal_escape_sanitized(self):
        self.assertNotIn('\x1b', cli.clean('evil\x1b[31m\n'))

    def test_report_existing_file_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / 'report.json'
            path.write_text('ORIGINAL')
            with self.assertRaises(FileExistsError):
                cli.save_new_file(str(path), 'new')
            self.assertEqual(path.read_text(), 'ORIGINAL')

    def test_symlink_not_followed(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp) / 'real'
            target.write_text('ORIGINAL')
            link = pathlib.Path(temp) / 'link'
            link.symlink_to(target)
            with self.assertRaises((FileExistsError, OSError)):
                cli.save_new_file(str(link), 'new')
            self.assertEqual(target.read_text(), 'ORIGINAL')

    def test_private_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / 'report.json'
            cli.save_new_file(str(path), 'ok')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_shortened_name(self):
        self.assertEqual(len(cli.clean('x' * 300, 30)), 30)


if __name__ == '__main__':
    unittest.main()
