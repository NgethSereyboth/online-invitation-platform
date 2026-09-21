import os,runpy,sys
_here=os.path.dirname(os.path.abspath(__file__))
_target=os.path.join(_here,'src','python','build','build_editor_bundle.py')
if not os.path.isfile(_target):
    sys.stderr.write('forwarder: missing '+_target+'\n');sys.exit(2)
sys.path.insert(0,os.path.join(_here,'src','python'))
sys.path.insert(0,os.path.join(_here,'src','python','build'))
sys.argv[0]=_target
runpy.run_path(_target,run_name='__main__')