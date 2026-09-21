#!/usr/bin/env python3
import pathlib, py_compile
p = pathlib.Path('src/python/run_review_checks.py')
src = p.read_text(encoding='utf-8')
src = src.replace("\npython_path=str(ROOT/'src'/'python')", "\n    ")
src = src.replace(" output_path=data_dir/'suite-output.log'\n   \n  env=",
                  " output_path=data_dir/'suite-output.log'\n env=")
src = src.replace("'PYTHONIOENCODING':'utf-8'}\n  \n if os.name==",
                  "'PYTHONIOENCODING':'utf-8'}\n if os.name==")
old = "env={**os.environ,'EINVITE_DATA_DIR':str(data_dir),'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'}\n"
new = old + " env['PYTHONPATH']=str(ROOT/'src'/'python')+os.pathsep+env.get('PYTHONPATH','')\n"
n = src.count(old)
assert n == 1, f"expected 1 env line, found {n}"
src = src.replace(old, new)
p.write_text(src, encoding='utf-8')
py_compile.compile(str(p), doraise=True)
print("REPAIRED OK")