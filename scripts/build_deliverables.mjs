// Build the Word deliverables for submission (screenshots can be pasted in).
//   node scripts/build_deliverables.mjs
// Output: docs/deliverables/*.docx
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, LevelFormat,
  Packer, PageBreak, PageOrientation, Paragraph, ShadingType, Table, TableCell,
  TableRow, TextRun, WidthType,
} from "docx";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "docs", "deliverables");
fs.mkdirSync(OUT, { recursive: true });

const LETTER = { width: 12240, height: 15840 };
const CONTENT = 9360;          // portrait content width (DXA)
const CONTENT_LS = 12960;      // landscape content width

const NUMBERING = {
  config: [{
    reference: "bullets",
    levels: [{
      level: 0, format: LevelFormat.BULLET, text: "•",
      alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 360, hanging: 240 } } },
    }],
  }],
};

const p = (text, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 140, line: 276 },
  alignment: opts.alignment,
  children: [new TextRun({ text, size: opts.size ?? 21, bold: opts.bold,
                           italics: opts.italics, color: opts.color })],
});

// Rich paragraph: array of [text, {bold?, italics?}] pairs.
const rich = (parts, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 140, line: 276 },
  children: parts.map(([text, o = {}]) =>
    new TextRun({ text, size: 21, bold: o.b, italics: o.i, color: o.color,
                  font: o.mono ? "Consolas" : undefined })),
});

const bullet = (parts) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  spacing: { after: 90, line: 276 },
  children: (Array.isArray(parts) ? parts : [[parts]]).map(([text, o = {}]) =>
    new TextRun({ text, size: 21, bold: o.b, italics: o.i,
                  font: o.mono ? "Consolas" : undefined })),
});

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 320, after: 160 },
  children: [new TextRun({ text, size: 26, bold: true, color: "16181D" })],
});

const rule = () => new Paragraph({
  spacing: { after: 200 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "C9C9C6" } },
  children: [new TextRun({ text: "", size: 2 })],
});

function cell(text, { width, bold, shade, size = 18, align } = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: shade ? { type: ShadingType.CLEAR, fill: shade, color: "auto" } : undefined,
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
    children: [new Paragraph({
      alignment: align,
      spacing: { after: 0, line: 250 },
      children: [new TextRun({ text, size, bold })],
    })],
  });
}

function table(headers, rows, widths) {
  return new Table({
    columnWidths: widths,
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) =>
          cell(h, { width: widths[i], bold: true, shade: "F0F0EE" })),
      }),
      ...rows.map((r) => new TableRow({
        children: r.map((c, i) => cell(String(c), { width: widths[i] })),
      })),
    ],
  });
}

// A visible "paste your screenshot here" box.
function screenshotBox(caption, instructions) {
  const inner = [
    new Paragraph({
      spacing: { before: 900, after: 120 },
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "[ Paste screenshot here ]", size: 22,
                               bold: true, color: "9A9CA1" })],
    }),
    new Paragraph({
      spacing: { after: 900 },
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: instructions, size: 18, color: "9A9CA1",
                               italics: true })],
    }),
  ];
  return [
    new Table({
      columnWidths: [CONTENT],
      width: { size: CONTENT, type: WidthType.DXA },
      rows: [new TableRow({
        children: [new TableCell({
          width: { size: CONTENT, type: WidthType.DXA },
          borders: {
            top: { style: BorderStyle.DASHED, size: 6, color: "C9C9C6" },
            bottom: { style: BorderStyle.DASHED, size: 6, color: "C9C9C6" },
            left: { style: BorderStyle.DASHED, size: 6, color: "C9C9C6" },
            right: { style: BorderStyle.DASHED, size: 6, color: "C9C9C6" },
          },
          children: inner,
        })],
      })],
    }),
    new Paragraph({
      spacing: { before: 100, after: 300 },
      children: [new TextRun({ text: caption, size: 18, italics: true,
                               color: "6E7178" })],
    }),
  ];
}

