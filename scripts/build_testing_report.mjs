// Builds the Testing & Security Report + Reflection deliverable.
//   node scripts/build_testing_report.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, ImageRun,
  LevelFormat, Packer, PageBreak, Paragraph, ShadingType, Table, TableCell,
  TableRow, TextRun, WidthType,
} from "docx";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "docs", "deliverables");
const SHOTS = path.join(ROOT, "docs", "screenshots", "dev");
fs.mkdirSync(OUT, { recursive: true });

const LETTER = { width: 12240, height: 15840 };
const CONTENT = 9360;

const NUMBERING = { config: [{
  reference: "bullets",
  levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
             alignment: AlignmentType.LEFT,
             style: { paragraph: { indent: { left: 360, hanging: 240 } } } }],
}] };

const p = (text, o = {}) => new Paragraph({
  spacing: { after: o.after ?? 130, line: 268 },
  children: [new TextRun({ text, size: o.size ?? 20, bold: o.bold,
                           italics: o.italics, color: o.color })],
});

const bullet = (parts) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  spacing: { after: 70, line: 264 },
  children: (Array.isArray(parts) ? parts : [[parts]]).map(([t, o = {}]) =>
    new TextRun({ text: t, size: 20, bold: o.b, italics: o.i })),
});

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 280, after: 140 },
  children: [new TextRun({ text, size: 25, bold: true, color: "16181D" })],
});

const h2 = (text) => new Paragraph({
  spacing: { before: 180, after: 90 },
  children: [new TextRun({ text, size: 21, bold: true })],
});

const rule = () => new Paragraph({
  spacing: { after: 180 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "C9C9C6" } },
  children: [new TextRun({ text: "", size: 2 })],
});

function cell(text, { width, bold, shade, size = 17 } = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: shade ? { type: ShadingType.CLEAR, fill: shade, color: "auto" } : undefined,
    margins: { top: 70, bottom: 70, left: 90, right: 90 },
    children: [new Paragraph({ spacing: { after: 0, line: 240 },
      children: [new TextRun({ text, size, bold })] })],
  });
}

const table = (headers, rows, widths) => new Table({
  columnWidths: widths,
  width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  rows: [
    new TableRow({ tableHeader: true,
      children: headers.map((h, i) => cell(h, { width: widths[i], bold: true, shade: "F0F0EE" })) }),
    ...rows.map((r) => new TableRow({
      children: r.map((c, i) => cell(String(c), { width: widths[i] })) })),
  ],
});

let figureNumber = 0;
function figure(fileName, caption, maxWidth = 500) {
  const file = path.join(SHOTS, fileName);
  const head = fs.readFileSync(file).subarray(16, 24);
  const w = head.readUInt32BE(0), h = head.readUInt32BE(4);
  const width = Math.min(maxWidth, w);
  figureNumber += 1;
  return [
    new Paragraph({ spacing: { before: 140, after: 50 }, alignment: AlignmentType.CENTER,
      children: [new ImageRun({ type: "png", data: fs.readFileSync(file),
        transformation: { width, height: Math.round(width * (h / w)) } })] }),
    new Paragraph({ spacing: { after: 200 }, alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: `Figure ${figureNumber}. ${caption}`, size: 16,
                               italics: true, color: "6E7178" })] }),
  ];
}

/* ------------------------------------------------------------------ data -- */

