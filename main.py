import os
import shutil
from pathlib import Path

output = Path(os.environ.get('MAKEFUN_OUTPUT_DIR', '/output'))
output.mkdir(parents=True, exist_ok=True)
shutil.copyfile(Path(__file__).with_name('entry.png'), output / 'entry.png')
