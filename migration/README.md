# GAMES PLANET — One website, one repository

This repository preserves the modern website from all 59 non-empty source repositories as they stood before the original websites were restored on 25 October 2026.

The home page opens the current Games Planet storefront. All legacy page folders, product photographs, calculators, order forms, selectors and other assets are included within this repository. The shared cart and checkout stay within this website. Product quantities have Buy and Add to Cart actions. Buy places the selected product and quantity in the shared cart and opens the order details form.

`migration/plan.json` records the exact source commits and the old versions used to restore the original websites. Each changed original repository also retains a `backup/before-restore-20261025` branch. Original repositories keep their original links and appearance; the new website is separate.

The `services/` folder contains the current order dashboard, parcel-photo / dispatch / delivered features, customer intake and console buyback backend source. These services use their existing hosted databases and private file storage. Customer records, credentials and runtime secrets are not included in this public repository. GitHub Pages serves the website; it does not execute these backend services.

## Publication

Enable GitHub Pages using GitHub Actions, then run the included Build and publish workflow. The first run imports the pinned source commits and commits the complete website to this repository. Later runs publish the files already present and preserve subsequent edits.

To reproduce locally, run `python migration/build-website.py --repository games-planet-website --output site`. This reads public source commits without needing a credential. The import script excludes runtime secret files and stored invoice/customer database backups.