const FEATURES = [
  ["Profile create / sign in", "Valid + wrong password, short password, duplicate email, 9 bad attempts", "Pass"],
  ["Profile switching", "Switch requires re-authentication; no data bleeds between profiles", "Pass"],
  ["Dashboard", "Spending power, month comparison, attention counts, recent activity", "Pass"],
  ["Live sync (SSE)", "Sync now, per-account progress, 50% provider failure rate, 429s", "Pass"],
  ["Accounts", "Grouping, balances, closed accounts de-emphasised", "Pass"],
  ["Transactions", "Search, 5 filters, paging, inline category edit + rollback", "Pass"],
  ["Statement upload", "PDF / CSV / OFX, 117 documents, duplicate upload, 16 MB file, .xyz file", "Pass"],
  ["Import preview", "Nothing written until confirmed; ambiguous account asks", "Pass"],
  ["Categorization", "Rules pass, LLM pass, hallucinated category, model absent", "Pass"],
  ["Review queue", "Accept, bulk apply, keyboard j/k/a/Shift+A", "Pass"],
  ["Reconciliation", "79 periods, 13 planted anomalies, resolve action", "Pass"],
  ["AI coach", "Grounded answers, 4-call cap, no-data honesty, model absent", "Pass"],
  ["Budgets + simulator", "Set/clear target, projection, category with no history", "Pass"],
  ["Settings", "Model status, speed test, sync, dev tool, audit log, theme", "Pass"],
  ["Error paths", "Unknown API route, server exception, invalid dates, empty body", "Pass"],
  ["Responsive", "1280 px and 375 px on every data-heavy screen", "Pass"],
];

const BUGS = [
  ["1", "Downloading the repository produced an app with no interface at all — the server ran, the browser showed a raw JSON error.", "The built frontend was excluded by .gitignore as \"build output\".", "Committed the built bundle; a missing interface now returns an explanatory page, not raw JSON."],
  ["2", "On Windows the app loaded a blank white page with the correct window title.", "Python reads MIME types from the Windows registry, where .js is often mapped to text/plain; browsers strictly MIME-check ES modules and silently refuse them.", "Static files are now served from an explicit content-type table instead of the host registry. Reproduced by poisoning the MIME map, then verified fixed."],
  ["3", "Blank page again after a rebuild, this time with no error at all.", "index.html names content-hashed bundles but was served with no cache headers, so the browser reused an old copy pointing at files that no longer existed.", "index.html is sent no-store; hashed assets cache for a year."],
  ["4", "Live sync created duplicate accounts for anything a statement import had already created.", "Sync matched accounts only by provider key, which statement-created accounts do not have.", "Sync now adopts a matching account by mask and type on first run."],
  ["5", "An account's ingested transactions vanished from the sync summary when only its balance refresh failed.", "One try/except wrapped both operations, so a late failure discarded the earlier success.", "Balance failure degrades the entry instead of failing the account."],
  ["6", "Unknown /api paths returned an HTML page with status 200.", "The single-page-app catch-all route swallowed API paths.", "Unknown API paths return a JSON 404."],
  ["7", "The local model auto-filed cryptic card descriptors (SQ *, TST*) with high confidence — wrong categories entering the ledger silently.", "A small model is overconfident on processor prefixes that hide the real merchant.", "Confidence for those descriptors is capped in code, so they can only be filed by the user's own correction."],
  ["8", "The model stated incorrect dollar totals in its written answers.", "It performed arithmetic instead of quoting the figures the tools had already computed.", "Every figure is precomputed and handed to the model; the interface prints the true total regardless of the prose."],
  ["9", "Account numbers masked with bullet characters became unreadable to the PDF parser.", "The glyph extracts as a placeholder code, which would have broken account matching.", "Masks use ASCII, as real statements do."],
  ["10", "A rendering crash would have shown a blank screen.", "No React error boundary existed.", "An error boundary shows a recovery view; a global handler logs the traceback server-side and returns a message that leaks nothing."],
];

