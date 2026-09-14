/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements. See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership. The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at
 *
 * https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { XMLParser, XMLValidator } from 'fast-xml-parser';
import { parse, stringify } from 'yaml';
import projectMetadata, { renderDoap, redirects } from '../plugins/project-metadata.mjs';

const config = parse(await readFile(new URL('../../.asf.yaml', import.meta.url), 'utf8'));
const parser = new XMLParser({ ignoreAttributes: false });

test('DOAP preserves text, resource attributes, and repeated fields through XML parsing', () => {
  const metadata = {
    ...config.project.metadata,
    name: 'An election: "A & B" < C',
    description: "It's a vote — yes & no",
    bug_database: 'https://example.org/issues?state=open&label=vote',
    repositories: ['https://example.org/one.git', 'https://example.org/two.git'],
    categories: ['library', 'testing'],
    programming_languages: ['Python', 'Perl'],
  };
  const xml = renderDoap(metadata);
  assert.equal(XMLValidator.validate(xml), true);
  // The projects.apache.org importer reads the first child of the RDF root.
  const root = parser.parse(xml)['rdf:RDF'];
  assert.equal(root['@_xmlns'], 'http://usefulinc.com/ns/doap#');
  const project = root.Project;
  assert.equal(project.name, metadata.name);
  assert.equal(project.description, metadata.description);
  assert.equal(project['bug-database']['@_rdf:resource'], metadata.bug_database);
  assert.deepEqual(
    project.repository.map((entry) => entry.GitRepository.location['@_rdf:resource']),
    metadata.repositories,
  );
  assert.deepEqual(project['programming-language'], metadata.programming_languages);
  assert.deepEqual(
    project.category.map((entry) => entry['@_rdf:resource']),
    metadata.categories.map((category) => `http://projects.apache.org/category/${category}`),
  );
});

test('build output uses the current source metadata and retains branch publishing configuration', async (t) => {
  const root = await mkdtemp(path.join(tmpdir(), 'steve-site-test-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const siteDir = path.join(root, 'site');
  const outDir = path.join(siteDir, 'build');
  await mkdir(outDir, { recursive: true });
  const source = structuredClone(config);
  source.project.metadata.name = 'An updated project';
  const yaml = stringify(source);
  await writeFile(path.join(root, '.asf.yaml'), yaml);
  const plugin = projectMetadata({
    siteDir,
    siteConfig: { url: 'https://steve-example.staged.apache.org' },
  });
  await plugin.postBuild({ outDir });
  assert.equal(await readFile(path.join(outDir, '.asf.yaml'), 'utf8'), yaml);
  const xml = await readFile(path.join(outDir, 'doap.rdf'), 'utf8');
  assert.equal(XMLValidator.validate(xml), true);
  const project = parser.parse(xml)['rdf:RDF'].Project;
  assert.equal(project.name, source.project.metadata.name);
  // A preview must still describe the production project to metadata consumers.
  assert.equal(project.homepage['@_rdf:resource'], source.project.metadata.homepage);
  for (const [from, to] of Object.entries(redirects)) {
    const html = await readFile(path.join(outDir, from), 'utf8');
    assert.ok(html.includes(`content="0;url=${to}"`));
    assert.ok(html.includes(new URL(to, 'https://steve-example.staged.apache.org').href));
  }
});
