import{i as e}from"./rolldown-runtime-COiEfhsA.js";import{i as t,t as n}from"./react-C-U61RdZ.js";import{n as r}from"./marked.esm-DnMePTNb.js";var i=e(t(),1),a=`# About Robotaxi Tracker

Robotaxi Tracker is an independent, community-powered dashboard for the autonomous ride-hailing rollout — tracking Tesla Robotaxi, Waymo, Zoox, and Avride fleets city by city.

## What we track

- **Vehicles** — every robotaxi the community has spotted, identified by license plate, with discovery dates, colors, and service-area assignments.
- **Trips** — real rides logged by riders, including synced Tesla ride receipts with actual fares.
- **Wait times** — live availability and ETA sampling across service areas.
- **Coverage** — official service-area boundaries on the map, kept current as cities launch and expand.
- **Government records** — NHTSA Standing General Order crash reports, the City of Austin's AV incident log, CPUC ride data, and state vehicle records from Texas, California and Arizona.

## How it works

Riders and spotters submit plates, photos, and trips. Submissions are reviewed before entering the registry, and contributors earn badges and leaderboard credit for verified finds. The result is an open, longitudinal record of the robotaxi rollout that doesn't depend on any operator's press releases.

## Apps

Robotaxi Tracker is free on [iPhone](https://apps.apple.com/app/robotaxi-tracker/id6757382794) and [Android](https://play.google.com/store/apps/details?id=com.ethanmckanna.robotaxitracker), with the same account as the site. The apps add Ride Sync, which imports your robotaxi trips so you don't log them by hand, plus a weekly recap of your rides and a quicker way to share what you spot.

## Independence

This project is not affiliated with, authorized by, or endorsed by Tesla, Waymo, Zoox, Avride, or any of their affiliates. All trademarks belong to their respective owners and are used for identification only.

## Get in touch

Questions, corrections, or data requests: reach out on X [@ethanmckanna](https://x.com/ethanmckanna).
`,o=`# Methodology

How the numbers on this site are collected, verified, and what their limits are.

## Vehicle registry

Vehicles enter the registry through community submissions — a spotter reports a license plate, optionally with photos and location. Every submission is manually reviewed before it appears publicly. Duplicate plates are merged per provider, and vehicles unseen for 30+ days are shown as deprecated rather than deleted, since fleets rotate.

**Limits:** the registry is a lower bound. It only contains vehicles the community has actually seen; fleet counts from official sources (like TxDMV registrations) will typically run higher.

### In service

Every "in service" or "vehicles here" figure — the home page, city pages, the provider comparison, and the mobile app — uses one rule: a tracked, non-test vehicle counts unless it is *presumed retired*, which requires both that it has not been spotted in 30+ days **and** that a registry no longer lists it. Two registries provide that evidence: the TxDMV automated-vehicle list (Texas, by VIN, polled continuously) and Tesla's own Robotaxi vehicle lookup (Texas Teslas, by VIN). A vehicle still on a registry stays in service through a sighting gap, and a registry that stalls keeps counting as evidence for up to a week rather than flipping every retired car back in. Outside Texas there is no registry to check, so every tracked vehicle counts — which is why Bay Area and Phoenix totals run high relative to recent sightings.

The \`/vehicles\` page's "deprecated" section is a different, simpler view: vehicles unseen for 30+ days, regardless of registry status. "Active" figures (30-day, 7-day, and the fleet chart) count sightings within a window and are not fleet-size claims.

## Trips and pricing

Trip data comes from rider-logged rides and synced Tesla ride receipts. Fare analytics (median, spread, per-mile, fare by trip length) use priced USD trips only. $0 promo rides are counted separately, every figure shows how many rides it rests on, and figures from fewer than 10 rides are faded so you can judge sample strength.

**Limits:** trips skew toward active community members and Austin-area riders. Pricing reflects what our riders paid, not the fleet-wide average.

## Wait times

Wait-time collectors sample in-app ride estimates at fixed geographic points across each service area every few minutes. "Availability" is the share of sample points where a car was actually offered. When collectors are offline, panels show "no live signal" rather than stale numbers.

## Fleet growth and discovery dates

"First spotted" dates are when the community first saw a vehicle — not when it entered service. Historical dates are refined over time as earlier evidence surfaces.

### The Active fleet chart

A vehicle counts as active on a given day if the community recorded it within the trailing lookback window (30 days by default) — a logged ride, an approved spotting, or a trip report. The shaded band above the line shows the span estimate, a heuristic that assumes each car remained in service between its first and most recent sighting.

Neither series bounds the real fleet: both count only community-recorded vehicles, so cars that operate without being logged — or that keep working after their latest sighting — can put the true count above the band. Read the solid line as "what we verified" and the band as "what the sighting spans make plausible."

Because both series are recomputed from today's records, history can shift as evidence arrives: a newly logged ride on a long-quiet plate raises the span estimate across the whole gap, while the observed line only moves on days with actual sightings. Waymo's headline fleet and per-market figures are the numbers Waymo publishes itself (most recently its September 1, 2026 media factsheet: more than 4,000 vehicles across 14 cities), and its growth chart uses official NHTSA recall fleet counts, since community sightings would undercount a fleet that large.

**Limits:** the observed line dips when logging slows down (quiet weeks read as fleet shrinkage), and days before mid-2025 predate ride syncing, so early history leans on spottings alone. The newest few days are drawn dashed because sightings arrive with a lag — only about a sixth of rides are logged the same day they happen, and receipt syncs come in batches — so a dip at the right edge usually fills in over the following days rather than meaning cars left service.

## Government data

- **NHTSA incidents** come from the Standing General Order 2021-01 public crash-report files, refreshed from NHTSA's published CSVs. Reports are self-reported by manufacturers and are not an exhaustive incident list. AI-generated fault analysis is informational only and may not reflect official determinations.
- **Texas registrations** are polled from the TxDMV Motor Carrier Credentialing System's public operator records, including per-operator fleet counts and authorization numbers.
- **Waymo rollout status** (operating / planned / testing cities) is compiled from official announcements and public testing reports.

## Corrections

Spotted something wrong? Every dataset here is correctable — reach out on X [@ethanmckanna](https://x.com/ethanmckanna) with evidence and we'll fix it.

## The national fleet count

The \`/fleet\` page publishes one "US active robotaxis" number with a breakdown by operator and state. By default it counts **driverless (L4) service only** — deployments with a safety driver or in-car monitor (L2), such as Tesla's Bay Area service, are shown greyed out and can be added with a toggle. Every cell is labeled with the kind of evidence behind it, in order of strength:

- **VIN registry** — Texas DMV automated-vehicle rosters list each active vehicle by VIN under the operator's authorization. We poll them hourly, so Texas is a live time series. Where a roster is known to include test vehicles and cars not yet in service (Waymo's), the operator's own published market figures are used instead and the roster is shown as the ceiling.
- **Estimate** — a dated figure the operator published itself (Waymo's media factsheet per market, NHTSA recall populations), or a curated anchor with a source. Waymo's per-market figures are folded up to states; markets Waymo reports only as "dozens" are counted at an assumed 24 vehicles each and labeled as such.
- **Permit roster** — California DMV permit rosters list vehicles by plate and VIN, but a permit is a ceiling rather than a deployment count: a car can hold one while staged, retired, or working in another state. When an operator has published its own figure for California, that statement wins and the roster is shown as the ceiling.
- **Community sightings** — where the only registry evidence is a *testing* permit (Tesla in California), the roster lists test mules alongside service cars, so the cell is the number of distinct vehicles our spotters have seen there in the last 30 days, with the permit roster as the ceiling.

Where an operator runs service in a state that has no registry and it has published no figure (Tesla in Florida, Zoox and Motional in Nevada), the cell reads "undisclosed" and adds nothing. Each operator is then lifted to its own latest stated national total when the state cells fall short. The headline is therefore a floor — "at least N" — not a point estimate, and it refreshes whenever the Texas registry, a California snapshot, a company statement, or our sightings change. Trucking permit holders on the same registries (Aurora, Kodiak, Gatik, and others) are counted separately and excluded from the robotaxi total.
`,s=`# Privacy Policy

Last updated: August 23, 2026

## Introduction

Welcome to Robotaxi Tracker ("we," "us," or "our"). This Privacy Policy explains how we collect, use, and share information when you use our website and services.

## Information We Collect

### Information You Provide

- Account information (username, display name, email address) when you create an account or sign in with Google, Apple or X, or with a username and password or a passkey. Passwords are stored only as salted hashes, and passkeys only as public keys; we never see your passkey or your password in readable form.

- A profile photo, if you upload one. Your username, display name, bio and profile photo are public on your profile page.

- User-generated content including vehicle submissions, trip logs, sightings, and notes

- Photos you upload for vehicle verification and trip logging

### Automatically Collected Information

- Usage data and analytics (via Google Analytics and Plausible Analytics)

- Device information, browser type, and IP address

- Cookies and similar tracking technologies

## How We Use Your Information

We use the information we collect to:

- Provide, maintain, and improve our services

- Track and display robotaxi fleet data and analytics

- Authenticate users and manage accounts

- Verify submitted vehicle and trip information

- Display community leaderboards and user contributions

- Analyze usage patterns and improve user experience

- Communicate with users about their accounts and our services

## Data Sharing and Third Parties

### Fleet Data Sharing

We may share aggregated, non-personal fleet data with third parties, including:

- Vehicle information (license plates, colors, service areas, discovery dates)

- Trip data (distances, dates, service areas)

- Fleet statistics and growth trends

Important: We do not share personal information such as your name, email address, account details, or any information that could identify you personally when sharing fleet data.

### Third-Party Services

We use the following third-party services:

- Google Analytics: For website analytics and usage tracking

- Plausible Analytics: For privacy-friendly website analytics and usage tracking

- Sign-in providers: Google, Apple and X (when you choose to sign in or link those accounts)

- Cloudflare: For website hosting, content delivery, and backend infrastructure

These services may collect information as described in their respective privacy policies.

## Cookies and Tracking

We use cookies and similar technologies to:

- Maintain your login session

- Remember your preferences (e.g., selected service area)

- Analyze site usage via Google Analytics and Plausible Analytics

## Data Retention

We retain your personal information for as long as your account is active or as needed to provide our services. Verification photos are deleted once vehicle or trip submissions are approved. You may request deletion of your account and associated data at any time.

## Your Rights

You have the right to:

- Access your personal information

- Correct inaccurate information

- Request deletion of your account and data

- Withdraw consent for data processing

## Children's Privacy

Our services are not directed to children under 13. We do not knowingly collect personal information from children under 13. If you believe we have collected such information, please contact us to have it removed.

## Changes to This Policy

We may update this Privacy Policy from time to time. We will notify users of significant changes by posting a notice on our website or through other appropriate communication channels.

## Contact Us

If you have questions about this Privacy Policy or wish to exercise your rights, please contact us at: ethan@robotaxitracker.com
`,c=`# Terms of Service

Last updated: August 23, 2026

## Acceptance of Terms

By accessing and using Robotaxi Tracker ("the Service"), you agree to be bound by these Terms of Service ("Terms"). If you do not agree to these Terms, please do not use the Service.

## Description of Service

Robotaxi Tracker is a community-driven platform that tracks and aggregates information about autonomous vehicle fleets. The Service allows users to:

- View real-time fleet data and statistics

- Submit vehicle discoveries and sightings

- Log trips and contribute to the community database

- Participate in community leaderboards

## User Accounts

To access certain features, you must create an account, either with a username and a password or passkey, or by signing in with Google, Apple or X. You are responsible for:

- Maintaining the security of your account

- All activities that occur under your account

- Providing accurate and complete information

- Updating your information to keep it current

## User Conduct and Content

When using the Service, you agree to:

- Provide accurate and truthful information

- Not submit false, misleading, or fraudulent data

- Not upload inappropriate, offensive, or illegal content

- Not harass, abuse, or harm other users

- Not attempt to gain unauthorized access to the Service

- Not use automated tools to scrape or collect data beyond our public API

- Comply with all applicable laws and regulations

We reserve the right to remove any content and suspend or terminate accounts that violate these Terms.

## Content Ownership and License

### Your Content

You retain ownership of content you submit (photos, trip data, notes). However, by submitting content, you grant us a worldwide, non-exclusive, royalty-free license to:

- Use, display, and distribute your content on the Service

- Include your content in aggregated fleet data and statistics

- Share non-personal fleet data via our public API

- Use your content for service improvement and analytics

### Our Content

All original content, features, and functionality of the Service (excluding user-generated content) are owned by us and protected by copyright, trademark, and other intellectual property laws.

## Data Usage and Sharing

By using the Service, you acknowledge and agree that:

- Fleet data you contribute may be shared with third parties

- Vehicle and trip information will be publicly accessible via our website

- We use analytics tools (Google Analytics and Plausible Analytics) to track usage

- Personal information will not be shared without your consent (see Privacy Policy)

For more details, please review our Privacy Policy.

## Third-Party Links and Services

The Service may contain links to third-party websites or services. We are not responsible for the content, privacy policies, or practices of third-party sites. We encourage you to review their terms and policies before using them.

## Disclaimer of Warranties

THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO:

- Accuracy, reliability, or completeness of information

- Uninterrupted or error-free operation

- Fitness for a particular purpose

- Non-infringement of third-party rights

Important: This project is an independent, community-built tool and is not affiliated with, authorized by, endorsed by, or in any way officially connected with any robotaxi service provider or their subsidiaries or affiliates.

## Limitation of Liability

TO THE MAXIMUM EXTENT PERMITTED BY LAW, WE SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS OR REVENUES, WHETHER INCURRED DIRECTLY OR INDIRECTLY, OR ANY LOSS OF DATA, USE, GOODWILL, OR OTHER INTANGIBLE LOSSES RESULTING FROM:

- Your use or inability to use the Service

- Any unauthorized access to or use of our servers

- Any bugs, viruses, or other harmful code

- Any errors or omissions in content or data

- Any content posted by users or third parties

## Indemnification

You agree to indemnify and hold harmless Robotaxi Tracker, its operators, and affiliates from any claims, damages, losses, liabilities, and expenses (including legal fees) arising from:

- Your use of the Service

- Your violation of these Terms

- Your violation of any rights of another party

- Content you submit to the Service

## Modifications to the Service

We reserve the right to modify, suspend, or discontinue the Service (or any part thereof) at any time with or without notice. We shall not be liable to you or any third party for any modification, suspension, or discontinuance of the Service.

## Changes to Terms

We may update these Terms from time to time. Significant changes will be communicated through the Service or via email. Your continued use of the Service after changes constitutes acceptance of the new Terms.

## Termination

We may terminate or suspend your account and access to the Service immediately, without prior notice, for any reason, including breach of these Terms. Upon termination, your right to use the Service will immediately cease.

## Governing Law

These Terms shall be governed by and construed in accordance with the laws of the United States, without regard to its conflict of law provisions.

## Entire Agreement

These Terms, together with our Privacy Policy, constitute the entire agreement between you and Robotaxi Tracker regarding the use of the Service.

## Contact Information

If you have questions about these Terms, please contact us at: ethan@robotaxitracker.com
`,l=`# Delete your account

Robotaxi Tracker lets you delete your account and its associated data at any time.

## Delete in the app or on the website

- **App (iOS or Android):** open **Robotaxi Tracker**, go to the **You** tab, open **Settings** and choose **Delete account**.
- **Website:** sign in at robotaxitracker.com, open **Account settings**, and under **Security** choose **Delete account**.

Deletion is immediate. It removes your account record (username, display name, email address), every way you signed in (linked Google, Apple and X accounts, your password and passkeys), your profile photo, and all signed-in sessions.

## Delete by request

If you can't access the app, email **ethan@robotaxitracker.com** from the address associated with your account and request deletion. We'll process the request within 30 days.

## What is kept

Rides you logged or imported and community contributions you made (vehicle sightings and submissions, with their photos) stay in the public dataset without your name, no longer connected to any account. No additional retention period applies.
`,u=n();function d({source:e}){let t=e.match(/^# (.+)$/m)?.[1]??``,n=(0,i.useMemo)(()=>r.parse(e.replace(/^# .+$/m,``).trim(),{async:!1}),[e]);return(0,u.jsxs)(`div`,{className:`mx-auto w-full max-w-3xl`,children:[(0,u.jsx)(`h1`,{className:`font-display text-3xl font-bold tracking-tight text-fg sm:text-4xl`,children:t}),(0,u.jsx)(`div`,{className:`prose-news mt-6`,dangerouslySetInnerHTML:{__html:n}})]})}function f(){return(0,u.jsx)(d,{source:a})}function p(){return(0,u.jsx)(d,{source:o})}function m(){return(0,u.jsx)(d,{source:s})}function h(){return(0,u.jsx)(d,{source:c})}function g(){return(0,u.jsx)(d,{source:l})}export{f as AboutPage,g as DeleteAccountPage,p as MethodologyPage,m as PrivacyPage,h as TermsPage};