const SECURITY = [
  ["Brute-force sign-in", "Found in this audit", "Nothing limited password guesses against the published demo emails.", "Eight failures per email triggers a five-minute lockout, returning 429 — verified by test."],
  ["Cross-profile data leakage", "Designed against, verified", "One profile's data reaching another would be the worst possible failure in a finance app.", "Every repository method takes a user ID; a structural test fails the build if any method omits it, and an integration test proves profile A sees zero of profile B's rows on every endpoint."],
  ["SQL injection", "Audited — none found", "User input reaches search, filters and category lookups.", "All queries use the SQLAlchemy ORM with bound parameters; no string-built SQL exists in the codebase."],
  ["Exposed secrets", "Audited — none found", "Keys or passwords committed to a public repository.", ".env is git-ignored and only .env.example is committed; the session secret is generated on first run and stored with owner-only permissions; no credentials appear in source."],
  ["Password storage", "In place", "Plaintext or weak hashing.", "Argon2id with a ten-character minimum and a strength meter."],
  ["Session hijacking / CSRF", "In place", "Token theft via JavaScript or cross-site form posts.", "JWT stored in an httpOnly, SameSite=Strict cookie; the token is never readable from JavaScript."],
  ["Path traversal", "In place", "A crafted path escaping the static or upload directory.", "Static paths are resolved and checked against the static root; uploaded filenames are stripped to a safe character set and stored under a per-user directory."],
  ["Denial of service by upload", "Hardened", "A very large file exhausting memory or disk.", "Uploads over 15 MB are rejected with a specific message."],
  ["Information disclosure in errors", "Hardened", "Stack traces or internal paths shown to the user.", "A global handler logs the detail server-side and returns a fixed message — verified by a test that injects an exception carrying a secret string."],
  ["Financial data leaving the machine", "Core design guarantee", "Transactions or balances sent to a third-party model.", "The AI layer verifies its endpoint resolves to a loopback address and refuses to run otherwise; the cloud provider is disabled by default and labelled as off-device; every model call is recorded in an audit table."],
  ["Prompt injection via transaction text", "Mitigated", "Malicious text in a merchant name steering the AI into exposing other data.", "Tools execute with the authenticated user's ID supplied by the server — the model never receives or can set a user ID — and unknown tool names are rejected."],
  ["Network exposure", "In place", "The finance app reachable from the local network.", "The server binds to 127.0.0.1 only."],
];

const ACCESSIBILITY = [
  "Full keyboard operation, including a review queue designed for it (j/k to move, a to accept, Shift+A to accept for every matching merchant)",
  "Visible focus rings on every interactive element, and a skip-to-content link",
  "prefers-reduced-motion respected globally; motion only ever follows a user action",
  "Semantic landmarks and labelled controls; live regions for status and error messages",
  "Per-page document titles, so the browser tab and screen-reader announcement say which screen is open",
  "Colour is never the only signal — status is always carried by text as well",
  "Layout verified free of horizontal overflow at 375 px, with tabular figures kept aligned",
];

/* ---------------------------------------------------------------- report -- */

const doc = new Document({
  numbering: NUMBERING,
  styles: { default: { document: { run: { font: "Calibri", size: 20 } } } },
  sections: [{
    properties: { page: { size: LETTER, margin: { top: 1300, bottom: 1300, left: 1300, right: 1300 } } },
    footers: { default: new Footer({ children: [new Paragraph({
      alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: "Meridian Financial — Testing & Security Report",
                               size: 15, color: "9A9CA1" })] })] }) },
    children: [
      new Paragraph({ spacing: { after: 50 },
        children: [new TextRun({ text: "Meridian Financial", size: 36, bold: true })] }),
      new Paragraph({ spacing: { after: 40 },
        children: [new TextRun({ text: "Testing & Security Report", size: 23, color: "6E7178" })] }),
      new Paragraph({ spacing: { after: 200 },
        children: [new TextRun({ text: "Application #2 · August 2026 · github.com/darrshen97-ui/Meridian",
                                 size: 18, color: "6E7178" })] }),
      rule(),

      h1("1. Testing approach and coverage"),
      p("Every feature was tested three ways: an automated suite that runs on each change, manual clicking of each screen and control in a browser, and adversarial inputs designed to break things. The suite now holds 158 backend tests and 13 frontend tests, all passing. Automated coverage includes the whole pipeline end to end — a full provider sync, importing all 117 sample statements, and reconciling 79 statement periods — so a regression anywhere in the chain fails the build rather than waiting to be noticed."),
      p("Testing was deliberately hostile rather than confirmatory. The mock provider injects a configurable failure rate and periodic rate-limit responses, so retry and back-off code is genuinely exercised; one test drives sync at a 50% failure rate and asserts the ledger still converges without duplicating a single row."),

      h2("Feature test checklist"),
      table(["Feature", "What was tested", "Result"], FEATURES, [2200, 5900, 1260]),

      new Paragraph({ children: [new PageBreak()] }),

      h1("2. Bugs found and fixed"),
      p("Ten defects of substance were found and fixed. Three were found by a user running the packaged application on Windows, which is noted honestly below because it is the most useful lesson in this report: the automated suite could not see them, since all three lived in packaging and browser behaviour rather than in application logic."),
      table(["#", "Symptom", "Cause", "Fix"], BUGS, [400, 2500, 3000, 3460]),

      new Paragraph({ children: [new PageBreak()] }),

      h1("3. Security audit"),
      p("A full audit was run across authentication, data isolation, injection, secret handling, file handling, error disclosure, and the AI data path. One live vulnerability was found and fixed during the audit; the remainder were verified as already controlled, with the specific control named."),
      table(["Area", "Status", "Risk", "Control in place"], SECURITY, [1500, 1300, 2900, 3660]),

      new Paragraph({ children: [new PageBreak()] }),

      h1("4. Accessibility"),
      ...ACCESSIBILITY.map((a) => bullet(a)),

      h1("5. Evidence"),
      ...figure("m9-review.png", "The review queue: low-confidence suggestions are held for a human decision rather than filed silently, and the whole screen is operable from the keyboard."),
      ...figure("m13-375-transactions.png", "The transaction ledger at 375 pixels — verified free of horizontal overflow.", 240),
    ],
  }],
});

