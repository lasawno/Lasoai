from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
import unittest
spec=spec_from_file_location('stop_reflex',Path(__file__).resolve().parents[1]/'scripts/stop-reflex.py')
module=module_from_spec(spec);spec.loader.exec_module(module)

class StopTests(unittest.TestCase):
    def test_selects_only_checkout_server_tree_not_other_projects_or_shells(self):
        app=Path('/workspaces/Lasoai/apps/reflex')
        def record(parent,cwd,args):return {'ppid':parent,'cwd':str(cwd),'args':args}
        records={1:record(0,app,['bash']),2:record(1,app,['uv','run','reflex','run','--env','prod']),
                 3:record(2,app,['python','-c','worker']),4:record(1,'/other/apps/reflex',['reflex','run']),
                 5:record(4,'/other/apps/reflex',['python']),6:record(1,app,['python','notes.py']),
                 7:record(1,app,['granian']),8:record(7,app,['python','-c','worker'])}
        self.assertEqual(module.select_processes(records,app),{2,3,7,8})

if __name__=='__main__':unittest.main()
