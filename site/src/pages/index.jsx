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

import React from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

export default function Home() {
  return (
    <Layout
      title="Tools for community elections"
      description="Apache STeVe is a collection of open source voting tools for Single Transferable Vote and other voting methods, developed at the Apache Software Foundation."
    >
      <main>
        <section className="home-hero">
          <div className="site-width hero-grid">
            <div>
              <p className="eyebrow">An Apache Software Foundation project</p>
              <h1>
                Community decisions.
                <br />
                <span>Counted together.</span>
              </h1>
              <p className="hero-description">
                Apache STeVe brings open source tools to community elections, from casting a ballot
                to counting a Single Transferable Vote.
              </p>
              <div className="hero-actions">
                <Link className="button button--primary button--lg" to="/getting-started/">
                  Get started <span aria-hidden="true">↗</span>
                </Link>
                <Link className="source-link" href="https://github.com/apache/steve">
                  Explore the source <span aria-hidden="true">→</span>
                </Link>
              </div>
            </div>
            <aside className="election-path" aria-label="The election process">
              <p className="eyebrow">From ballot to result</p>
              <ol>
                <li>
                  <span className="step-number" aria-hidden="true">
                    01
                  </span>
                  <div>
                    <h2>Set up an election</h2>
                    <p>Define the issues, candidates, and eligible voters.</p>
                  </div>
                </li>
                <li>
                  <span className="step-number" aria-hidden="true">
                    02
                  </span>
                  <div>
                    <h2>Cast a vote</h2>
                    <p>Rank candidates or vote yes, no, or abstain.</p>
                  </div>
                </li>
                <li>
                  <span className="step-number" aria-hidden="true">
                    03
                  </span>
                  <div>
                    <h2>Count the ballots</h2>
                    <p>Tally the result and explore STV scenarios.</p>
                  </div>
                </li>
              </ol>
            </aside>
          </div>
        </section>
        <div className="development-note">
          <div className="site-width">
            <strong>Current development: v3</strong>
            <span>A Python application with SQLite storage.</span>
            <Link to="/getting-started/">
              Set up a development environment <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
        <section className="site-width home-section">
          <div className="section-heading">
            <p className="eyebrow">The tools</p>
            <h2>Two ways to work with STeVe.</h2>
          </div>
          <div className="tool-grid">
            <article>
              <span className="tool-label">Run an election</span>
              <h3>The v3 voting application</h3>
              <p>
                Manage elections, issues, and ballots in a web application. The current
                implementation supports Single Transferable Vote and yes/no/abstain voting.
              </p>
              <Link to="/documentation/#v3-voting-application">
                Read the v3 documentation <span aria-hidden="true">→</span>
              </Link>
            </article>
            <article>
              <span className="tool-label">Work with the results</span>
              <h3>STV tally &amp; what-if tools</h3>
              <p>
                Use the shared Meek STV engine to count ballots from a closed election. Explore how
                the result changes with different seat counts or candidate selections.
              </p>
              <Link to="/documentation/#tally-and-what-if-tools">
                Explore the tally tools <span aria-hidden="true">→</span>
              </Link>
            </article>
          </div>
        </section>
        <section className="community-band">
          <div className="site-width community-grid">
            <div>
              <p className="eyebrow">Built in the open</p>
              <h2>A project shaped by its community.</h2>
              <p>
                STeVe grew out of the system used to elect the ASF Board of Directors. Development
                happens in public, and contributions to the code and documentation are welcome.
              </p>
            </div>
            <Link className="button button--outline button--primary button--lg" to="/community/">
              Join the conversation <span aria-hidden="true">→</span>
            </Link>
          </div>
        </section>
      </main>
    </Layout>
  );
}
