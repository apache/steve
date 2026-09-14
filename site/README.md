# Apache STeVe website

The public website is built with Docusaurus from this directory. The Python application and its documentation remain in `v3/`; the website links to those guides instead of maintaining another copy.

## Local development

Use Node.js 24 and the pnpm version pinned in `package.json` (available through Corepack).

```shell
cd site
corepack enable pnpm
pnpm install --frozen-lockfile
pnpm start
```

Pages live in `src/pages/`, styles in `src/css/`, and static assets in `static/`.

Before opening a pull request, run:

```shell
pnpm validate
pnpm serve
```

Validation checks formatting, runs the metadata tests, and performs a production build, including Docusaurus's broken-link checks. Use `pnpm format` to format website sources. `pnpm serve` serves the generated `build/` directory, including the DOAP document and legacy URL redirects.

## Publishing and previews

The `Website` GitHub Actions workflow builds website changes in pull requests. Pushes to `trunk` also publish the generated files to `asf-site`, which ASF Infrastructure serves at <https://steve.apache.org/>. The publishing action makes ordinary commits and pushes, preserving the generated branch's history.

For a hosted preview, a committer can push a branch named `preview/<name>` to this repository. Use lowercase letters, numbers, and single hyphens in the name, for example `preview/website`. The workflow publishes `site/<name>-staging`, and ASF Infrastructure serves it at `https://steve-<name>.staged.apache.org`. The workflow summary links to the preview; allow a few minutes for ASF publishing after the workflow finishes. Fork pull requests are built and validated, but do not publish a hosted preview.

Closing a pull request from a preview branch deletes its generated staging branch. The cleanup workflow must already exist on the default branch to handle a closed pull request. For a preview without a pull request, delete the generated branch when it is no longer needed.

The root `.asf.yaml` controls production publishing and automatic staging. The build copies it into the output because ASF reads that configuration on each generated branch. See the [ASF Infrastructure documentation](https://infra.apache.org/asf-yaml.html) for branch-specific configuration.

## Project metadata

Maintain project information in `project.metadata` in the root `.asf.yaml`. ATR synchronization uses that section, and the website build generates `doap.rdf` from it for consumers that require DOAP XML. The generated document identifies the project and its PMC without maintaining a list of individual maintainers.

The legacy `projects.apache.org` feed still points to the separate SVN DOAP file. After this website is published and <https://steve.apache.org/doap.rdf> is available, update the STeVe entry in [`apache/comdev-projects/data/projects.xml`](https://github.com/apache/comdev-projects/blob/trunk/data/projects.xml) to that URL. Until that separate change lands, the feed continues reading SVN. Do not edit the SVN copy as an ongoing second source of metadata.

Old entry points such as `demo.html`, `documentation.html`, `community.html`, and `downloads.html` are generated as redirect pages to the current content. The former privacy-policy page redirects to the ASF privacy policy.
