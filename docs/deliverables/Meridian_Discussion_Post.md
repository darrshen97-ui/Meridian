# Meridian Financial — an honest ledger for money spread across too many institutions

## Application overview

Meridian Financial consolidates accounts, statements and transactions from many
institutions into one ledger, and then does the thing nobody does by hand: it checks that
the statements and the live account feeds actually agree.

**The problem it solves.** Money is scattered — a couple of banks, a credit card or two, a
payment app, an exchange. Each one shows a slice, and the two records of the same account
routinely disagree: a charge appears twice, an authorisation hold never clears, a cheque
clears on paper but never reaches the app's feed. Spotting that means reading twelve
months of statements line by line against twelve months of app history, so nobody does it,
and small errors sit there for years.

**Who it is for.** People whose finances span several institutions and who want an accurate
picture without handing a year of transaction history to a third-party service. The whole
application runs on the user's own machine, and the AI layer is not permitted to leave it.

**Key features**

- **Statement ingestion that does real work** — PDF, CSV and OFX statements across five
  institution layouts, each with a different column order, date format and sign
  convention. One prints unsigned Withdrawals and Deposits columns, so a row's direction
  survives only in the running balance; another prints dates with no year on them at all.
- **Reconciliation with findings, not just totals** — compares each imported statement
  against the account feed for the same period and reports what differs: duplicate
  charges, transactions on the statement that never reached the feed, holds that never
  cleared. Matching is deterministic; a row dated one to three days apart in the two
  sources is matched, not flagged, because a false alarm costs more than a miss.
- **Deduplication across sources** — importing a statement for an account that already
  synced adds nothing. In the demo, 153 imported documents produced exactly one new row;
  the other few thousand matched what was already there.
- **A local AI layer that stays local** — categorisation and a question-answering coach run
  against a model on `127.0.0.1`. There is no configuration that sends financial data
  anywhere, and the check is enforced at start-up rather than documented in a README.
- **Budgets and a what-if simulator** — targets per category per month, and a simulator for
  adjusting spending and seeing the effect before committing to it.

## Live demo

**https://meridian-792468836580.us-central1.run.app**

Two demo profiles are already signed up, and the welcome screen fills their passwords in —
one click each, nothing to type:

| Profile | What it shows |
| --- | --- |
| Jordan Reyes | Twelve institutions, 117 imported statements, 79 reconciled periods, and three real findings buried in a year of data. |
| Priya Raman | A second, entirely separate ledger — different institutions, merchants and city. Nothing of the first profile is reachable from it. |

Both profiles arrive fully worked through — statements imported, transactions categorised,
every period reconciled, budgets set — so no screen opens empty. Roughly 3,350
transactions across the two of them, all generated; no real financial data exists anywhere
in the project.

*Worth trying:* open **Reconciliation** as the first profile and look for the November
cheque for $230 that never reached the account feed. Every month afterwards still shows a
$230 gap, because the feed's balance stays permanently higher than the statements imply.
That is the point of the feature.

*One thing does not work on the live URL, on purpose:* the AI features. The application
refuses to send financial data to a model it does not host locally, and a container in the
cloud has no local model, so the Coach and the AI-assisted categoriser report themselves
unavailable instead of quietly routing transactions to somebody's API. Everything else
works. To see those features, run it locally with Ollama installed.

## Technical report

### Architecture

| Layer | Choice |
| --- | --- |
| Frontend | React 18 with TypeScript, built by Vite, styled with Tailwind. Compiled into the backend and served by it, so the deployment has no separate frontend host and needs no Node at runtime. |
| Backend | Python 3.11 with FastAPI, fully async. Layered strictly: routers do no business logic, services do no SQL, repositories do no HTTP. Every repository method takes a user id and filters on it. |
| Database | SQLite through SQLAlchemy 2 with Alembic migrations, written to stay PostgreSQL-compatible so moving to a hosted database is configuration rather than a rewrite. Money is stored as integer cents everywhere — never a float. |
| Cloud services | Google Cloud Run (the container), Cloud Build (builds the image from the Dockerfile), Artifact Registry (stores it). The service scales to zero between visits. |
| AI | A local model over Ollama, reached only on `127.0.0.1`. A start-up check refuses any endpoint that does not resolve to loopback. |

