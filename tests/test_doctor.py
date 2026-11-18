import json
import pathlib
import tempfile
import unittest
from unittest import mock

from brightery_doctor import cli
from brightery_doctor import dashboard
from brightery_doctor import report


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


def fixture():
    return dict(name='Brightery Server Doctor', version='1.2.0', sample_seconds=6.,
                timestamp_utc='2026-11-18T12:00:00Z', logical_cpus=8,
                load_1_5_15=[2., 2.5, 2.7], memory_total_bytes=24 * 1073741824,
                memory_available_bytes=16 * 1073741824, swap_used_bytes=0,
                cpu={'user_pct':12,'system_pct':8,'idle_pct':79,'iowait_pct':1},
                io_pressure={'full':{'avg10':0}, 'some':{'avg10':1}},
                disks=[{'device':'sda','writes_per_s':56,'write_await_ms':3.5,
                        'queue_depth':0.3,'busy_pct':13.9}],
                findings=['OK: No obvious bottleneck detected in this short sample'],
                suspects=[],note='Snapshot only')


class DashboardTests(unittest.TestCase):
    def test_green_healthy(self):
        health = dashboard.enrich(fixture())
        self.assertEqual(health['health'], 'healthy')
        self.assertTrue(all(c['severity'] == 'healthy' for c in health['checks']))
        self.assertIn('HEALTHY', dashboard.render(health, color=False))
        self.assertIn('1.2.0', dashboard.render(health, color=False))

    def test_orange_warning(self):
        f = fixture()
        f['cpu']['iowait_pct'] = 11
        f['findings'] = ['WARNING: Elevated CPU I/O wait']
        health = dashboard.enrich(f)
        self.assertEqual(health['health'], 'warning')
        s = dashboard.render(health, color=True)
        self.assertIn('\x1b[33m', s)
        self.assertIn('WARNING', s)

    def test_red_critical(self):
        f = fixture()
        f['disks'][0].update({'write_await_ms':78.3, 'queue_depth':471, 'writes_per_s':8444})
        f['findings'] = ['CRITICAL: sda write bottleneck']
        health = dashboard.enrich(f)
        self.assertEqual(health['health'], 'critical')
        self.assertIn('\x1b[31m', dashboard.render(health, color=True))
        self.assertIn('CRITICAL', dashboard.render(health, color=False))

    def test_no_color_respects_no_color_env(self):
        with mock.patch.dict('os.environ', {'NO_COLOR': ''}, clear=False):
            self.assertFalse(dashboard.use_color())

    def test_ascii_and_narrow_width(self):
        f = dashboard.enrich(fixture())
        s = dashboard.render(f, color=False, width=52, ascii_only=True)
        self.assertNotIn('\x1b', s)
        self.assertNotIn('╭', s)
        self.assertTrue(all(len(line) == 52 for line in s.splitlines()))

    def test_colors_are_opt_in_for_redirected_text(self):
        f = dashboard.enrich(fixture())
        self.assertNotIn('\x1b', dashboard.render(f, color=False))

    def test_report_has_no_remote_assets_or_scripts(self):
        f = fixture()
        f['findings'] = ['WARNING: <script>alert("x")</script>']
        f['disks'][0]['device'] = '<img src=x onerror=alert(1)>'
        f['suspects'] = [{'pid': 44,'name':'<script>','cpu_pct_one_core':11,
                          'blocked_samples':0, 'seen_samples':7, 'recursive_permissions':False,
                          'service':'secret & service'}]
        h = report.html_report(f)
        self.assertIn('Content-Security-Policy', h)
        self.assertNotIn('<script>', h)
        self.assertNotIn('<img src=', h)
        self.assertIn('&lt;script&gt;', h)
        self.assertIn('secret &amp; service', h)
        self.assertNotIn('http://', h)
        self.assertNotIn('https://', h)

    def test_severity_consistency(self):
        f = fixture()
        f['findings']=['SUSPECT: Recursive chmod detected']
        self.assertEqual(dashboard.enrich(f)['health'], 'warning')


if __name__ == '__main__':
    unittest.main()
