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

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Apache STeVe',
  tagline: 'Open source tools for community elections',
  url: process.env.SITE_URL || 'https://steve.apache.org',
  baseUrl: '/',
  trailingSlash: true,
  onBrokenLinks: 'throw',
  markdown: {
    format: 'detect',
    hooks: { onBrokenMarkdownLinks: 'throw' },
  },
  presets: [
    [
      'classic',
      {
        docs: false,
        blog: false,
        theme: { customCss: './src/css/custom.css' },
      },
    ],
  ],
  plugins: ['./plugins/project-metadata.mjs'],
  themeConfig: {
    colorMode: { defaultMode: 'light', disableSwitch: true, respectPrefersColorScheme: false },
    navbar: {
      logo: { alt: 'Apache STeVe', src: 'images/logo.svg' },
      items: [
        { to: '/getting-started/', label: 'Get started', position: 'right' },
        { to: '/documentation/', label: 'Documentation', position: 'right' },
        { to: '/community/', label: 'Community', position: 'right' },
        { to: '/downloads/', label: 'Downloads', position: 'right' },
        { href: 'https://github.com/apache/steve', label: 'GitHub', position: 'right' },
      ],
    },
    footer: {
      style: 'light',
      links: [
        {
          title: 'Apache STeVe',
          items: [
            { label: 'Documentation', to: '/documentation/' },
            { label: 'Community', to: '/community/' },
            { label: 'Source code', href: 'https://github.com/apache/steve' },
          ],
        },
        {
          title: 'The Apache Software Foundation',
          items: [
            { label: 'Foundation', href: 'https://www.apache.org/' },
            { label: 'License', href: 'https://www.apache.org/licenses/LICENSE-2.0' },
            { label: 'Events', href: 'https://events.apache.org/' },
          ],
        },
        {
          title: 'More from Apache',
          items: [
            { label: 'Security', href: 'https://www.apache.org/security/' },
            {
              label: 'Privacy',
              href: 'https://privacy.apache.org/policies/privacy-policy-public.html',
            },
            { label: 'Sponsorship', href: 'https://www.apache.org/foundation/sponsorship.html' },
            { label: 'Thanks', href: 'https://www.apache.org/foundation/thanks.html' },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} The Apache Software Foundation. Licensed under the Apache License, Version 2.0.<br />Apache, Apache STeVe, STeVe, the Apache feather logo, and the Apache STeVe logo are trademarks of The Apache Software Foundation.`,
    },
  },
};

export default config;
