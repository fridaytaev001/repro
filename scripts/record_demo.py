"""Record a labelled local UI demonstration; never starts inference or repair.

The case must already contain actual verified repair proof. This is a recorded
walkthrough of saved evidence, explicitly distinguished from a new live run.
"""
import argparse
import asyncio
from pathlib import Path
import time

from playwright.async_api import async_playwright


async def record(base,case_id,output):
    output.mkdir(parents=True,exist_ok=True)
    async with async_playwright() as engine:
        browser=await engine.chromium.launch()
        started=time.monotonic()
        context=await browser.new_context(viewport={'width':1360,'height':900},
            record_video_dir=output,record_video_size={'width':1360,'height':900})
        page=await context.new_page()
        async def caption(text,seconds=5):
            await page.evaluate('''text => {
              let box=document.getElementById('recording-caption');
              if(!box){box=document.createElement('div');box.id='recording-caption';}
              (document.querySelector('dialog[open]')||document.body).append(box);
              box.style.cssText='position:fixed;z-index:999999;left:20px;right:20px;bottom:16px;background:#182c20;color:white;padding:18px;font:20px sans-serif;box-shadow:0 2px 20px #0004;pointer-events:none';
              box.textContent=text;
            }''',text)
            await asyncio.sleep(seconds)
        await page.goto(base+'/')
        await caption('Repro — recorded walkthrough. Synthetic target; saved real Crusoe evidence, not a new live inference run.')
        await page.locator('#open-cart').click()
        await page.locator('#coupon').fill('SAVE10')
        await page.get_by_role('button',name='Apply',exact=True).click()
        await page.locator('#continue-review').click()
        await caption('The original target: SAVE10 correctly gives $90. Coupon entry is hidden on review.')
        await page.locator('#edit-address').click()
        await page.get_by_label('Street address',exact=True).fill('222 Market Street')
        await page.locator('#continue-review').click()
        if await page.locator('#total').inner_text()!='$100.00':
            raise ValueError('Expected baseline defect was not observed; do not record a staged claim.')
        await caption('Actual seeded bug: saving an address edit from review drops SAVE10. The total becomes $100.')
        await page.goto(base+'/cases/'+case_id)
        await page.get_by_role('heading',name='A repair passed in an isolated copy.',exact=True).wait_for()
        await caption('Saved real Crusoe case: vague complaint, frozen criteria, failed remembered steps, alternative hypothesis, fresh-browser confirmation.')
        await page.locator('#repair-panel').scroll_into_view_if_needed()
        await caption('Protected proof: baseline regression FAILS; isolated candidate PASSES, with syntax and checkout controls passing. Original target unchanged.',7)
        await page.locator('#handoff-panel').scroll_into_view_if_needed()
        await caption('Engineer handoff: report, frozen replay, separate tests, screenshots, traces, patch and check receipts. No credentials in the bundle.',6)
        remaining=max(0,60-(time.monotonic()-started))
        await caption('New hackathon contribution: an evidence-driven investigate → verify → repair loop on Crusoe. Local prototype; one seeded target and a small measured sample.',remaining)
        video=page.video
        await context.close()
        path=await video.path()
        await browser.close()
        destination=output/'repro-demo.webm'
        Path(path).replace(destination)
        print('Recorded walkthrough saved:',destination)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='http://127.0.0.1:8000')
    parser.add_argument('--case',required=True)
    parser.add_argument('--output',type=Path,default=Path('.local/delivery'))
    args=parser.parse_args()
    asyncio.run(record(args.base,args.case,args.output))


if __name__=='__main__':
    main()
