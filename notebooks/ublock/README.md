# uBlock Origin core runner

Used by the tracking analysis notebooks to label requests as tracker/ads via the uBlock filter engine.

**One-time setup:** From this directory, install the Node dependency:

```bash
cd notebooks/ublock
npm install
```

Requires Node.js (with ES modules support). The script is run by `utils.run_ublock_script()` when building the analysis dataframe.
