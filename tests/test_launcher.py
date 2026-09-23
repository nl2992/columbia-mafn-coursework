"""Exercise launch routing without opening apps or installing dependencies."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def launch(self, configured):
        with tempfile.TemporaryDirectory(prefix='archive with spaces ') as directory:
            root = Path(directory).resolve()
            script = root / 'START HERE - Open Course Archive.command'
            shutil.copy2(ROOT / script.name, script)
            if configured:
                (root / '.rag/search').mkdir(parents=True)
                (root / '.rag/search/CURRENT.json').write_text('{}')
            # Stub only external effects; execute the real shell routing and PATH setup.
            result = subprocess.run([
                '/bin/zsh', '-c',
                'function /usr/bin/open { print -r -- "SETUP:$*"; }; '
                'function /usr/bin/env { print -r -- "RUN:$* PATH=$PATH"; }; '
                'source "$1"', 'test', str(script),
            ], env={'HOME': directory, 'PATH': '/usr/bin:/bin:/usr/sbin:/sbin'},
                text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout, root

    def test_fresh_clone_opens_visible_setup(self):
        output, root = self.launch(False)
        self.assertIn(f'SETUP:-a Terminal {root}/SET UP THIS MAC.command', output)
        self.assertNotIn('RUN:', output)

    def test_configured_checkout_launches_with_homebrew_path(self):
        output, _ = self.launch(True)
        self.assertIn('RUN:python3 scripts/run_rag.py --port 8765 --open', output)
        self.assertIn('PATH=/opt/homebrew/bin:/usr/local/bin:', output)
        self.assertNotIn('SETUP:', output)


if __name__ == '__main__':
    unittest.main()
