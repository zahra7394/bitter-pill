import { readFileSync } from 'fs';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

var requestFile = process.argv.slice(2);

async function read(path) {
  return readFileSync(resolve(__dirname, path), 'utf8');
}



(async () => {
  try {
    const { StaticNetFilteringEngine } = await import('@gorhill/ubo-core');
    const snfe = await StaticNetFilteringEngine.create();
    await snfe.useLists([
      read('./lists/easylist.txt').then(raw => ({ name: 'easylist', raw })),
      read('./lists/easyprivacy.txt').then(raw => ({ name: 'easyprivacy', raw })),
      read('./lists/ubo-filters-ads.txt').then(raw => ({ name: 'ads', raw })),
      read('./lists/ubo-filters-privacy.txt').then(raw => ({ name: 'privacy', raw })),
      read('./lists/ubo-filters-quick-fixes.txt').then(raw => ({ name: 'quick-fixes', raw })),
      read('./lists/ubo-filters-unbreak.txt').then(raw => ({ name: 'unbreak', raw })),
      read('./lists/pl-serverlist.txt').then(raw => ({ name: 'serverlist', raw })),
    ]);

    // Call uBO core to detect ad and tracking-related requests
    // Prints 0 (not blocked), 1 (blocked) or 2 (unblocked/allowed)
    //  to the console, which is read by the caller
    const input = await read(String(requestFile));
    const reqs = JSON.parse(input);
    reqs.forEach(req => {
      const is_request_blocked = req.url ? snfe.matchRequest({
      originURL: req.originURL,
      url: req.url,
      type: req.type
      }) : 0;  // 0 if no URL
      // uBO returns 1 for 3rd-party ping requests
      // even if the URL is empty
      console.log(is_request_blocked);
    });

  } catch (error) {
      console.log("uBOCoreError", error)
    }
})();