*Platform note:* the brief describes AWS App Runner. This is deployed to Google Cloud Run
instead — the same idea (hand it a container, get a public HTTPS URL, scale to zero) on the
platform the first application already used.

### Most challenging feature

Deduplication, and it was not close. When the same transaction arrives from a live feed and
from a PDF statement, the two records differ in date by a day or three and in description
entirely, and the same coffee shop legitimately charges the same amount twice in a week.
Matching too eagerly silently deletes a real transaction from someone's ledger; matching
too cautiously shows every purchase twice. It ended up as two layers: an exact hash that
counts occurrences, so a genuine second identical charge survives, then a one-to-one
assignment pass over amount-exact candidates within three days. The proof it works is the
import figure above — 153 documents, one new row.

### Biggest learning moment

The three worst bugs in this project all lived where the tests do not run. A full test
suite passed while the downloaded application showed a blank white page on Windows,
because that machine's registry maps `.js` to `text/plain` and browsers refuse to execute
a module served that way. Another rendered blank after a rebuild because the browser had
cached an HTML file pointing at bundles that no longer existed. A third would have made
every document in the deployed version unreadable, because file paths were recorded
absolutely and the container builds its database in one directory and reads it from
another.

None of those is a logic error, and no amount of unit testing would have found them. A
green test run proves the code is correct in the environment the tests run in — and
download, install, and deployment are each a different environment. The fix was not more
tests of the same kind; it was regression tests that reproduce the hostile environment, and
actually running the deployment artefact rather than reading it.

### How this differed from the first application

The first was a static site: a folder of files handed to a browser, with no server, no
database and no runtime state to get wrong. This one is a running Python process with a
database, migrations and seeded data, so the deployment was different in kind rather than a
repeat. What made it go faster anyway was deciding the deployment shape at the start
instead of the end — the database layer was written to be portable from the first
migration, and the interface was compiled into the application, so the container needs no
Node toolchain and one command deploys the whole thing.

## Known issues and limitations

**Current limitations**

- **Data entered on the live URL does not persist.** The database is a file inside the
  container, so anything added there resets when the service scales to zero and starts
  fresh. The seeded demo data always returns because it is baked into the image. Fixing
  this means pointing the database URL at a hosted PostgreSQL instance — configuration,
  not a rewrite, since the schema was kept compatible from the beginning — at a real
  monthly cost, which is why it is not done.
- **AI features are unavailable on the public URL.** Described above; a deliberate
  consequence of the privacy rule rather than an omission.
- **Cold starts are visible.** The first request after an idle period takes about four
  seconds while a container starts. Building the seeded database into the image at build
  time cut that down, but scale-to-zero always costs the first visitor something. The trade
  is a service that costs nothing while nobody is using it.

**Not yet implemented**

- **Real bank connections.** Account data comes from a mock provider behind a provider
  interface; the real-provider implementation exists as a documented stub, not working
  code. Building it needs credentials and a production agreement, neither of which a course
  project has.
- **A visible rules editor.** Corrections are already captured and fed back to improve later
  categorisation, but there is no screen for writing a rule directly — the user has to
  correct transactions and let it learn.
- **Multi-currency.** Amounts carry a currency code and are stored as integer minor units,
  so the data model is ready; there is no conversion or mixed-currency reporting on top of
  it.

**Scalability constraints**

The deployed service is pinned to a single instance, because the database is a file inside
the container and two instances would mean two divergent copies of it. That is the binding
limit, and it is the same change that fixes persistence — a hosted database removes both.
Below that, the application is comfortable: queries are indexed and paginated, and the
heaviest operation, reconciling every period at once, is a background-shaped job that took
under a minute for 115 periods.

## Three things I would add with more time

1. **A hosted database**, so the live URL keeps what people put into it. This is the one
   change that turns the deployment from a demonstration into something usable, and it also
   lifts the single-instance ceiling.
2. **A real provider integration** behind the existing interface, so the mock and the real
   feed are interchangeable. The interface was designed for this — the work is credentials,
   error handling and the reconnection flow, not architecture.
3. **A rules screen for categorisation**, so a user can say once that a descriptor means
   Groceries instead of correcting it repeatedly. The corrections are already recorded and
   already improve the model's later suggestions; what is missing is letting someone see
   and edit that knowledge directly.
