#!/usr/bin/env python3
from pathlib import Path
import subprocess,sys,tempfile,json
from route_bundle_sources import has
ROOT=Path(__file__).resolve().parents[1]
def main():
    for name in ['src/js/experience-schema.js','src/js/style-kits.js','src/css/style-kits.css','src/js/opening-scenes.js','src/css/opening-scenes.css','src/js/storyboard.js','src/css/storyboard.css','src/js/guest-layouts.js','src/css/guest-layouts.css','src/js/social-card.js','src/css/social-card.css','src/js/accessibility-polish.js','src/js/dashboard-empty-state.js']:
        assert (ROOT/name).is_file(),name
    public=(ROOT / "src" / "html" / "public.html").read_text(encoding='utf-8');index=(ROOT / "src" / "html" / "index.html").read_text(encoding='utf-8');server=(ROOT / "src" / "python" / "server.py").read_text(encoding='utf-8')
    assert '__INVITATION_OG_IMAGE__' in public and 'twitter:card' in public
    assert 'social_card_svg' in server
    assert has('index.html','experience-schema.js') and has('index.html','style-kits.js')
    node='''global.window=global;require(process.argv[1]);let old={fields:{names:'Old'},settings:{rsvpEnabled:false},openingStyle:'curtain',sectionOrder:['gallery','rsvp'],objects:{}};let d=EInviteExperience.migrate(old);if(d.schemaVersion!==13||d.openingScene.id!=='silk-curtain'||d.desktopGuestLayout!=='ambient-frame')throw Error(JSON.stringify(d));let a=EInviteExperience.applyKit(d,'royal-khmer-gold');if(a.styleKit.id!=='royal-khmer-gold'||a.fields.names!=='Old'||a.settings.rsvpEnabled!==false)throw Error('apply');let r=EInviteExperience.restoreDefaults(a);if(r.fields.names!=='Old'||r.settings.rsvpEnabled!==false)throw Error('restore');console.log('ok')'''
    result=subprocess.run(['node','-e',node,str(ROOT / "src" / "js" / "experience-schema.js")],text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    print('V10_EXPERIENCE_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
