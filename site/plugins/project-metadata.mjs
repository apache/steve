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

import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { parse } from 'yaml';

const entities = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' };
const escapeXml = (value) => String(value).replace(/[&<>"']/g, (character) => entities[character]);

export function renderDoap(project) {
  const text = (tag, value) => `  <${tag}>${escapeXml(value)}</${tag}>`;
  const resource = (tag, value) => `  <${tag} rdf:resource="${escapeXml(value)}" />`;
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<!-- Generated from .asf.yaml. Edit project.metadata in the source repository. -->',
    '<rdf:RDF xmlns="http://usefulinc.com/ns/doap#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:asfext="http://projects.apache.org/ns/asfext#">',
    `<Project rdf:about="${escapeXml(project.homepage)}">`,
    text('name', project.name),
    text('shortdesc', project.short_description),
    text('description', project.description),
    resource('homepage', project.homepage),
    resource('download-page', project.download_page),
    resource('bug-database', project.bug_database),
    resource('mailing-list', project.mailing_lists),
    resource('license', 'https://www.apache.org/licenses/LICENSE-2.0'),
    resource('asfext:pmc', `https://${project.committee}.apache.org`),
    ...project.categories.map((category) =>
      resource('category', `http://projects.apache.org/category/${category}`),
    ),
    ...project.programming_languages.map((language) => text('programming-language', language)),
    ...project.repositories.map(
      (repository) =>
        `  <repository><GitRepository><location rdf:resource="${escapeXml(repository)}" /></GitRepository></repository>`,
    ),
    '</Project>',
    '</rdf:RDF>',
    '',
  ].join('\n');
}

export const redirects = {
  'demo.html': '/getting-started/',
  'develop.html': '/getting-started/',
  'documentation.html': '/documentation/',
  'vote_types.html': '/documentation/#voting-methods',
  'community.html': '/community/',
  'support.html': '/community/',
  'downloads.html': '/downloads/',
  'privacy-policy.html': 'https://privacy.apache.org/policies/privacy-policy-public.html',
};

export default function projectMetadata(context) {
  const asfConfig = path.resolve(context.siteDir, '../.asf.yaml');
  return {
    name: 'project-metadata',
    getPathsToWatch: () => [asfConfig],
    async postBuild({ outDir }) {
      const source = await readFile(asfConfig, 'utf8');
      const { project } = parse(source);
      await writeFile(path.join(outDir, 'doap.rdf'), renderDoap(project.metadata));
      // ASF evaluates publishing and staging configuration on the generated branch.
      await writeFile(path.join(outDir, '.asf.yaml'), source);
      for (const [from, to] of Object.entries(redirects)) {
        const destination = escapeXml(to);
        await writeFile(
          path.join(outDir, from),
          `<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>Page moved · Apache STeVe</title><meta http-equiv="refresh" content="0;url=${destination}"><link rel="canonical" href="${escapeXml(new URL(to, context.siteConfig.url).href)}"></head><body><p>This page has moved. <a href="${destination}">Continue to Apache STeVe</a>.</p></body></html>\n`,
        );
      }
    },
  };
}
