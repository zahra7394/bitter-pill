# The Bitter Pill: Tracking and Remarketing on EU Pharmacy Websites

This repository contains the analysis code and Jupyter notebooks for the paper titled **The Bitter Pill: Tracking and Remarketing on EU Pharmacy Websites**, presented at the **Data Privacy Management Workshop (DPM'25)**, ESORICS Workshops.

**Paper:** [The Bitter Pill: Tracking and Remarketing on EU Pharmacy Websites](https://gunesacar.net/assets/bitter-pill-pharmacy-privacy-dpm-25.pdf) (PDF)

We investigate online tracking and remarketing on 50 pharmacy websites in five European countries (DE, FR, ES, IT, NL). By shopping for pregnancy tests and analyzing HAR-captured traffic, we find that personal data and shopping activity are routinely collected by third parties; some sites share product names, emails, and phone numbers even when consent was declined. We identify server-side tagging (SST) and CNAME-based tracking, which can circumvent adblockers and browser protections, and observe retargeted pregnancy-test ads on news sites. Declining consent reduces but does not eliminate data sharing, and consent interfaces often discourage opting out. Overall, the study reveals widespread potential legal violations and evasive tracking on sites that handle highly sensitive health-related data.

---

### Notebooks

| Notebook | Description |
|----------|-------------|
| **General-Stats** | Dataset overview: request counts, third-party and tracker prevalence by country and consent mode |
| **Cname-Analysis** | CNAME cloaking: requests that evade URL-based tracker detection via first-party CNAME aliases |
| **Pixel-Analysis** | Hashed PII leaks via tracking pixels (e.g. Facebook, TikTok, Pinterest) and Facebook Automated Advanced Matching |
| **Tracking-Analysis** | Tracker and consent-mode analysis |
| **Product-Leaks** | Product and cart data in outgoing requests |
| **SST-Detection** / **SST-Analysis** | Server-side tagging (SST) detection and analysis |

---

## Getting started

### Installation

1. Clone this repository and navigate to the project directory.

2. Install Python dependencies (Python 3.10+):
   ```bash
   pip install -r requirements.txt
   ```

3. For the uBlock Origin core runner, install [Node.js](https://nodejs.org/) (v18+) and install the npm dependencies:
   ```bash
   cd notebooks/ublock
   npm install
   ```
   See `notebooks/ublock/README.md` for details.

4. **Data:** The notebooks expect HAR files from the data collection procedure described in the paper. Place your own HAR files in `har_data/` (or set `BASE_HAR_DIR` in `notebooks/common.py` to your data path). The folder structure should match the expected layout (e.g. per consent mode and experiment mode). We do not plan to publish the HAR files collected during the study, as they contain security-sensitive cookies and identifiers associated with the accounts used in our research. If you have any questions, or if your work depends on access to our data, please feel free to reach out to us.

### Running the notebooks

Start Jupyter from the repo root and open the notebooks under `notebooks/`:

```bash
jupyter notebook notebooks/
```

Run the **Setup and data load** cell if it is present. The cell calls `parse_har_files_to_dataframe(BASE_HAR_DIR, ...)`, which may take a few minutes depending on the HAR file count. CNAME and other caches (e.g. `cname_cache.json`) are saved under `notebooks/` to speed up re-runs.

**Note:** For **Pixel-Analysis** (hashed PII leak detection), the notebooks use persona details from `PERSONA_DETAILS` in `notebooks/common.py`, which currently contains placeholders. 

---


## Reference

If you use this code in your work, please consider citing our paper:

```bibtex
@inproceedings{moti2025bitterpill,
  author    = {Zahra Moti and Kimberley Frings and Christine Utz and Frederik Zuiderveen Borgesius and Gunes Acar},
  title     = {The Bitter Pill: Tracking and Remarketing on EU Pharmacy Websites},
  booktitle = {Data Privacy Management (DPM) -- ESORICS Workshops},
  year      = {2025}
}
```

---

## Contact

For questions or issues regarding this repository or the paper, please open an issue on GitHub or contact:

| Author | Email |
|--------|--------|
| [Zahra Moti](https://www.ru.nl/en/people/moti-jeshveghani-z) | zahra.moti@ru.nl |
| [Gunes Acar](https://gunesacar.net/) | g.acar@cs.ru.nl |
| [Christine Utz](https://christineutz.net/) | christine.utz@ru.nl |
| [Frederik Zuiderveen Borgesius](https://www.ru.nl/personen/zuiderveen-borgesius-f) | frederikzb@cs.ru.nl |


