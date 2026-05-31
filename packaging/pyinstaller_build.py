import os
import sys
from PyInstaller.__main__ import run as pyinst_run

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(root)

def path_join(*parts):
    return os.path.join(*parts)

datas = [
    os.path.abspath(path_join('config', 'planner_config.yaml')) + os.pathsep + 'config',
    os.path.abspath(path_join('data', 'mw_links', 'existing_links.csv')) + os.pathsep + path_join('data', 'mw_links'),
    os.path.abspath(path_join('frontend', 'dist')) + os.pathsep + path_join('frontend', 'dist'),
]

args = [
    '--clean',
    '--onefile',
    '--name', 'MWPreplanning',
    '--specpath', root,
    '--collect-all', 'rasterio',
]
for d in datas:
    args += ['--add-data', d]

args.append(path_join('backend', 'run.py'))

print('Running PyInstaller with args:', args)
pyinst_run(args)
print('PyInstaller finished')
