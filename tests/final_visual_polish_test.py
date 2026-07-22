from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def text(name): return (ROOT/name).read_text(encoding='utf-8')

assert (ROOT/'final-polish.css').exists()
assert (ROOT/'final-polish.js').exists()
for page in ['dashboard.html','materials.html','index.html']:
    data=text(page)
    assert 'final-polish.css' in data and 'final-polish.js' in data

dash=text('dashboard.html')
assert 'value="demo@e-invitation.test"' not in dash
assert 'value="demo1234"' not in dash
server=text('server.py')
assert '"preview":preview' in server
js=text('final-polish.js')
for token in ['fp-project-preview','fp-project-menu','fp-material-preview-dialog','fp-visual-assets','fp-text-fonts','mobile-pane-collapsed','einvite-pending-material-insert']:
    assert token in js or token in text('final-polish.css')
visual=text('tests/visual_regression.py')
for size in ['375,812','430,932','768,1024','1024,768','1366,768','1920,1080','2560,1440']:
    assert size in visual
print('FINAL_VISUAL_POLISH_TEST_PASSED')
