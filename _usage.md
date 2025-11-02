# Usage

## Installation

### Install Quarto

Follow the instructions on the [Quarto website](https://quarto.org/docs/get-started/).

Install also the extension for your code editor, e.g., [Quarto for VS Code](https://marketplace.visualstudio.com/items?itemName=quarto.quarto).

### Install uv
Install the uv package manager for using python in this repository. Follow the instructions in the [uv documentation](https://docs.astral.sh/uv/getting-started/installation/). 

To run a script with uv, use the command:
```bash
uv run <my_script.py>
```

To build a environment reflecting the dependencies in `pyproject.toml`, use:
```bash
uv sync
```

## Preview the Site Locally
To preview the site locally with a live server, you can use the following command:

```bash
quarto preview
```
This will start a local server and open the site in your default web browser. Any changes you make to the source files will automatically refresh the browser.

## Render the Site Locally
To render the site locally, you can use the following command:

```bash
quarto render
```
This will generate the static files for the site in the `_site` directory. Additionally, it will save the results of computatations in the `_freeze` directory, that should be checked into version control, such that the site can be deployed (e.g. with GitHub Actions) without re-running computations.

## Deploy the Site

Documentation for deploying the site on github pages can be found in [quarto's documentation](https://quarto.org/docs/publishing/github-pages.html).

Briefly, to deploy the site, you can push the changes to your GitHub repository if you have set up GitHub Pages or any other hosting service. Make sure to commit and push all changes before deployment.
```bash
git add .
git commit -m "Update site"
git push origin main
```
### Publish via GitHub Actions

Is done using the CI workflow defined in `.github/workflows/deploy.yml`, which is triggered on pushes to the `main` branch. This can be done only, if at least one time the  ```quarto publish gh-pages
``` (see quarto documentation) command has been run locally to set up the `gh-pages` branch.

### Publish locally to GitHub Pages

To build the site locally, run (on the main branch):
```bash
quarto publish gh-pages
```
This command will build the site and publish it to the `gh-pages` branch of your GitHub repository.

To update the publications list from ORCID, run:
```bash
uv run fetch_orcid.py
```