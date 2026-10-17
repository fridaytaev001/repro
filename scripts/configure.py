"""Save a key locally through a masked prompt, without opening the .env editor."""
import getpass
import shutil
from dotenv import set_key
from app.settings import ROOT


def main():
    path=ROOT/'.env'
    if not path.exists():
        shutil.copyfile(ROOT/'.env.example',path)
    key=getpass.getpass('Crusoe key (hidden; stored only in local .env): ').strip()
    if not key or '\n' in key or '\r' in key:
        raise SystemExit('No valid single-line key entered; file unchanged.')
    set_key(path,'CRUSOE_API_KEY',key,quote_mode='always')
    key=''
    print('Local key saved. Start the app or retry the case; no key was displayed.')


if __name__=='__main__':
    main()
