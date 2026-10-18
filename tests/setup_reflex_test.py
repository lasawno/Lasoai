from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
import tempfile
import unittest
from unittest.mock import patch
import subprocess

spec = spec_from_file_location('setup_reflex', Path(__file__).resolve().parents[1] / 'scripts/setup_reflex.py')
setup = module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def test_init_restores_source_on_success_and_failure(self):
        for fail in [False, True]:
            with tempfile.TemporaryDirectory() as folder:
                project = Path(folder)
                (project/'lasoai_workspace').mkdir()
                (project/'rxconfig.py').write_text('custom configuration')
                (project/'lasoai_workspace/app.py').write_text('custom app')
                def run(*args, **kwargs):
                    (project/'rxconfig.py').write_text('template configuration')
                    (project/'lasoai_workspace/app.py').write_text('template app')
                    if fail:
                        raise subprocess.CalledProcessError(1, args[0])
                with patch.object(setup.subprocess, 'run', side_effect=run):
                    if fail:
                        with self.assertRaises(subprocess.CalledProcessError): setup.initialize(project)
                    else: setup.initialize(project)
                self.assertEqual((project/'rxconfig.py').read_text(), 'custom configuration')
                self.assertEqual((project/'lasoai_workspace/app.py').read_text(), 'custom app')

    def test_existing_generated_assets_skip_reinitialization(self):
        with tempfile.TemporaryDirectory() as folder:
            project=Path(folder);(project/'.web').mkdir()
            with patch.object(setup.subprocess,'run') as run:
                setup.initialize(project)
                run.assert_not_called()


if __name__ == '__main__': unittest.main()
