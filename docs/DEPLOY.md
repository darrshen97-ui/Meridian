# Deploying Meridian to Google Cloud Run

This is the whole deployment: one command, no local installs, and it costs nothing
under normal demo traffic. Read the first section if you want to know *why* it's
Cloud Run and not the static hosting used for the first application; skip to
**Deploy it** if you just want the URL.

---

## Why this app needs Cloud Run and the first one didn't

The first application was a **static site** — HTML, CSS and JavaScript files. A
static host takes that folder and hands the files to browsers. Nothing runs on the
server; all the behaviour happens in the visitor's browser.

Meridian is a **server application**. There is a Python process that has to be
running to answer requests: it holds the database, hashes passwords, parses uploaded
statements, runs reconciliation. A static host has nowhere to put that process, so
there is nothing it can serve except the interface, which would then have no
backend to talk to.

**Cloud Run runs containers.** You hand it the app packaged as a container image, it
runs the container on Google's infrastructure and gives you a public HTTPS URL. It
starts containers when requests arrive and stops them when traffic stops — this is
called **scale to zero**, and it's the reason the bill is what it is.

## What it costs

Nothing, for this. Cloud Run bills for the time a container is actually handling a
request, measured in vCPU-seconds and memory-seconds, and its permanent monthly free
tier — around 2 million requests, 180,000 vCPU-seconds and 360,000 GiB-seconds at
the time of writing — is far more than a demo, a marker and a handful of classmates
will use. Between visits the service scales to zero instances and bills nothing at
all. Cloud Build (which turns the repository into a container image) has a free daily
build allowance, and the built image sits in Artifact Registry, whose first 0.5 GB is
free — this image is well under that.

Two things to know:

- A billing account with a card must be attached to the project even though the free
  tier covers this. New Google Cloud accounts get $300 of credit.
- **Do not set `--min-instances`.** Leaving it at the default of 0 is what makes the
  service free when idle; setting it to 1 keeps a container running around the clock
  and is the one easy way to turn this into a real monthly charge.

Confirm current figures at https://cloud.google.com/run/pricing — these are the
published rates, not a quote.

---

## Deploy it

You do not need to install anything. **Google Cloud Shell** is a terminal in the
browser with `gcloud`, `git` and Docker already installed, and it is free.

1. **Open Cloud Shell** — go to https://shell.cloud.google.com and sign in with the
   Google account you want the project billed to. Click **Continue** when it asks to
   authorise the shell.

2. **Pick or create a project.** To see the projects you already have:

   ```bash
   gcloud projects list
   ```

   To create one (the ID must be globally unique — add digits if it's taken):

   ```bash
   gcloud projects create meridian-finance-app --name="Meridian"
   ```

   Then set it as the default and link billing in the console at
   https://console.cloud.google.com/billing if the project is new:

   ```bash
   gcloud config set project meridian-finance-app
   ```

3. **Turn on the two services this uses** (one time per project):

   ```bash
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
       artifactregistry.googleapis.com
   ```

4. **Get the code:**

   ```bash
   git clone https://github.com/darrshen97-ui/Meridian.git
   cd Meridian
   ```

5. **Deploy:**

   ```bash
   gcloud run deploy meridian \
       --source . \
       --region us-central1 \
       --allow-unauthenticated \
       --max-instances 1 \
       --memory 1Gi \
       --set-env-vars JWT_SECRET=$(openssl rand -base64 36)
   ```

   Answer `y` if it offers to create an Artifact Registry repository. The build takes
   three to five minutes the first time; it prints the public URL when it finishes:

   ```
   Service URL: https://meridian-xxxxxxxxxx-uc.a.run.app
   ```

6. **Open the URL and sign in** with either demo profile:

   | Profile | Email | Password |
   | --- | --- | --- |
   | Jordan Reyes | `jordan@meridian.demo` | `rowhouse-ledger-26` |
   | Priya Raman | `priya@meridian.demo` | `lakefront-audit-26` |

That URL is public. Anyone you send it to can use the app.

### What the flags mean

| Flag | Why |
| --- | --- |
| `--source .` | Build from this folder using its `Dockerfile`. No local Docker needed — Cloud Build does it. |
| `--allow-unauthenticated` | The URL is public. Without this, visitors get a Google sign-in wall. |
| `--max-instances 1` | The database is a file inside the container, so two instances would mean two separate databases. |
| `--memory 1Gi` | Enough headroom for the PDF parser and the seeded dataset. |
| `--set-env-vars JWT_SECRET=…` | Fixes the session-signing key. Without it a new key is generated on each cold start, which signs everyone out whenever the service has been idle. |

### Updating it

Push to GitHub, then in Cloud Shell:

```bash
git pull && gcloud run deploy meridian --source . --region us-central1
```

Flags set on an earlier deploy are kept. Cloud Run switches traffic to the new
revision only after it starts successfully, so a broken build cannot take the live
URL down.

### Shutting it down

```bash
gcloud run services delete meridian --region us-central1
```

---

## What the deployed version can and cannot do

**Works:** every screen — dashboard, accounts, transactions, document upload and
parsing, reconciliation, budgets, the simulator, search, settings — plus the two
seeded profiles with 3,350 transactions between them.

**Resets on restart.** The database is a file inside the container, so anything you
add on the live URL disappears when the service scales to zero and starts fresh. The
seeded demo data always comes back, because it's baked into the image. Making it
permanent means pointing `DATABASE_URL` at Cloud SQL — a configuration change, since
the schema was kept PostgreSQL-compatible from the first migration, but one that
costs about $9/month for the smallest instance and so is deliberately not done here.

**AI features are off, by design.** Meridian refuses to send financial data to any
model it does not host on `127.0.0.1`, and that check is not bypassable by
configuration. A Cloud Run container has no local model, so the Coach and the
AI-assisted categoriser report themselves unavailable rather than quietly routing
your transactions to somebody's API. This is the same degraded-but-honest behaviour
you get locally when Ollama isn't running — to see those features, run the app from
the release zip on your own machine.

## Cold starts

The first request after an idle period waits for a container to start. The seeded
database is built into the image at build time rather than migrated and seeded on
each start, which took that wait from about 4.4 seconds to under one (D-028). It is
still not instant — that's the trade for a service that costs nothing while nobody
is using it.