const footer = (label) => new Footer({
  children: [new Paragraph({
    alignment: AlignmentType.RIGHT,
    children: [new TextRun({ text: label, size: 16, color: "9A9CA1" })],
  })],
});

/* ---------------------------------------------------------------- report -- */

const TIME_ROWS = [
  ["0", "Brief, build plan, project setup", "~1 h"],
  ["1–3", "Scaffold, data model + migrations, auth & profile isolation", "~2.25 h"],
  ["4", "Deterministic mock dataset (117 documents, 13 planted events)", "~2 h"],
  ["5", "Statement parsers (PDF/CSV/OFX) + ingestion pipeline", "~1.5 h"],
  ["6", "Provider layer, incremental sync, live updates (SSE)", "~1.5 h"],
  ["7–8", "Design system, shell, and the four data screens", "~3 h"],
  ["9", "Local model, two-pass categorization, learning loop", "~2.5 h"],
  ["10", "Reconciliation engine + narration", "~1.5 h"],
  ["11", "AI spending coach with tool use", "~2 h"],
  ["12", "Budgets and what-if simulator", "~1.5 h"],
  ["13–15", "Hardening, packaging & launcher, deliverables", "~3.25 h"],
  ["", "Total", "~22 h"],
];

const report = new Document({
  numbering: NUMBERING,
  styles: { default: { document: { run: { font: "Calibri", size: 21 } } } },
  sections: [{
    properties: { page: { size: LETTER, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: footer("Meridian Financial — Development Report") },
    children: [
      new Paragraph({
        spacing: { after: 60 },
        children: [new TextRun({ text: "Meridian Financial", size: 40, bold: true })],
      }),
      new Paragraph({
        spacing: { after: 40 },
        children: [new TextRun({ text: "Development Report — Application #2", size: 24,
                                 color: "6E7178" })],
      }),
      new Paragraph({
        spacing: { after: 60 },
        children: [new TextRun({ text: "Workshop 5.3 · Iteration 1 · August 9–10, 2026",
                                 size: 20, color: "6E7178" })],
      }),
      new Paragraph({
        spacing: { after: 240 },
        children: [new TextRun({ text: "Repository: github.com/darrshen97-ui/Meridian",
                                 size: 20, color: "6E7178" })],
      }),
      rule(),

      h1("1. What was built"),
      p("Meridian Financial is an AI-powered personal finance platform: it aggregates accounts across banks, credit cards, payment apps, and crypto exchanges, reconciles live account data against uploaded monthly statements, and answers plain-language questions about actual spending. The AI model runs entirely on the local machine — no transaction, balance, or merchant name leaves it."),
      p("All five product features are functional end to end, with no stubbed interiors: dashboard with spending power; statement ingestion for PDF, CSV, and OFX with preview-before-import; live sync over Server-Sent Events; two-pass categorization with a human review queue; reconciliation with plain-language narration; a tool-using spending coach; and a budget simulator. The application ships as a zip with a double-click launcher and is backed by 154 backend tests and 13 frontend tests."),

      h1("2. AI assistant and prompts used"),
      p("The application was built with Claude Code (Anthropic). The workflow differed deliberately from Application #1: rather than prompting screen by screen, a complete build brief was written first — scope, data model, design system, a fifteen-milestone build order, and a set of non-negotiable requirements — and the assistant was required to produce a written build plan before any code was written. It then built one milestone per prompt, stopping at each checkpoint to report evidence."),
      p("Fifteen substantive prompts produced the entire application. Each is logged with its outcome in the accompanying Prompt Log deliverable. Every judgment call the brief did not specify was recorded with its reasoning in a decisions log that now runs to 23 entries."),

      h1("3. The most helpful prompts"),
      p("The single most valuable prompt was the build brief itself. Front-loading the specification meant that nearly every subsequent instruction — literally the word “build” — worked close to first try. Three elements inside it paid off repeatedly:"),
      bullet([["“Produce a build plan before writing any code.” ", { b: true }],
              ["This surfaced six internal inconsistencies in my own specification — including a schema with no account type for one of the demo profiles' brokerage account — before they could become bugs."]]),
      bullet([["The planted-events dataset specification. ", { b: true }],
              ["Thirteen known anomalies generated into the mock data gave every later feature a testable target. The reconciliation checkpoint imports all 117 sample documents, reconciles 79 statement periods, and asserts that the only actionable findings are the three planted divergences — zero false positives."]]),
      bullet([["“Test every prompt against the actual model, not against intuition.” ", { b: true }],
              ["The assistant installed a real local model server inside its own development container and iterated the prompts against it, which exposed genuine failures that no mocked model would have revealed."]]),

      h1("4. Key features and how AI helped"),
      p("The assistant wrote effectively all of the application code and all of the tests. The more interesting result is that the tests repeatedly caught the assistant's own defects: synchronization duplicating accounts that a statement import had already created, and a balance-refresh failure silently discarding an account's ingested-row count. Both were found by the milestone checkpoint tests rather than by inspection — which is precisely why tests were written alongside features instead of afterwards."),
      p("AI contributed most where the work was broad but well-specified: generating a year of realistic bank statements in three different layouts, writing one parser per layout, and producing the test suites that cross-check every parsed document against the canonical ledger."),

      h1("5. Challenges encountered, and how they were solved"),
      bullet([["Small local models are confidently wrong. ", { b: true }],
              ["The smaller model auto-applied incorrect categories to cryptic payment-processor descriptors, and both models misreported precomputed dollar totals when writing prose. The pattern that resolved every instance was the same: judgment in the model, guarantees in code. Cryptic descriptors receive a deterministic confidence cap; tool-computed totals are printed by the interface regardless of the model's wording; and the model is handed every derived figure so that it has nothing left to calculate."]]),
      bullet([["PDF text extraction silently corrupted account masks. ", { b: true }],
              ["The typographic bullet characters used to mask account numbers extract as placeholder codes, which would have quietly broken the parsers' account matching. This was caught by reading the generated PDFs back programmatically and fixed by using ASCII masking, as real statements do."]]),
      bullet([["Cross-format transaction identity. ", { b: true }],
              ["A statement row, an OFX row, and a live provider row describing the same purchase had to collapse into a single record — without ever collapsing two genuinely identical purchases. One shared two-layer matcher serves both import de-duplication and reconciliation, so the three planted date-shifted transactions match silently while the planted duplicate charge is still flagged."]]),
      bullet([["A packaging defect found by the user. ", { b: true }],
              ["The built web interface was excluded from version control, so downloading the repository produced a copy that started correctly but served no interface. The build artifact is now committed, and a missing interface produces an explanatory page rather than a bare error."]]),

      new Paragraph({ children: [new PageBreak()] }),

      h1("6. The local-model decision"),
      p("The architecture submitted for Workshop 5.2 specified the Claude API. The application as built defaults to a fully local model served by Ollama. This is a deliberate architectural evolution rather than a discrepancy, and it is driven by the sensitivity of the data the application handles."),
      p("Under the built design, no transaction, balance, or merchant name can leave the machine: the AI layer verifies that its configured endpoint resolves to a loopback address and refuses to run otherwise, and every model call is recorded in an audit table that the Settings screen displays. The cloud provider survives behind the same provider interface — disabled by default and clearly labelled as sending data off the device — so the submitted architecture is retained while the product default is private."),
      p("The choice has a measurable cost, and the application is designed around it rather than pretending otherwise: a local model of this size sends more transactions to the review queue and needs deterministic guardrails around numbers. The review queue was therefore designed as a feature in its own right — and as the engine of the learning loop, since every correction it captures becomes a rule that the model never sees again."),

      h1("7. Comparison: Application #1 (GridPilot) versus Application #2 (Meridian)"),
      p("GridPilot was a frontend-only prototype whose core feature was simulated and whose state evaporated on reload. Meridian inverted each of those weaknesses: a real backend with database migrations from the second milestone, strict layering between routers, services, and repositories, all five interface states on every view, configuration through environment variables from the first milestone, and tests written beside every feature."),
      p("Counter-intuitively, the second application was faster per feature despite being far larger. The up-front brief eliminated the re-prompting cycles that dominated the first build, and the deterministic sample dataset meant correctness was checkable by machine rather than by eye. The clearest difference in experience: with GridPilot, problems were discovered by clicking around; with Meridian, the test suite usually found them before the screen was ever opened."),

      h1("8. Time spent"),
      p("Approximately 22 hours of assistant session time across two days."),
      table(["Milestone", "Work", "Time"], TIME_ROWS, [1200, 6560, 1600]),
      new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: "" })] }),

      new Paragraph({ children: [new PageBreak()] }),

      h1("9. Required screenshots"),
      p("Both screenshots below must show the system date and time. On Windows, click the taskbar clock so the date flyout is open, then capture the full screen with Windows + PrtScn (not a region snip, so the clock is included)."),

      new Paragraph({
        spacing: { before: 160, after: 100 },
        children: [new TextRun({ text: "Screenshot 1 — the completed project code in the IDE",
                                 size: 22, bold: true })],
      }),
      ...screenshotBox(
        "Figure 1. The Meridian project open in the IDE, with the system date and time visible.",
        "Have on screen: the meridian project open with the file explorer visible (app, frontend, alembic, scripts, sample_data, tests, docs), a substantial file open such as app/services/reconciliation.py, and the taskbar clock flyout showing today's date."),

      new Paragraph({
        spacing: { before: 160, after: 100 },
        children: [new TextRun({ text: "Screenshot 2 — the application running on localhost",
                                 size: 22, bold: true })],
      }),
      ...screenshotBox(
        "Figure 2. Meridian running at http://127.0.0.1:8787, with the system date and time visible.",
        "Have on screen: the browser at http://127.0.0.1:8787 with the URL bar visible, signed in as Jordan Reyes, on the Dashboard so spending power, accounts, and recent activity all show real data — and the taskbar clock flyout showing today's date."),
    ],
  }],
});

