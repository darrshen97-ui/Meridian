// Deployment report deliverable.  node scripts/build_deployment_report.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, LevelFormat,
  Packer, PageBreak, Paragraph, ShadingType, Table, TableCell, TableRow,
  TextRun, WidthType,
} from "docx";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "docs", "deliverables");
fs.mkdirSync(OUT, { recursive: true });
const LETTER = { width: 12240, height: 15840 };
const CONTENT = 9360;

const NUMBERING = { config: [{
  reference: "bullets",
  levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
             alignment: AlignmentType.LEFT,
             style: { paragraph: { indent: { left: 360, hanging: 240 } } } }],
}] };

const p = (t, o = {}) => new Paragraph({
  spacing: { after: o.after ?? 130, line: 268 },
  children: [new TextRun({ text: t, size: o.size ?? 20, bold: o.bold, italics: o.italics })],
});
const bullet = (t) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  spacing: { after: 70, line: 264 },
  children: [new TextRun({ text: t, size: 20 })],
});
const mono = (t) => new Paragraph({
  spacing: { after: 90, line: 250 },
  shading: { type: ShadingType.CLEAR, fill: "F4F4F2", color: "auto" },
  children: [new TextRun({ text: t, size: 17, font: "Consolas" })],
});
const h1 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 140 },
  children: [new TextRun({ text: t, size: 25, bold: true })] });
const h2 = (t) => new Paragraph({
  spacing: { before: 180, after: 90 },
  children: [new TextRun({ text: t, size: 21, bold: true })] });
const rule = () => new Paragraph({
  spacing: { after: 180 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "C9C9C6" } },
  children: [new TextRun({ text: "", size: 2 })] });

function cell(text, { width, bold, shade, size = 17 } = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: shade ? { type: ShadingType.CLEAR, fill: shade, color: "auto" } : undefined,
    margins: { top: 70, bottom: 70, left: 90, right: 90 },
    children: [new Paragraph({ spacing: { after: 0, line: 240 },
      children: [new TextRun({ text, size, bold })] })] });
}
const table = (headers, rows, widths) => new Table({
  columnWidths: widths,
  width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  rows: [
    new TableRow({ tableHeader: true, children: headers.map((h, i) =>
      cell(h, { width: widths[i], bold: true, shade: "F0F0EE" })) }),
    ...rows.map((r) => new TableRow({ children: r.map((c, i) =>
      cell(String(c), { width: widths[i] })) })),
  ] });

function shotBox(instructions) {
  return [
    new Table({ columnWidths: [CONTENT], width: { size: CONTENT, type: WidthType.DXA },
      rows: [new TableRow({ children: [new TableCell({
        width: { size: CONTENT, type: WidthType.DXA },
        borders: {
          top: { style: BorderStyle.DASHED, size: 6, color: "C9C9C6" },
          bottom: { style: BorderStyle.DASHED, size: 6, color: "C9C9C6" },
          left: { style: BorderStyle.DASHED, size: 6, color: "C9C9C6" },
          right: { style: BorderStyle.DASHED, size: 6, color: "C9C9C6" } },
        children: [
          new Paragraph({ spacing: { before: 700, after: 100 }, alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "[ Paste screenshot here ]", size: 21, bold: true, color: "9A9CA1" })] }),
          new Paragraph({ spacing: { after: 700 }, alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: instructions, size: 17, italics: true, color: "9A9CA1" })] }),
        ] })] })] }),
    new Paragraph({ spacing: { after: 260 }, children: [new TextRun({ text: "" })] }),
  ];
}

const STEPS = [
  ["1", "Containerised the app", "Wrote a Dockerfile (python:3.11-slim, non-root user) and serve.py, a production entry point that binds 0.0.0.0:$PORT, applies database migrations and seeds the two demo profiles at start-up."],
  ["2", "Configured for TLS behind Cloud Run", "Session cookies are issued with the Secure flag in the container image, because Cloud Run terminates HTTPS in front of the application."],
  ["3", "Verified the deployment artefact locally", "Ran the production entry point under Cloud Run's exact environment variables: migrations applied, 2,277 and 1,073 transactions seeded, health endpoint healthy, interface rendered, and the session cookie confirmed to carry HttpOnly, SameSite=Strict and Secure."],
  ["4", "Pushed to GitHub", "The repository already held the built interface and the release archive, so the same commit is both the local download and the deployment source."],
  ["5", "Deployed to Cloud Run", "gcloud run deploy builds the container with Cloud Build and publishes it; the service is pinned to a single instance because the database is a file inside the container."],
  ["6", "Verified the live URL", "Loaded the public URL, signed in as the demo profile, exercised each screen, and checked it on a phone."],
];