/* ------------------------------------------------------------ reflection -- */

const reflection = new Document({
  numbering: NUMBERING,
  styles: { default: { document: { run: { font: "Calibri", size: 21 } } } },
  sections: [{
    properties: { page: { size: LETTER, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    children: [
      new Paragraph({ spacing: { after: 50 },
        children: [new TextRun({ text: "Reflection", size: 32, bold: true })] }),
      new Paragraph({ spacing: { after: 200 },
        children: [new TextRun({ text: "Meridian Financial · Testing, security and what the second build taught me",
                                 size: 19, color: "6E7178" })] }),
      rule(),

      h2("The most critical bug"),
      p("The worst bug was invisible to every test I had. Downloading the finished app and running it gave a blank white page: the server started perfectly, the console reported both profiles seeded, the browser showed nothing. It was three faults in a row — the built interface was excluded from version control as disposable build output; Windows reports JavaScript as plain text through its registry, so browsers silently refuse to run it; and the page was cached, leaving the browser asking for files a rebuild had renamed. Each produced an identical symptom, so each fix looked like a failure. What made it critical was its location: all three lived in packaging and browser behaviour, the one area my 158 tests never touched, because tests run code — they do not download it, install it, or open it on someone else's operating system."),

      h2("The most important security issue"),
      p("The audit found nothing limiting password guessing. That is routine elsewhere, but the demo emails are published in the README, so an attacker would already hold half of every credential. I added a five-minute lockout after eight failures, with a test proving even the correct password is refused while locked. I am most confident in the isolation guarantee, because it is structural rather than careful: a test inspects every database method and fails the build if one can be called without a user's identity."),

      h2("How AI helped, and how this differed from my first app"),
      p("AI was strongest where work was broad but well specified — a year of realistic statements in three layouts, a parser for each, and the suites checking them. It was least reliable where it seemed most confident: it wrote real defects, and its own tests caught them. It also misstated dollar totals until I stopped letting it calculate and made it quote figures the code had computed. Judgment in the model, guarantees in code."),
      p("My first app simulated its core feature and lost state on reload, so testing meant clicking and hoping. Here tests came with each feature and usually found problems before I opened the screen. The real lesson came from what they missed: a green run says the code is correct on my machine, not that the product works on someone else's — and that gap is where all three of my worst bugs lived."),
    ],
  }],
});

for (const [name, d] of [["Meridian_Testing_Security_Report.docx", doc],
                         ["Meridian_Reflection.docx", reflection]]) {
  fs.writeFileSync(path.join(OUT, name), await Packer.toBuffer(d));
  console.log(`wrote docs/deliverables/${name}`);
}