/* ------------------------------------------------------------ prompt log -- */

function parseMarkdownTable(file) {
  const lines = fs.readFileSync(file, "utf8").split("\n");
  const rows = lines.filter((l) => l.startsWith("| ") && !l.startsWith("| #")
                                   && !l.startsWith("|---"));
  return rows.map((line) => line.slice(1, line.lastIndexOf("|"))
    .split(" | ").map((c) => c.trim().replace(/\*\*/g, "").replace(/`/g, "")));
}

const promptRows = parseMarkdownTable(path.join(ROOT, "docs", "PROMPT_LOG.md"));

const promptLog = new Document({
  styles: { default: { document: { run: { font: "Calibri", size: 21 } } } },
  sections: [{
    properties: {
      page: {
        size: { ...LETTER, orientation: PageOrientation.LANDSCAPE },
        margin: { top: 1080, bottom: 1080, left: 1440, right: 1440 },
      },
    },
    footers: { default: footer("Meridian Financial — Prompt Log") },
    children: [
      new Paragraph({
        spacing: { after: 60 },
        children: [new TextRun({ text: "Meridian Financial — Prompt Log", size: 32,
                                 bold: true })],
      }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({
          text: "Every prompt given to Claude Code during the build, with what it produced and whether it worked first try. Workshop 5.3 · August 9–10, 2026.",
          size: 20, color: "6E7178" })],
      }),
      table(["#", "Date", "Prompt (condensed)", "What it produced", "First try?"],
            promptRows, [500, 900, 2700, 7060, 1800]),
    ],
  }],
});

/* --------------------------------------------------------------- output --- */

const targets = [
  ["Meridian_Development_Report.docx", report],
  ["Meridian_Prompt_Log.docx", promptLog],
];
for (const [name, doc] of targets) {
  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(path.join(OUT, name), buffer);
  console.log(`wrote docs/deliverables/${name}`);
}