const doc = new Document({
  numbering: NUMBERING,
  styles: { default: { document: { run: { font: "Calibri", size: 20 } } } },
  sections: [{
    properties: { page: { size: LETTER, margin: { top: 1300, bottom: 1300, left: 1300, right: 1300 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: "Meridian Financial — Deployment Report", size: 15, color: "9A9CA1" })] })] }) },
    children: [
      new Paragraph({ spacing: { after: 50 },
        children: [new TextRun({ text: "Meridian Financial", size: 36, bold: true })] }),
      new Paragraph({ spacing: { after: 40 },
        children: [new TextRun({ text: "Deployment Report — Application #2", size: 23, color: "6E7178" })] }),
      new Paragraph({ spacing: { after: 200 },
        children: [new TextRun({ text: "Google Cloud Run · August 2026 · github.com/darrshen97-ui/Meridian", size: 18, color: "6E7178" })] }),
      rule(),

      h1("1. Live application URL"),
      p("Cloud Run assigns the URL when the service is first deployed. Paste it here once the deploy completes:"),
      mono("https://______________________.run.app"),
      p("Platform note: the course template describes AWS App Runner. Meridian is deployed to Google Cloud Run instead, which is the platform used for the first application and the target named in this project's own architecture document. Cloud Run is the equivalent service — a container is built from the GitHub repository and served on a public HTTPS URL with automatic scaling and a free tier.", { italics: true }),

      h1("2. Deployment steps"),
      table(["#", "Step", "What was done"], STEPS, [420, 1900, 7040]),

      h2("The commands"),
      p("Run from Google Cloud Shell (shell.cloud.google.com), a browser terminal with gcloud and git already installed, so the deployment needs nothing installed locally. Once per project:"),
      mono("gcloud config set project YOUR_PROJECT_ID"),
      mono("gcloud services enable run.googleapis.com cloudbuild.googleapis.com \\"),
      mono("    artifactregistry.googleapis.com"),
      mono("git clone https://github.com/darrshen97-ui/Meridian.git && cd Meridian"),
      p("Then to deploy, and again for any future update:"),
      mono("gcloud run deploy meridian --source . --region us-central1 \\"),
      mono("    --allow-unauthenticated --max-instances 1 --memory 1Gi \\"),
      mono("    --set-env-vars JWT_SECRET=$(openssl rand -base64 36)"),
      p("Cloud Build reads the committed Dockerfile, builds the image, and Cloud Run publishes it. The command prints the public URL when it finishes. One instance because the database is a file inside the container; a fixed session key because otherwise a new one is generated on each cold start and signs everyone out; and no --min-instances, which is what lets the service scale to zero and cost nothing while idle."),

      h2("What it costs"),
      p("Nothing, at this scale. Cloud Run bills for the time a container is actually serving a request, and its permanent monthly free tier — on the order of two million requests and 180,000 vCPU-seconds — is far beyond what a demonstration uses. Between visits the service runs zero instances and bills zero. Cloud Build and the image registry are likewise inside their free allowances for an image this size. A billing account has to be attached to the project even so."),

      new Paragraph({ children: [new PageBreak()] }),

      h1("3. Evidence"),
      h2("Screenshot 1 — the application running on its Cloud Run URL"),
      ...shotBox("The live https://….run.app address visible in the URL bar, signed in as Jordan Reyes on the Dashboard, with the system clock visible."),
      h2("Screenshot 2 — the Cloud Run console showing both services running"),
      ...shotBox("Google Cloud console → Cloud Run, showing this service and the first application's service, both with a green Running status, with the system clock visible."),
      h2("Screenshot 3 — the GitHub repository holding this application's code"),
      ...shotBox("github.com/darrshen97-ui/Meridian with the file list visible, with the system clock visible."),

      new Paragraph({ children: [new PageBreak()] }),

      h1("4. How this deployment compared with the first"),
      p("The first deployment was a static site: a folder of built files copied to a host, with no server, no database and no runtime configuration to get wrong. This one is a real application — a Python service, a database, migrations and seeded data — so the work was different in kind rather than simply repeated. What made it faster anyway was that the deployment shape had been decided at the start rather than at the end: the architecture named Cloud Run before any code existed, the database layer was written to be portable from the first migration, and the interface was already built into the application, so the container needs no Node toolchain and the same commit serves as both the local download and the deployment source."),
      p("The practical difference is that the second deployment is one command that anyone can repeat, and it is reproducible: the same Dockerfile that Cloud Build uses can be run locally, so the deployment artefact is testable rather than something that only exists in the cloud."),

      h1("5. Challenges, and how AI helped"),
      h2("A path bug that only exists in a container"),
      p("Preparing the image surfaced a genuine defect. The code that ensures the database directory exists split the connection string on three slashes, which strips the leading slash of an absolute path: sqlite:////tmp/meridian/meridian.db silently became the relative tmp/meridian/meridian.db. Local runs use a relative path, so 157 passing tests had never touched the branch; the very first container start failed to open its database. It is now parsed with the database library's own URL parser, and a regression test covers both the absolute and relative forms."),
      p("The lesson matches the one from the testing assignment: a green test run proves the code is correct in the environment the tests run in, and deployment is a different environment."),

      h2("Paying for the same work on every visit"),
      p("Scale-to-zero has a cost of its own: the first request after an idle period waits for a container to start, and the start-up applied database migrations and seeded 3,350 transactions every single time — identical work with an identical result, charged as CPU and paid for in latency by whoever arrived first. The database is now built once during the image build and copied into place at start-up, which measured 4.4 seconds down to 0.76. The original path still runs when no prepared database is present, so an older image, or a future move to a hosted database, starts correctly either way."),

      h2("Deliberate limitations, stated rather than hidden"),
      bullet("The database is a file inside the container, so anything entered on the live URL resets when a new revision starts. The service is pinned to one instance for that reason. Persistence is a configuration change to Cloud SQL, not a rewrite — the schema was constrained to be portable from the beginning."),
      bullet("The AI features are unavailable on the public URL, and this is by design rather than an omission: the application refuses to send financial data to any model it does not host locally, so a cloud deployment has no model to talk to. Every other feature works, which is the same degraded-but-not-broken behaviour the application shows when the local model is missing."),

      h2("How AI helped"),
      p("The assistant produced the whole deployment configuration — container image, production entry point, and the verification run — and, more usefully, tested it under Cloud Run's environment variables rather than assuming it would work. That is what exposed the path bug before it became a failed deployment to debug through cloud logs."),
    ],
  }],
});

fs.writeFileSync(path.join(OUT, "Meridian_Deployment_Report.docx"), await Packer.toBuffer(doc));
console.log("wrote docs/deliverables/Meridian_Deployment_Report.docx");
