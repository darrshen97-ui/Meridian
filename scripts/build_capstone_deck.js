// Capstone presentation: GridPilot AI + Meridian Financial across Workshops 1-6.
// node deck.js  ->  AI_Capstone_Presentation.pptx
const PptxGenJS = require("pptxgenjs");
const path = require("path");

const GP_SHOTS = "/home/user/GridPilot-AI/docs/screenshots";
const MF_SHOTS = "/workspace/meridian/docs/screenshots/dev";

const pres = new PptxGenJS();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.author = "AIML-515 Capstone";
pres.title = "GridPilot AI and Meridian Financial";

// ---------------------------------------------------------------- palette
const INK = "141A24";        // dark ground
const INK2 = "1F2836";       // dark card
const PAPER = "FFFFFF";
const WASH = "F3F5F8";       // light card
const BODY = "36404F";
const MUTED = "737F91";
const RULE = "DCE1E8";
const GP = "C8791B";         // GridPilot amber (utility / energy)
const GP_WASH = "FBF1E2";
const MF = "1B6B52";         // Meridian green (finance)
const MF_WASH = "E3F0EA";

const HEAD = "Cambria";
const TEXT = "Calibri";
const W = 13.333, H = 7.5, M = 0.72;

// ---------------------------------------------------------------- helpers
function shadow() {
  return { type: "outer", angle: 90, blur: 12, offset: 2, color: "8C97A8", opacity: 0.18 };
}

function light(title, kicker) {
  const s = pres.addSlide();
  s.background = { color: PAPER };
  if (kicker) {
    s.addText(kicker.toUpperCase(), {
      x: M, y: 0.42, w: 8, h: 0.26, fontSize: 11, bold: true, charSpacing: 1.6,
      color: MUTED, fontFace: TEXT, margin: 0,
    });
  }
  s.addText(title, {
    x: M, y: kicker ? 0.68 : 0.5, w: W - 2 * M, h: 0.7, fontSize: 32, bold: true,
    color: INK, fontFace: HEAD, margin: 0, valign: "top",
  });
  return s;
}

function dark(title, kicker) {
  const s = pres.addSlide();
  s.background = { color: INK };
  if (kicker) {
    s.addText(kicker.toUpperCase(), {
      x: M, y: 0.42, w: 8, h: 0.26, fontSize: 11, bold: true, charSpacing: 1.6,
      color: "9AA6B8", fontFace: TEXT, margin: 0,
    });
  }
  s.addText(title, {
    x: M, y: kicker ? 0.68 : 0.5, w: W - 2 * M, h: 0.8, fontSize: 32, bold: true,
    color: PAPER, fontFace: HEAD, margin: 0, valign: "top",
  });
  return s;
}

// The repeated motif: a small app badge, in that app's colour, top-right.
function badge(s, which) {
  const isGP = which === "gp";
  s.addShape(pres.ShapeType.roundRect, {
    x: W - M - 2.35, y: 0.42, w: 2.35, h: 0.36, rectRadius: 0.18,
    fill: { color: isGP ? GP_WASH : MF_WASH }, line: { color: isGP ? GP : MF, width: 0.75 },
  });
  s.addText(isGP ? "APP 1  ·  GRIDPILOT AI" : "APP 2  ·  MERIDIAN", {
    x: W - M - 2.35, y: 0.42, w: 2.35, h: 0.36, fontSize: 10, bold: true, charSpacing: 0.6,
    color: isGP ? GP : MF, fontFace: TEXT, align: "center", valign: "middle", margin: 0,
  });
}

function card(s, x, y, w, h, fill) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.09,
    fill: { color: fill || WASH }, line: { color: RULE, width: 0.75 }, shadow: shadow(),
  });
}

// Big number + label, used everywhere metrics appear.
function stat(s, x, y, w, value, label, color, sub) {
  s.addText(value, {
    x, y, w, h: 0.78, fontSize: 36, bold: true, color: color || INK,
    fontFace: HEAD, margin: 0, valign: "middle",
  });
  s.addText(label, {
    x, y: y + 0.68, w, h: 0.3, fontSize: 12, bold: true, color: BODY,
    fontFace: TEXT, margin: 0,
  });
  if (sub) {
    s.addText(sub, {
      x, y: y + 0.95, w, h: 0.5, fontSize: 10.5, color: MUTED, fontFace: TEXT, margin: 0,
    });
  }
}

function body(s, text, x, y, w, h, opts = {}) {
  s.addText(text, {
    x, y, w, h, fontSize: opts.size || 13.5, color: opts.color || BODY, fontFace: TEXT,
    margin: 0, lineSpacing: opts.lineSpacing || 19, valign: opts.valign || "top",
    bold: opts.bold, align: opts.align,
  });
}

function heading(s, text, x, y, w, color) {
  s.addText(text, {
    x, y, w, h: 0.3, fontSize: 14.5, bold: true, color: color || INK,
    fontFace: TEXT, margin: 0,
  });
}

// Numbered step circle, for flows and timelines.
function node(s, x, y, d, n, color, textColor) {
  s.addShape(pres.ShapeType.ellipse, {
    x, y, w: d, h: d, fill: { color }, line: { color, width: 0 },
  });
  s.addText(String(n), {
    x, y, w: d, h: d, fontSize: 13, bold: true, color: textColor || PAPER,
    fontFace: TEXT, align: "center", valign: "middle", margin: 0,
  });
}

function arrow(s, x, y, w, color) {
  s.addShape(pres.ShapeType.rightArrow, {
    x, y, w, h: 0.16, fill: { color: color || RULE }, line: { color: color || RULE, width: 0 },
  });
}

function bullets(s, items, x, y, w, h, color, size) {
  s.addText(
    items.map((t, i) => ({
      text: t, options: { bullet: true, breakLine: i !== items.length - 1 },
    })),
    { x, y, w, h, fontSize: size || 13, color: color || BODY, fontFace: TEXT, margin: 0,
      lineSpacing: size ? 16 : 18, paraSpaceAfter: 6 }
  );
}

function footnote(s, text, colour) {
  s.addText(text, {
    x: M, y: H - 0.62, w: W - 2 * M, h: 0.3, fontSize: 10, italic: true,
    color: colour || MUTED, fontFace: TEXT, margin: 0,
  });
}

const GP_URL = "gridpilot-ai-fb150.web.app";
const MF_URL = "meridian-792468836580.us-central1.run.app";

// ============================================================ 1. TITLE
{
  const s = dark("");
  s.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: W, h: H, fill: { color: INK } });
  s.addText("Two problems, two applications,", {
    x: M, y: 1.35, w: 11.5, h: 0.75, fontSize: 40, color: "9AA6B8", fontFace: HEAD, margin: 0,
  });
  s.addText("one lifecycle run twice.", {
    x: M, y: 2.05, w: 11.5, h: 0.85, fontSize: 44, bold: true, color: PAPER, fontFace: HEAD, margin: 0,
  });
  s.addText("AIML-515 Capstone  ·  Workshops 1–6", {
    x: M, y: 3.05, w: 8, h: 0.35, fontSize: 14, color: "9AA6B8", fontFace: TEXT, margin: 0,
  });

  // Two app blocks, each in its own colour — the motif introduced.
  const bw = 5.6, by = 4.0;
  [["gp", "GridPilot AI", "Source-cited answers for utility engineers", GP, GP_URL],
   ["mf", "Meridian Financial", "Reconciles bank statements against live account feeds", MF, MF_URL],
  ].forEach(([, name, tag, colour, url], i) => {
    const x = M + i * (bw + 0.5);
    s.addShape(pres.ShapeType.roundRect, {
      x, y: by, w: bw, h: 1.85, rectRadius: 0.1,
      fill: { color: INK2 }, line: { color: colour, width: 1.25 },
    });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.42, y: by + 0.42, w: 0.2, h: 0.2, fill: { color: colour } });
    s.addText(name, {
      x: x + 0.75, y: by + 0.3, w: bw - 1.1, h: 0.42, fontSize: 20, bold: true,
      color: PAPER, fontFace: HEAD, margin: 0, valign: "middle",
    });
    s.addText(tag, {
      x: x + 0.42, y: by + 0.78, w: bw - 0.84, h: 0.5, fontSize: 12, color: "9AA6B8",
      fontFace: TEXT, margin: 0, lineSpacing: 16,
    });
    s.addText(url, {
      x: x + 0.42, y: by + 1.33, w: bw - 0.84, h: 0.32, fontSize: 11.5, bold: true,
      color: colour, fontFace: TEXT, margin: 0,
    });
  });
  s.addText("Presented by  [ your name ]", {
    x: M, y: 6.35, w: 8, h: 0.3, fontSize: 12, color: "6E7A8C", fontFace: TEXT, margin: 0,
  });
  s.addNotes(
    "This capstone covers two complete applications, each taken through all six phases of the AI/Tech project lifecycle.\n\n" +
    "GridPilot AI is a knowledge assistant for electric utility engineers. Meridian Financial is a personal finance ledger that reconciles statements against live account feeds.\n\n" +
    "Both are deployed and publicly reachable right now, and both URLs are on this slide. Everything I show today can be opened and checked."
  );
}

// ============================================================ 2. EXEC SUMMARY
{
  const s = light("What was built, and what it does", "Executive summary");
  const cw = 5.85, cy = 1.55, ch = 4.55;
  [[GP, GP_WASH, "GridPilot AI",
    "Utility engineers answer technical questions by searching scattered PDF manuals, standards and procedure binders.",
    "A role-aware assistant that answers in plain language, cites the exact source passage, and declines when no source is confident enough.",
    [["27", "source files"], ["3", "user roles"], ["0", "invented answers"]]],
   [MF, MF_WASH, "Meridian Financial",
    "Money sits across many institutions, and each institution's statement disagrees with its own live feed more often than people think.",
    "Imports statements in five formats, merges them with the account feed without duplicating, and reports what does not reconcile.",
    [["3,350", "transactions"], ["153", "documents"], ["205", "backend tests"]]],
  ].forEach(([colour, wash, name, problem, solution, stats], i) => {
    const x = M + i * (cw + 0.55);
    card(s, x, cy, cw, ch, PAPER);
    s.addShape(pres.ShapeType.roundRect, {
      x: x + 0.35, y: cy + 0.32, w: 2.1, h: 0.33, rectRadius: 0.16, fill: { color: wash },
      line: { color: colour, width: 0.75 },
    });
    s.addText(`APP ${i + 1}`, {
      x: x + 0.35, y: cy + 0.32, w: 2.1, h: 0.33, fontSize: 10, bold: true, color: colour,
      fontFace: TEXT, align: "center", valign: "middle", margin: 0, charSpacing: 0.8,
    });
    s.addText(name, {
      x: x + 0.35, y: cy + 0.78, w: cw - 0.7, h: 0.45, fontSize: 22, bold: true,
      color: INK, fontFace: HEAD, margin: 0,
    });
    heading(s, "The problem", x + 0.35, cy + 1.32, cw - 0.7, colour);
    body(s, problem, x + 0.35, cy + 1.62, cw - 0.7, 0.85, { size: 12.5, lineSpacing: 17 });
    heading(s, "The solution", x + 0.35, cy + 2.5, cw - 0.7, colour);
    body(s, solution, x + 0.35, cy + 2.8, cw - 0.7, 0.9, { size: 12.5, lineSpacing: 17 });
    stats.forEach(([v, l], j) => {
      const sx = x + 0.35 + j * ((cw - 0.7) / 3);
      s.addText(v, {
        x: sx, y: cy + 3.72, w: (cw - 0.7) / 3, h: 0.45, fontSize: 24, bold: true,
        color: colour, fontFace: HEAD, margin: 0,
      });
      s.addText(l, {
        x: sx, y: cy + 4.14, w: (cw - 0.7) / 3, h: 0.3, fontSize: 10.5, color: MUTED,
        fontFace: TEXT, margin: 0,
      });
    });
  });
  s.addNotes(
    "Both applications solve a problem where the information already exists but is too scattered or too tedious to check by hand.\n\n" +
    "GridPilot is a front-end prototype with simulated retrieval, and it says so plainly. Meridian is a full-stack application with a real backend, database and parsers.\n\n" +
    "The 'zero invented answers' figure is a design property, not a marketing claim: when no source scores high enough, GridPilot returns a decline card instead of an answer."
  );
}

// ============================================================ 3. LIFECYCLE
{
  const s = dark("The same six phases, run twice", "Workshops 1–6");
  const phases = ["Problem framing", "Technical solution", "Design & prototype",
                  "Testing & evaluation", "Deployment", "Feedback & iteration"];
  const x0 = M, cw = (W - 2 * M) / 6;
  phases.forEach((p, i) => {
    const x = x0 + i * cw;
    node(s, x + cw / 2 - 0.19, 1.55, 0.38, i + 1, i < 3 ? "3C4A5E" : "56657C");
    s.addText(p, {
      x: x + 0.05, y: 2.05, w: cw - 0.1, h: 0.6, fontSize: 11.5, bold: true, color: PAPER,
      fontFace: TEXT, align: "center", margin: 0, lineSpacing: 14,
    });
    if (i < 5) {
      s.addShape(pres.ShapeType.line, {
        x: x + cw / 2 + 0.24, y: 1.74, w: cw - 0.48, h: 0,
        line: { color: "3C4A5E", width: 1.5 },
      });
    }
  });
  const rows = [
    [GP, "GridPilot AI",
     ["Field crews and analysts hunt through binders", "Retrieval + citations, no invented answers",
      "Claude Artifacts, then Vite + React in an IDE", "Playwright at 3 viewports, security pass",
      "Firebase Hosting, CI/CD from GitHub", "Mobile layout rebuilt after testing"]],
    [MF, "Meridian Financial",
     ["Statements and account feeds silently disagree", "Local model only, deterministic matching",
      "Written brief first, then 15 milestones", "205 backend tests, real-model runs",
      "Cloud Run container, scale to zero", "Demo profiles seeded end to end"]],
  ];
  rows.forEach(([colour, name, cells], r) => {
    const y = 2.95 + r * 1.95;
    s.addText(name, {
      x: M, y: y - 0.35, w: 4, h: 0.3, fontSize: 13, bold: true, color: colour, fontFace: TEXT, margin: 0,
    });
    cells.forEach((c, i) => {
      const x = x0 + i * cw;
      s.addShape(pres.ShapeType.roundRect, {
        x: x + 0.05, y, w: cw - 0.14, h: 1.4, rectRadius: 0.08,
        fill: { color: INK2 }, line: { color: "2E3A4B", width: 0.75 },
      });
      s.addText(c, {
        x: x + 0.18, y: y + 0.12, w: cw - 0.4, h: 1.16, fontSize: 10.5, color: "C6CFDC",
        fontFace: TEXT, margin: 0, lineSpacing: 13.5, valign: "top",
      });
    });
  });
  s.addNotes(
    "This is the map for the rest of the deck. Six phases across the top, one row per application.\n\n" +
    "The second run was faster not because the work was smaller, but because decisions that were made late the first time were made first the second time. The clearest example is deployment: GridPilot was built and then deployed; Meridian was designed around its deployment target from the first migration.\n\n" +
    "Each column becomes a slide or two in the sections that follow."
  );
}

// ============================================================ 4. APP1 PROBLEM
{
  const s = light("Answers exist. Finding them is the job.", "App 1 · Phase 1 · Problem framing");
  badge(s, "gp");
  card(s, M, 1.6, 6.1, 2.35, WASH);
  s.addText("“What is the maintenance interval for an unmonitored microprocessor relay?”", {
    x: M + 0.35, y: 1.85, w: 5.4, h: 0.85, fontSize: 16, italic: true, color: INK,
    fontFace: HEAD, margin: 0, lineSpacing: 21,
  });
  body(s, "The answer is one line in PRC-005-6, Table 1-1. Finding it means knowing the standard " +
       "exists, having the current revision, and reading to the right table.",
       M + 0.35, 2.8, 5.4, 0.95, { size: 12.5, lineSpacing: 17 });

  heading(s, "Who this hurts", M, 4.25, 6.1, GP);
  const who = [["Protection engineers", "Relay settings, maintenance standards, vendor manuals"],
               ["Compliance analysts", "NERC CIP, TOP and BAL obligations across revisions"],
               ["Field crews", "Switching procedures, grounding order, on a tablet, in gloves"]];
  who.forEach(([role, what], i) => {
    const y = 4.62 + i * 0.62;
    s.addShape(pres.ShapeType.ellipse, { x: M + 0.02, y: y + 0.09, w: 0.16, h: 0.16, fill: { color: GP } });
    s.addText(role, { x: M + 0.3, y, w: 1.85, h: 0.28, fontSize: 12.5, bold: true, color: INK, fontFace: TEXT, margin: 0 });
    s.addText(what, { x: M + 2.2, y, w: 3.9, h: 0.5, fontSize: 11.5, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 14 });
  });

  card(s, 7.2, 1.6, W - M - 7.2, 4.75, PAPER);
  heading(s, "What the assistant has to do differently", 7.55, 1.9, 4.9, GP);
  const musts = [
    ["Cite the passage", "Not a document name. The exact paragraph, shown beside the answer."],
    ["Decline when unsure", "A confident wrong answer about a relay interval is worse than no answer."],
    ["Respect the role", "A field crew running a switching order should not be handed a maintenance standard."],
    ["Work on a tablet", "In the field, one column, large targets, gloved hands."],
  ];
  musts.forEach(([t, d], i) => {
    const y = 2.4 + i * 1.0;
    node(s, 7.55, y, 0.32, i + 1, GP);
    s.addText(t, { x: 8.05, y: y - 0.02, w: 4.4, h: 0.3, fontSize: 13, bold: true, color: INK, fontFace: TEXT, margin: 0 });
    s.addText(d, { x: 8.05, y: y + 0.28, w: 4.4, h: 0.6, fontSize: 11.5, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 14 });
  });
  s.addNotes(
    "The problem is not that utility engineering knowledge is missing. It is published, often mandated, and sitting in PDFs.\n\n" +
    "The problem is retrieval under time pressure, and the cost of a wrong answer is regulatory as well as physical. That shaped four requirements that most chat assistants do not meet: cite the passage, decline when unsure, scope by role, and work on a tablet in the field.\n\n" +
    "Those four requirements drove every design decision that follows."
  );
}

// ============================================================ 5. APP1 STACK
{
  const s = light("Choosing the stack, and what it cost", "App 1 · Phase 2 · Technical solution");
  badge(s, "gp");
  const cols = [
    ["React 18 + Vite", "Component reuse and a fast dev loop. Vite's production build is what Firebase serves.", "Chosen"],
    ["In-memory retrieval", "Keyword scoring in src/lib/retrieval.js stands in for a hybrid vector search.", "Simulated"],
    ["No backend", "Nothing to secure, nothing to pay for, nothing between the demo and the reviewer.", "Deliberate"],
    ["lucide-react only", "Three dependencies total, so the supply-chain surface stays small.", "Chosen"],
  ];
  cols.forEach(([t, d, tag], i) => {
    const x = M + i * 3.11;
    card(s, x, 1.6, 2.9, 2.3, WASH);
    s.addShape(pres.ShapeType.roundRect, {
      x: x + 0.28, y: 1.85, w: 1.15, h: 0.3, rectRadius: 0.15,
      fill: { color: tag === "Simulated" ? "F5E4C8" : GP_WASH }, line: { color: GP, width: 0.6 },
    });
    s.addText(tag.toUpperCase(), {
      x: x + 0.28, y: 1.85, w: 1.15, h: 0.3, fontSize: 8.5, bold: true, color: GP,
      fontFace: TEXT, align: "center", valign: "middle", margin: 0, charSpacing: 0.5,
    });
    s.addText(t, { x: x + 0.28, y: 2.28, w: 2.35, h: 0.55, fontSize: 15, bold: true, color: INK, fontFace: HEAD, margin: 0, lineSpacing: 18 });
    s.addText(d, { x: x + 0.28, y: 2.88, w: 2.35, h: 0.9, fontSize: 11.5, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 14.5 });
  });

  card(s, M, 4.2, W - 2 * M, 2.1, "FBF7F0");
  heading(s, "The honest trade, stated in the README rather than discovered by a reviewer", M + 0.4, 4.5, 11, GP);
  body(s, "Retrieval is keyword scoring over a seeded document set. There is no vector database and no language model in the " +
       "deployed build. That is written at the top of the repository, and the production gaps are listed with named " +
       "technologies: a managed vector store and embeddings, a hosted model for synthesis with a guardrail against uncited " +
       "claims, an ingestion pipeline, Okta SSO, and CIP-appropriate hosting with audit logging.",
       M + 0.4, 4.88, 11.4, 1.2, { size: 13, lineSpacing: 19 });
  s.addNotes(
    "Every choice here was made for a prototype that had to be reviewable by someone who is not going to install anything.\n\n" +
    "The important line is the last panel. Simulating retrieval was a legitimate scope decision for Workshop 1, but calling it AI-powered without qualification would not have been. The README opens with the limitation and lists what a real deployment would add, by name.\n\n" +
    "That habit — write the limitation where the reader will hit it first — carried into the second application."
  );
}

// ============================================================ 6. APP1 ARCHITECTURE
{
  const s = light("How a question becomes a cited answer", "App 1 · Phase 2 · Architecture");
  badge(s, "gp");
  const steps = [
    ["Role", "Protection engineer,\ncompliance analyst,\nor field crew"],
    ["Query", "Natural language,\nvalidated and\nlength-clamped"],
    ["Score", "Tokenize, score every\nvisible document\nsection by overlap"],
    ["Band", "High / low / none,\nfrom the top score\nand its margin"],
    ["Answer", "Synthesized text with\nthe cited passage\nbeside it"],
  ];
  const bw = 2.18, gap = 0.42, y = 1.85;
  steps.forEach(([t, d], i) => {
    const x = M + i * (bw + gap);
    s.addShape(pres.ShapeType.roundRect, {
      x, y, w: bw, h: 1.75, rectRadius: 0.09,
      fill: { color: i === 4 ? GP_WASH : WASH }, line: { color: i === 4 ? GP : RULE, width: i === 4 ? 1.1 : 0.75 },
      shadow: shadow(),
    });
    s.addText(t, { x: x + 0.2, y: y + 0.18, w: bw - 0.4, h: 0.35, fontSize: 15, bold: true, color: i === 4 ? GP : INK, fontFace: HEAD, margin: 0 });
    s.addText(d, { x: x + 0.2, y: y + 0.58, w: bw - 0.4, h: 1.0, fontSize: 11, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 14 });
    if (i < 4) arrow(s, x + bw + 0.08, y + 0.79, gap - 0.16, RULE);
  });

  s.addShape(pres.ShapeType.roundRect, {
    x: M + 3 * (bw + gap), y: 3.95, w: bw, h: 0.95, rectRadius: 0.09,
    fill: { color: "F7E9E9" }, line: { color: "A8473F", width: 1 },
  });
  s.addText("No confident source\n→ decline card", {
    x: M + 3 * (bw + gap) + 0.2, y: 4.1, w: bw - 0.4, h: 0.65, fontSize: 11.5, bold: true,
    color: "A8473F", fontFace: TEXT, margin: 0, lineSpacing: 15,
  });
  s.addShape(pres.ShapeType.line, {
    x: M + 3 * (bw + gap) + bw / 2, y: 3.6, w: 0, h: 0.35, line: { color: "A8473F", width: 1.25, endArrowType: "triangle" },
  });

  card(s, M, 5.25, W - 2 * M, 1.4, WASH);
  const facts = [["3", "personas, each with\nits own document set"],
                 ["4", "workspace tabs:\nsearch, library, upload, admin"],
                 ["100%", "client side — no network\ncalls, no third-party scripts"],
                 ["1,586", "lines across\n27 source files"]];
  facts.forEach(([v, l], i) => {
    const x = M + 0.45 + i * 2.95;
    s.addText(v, { x, y: 5.45, w: 1.0, h: 0.5, fontSize: 26, bold: true, color: GP, fontFace: HEAD, margin: 0 });
    s.addText(l, { x: x + 1.05, y: 5.48, w: 1.85, h: 0.75, fontSize: 10.5, color: BODY, fontFace: TEXT, margin: 0, lineSpacing: 13 });
  });
  s.addNotes(
    "Five stages, all in the browser. The one worth pausing on is the fourth.\n\n" +
    "Banding decides whether the app answers at all. If the top-scoring passage is not far enough ahead of the rest, the app returns a decline card rather than a low-confidence guess. That is the difference between a demo that always says something and a tool an engineer could trust.\n\n" +
    "The admin dashboard records every declined and low-confidence query, so the gaps in the document set become a work list for a content owner."
  );
}

// ============================================================ 7. APP1 PROTOTYPE
{
  const s = light("From a single artifact file to a real project", "App 1 · Phase 3 · Design & prototype");
  badge(s, "gp");
  s.addImage({ path: path.join(GP_SHOTS, "app-running-localhost.png"), x: 6.55, y: 1.55, w: 6.05, h: 3.78 });
  s.addText("The running app: query, cited answer, and the source passage beside it", {
    x: 6.55, y: 5.4, w: 6.05, h: 0.3, fontSize: 10.5, italic: true, color: MUTED, fontFace: TEXT, margin: 0,
  });

  heading(s, "Workshop 1 — Claude Artifacts", M, 1.65, 5.5, GP);
  body(s, "The first version was a single-file artifact: one React component, seeded documents inline, " +
       "no build step. Good for proving the interaction was worth building. Impossible to test, " +
       "review, or deploy.", M, 2.0, 5.5, 1.3, { size: 13 });

  heading(s, "Workshop 2 — into an IDE", M, 3.2, 5.5, GP);
  body(s, "Migrated to Vite + React as 27 files: components, design tokens, role definitions, seeded " +
       "data, and the retrieval logic isolated in src/lib/retrieval.js so it could be reasoned about " +
       "on its own.", M, 3.55, 5.5, 1.1, { size: 13 });

  card(s, M, 4.8, 5.5, 1.55, WASH);
  s.addText("1 file  →  27 files", {
    x: M + 0.35, y: 5.0, w: 4.8, h: 0.4, fontSize: 20, bold: true, color: INK, fontFace: HEAD, margin: 0,
  });
  s.addText("The migration was not cosmetic: separating retrieval from rendering is what made the " +
       "confidence banding testable, and the design tokens are what made a full dark theme a " +
       "one-file change.", {
    x: M + 0.35, y: 5.45, w: 4.8, h: 0.8, fontSize: 11.5, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 14.5,
  });
  s.addNotes(
    "The prototype answered one question: is a cited-answer interface actually better than searching a PDF? Once that was clear, the single file became the constraint.\n\n" +
    "Splitting the project into 27 files was what made the rest of the work possible. Retrieval moved into its own module, so confidence banding could be reasoned about without touching the UI. Design tokens moved into theme.js, so light and dark are one palette definition rather than scattered overrides.\n\n" +
    "This is the screenshot of the migrated app running locally at the end of Workshop 2."
  );
}

// ============================================================ 8. APP1 DESIGN
{
  const s = light("One product, three ways to look at it", "App 1 · Phase 3 · Interface");
  badge(s, "gp");
  const shots = [
    ["app-library.png", "Library", "Role-scoped document grid, filterable, with a full reader behind every card"],
    ["app-field-mode.png", "Field mode", "One column, large targets, tinted in the field crew's accent, for gloved use"],
    ["app-admin-dashboard.png", "Admin", "Searches, average confidence, decline rate, and every flagged query"],
  ];
  shots.forEach(([f, t, d], i) => {
    const x = M + i * 4.05;
    s.addImage({ path: path.join(GP_SHOTS, f), x, y: 1.6, w: 3.85, h: 2.41 });
    s.addText(t, { x, y: 4.12, w: 3.85, h: 0.32, fontSize: 15, bold: true, color: INK, fontFace: HEAD, margin: 0 });
    s.addText(d, { x, y: 4.46, w: 3.85, h: 0.75, fontSize: 11.5, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 14.5 });
  });
  card(s, M, 5.4, W - 2 * M, 1.15, GP_WASH);
  s.addText("Role scoping is product design, not a limitation.", {
    x: M + 0.4, y: 5.6, w: 5.6, h: 0.32, fontSize: 14, bold: true, color: GP, fontFace: TEXT, margin: 0,
  });
  s.addText("A field crew view deliberately does not surface PRC-005 or the CIP standards. A compliance " +
       "analyst sees the full standards set but not the relay setting sheet. Each role sees the documents its work actually uses.", {
    x: M + 0.4, y: 5.92, w: 11.4, h: 0.5, fontSize: 12, color: BODY, fontFace: TEXT, margin: 0, lineSpacing: 15.5,
  });
  s.addNotes(
    "Three screens, one product. The library gives browsing rather than only search, because engineers often want the whole procedure, not the paragraph that matched.\n\n" +
    "Field mode is the design decision I am most pleased with. It is not a responsive breakpoint; it is a different layout chosen by role, because a crew on a tablet has different needs from an analyst at a desk.\n\n" +
    "The admin dashboard closes the loop: every query the assistant could not answer is recorded, so the document set improves based on evidence."
  );
}

// ============================================================ 9. APP1 TESTING
{
  const s = light("Tested in a real browser, at three sizes", "App 1 · Phase 4 · Testing & responsible AI");
  badge(s, "gp");
  stat(s, M, 1.6, 2.6, "18", "automated checks", GP, "Driven through Chromium with Playwright");
  stat(s, M + 2.9, 1.6, 2.6, "3", "viewports", GP, "390 phone, 768 tablet, 1440 desktop");
  stat(s, M + 5.8, 1.6, 2.6, "0", "console errors", GP, "Across every run and every route");
  stat(s, M + 8.7, 1.6, 2.6, "1", "script error, not a bug", MUTED, "The test asserted a section title that had been renamed");

  card(s, M, 3.35, 6.1, 3.0, WASH);
  heading(s, "What was verified", M + 0.35, 3.6, 5.4, GP);
  bullets(s, [
    "Search across high-confidence, low-confidence and declined paths",
    "Role switching, and that the library contents change with it",
    "Upload validation, then immediate searchability of the new document",
    "Feedback thumbs, and the admin metrics that count them",
    "Light and dark appearance, persisting across reload",
    "Production build, clean, with no warnings",
  ], M + 0.35, 3.95, 5.4, 2.3);

  card(s, 7.2, 3.35, W - M - 7.2, 3.0, PAPER);
  heading(s, "Responsible AI as behaviour, not a disclaimer", 7.55, 3.6, 5.0, GP);
  const ra = [
    ["Every answer carries its source", "The passage is shown beside the answer, not just named."],
    ["The assistant declines", "Below the confidence threshold it says so instead of guessing."],
    ["Uncertainty is visible", "A confidence meter, with an accessible value, sits on every answer."],
    ["Gaps are recorded", "Declined queries land on the admin dashboard for a human to fix."],
  ];
  ra.forEach(([t, d], i) => {
    const y = 3.98 + i * 0.6;
    s.addShape(pres.ShapeType.ellipse, { x: 7.55, y: y + 0.07, w: 0.15, h: 0.15, fill: { color: GP } });
    s.addText(t, { x: 7.82, y, w: 5.0, h: 0.26, fontSize: 12.5, bold: true, color: INK, fontFace: TEXT, margin: 0 });
    s.addText(d, { x: 7.82, y: y + 0.25, w: 5.0, h: 0.3, fontSize: 11, color: MUTED, fontFace: TEXT, margin: 0 });
  });
  s.addNotes(
    "Testing was done by driving the real app in a real browser, not by reasoning about the code. Playwright at three viewports, with screenshots at each step for manual review.\n\n" +
    "The single failure was a test-script error rather than an application bug: it asserted an old section title that had been deliberately renamed. Worth reporting honestly, because a green suite that never fails is usually a suite that never checks anything.\n\n" +
    "On the right is the responsible-AI position. Every item is a behaviour you can observe in the running app, not a paragraph in a policy document."
  );
}

// ============================================================ 10. APP1 BUGS
{
  const s = light("The bug that only appears at 390 pixels", "App 1 · Phase 4 · Bugs found and fixed");
  badge(s, "gp");
  card(s, M, 1.6, 6.05, 4.5, PAPER);
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.35, y: 1.9, w: 1.35, h: 0.32, rectRadius: 0.16, fill: { color: "F7E9E9" }, line: { color: "A8473F", width: 0.7 } });
  s.addText("FOUND", { x: M + 0.35, y: 1.9, w: 1.35, h: 0.32, fontSize: 9.5, bold: true, color: "A8473F", fontFace: TEXT, align: "center", valign: "middle", margin: 0, charSpacing: 0.8 });
  s.addText("Mobile layout was fundamentally broken", { x: M + 0.35, y: 2.35, w: 5.35, h: 0.4, fontSize: 17, bold: true, color: INK, fontFace: HEAD, margin: 0 });
  bullets(s, [
    "The 252px sidebar never collapsed, squeezing content into a sliver",
    "Header text overlapped the search bar",
    "The two-pane search compressed both columns past readability",
  ], M + 0.35, 2.85, 5.35, 1.1, BODY);
  s.addText("Nobody had opened it at phone width. It looked correct on a laptop, and the checklist " +
       "item that caught it existed only because responsive behaviour was written down as something to test.", {
    x: M + 0.35, y: 4.2, w: 5.35, h: 1.2, fontSize: 12, italic: true, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 16,
  });

  card(s, 7.15, 1.6, W - M - 7.15, 4.5, GP_WASH);
  s.addShape(pres.ShapeType.roundRect, { x: 7.5, y: 1.9, w: 1.35, h: 0.32, rectRadius: 0.16, fill: { color: PAPER }, line: { color: GP, width: 0.7 } });
  s.addText("FIXED", { x: 7.5, y: 1.9, w: 1.35, h: 0.32, fontSize: 9.5, bold: true, color: GP, fontFace: TEXT, align: "center", valign: "middle", margin: 0, charSpacing: 0.8 });
  s.addText("Two breakpoints, both verified in-browser", { x: 7.5, y: 2.35, w: 5.1, h: 0.4, fontSize: 17, bold: true, color: INK, fontFace: HEAD, margin: 0 });
  bullets(s, [
    "≤980px: sidebar becomes a drawer, with a scrim and Escape to close",
    "≤700px: the two panes stack, answer first, source below",
    "Measured at 390px and 768px: no horizontal overflow",
    "Found in the same pass: reduced motion missed the loading shimmer",
  ], 7.5, 2.85, 5.1, 2.0, BODY);
  s.addText("Accessibility went in alongside: focus rings on every control, ARIA on the confidence " +
       "meter, keyboard-only navigation verified end to end.", {
    x: 7.5, y: 5.05, w: 5.1, h: 0.85, fontSize: 12, italic: true, color: BODY, fontFace: TEXT, margin: 0, lineSpacing: 16,
  });
  footnote(s, "Full detail in docs/testing-report.md and docs/security-checklist.md in the repository.");
  s.addNotes(
    "This is the first appearance of the lesson that ends up defining the whole capstone: the code was correct in the environment I was looking at, and broken in one I was not.\n\n" +
    "The fix was two breakpoints and a drawer, but the interesting part is how it was found. Responsive behaviour was a written checklist item, so it got opened at 390 pixels deliberately rather than by accident.\n\n" +
    "The reduced-motion gap came out of the same pass. The animations were disabled under prefers-reduced-motion, except the one added last."
  );
}

// ============================================================ 11. APP1 DEPLOY
{
  const s = light("Push to main, and it is live", "App 1 · Phase 5 · Deployment");
  badge(s, "gp");
  const steps = [["Commit", "Push to GitHub"], ["Build", "npm ci, then vite build"],
                 ["Deploy", "Firebase Hosting, live channel"], ["Serve", "HTTPS, global CDN, immutable assets"]];
  const bw = 2.7, gap = 0.55;
  steps.forEach(([t, d], i) => {
    const x = M + i * (bw + gap);
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.75, w: bw, h: 1.25, rectRadius: 0.09, fill: { color: i === 3 ? GP_WASH : WASH }, line: { color: i === 3 ? GP : RULE, width: i === 3 ? 1.1 : 0.75 }, shadow: shadow() });
    node(s, x + 0.25, 1.98, 0.32, i + 1, GP);
    s.addText(t, { x: x + 0.68, y: 1.96, w: bw - 0.9, h: 0.32, fontSize: 15, bold: true, color: INK, fontFace: HEAD, margin: 0 });
    s.addText(d, { x: x + 0.25, y: 2.4, w: bw - 0.5, h: 0.5, fontSize: 11.5, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 14 });
    if (i < 3) arrow(s, x + bw + 0.1, 2.3, gap - 0.2, RULE);
  });

  card(s, M, 3.3, 6.05, 2.55, WASH);
  heading(s, "What the pipeline does for free", M + 0.35, 3.55, 5.3, GP);
  bullets(s, [
    "Pull requests get their own preview URL, commented on the PR",
    "Only pushes to main go to the live channel",
    "Hashed assets cached for a year; index.html never cached",
    "Rollback is redeploying a previous commit",
  ], M + 0.35, 3.9, 5.3, 1.8, BODY);

  card(s, 7.15, 3.3, W - M - 7.15, 2.55, INK2);
  s.addText("Live now", { x: 7.5, y: 3.55, w: 5.1, h: 0.3, fontSize: 12, bold: true, color: "9AA6B8", fontFace: TEXT, margin: 0, charSpacing: 1 });
  s.addText(GP_URL, { x: 7.5, y: 3.9, w: 5.1, h: 0.45, fontSize: 18, bold: true, color: GP, fontFace: TEXT, margin: 0 });
  s.addText("Verified reachable, HTTP 200, serving the built bundle. No sign-in, no setup — the role " +
       "switcher is in the sidebar and the seeded document set is already there.", {
    x: 7.5, y: 4.45, w: 5.1, h: 1.1, fontSize: 12, color: "C6CFDC", fontFace: TEXT, margin: 0, lineSpacing: 16,
  });
  s.addNotes(
    "Deployment for a static React app is a solved problem, and the point of this slide is that connecting GitHub to hosting turns deployment from an event into a property of the repository.\n\n" +
    "The preview-URL behaviour is worth calling out: every pull request gets its own temporary URL, so a change can be reviewed running rather than as a diff.\n\n" +
    "The cache headers matter more than they look. Hashed assets are immutable for a year, index.html is never cached — and the second application later broke in exactly the way that rule prevents."
  );
}

// ============================================================ 12. APP1 CHALLENGES
{
  const s = light("What deployment actually taught me", "App 1 · Phase 5 · Challenges");
  badge(s, "gp");
  const items = [
    ["Choosing the service", "A static bundle does not need a container or a server. Picking hosting that matches the shape of the artifact removed most of the work rather than adding to it.", "Right-sized"],
    ["Secrets in CI", "The deploy needs a service-account credential. It lives in a GitHub secret and is never in the repository, and the workflow declares least-privilege permissions.", "Handled"],
    ["Cache correctness", "Hashed assets immutable, index.html never cached. Get this backwards and users load an HTML file pointing at bundles that no longer exist.", "Configured"],
  ];
  items.forEach(([t, d, tag], i) => {
    const y = 1.7 + i * 1.6;
    card(s, M, y, W - 2 * M, 1.4, i === 2 ? GP_WASH : WASH);
    s.addText(t, { x: M + 0.4, y: y + 0.22, w: 3.6, h: 0.4, fontSize: 16, bold: true, color: INK, fontFace: HEAD, margin: 0 });
    s.addShape(pres.ShapeType.roundRect, { x: M + 0.4, y: y + 0.72, w: 1.35, h: 0.3, rectRadius: 0.15, fill: { color: PAPER }, line: { color: GP, width: 0.7 } });
    s.addText(tag.toUpperCase(), { x: M + 0.4, y: y + 0.72, w: 1.35, h: 0.3, fontSize: 8.5, bold: true, color: GP, fontFace: TEXT, align: "center", valign: "middle", margin: 0, charSpacing: 0.6 });
    s.addText(d, { x: M + 4.3, y: y + 0.28, w: 7.5, h: 0.85, fontSize: 13, color: BODY, fontFace: TEXT, margin: 0, lineSpacing: 18 });
  });
  s.addText("The third item is the one that came back. Meridian shipped a blank page for exactly this reason, " +
       "and the fix was the rule GridPilot already had.", {
    x: M, y: 6.35, w: W - 2 * M, h: 0.4, fontSize: 12.5, italic: true, color: GP, fontFace: TEXT, margin: 0,
  });
  s.addNotes(
    "Three challenges, and the honest ranking is that the first was the largest at the time and the third mattered most in the end.\n\n" +
    "Choosing hosting that matched the artifact removed work. I had assumed deployment meant a server, and a static bundle does not need one.\n\n" +
    "The caching rule is the one to remember. GridPilot got it right by configuration. Meridian got it wrong months later and rendered a blank white page, and the fix was the same rule."
  );
}

// ============================================================ 13. APP1 FEEDBACK
{
  const s = light("What the showcase changed", "App 1 · Phase 6 · Feedback & iteration");
  badge(s, "gp");
  const pairs = [
    ["“How do I even run this?”", "Double-click launchers for Windows and macOS that check for Node, install once, start the server, and open the browser — no terminal, no URLs to find."],
    ["“Is it making the answers up?”", "The source passage moved beside the answer rather than behind a click, and the confidence meter became a permanent part of every answer card."],
    ["“What happens when it doesn't know?”", "The decline path became a demonstrated feature: a distinct card, and every declined query recorded on the admin dashboard."],
  ];
  pairs.forEach(([q, a], i) => {
    const y = 1.65 + i * 1.62;
    s.addShape(pres.ShapeType.roundRect, { x: M, y, w: 4.5, h: 1.4, rectRadius: 0.09, fill: { color: INK2 }, line: { color: INK2, width: 0 } });
    s.addText(q, { x: M + 0.35, y: y + 0.25, w: 3.8, h: 0.9, fontSize: 14.5, italic: true, color: PAPER, fontFace: HEAD, margin: 0, lineSpacing: 19, valign: "middle" });
    arrow(s, M + 4.62, y + 0.62, 0.5, GP);
    card(s, M + 5.28, y, W - M - (M + 5.28), 1.4, WASH);
    s.addText(a, { x: M + 5.63, y: y + 0.22, w: W - 2 * M - 5.98 + 0.35, h: 1.0, fontSize: 12.5, color: BODY, fontFace: TEXT, margin: 0, lineSpacing: 17, valign: "middle" });
  });
  footnote(s, "Every item above shipped. The launchers and the two-pane answer layout are in the deployed build today.");
  s.addNotes(
    "Three pieces of feedback from the Workshop 4 showcase, and what each one changed.\n\n" +
    "The first is the one I did not expect. I had been running the app with a dev server for weeks and had stopped seeing that command lines are a barrier. The launchers exist because of that comment.\n\n" +
    "The second and third are the same underlying question — can I trust this — asked two ways. The answer in both cases was to make the app's honesty visible rather than documented: show the source, show the confidence, and show the decline."
  );
}

// ============================================================ 14. APP2 PROBLEM
{
  const s = light("A harder problem, on purpose", "App 2 · Workshop 5 · Problem & AI use case");
  badge(s, "mf");
  card(s, M, 1.6, 6.05, 2.5, WASH);
  s.addText("Two records of the same account routinely disagree.", {
    x: M + 0.35, y: 1.85, w: 5.35, h: 0.7, fontSize: 18, bold: true, color: INK, fontFace: HEAD, margin: 0, lineSpacing: 23,
  });
  body(s, "A charge posts twice. An authorisation hold never clears. A cheque clears on paper and never " +
       "reaches the app's feed. Catching that by hand means reading a year of statements against a year " +
       "of app history, line by line, so nobody does it.",
       M + 0.35, 2.6, 5.35, 1.3, { size: 13, lineSpacing: 18 });

  card(s, 7.15, 1.6, W - M - 7.15, 2.5, MF_WASH);
  heading(s, "The AI use case, and its hard boundary", 7.5, 1.85, 5.1, MF);
  body(s, "Categorising thousands of cryptic merchant descriptors and answering questions about a ledger " +
       "is genuine model work. But financial data is the last thing that should leave a machine, so the " +
       "model runs on 127.0.0.1 and a start-up check refuses any endpoint that does not resolve to loopback.",
       7.5, 2.2, 5.1, 1.7, { size: 13, lineSpacing: 18 });

  const facts = [["2", "profiles, fully isolated"], ["11", "accounts, 7 institutions"],
                 ["3,350", "generated transactions"], ["13", "planted events to catch"]];
  facts.forEach(([v, l], i) => {
    const x = M + i * 3.11;
    card(s, x, 4.35, 2.9, 1.3, PAPER);
    s.addText(v, { x: x + 0.3, y: 4.55, w: 2.3, h: 0.5, fontSize: 26, bold: true, color: MF, fontFace: HEAD, margin: 0 });
    s.addText(l, { x: x + 0.3, y: 5.05, w: 2.3, h: 0.45, fontSize: 11.5, color: BODY, fontFace: TEXT, margin: 0, lineSpacing: 14 });
  });
  s.addText("The dataset was generated with thirteen deliberate anomalies planted in it — a duplicate charge, " +
       "a card compromise, a subscription that creeps up, a cheque the feed never saw — so the app could be " +
       "measured on whether it finds them rather than on whether it runs.", {
    x: M, y: 5.85, w: W - 2 * M, h: 0.8, fontSize: 12.5, italic: true, color: BODY, fontFace: TEXT, margin: 0, lineSpacing: 17,
  });
  s.addNotes(
    "The second application was chosen to be harder in a specific way: it needed a real backend, real parsing, and a correctness problem where being almost right is worse than being obviously wrong.\n\n" +
    "The privacy boundary is the defining constraint. The AI layer talks only to a local model, and that is enforced by a start-up check rather than a promise in the README.\n\n" +
    "The thirteen planted events are how the project avoided grading itself on vibes. The dataset has known answers, so the reconciliation engine can be measured."
  );
}

// ============================================================ 15. APP2 ARCHITECTURE
{
  const s = light("Layers, and the rules between them", "App 2 · Architecture");
  badge(s, "mf");
  const layers = [
    ["Interface", "React 18 · TypeScript · Vite · Tailwind", "Compiled into the backend and served by it, so the container needs no Node at runtime"],
    ["Routers", "FastAPI · async · cookie sessions", "HTTP only. No business logic lives here"],
    ["Services", "Ingestion · dedupe · reconciliation · budgets · coach", "All the judgment. Returns domain objects, never ORM rows"],
    ["Repositories", "SQLAlchemy 2 · every method scoped by user_id", "All the SQL. A structural test fails the build if a method forgets the user"],
    ["Storage", "SQLite today, PostgreSQL-compatible schema · Alembic migrations", "Money is integer cents everywhere, never a float"],
  ];
  layers.forEach(([t, tech, note], i) => {
    const y = 1.6 + i * 0.98;
    s.addShape(pres.ShapeType.roundRect, {
      x: M, y, w: 9.35, h: 0.82, rectRadius: 0.08,
      fill: { color: i % 2 === 0 ? WASH : PAPER }, line: { color: RULE, width: 0.75 },
    });
    s.addText(t, { x: M + 0.32, y: y + 0.12, w: 1.75, h: 0.3, fontSize: 14, bold: true, color: MF, fontFace: HEAD, margin: 0 });
    s.addText(tech, { x: M + 0.32, y: y + 0.44, w: 4.4, h: 0.28, fontSize: 10.5, color: MUTED, fontFace: TEXT, margin: 0 });
    s.addText(note, { x: M + 4.9, y: y + 0.18, w: 4.3, h: 0.5, fontSize: 11.5, color: BODY, fontFace: TEXT, margin: 0, lineSpacing: 14.5, valign: "middle" });
  });
  card(s, 10.3, 1.6, W - M - 10.3, 4.95, MF_WASH);
  s.addText("The AI layer", { x: 10.6, y: 1.85, w: 2.1, h: 0.3, fontSize: 14, bold: true, color: MF, fontFace: HEAD, margin: 0 });
  s.addText("Ollama\nqwen2.5 · local", { x: 10.6, y: 2.2, w: 2.1, h: 0.6, fontSize: 11.5, color: BODY, fontFace: TEXT, margin: 0, lineSpacing: 15 });
  s.addShape(pres.ShapeType.roundRect, { x: 10.6, y: 2.95, w: 2.1, h: 1.5, rectRadius: 0.08, fill: { color: PAPER }, line: { color: MF, width: 1 } });
  s.addText("127.0.0.1\nonly", { x: 10.6, y: 3.15, w: 2.1, h: 0.6, fontSize: 15, bold: true, color: MF, fontFace: HEAD, align: "center", margin: 0, lineSpacing: 19 });
  s.addText("Enforced at\nstart-up, not\nby configuration", { x: 10.6, y: 3.8, w: 2.1, h: 0.6, fontSize: 10.5, color: MUTED, fontFace: TEXT, align: "center", margin: 0, lineSpacing: 13 });
  s.addText("Judgment in the model.\nGuarantees in code.", { x: 10.6, y: 4.7, w: 2.1, h: 0.8, fontSize: 12.5, bold: true, italic: true, color: MF, fontFace: HEAD, margin: 0, lineSpacing: 16 });
  s.addText("Totals, confidence ceilings and category identifiers are computed in Python after the model answers.", { x: 10.6, y: 5.5, w: 2.1, h: 0.95, fontSize: 10.5, color: BODY, fontFace: TEXT, margin: 0, lineSpacing: 13 });
  footnote(s, "Layering rule: routers do no business logic, services do no SQL, repositories do no HTTP.");
  s.addNotes(
    "Five layers with one rule between them: routers do no business logic, services do no SQL, repositories do no HTTP.\n\n" +
    "Two of these are enforced rather than encouraged. A structural test reads the repository signatures and fails if any method can be called without a user id, which is how profile isolation stays true as the code grows. And money is integer cents everywhere.\n\n" +
    "The panel on the right is the phrase the whole AI design comes down to. The model is allowed to have opinions about categories and phrasing. It is never allowed to be the reason a number is correct."
  );
}

// ============================================================ 16. APP2 PARSERS
{
  const s = light("Five formats in, one ledger out", "App 2 · The hard part");
  badge(s, "mf");
  const layouts = [
    ["American Bank", "MM/DD/YY", "Date, description,\namount, balance"],
    ["Chase", "Mon DD, YYYY", "Card purchases print\npositive, so signs flip"],
    ["Discover", "MM/DD/YYYY", "Transaction and post\ndates in separate columns"],
    ["Ally", "ISO 8601", "Unsigned columns — direction\nlives in the running balance"],
    ["Capital One", "Mon DD, no year", "Year comes from the\nbilling period header"],
  ];
  layouts.forEach(([n, d, q], i) => {
    const x = M + i * 2.42;
    card(s, x, 1.6, 2.22, 1.85, i > 2 ? MF_WASH : WASH);
    s.addText(n, { x: x + 0.22, y: 1.78, w: 1.8, h: 0.3, fontSize: 13.5, bold: true, color: INK, fontFace: HEAD, margin: 0 });
    s.addText(d, { x: x + 0.22, y: 2.08, w: 1.8, h: 0.26, fontSize: 10.5, bold: true, color: MF, fontFace: TEXT, margin: 0 });
    s.addText(q, { x: x + 0.22, y: 2.4, w: 1.8, h: 0.85, fontSize: 10.5, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 13 });
  });
  s.addText("Plus CSV exports from four platforms and monthly OFX files.", {
    x: M, y: 3.55, w: 6, h: 0.3, fontSize: 11.5, italic: true, color: MUTED, fontFace: TEXT, margin: 0,
  });

  card(s, M, 4.0, 6.05, 2.35, PAPER);
  heading(s, "Deduplication is where correctness is won or lost", M + 0.35, 4.25, 5.4, MF);
  body(s, "The same purchase arrives from the feed and from a statement, dated a day or three apart, described " +
       "differently. Match too eagerly and a real transaction disappears from someone's ledger. Match too " +
       "cautiously and every purchase shows twice.",
       M + 0.35, 4.6, 5.4, 1.2, { size: 12.5, lineSpacing: 17 });
  s.addText("Two layers: an occurrence-aware hash, then a one-to-one assignment pass over amount-exact " +
       "candidates within three days.", {
    x: M + 0.35, y: 5.72, w: 5.4, h: 0.5, fontSize: 12, bold: true, color: INK, fontFace: TEXT, margin: 0, lineSpacing: 15,
  });

  card(s, 7.15, 4.0, W - M - 7.15, 2.35, MF_WASH);
  s.addText("The proof", { x: 7.5, y: 4.25, w: 5.1, h: 0.3, fontSize: 12, bold: true, color: MF, fontFace: TEXT, margin: 0, charSpacing: 0.8 });
  s.addText("153", { x: 7.5, y: 4.5, w: 1.6, h: 0.78, fontSize: 42, bold: true, color: MF, fontFace: HEAD, margin: 0 });
  s.addText("documents imported\ninto seeded profiles", { x: 9.15, y: 4.62, w: 3.4, h: 0.55, fontSize: 12, color: BODY, fontFace: TEXT, margin: 0, lineSpacing: 15 });
  s.addText("1", { x: 7.5, y: 5.28, w: 1.6, h: 0.78, fontSize: 42, bold: true, color: INK, fontFace: HEAD, margin: 0 });
  s.addText("new row created — every\nother line matched what\nthe feed already had", { x: 9.15, y: 5.32, w: 3.4, h: 0.75, fontSize: 12, color: BODY, fontFace: TEXT, margin: 0, lineSpacing: 15 });
  s.addNotes(
    "Five PDF layouts, deliberately different, because a parser that only handles one bank has not been tested.\n\n" +
    "The last two are the interesting ones. Ally prints withdrawals and deposits as separate unsigned columns, so nothing on the row says which direction the money went — the parser derives it from the running balance. Capital One prints no year on the row at all.\n\n" +
    "The numbers on the right are the deduplication result, and they are the single best evidence in the project. 153 documents imported into profiles that had already synced, and exactly one row was genuinely new."
  );
}

// ============================================================ 17. APP2 SCREENS
{
  const s = light("Eight screens, and what each one is for", "App 2 · The application");
  badge(s, "mf");
  const shots = [
    ["m8-dashboard-live.png", 2.58, "Dashboard", "Spending power, not just a balance: liquid funds minus what is already committed"],
    ["m10-reconciliation.png", 2.58, "Reconciliation", "Every statement period, its status, and the arithmetic that does not close"],
    ["m12-budgets.png", 2.75, "Budgets", "Targets against real spending, with a simulator for changing one and seeing the effect"],
  ];
  shots.forEach(([f, h, t, d], i) => {
    const x = M + i * 4.05;
    s.addImage({ path: path.join(MF_SHOTS, f), x, y: 1.6, w: 3.85, h });
    s.addText(t, { x, y: 4.5, w: 3.85, h: 0.32, fontSize: 15, bold: true, color: INK, fontFace: HEAD, margin: 0 });
    s.addText(d, { x, y: 4.84, w: 3.85, h: 0.8, fontSize: 11.5, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 14.5 });
  });
  card(s, M, 5.7, W - 2 * M, 0.95, MF_WASH);
  s.addText("Plus Accounts, Transactions, Documents, Review and Coach — and the Coach says plainly when the local model is missing rather than pretending to answer.", {
    x: M + 0.4, y: 5.88, w: 11.4, h: 0.6, fontSize: 12.5, color: BODY, fontFace: TEXT, margin: 0, lineSpacing: 16, valign: "middle",
  });
  s.addNotes(
    "Three of the eight screens. The dashboard leads with spending power rather than a balance, because a balance that includes money already committed to a credit card bill is misleading.\n\n" +
    "Reconciliation is the screen the whole application exists for. Every period, its status, and where the arithmetic does not close.\n\n" +
    "Budgets are set per category per month and measured against categorised spending, with a simulator for testing a change before committing to it."
  );
}

// ============================================================ 17. APP2 TESTING
{
  const s = light("205 backend tests, and what they defend", "App 2 · Testing & security");
  badge(s, "mf");
  s.addChart(pres.ChartType.bar, [{
    name: "Tests",
    labels: ["Parser golden files", "Domain services", "Dataset integrity", "Deploy & migrations", "Hardening", "Auth"],
    values: [123, 32, 23, 13, 8, 6],
  }], {
    x: M, y: 1.6, w: 6.6, h: 3.2, barDir: "bar", chartColors: [MF],
    showTitle: false, showLegend: false, showValue: true, dataLabelPosition: "outEnd",
    dataLabelColor: BODY, dataLabelFontSize: 11, dataLabelFontFace: TEXT,
    catAxisLabelColor: BODY, catAxisLabelFontSize: 11, catAxisLabelFontFace: TEXT,
    valAxisLabelColor: MUTED, valAxisLabelFontSize: 10, valAxisHidden: true,
    valGridLine: { style: "none" }, catGridLine: { style: "none" },
    barGapWidthPct: 45, valAxisMaxVal: 145,
  });
  s.addText("Plus 13 frontend tests and a TypeScript build gate in CI.", {
    x: M, y: 4.85, w: 6.6, h: 0.3, fontSize: 11.5, italic: true, color: MUTED, fontFace: TEXT, margin: 0,
  });

  card(s, 7.5, 1.6, W - M - 7.5, 2.3, MF_WASH);
  heading(s, "Tests that exist because of a real defect", 7.85, 1.85, 4.7, MF);
  bullets(s, [
    "A poisoned MIME map, so a bad registry cannot break the bundle",
    "index.html must never be cached, or a rebuild renders blank",
    "Absolute SQLite paths, after one silently became relative",
    "Login throttling, from the security audit",
  ], 7.85, 2.22, 4.7, 1.6, BODY, 11.5);

  card(s, 7.5, 4.05, W - M - 7.5, 2.3, PAPER);
  heading(s, "Security posture", 7.85, 4.3, 4.7, MF);
  bullets(s, [
    "Argon2id hashing; JWT in an HttpOnly SameSite=Strict cookie",
    "Every query scoped by user_id, enforced structurally",
    "Uploads capped and type-checked; errors leak nothing",
    "No secrets in the repository; config from the environment",
  ], 7.85, 4.67, 4.7, 1.6, BODY, 11.5);
  s.addNotes(
    "205 backend tests, and the shape of the chart is the point. Well over half are golden-file parser tests, because parsing other people's PDF layouts is where silent corruption enters a ledger.\n\n" +
    "The four tests on the top right did not exist when the code was written. Each one exists because something broke in a way the suite could not see — a Windows MIME map, a cached HTML file, a path that lost its leading slash, and unlimited password guesses against demo accounts published in the README.\n\n" +
    "That is what a regression test is for: not proving the fix works today, but making the environment that broke it part of the suite."
  );
}

// ============================================================ 18. APP2 DEPLOY
{
  const s = light("A container that costs nothing while idle", "App 2 · Workshop 6 · Deployment");
  badge(s, "mf");
  const steps = [["Push", "GitHub"], ["Build", "Cloud Build reads the Dockerfile"],
                 ["Store", "Artifact Registry"], ["Run", "Cloud Run, scale to zero"]];
  const bw = 2.7, gap = 0.55;
  steps.forEach(([t, d], i) => {
    const x = M + i * (bw + gap);
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.7, w: bw, h: 1.15, rectRadius: 0.09, fill: { color: i === 3 ? MF_WASH : WASH }, line: { color: i === 3 ? MF : RULE, width: i === 3 ? 1.1 : 0.75 }, shadow: shadow() });
    node(s, x + 0.25, 1.9, 0.32, i + 1, MF);
    s.addText(t, { x: x + 0.68, y: 1.88, w: bw - 0.9, h: 0.32, fontSize: 15, bold: true, color: INK, fontFace: HEAD, margin: 0 });
    s.addText(d, { x: x + 0.25, y: 2.3, w: bw - 0.5, h: 0.45, fontSize: 11.5, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 14 });
    if (i < 3) arrow(s, x + bw + 0.1, 2.2, gap - 0.2, RULE);
  });

  s.addChart(pres.ChartType.bar, [{
    name: "Cold start",
    labels: ["Migrate and seed\non every start", "Database baked\ninto the image"],
    values: [4.44, 0.76],
  }], {
    x: M, y: 3.2, w: 5.9, h: 2.35, barDir: "col", chartColors: [MUTED, MF],
    varyColors: true, showTitle: true, title: "Cold start, seconds", titleFontSize: 12,
    titleColor: BODY, titleFontFace: TEXT, showLegend: false, showValue: true,
    dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontSize: 13,
    dataLabelFontFace: TEXT, dataLabelFormatCode: "0.00",
    catAxisLabelColor: BODY, catAxisLabelFontSize: 10.5, catAxisLabelFontFace: TEXT,
    valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    barGapWidthPct: 90, valAxisMaxVal: 5.6,
  });
  s.addText("Migrating and seeding 3,350 transactions ran on every scale-from-zero. The same work now happens once, at image build time.", {
    x: M, y: 5.6, w: 5.9, h: 0.6, fontSize: 11.5, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 15,
  });

  card(s, 7.0, 3.2, W - M - 7.0, 1.4, INK2);
  s.addText("Live now", { x: 7.35, y: 3.4, w: 5.2, h: 0.28, fontSize: 12, bold: true, color: "9AA6B8", fontFace: TEXT, margin: 0, charSpacing: 1 });
  s.addText(MF_URL, { x: 7.35, y: 3.7, w: 5.3, h: 0.35, fontSize: 14.5, bold: true, color: "5FBF9B", fontFace: TEXT, margin: 0 });
  s.addText("Both demo profiles sign in with one click.", { x: 7.35, y: 4.08, w: 5.2, h: 0.3, fontSize: 11.5, color: "C6CFDC", fontFace: TEXT, margin: 0 });

  card(s, 7.0, 4.75, W - M - 7.0, 1.6, "FBF7F0");
  heading(s, "Two limits, stated rather than hidden", 7.35, 4.95, 5.2, "9A6B1E");
  bullets(s, [
    "The database is a file in the container, so live edits reset on restart",
    "AI features are off on the public URL — a container has no local model",
  ], 7.35, 5.28, 5.2, 1.05, BODY, 11.5);
  s.addNotes(
    "One command deploys this: gcloud run deploy from the repository root. Cloud Build reads the Dockerfile, Artifact Registry stores the image, Cloud Run serves it and scales to zero between visits, which is why it costs nothing.\n\n" +
    "The chart is a real measurement. Migrating and seeding thousands of transactions ran on every cold start until the database was baked into the image at build time.\n\n" +
    "The two limits on the right are deliberate. The AI one especially: the app refuses to send financial data to a model it does not host, and a cloud container has no local model, so those features report themselves unavailable rather than quietly using someone's API."
  );
}

// ============================================================ 19. APP2 FEEDBACK
{
  const s = light("The demo was working. It just looked broken.", "App 2 · Workshop 6 · Feedback & iteration");
  badge(s, "mf");
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 1.6, w: 5.5, h: 1.5, rectRadius: 0.09, fill: { color: INK2 } });
  s.addText("“My downloaded version does not have the same outputs as the screenshots you show.”", {
    x: M + 0.35, y: 1.8, w: 4.8, h: 1.1, fontSize: 14, italic: true, color: PAPER, fontFace: HEAD, margin: 0, lineSpacing: 19, valign: "middle",
  });
  body(s, "Correct, and my fault. The demo profiles were seeded with account data only, so Documents, " +
       "Reconciliation and Budgets opened empty. Three of eight screens looked unimplemented, which is " +
       "the opposite of what a demo is for.",
       M, 3.25, 5.5, 1.3, { size: 13, lineSpacing: 18 });

  card(s, 6.85, 1.6, W - M - 6.85, 3.15, MF_WASH);
  heading(s, "What shipped in response", 7.2, 1.85, 5.4, MF);
  const rows = [["Documents", "0", "117 and 36"], ["Reconciled periods", "0", "79 and 36"],
                ["Budget targets", "0", "6 and 6"], ["Review queue", "0", "309 waiting"]];
  rows.forEach(([label, before, after], i) => {
    const y = 2.3 + i * 0.52;
    s.addText(label, { x: 7.2, y, w: 2.5, h: 0.3, fontSize: 12.5, color: BODY, fontFace: TEXT, margin: 0 });
    s.addText(before, { x: 9.8, y, w: 0.6, h: 0.3, fontSize: 12.5, bold: true, color: MUTED, fontFace: TEXT, margin: 0, align: "right" });
    arrow(s, 10.55, y + 0.08, 0.35, MF);
    s.addText(after, { x: 11.05, y, w: 1.5, h: 0.3, fontSize: 12.5, bold: true, color: MF, fontFace: TEXT, margin: 0 });
  });
  s.addText("Seeding now runs the whole pipeline, and the finished result is built into the image and the download.", {
    x: 7.2, y: 4.22, w: 5.4, h: 0.45, fontSize: 11, italic: true, color: BODY, fontFace: TEXT, margin: 0, lineSpacing: 14,
  });

  card(s, M, 4.75, W - 2 * M, 1.6, PAPER);
  heading(s, "Deliberately still empty: 309 transactions in the review queue", M + 0.4, 4.95, 8, MF);
  body(s, "Those are the cryptic descriptors — SQ *BLUE STEM, TST* MERIDIAN 04 — that exist to be triaged. " +
       "Pre-filling them from the generator's own answer key would have deleted the feature they were built " +
       "to demonstrate. The one-click demo sign-in shipped in the same pass.",
       M + 0.4, 5.3, 11.4, 0.9, { size: 12.5, lineSpacing: 17 });
  s.addNotes(
    "This is the most useful feedback I received across both applications, and it came from someone downloading the app rather than watching me demo it.\n\n" +
    "The features worked. The demo data did not exercise them. Seeding now runs the entire pipeline — import, categorise, reconcile, budget — and the finished result is baked into both the container image and the download, so it costs nothing at start-up.\n\n" +
    "The last panel is the judgment call. I deliberately left 309 transactions uncategorised, because those are the ones the review queue exists for."
  );
}

// ============================================================ 20. AI ROLE
{
  const s = dark("How the AI was actually used", "AI's role");
  const patterns = [
    ["Write the brief before the code",
     "The second project started with a written build plan and fifteen milestones, produced and argued over before a single file existed. Every later prompt could refer to it.",
     "Prevented the drift that costs the most time: rewriting something because the shape was wrong."],
    ["Judgment in the model, guarantees in code",
     "The model proposes categories and phrasing. Totals, confidence ceilings and identifiers are computed in Python afterwards.",
     "A 3B model was overconfident about cryptic descriptors. The fix was a deterministic cap in code, not a sterner prompt."],
    ["Log the decision, not just the change",
     "Thirty numbered decision records, each with the reasoning and the rejected alternative.",
     "Made it possible to answer 'why is it like this' months later, and to hand context to a fresh session."],
  ];
  patterns.forEach(([t, d, e], i) => {
    const x = M + i * 4.15;
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.7, w: 3.9, h: 4.3, rectRadius: 0.1, fill: { color: INK2 }, line: { color: "2E3A4B", width: 0.75 } });
    node(s, x + 0.35, 1.98, 0.36, i + 1, i === 1 ? MF : GP);
    s.addText(t, { x: x + 0.35, y: 2.5, w: 3.2, h: 0.85, fontSize: 16, bold: true, color: PAPER, fontFace: HEAD, margin: 0, lineSpacing: 20 });
    s.addText(d, { x: x + 0.35, y: 3.42, w: 3.2, h: 1.35, fontSize: 12, color: "C6CFDC", fontFace: TEXT, margin: 0, lineSpacing: 16 });
    s.addShape(pres.ShapeType.line, { x: x + 0.35, y: 4.85, w: 3.2, h: 0, line: { color: "3C4A5E", width: 1 } });
    s.addText(e, { x: x + 0.35, y: 5.0, w: 3.2, h: 0.9, fontSize: 11.5, italic: true, color: "9AA6B8", fontFace: TEXT, margin: 0, lineSpacing: 15 });
  });
  s.addText("Tools: Claude Artifacts for the first prototype · Claude Code in the terminal for both builds · Playwright for browser testing · a local qwen2.5 through Ollama as the application's own model", {
    x: M, y: 6.3, w: W - 2 * M, h: 0.6, fontSize: 11.5, color: "9AA6B8", fontFace: TEXT, margin: 0, lineSpacing: 15,
  });
  s.addNotes(
    "Three patterns that changed how much the assistance was worth.\n\n" +
    "Writing the brief first was the single biggest improvement between the two applications. The first was built by conversation; the second started from a plan we argued about before any code existed.\n\n" +
    "The middle one is the design principle for anything that has to be correct. When a smaller model was overconfident about cryptic merchant descriptors, the fix was a deterministic confidence cap in code. Writing a sterner prompt made the model worse, not better.\n\n" +
    "The decision log mattered more than expected, because it let a fresh session pick up months of context without re-deriving it."
  );
}

// ============================================================ 21. LESSONS
{
  const s = light("What changed between the first and the second", "Lessons learned");
  const rows = [
    ["Where the plan lived", "In the conversation", "In a written brief, argued before any code"],
    ["When deployment was decided", "After it was built", "Before the first migration was written"],
    ["What tests covered", "The features, in one browser", "The features, plus the environments that broke them"],
    ["How the model was trusted", "Asked, then checked by eye", "Constrained in code, tested against a real local model"],
    ["What the demo data proved", "That the app runs", "That the app finds thirteen known anomalies"],
  ];
  s.addText("GridPilot AI", { x: 4.9, y: 1.5, w: 3.6, h: 0.3, fontSize: 12.5, bold: true, color: GP, fontFace: TEXT, margin: 0 });
  s.addText("Meridian Financial", { x: 8.85, y: 1.5, w: 3.9, h: 0.3, fontSize: 12.5, bold: true, color: MF, fontFace: TEXT, margin: 0 });
  rows.forEach(([label, a, b], i) => {
    const y = 1.85 + i * 0.78;
    if (i % 2 === 0) {
      s.addShape(pres.ShapeType.rect, { x: M, y: y - 0.06, w: W - 2 * M, h: 0.72, fill: { color: WASH }, line: { color: WASH, width: 0 } });
    }
    s.addText(label, { x: M + 0.25, y: y + 0.08, w: 3.9, h: 0.5, fontSize: 12.5, bold: true, color: INK, fontFace: TEXT, margin: 0, valign: "middle" });
    s.addText(a, { x: 4.9, y: y + 0.08, w: 3.7, h: 0.5, fontSize: 12, color: MUTED, fontFace: TEXT, margin: 0, valign: "middle", lineSpacing: 15 });
    s.addText(b, { x: 8.85, y: y + 0.08, w: 3.9, h: 0.5, fontSize: 12, color: BODY, fontFace: TEXT, margin: 0, valign: "middle", lineSpacing: 15 });
  });
  card(s, M, 5.9, W - 2 * M, 0.95, MF_WASH);
  s.addText("The lesson underneath all five: a green test run proves the code is correct in the environment the tests run in. Download, install and deployment are each a different environment.", {
    x: M + 0.4, y: 6.08, w: 11.4, h: 0.6, fontSize: 13.5, bold: true, color: INK, fontFace: HEAD, margin: 0, lineSpacing: 18, valign: "middle",
  });
  s.addNotes(
    "Five concrete changes, and one lesson underneath them.\n\n" +
    "The three worst bugs in the second application all lived where the tests do not run. A blank white page on Windows because that machine maps .js to text/plain. A blank page after a rebuild because a cached HTML file pointed at bundles that no longer existed. A database path that silently lost its leading slash inside a container.\n\n" +
    "None is a logic error. No amount of unit testing would have found them, because they live in the gap between environments. What I would do differently is treat download, install and deploy as testable environments from the first week."
  );
}

// ============================================================ 22. VALUE GP
{
  const s = light("What GridPilot is worth to a utility", "Value & impact · App 1");
  badge(s, "gp");
  card(s, M, 1.6, 5.9, 2.4, WASH);
  heading(s, "Where the time goes today", M + 0.35, 1.85, 5.2, GP);
  body(s, "An engineer with a standards question opens a shared drive, finds a PDF, checks it is the current " +
       "revision, and reads to the right table. Ten to fifteen minutes when it goes well. Longer when the " +
       "answer is in a document they did not know existed.", M + 0.35, 2.2, 5.2, 1.4, { size: 12.5, lineSpacing: 17 });

  card(s, 6.95, 1.6, W - M - 6.95, 2.4, GP_WASH);
  heading(s, "Illustrative annual value", 7.3, 1.85, 5.3, GP);
  s.addText("200 engineers  ×  2 lookups a week  ×  10 minutes saved  ≈  3,470 hours a year", {
    x: 7.3, y: 2.2, w: 5.3, h: 0.85, fontSize: 13.5, bold: true, color: INK, fontFace: TEXT, margin: 0, lineSpacing: 19,
  });
  s.addText("Assumption-based, not measured. The point is the shape: the saving scales with headcount and " +
       "question volume, and the platform cost does not.", {
    x: 7.3, y: 3.1, w: 5.3, h: 0.7, fontSize: 11, italic: true, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 14,
  });

  const benefits = [
    ["Compliance risk", "An answer that cites its source is auditable. An answer from memory is not."],
    ["Onboarding", "A new analyst asks the workspace instead of asking a senior engineer."],
    ["Content gaps", "Declined queries are recorded, so the document set improves from evidence."],
    ["Field safety", "The right procedure, on a tablet, without a laptop or a phone call."],
  ];
  benefits.forEach(([t, d], i) => {
    const x = M + (i % 2) * 6.05, y = 4.25 + Math.floor(i / 2) * 1.15;
    s.addShape(pres.ShapeType.ellipse, { x, y: y + 0.06, w: 0.17, h: 0.17, fill: { color: GP } });
    s.addText(t, { x: x + 0.32, y, w: 5.3, h: 0.28, fontSize: 13.5, bold: true, color: INK, fontFace: TEXT, margin: 0 });
    s.addText(d, { x: x + 0.32, y: y + 0.3, w: 5.3, h: 0.6, fontSize: 11.5, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 15 });
  });
  s.addNotes(
    "The arithmetic on this slide is labelled illustrative because it is. I have assumptions, not measurements, and presenting an estimate as a finding is exactly the habit this course taught me to avoid.\n\n" +
    "What I would defend is the shape. The saving scales with headcount and question volume, and the hosting cost does not move.\n\n" +
    "The four benefits below are harder to price and probably matter more. The compliance one especially: in a regulated environment, an answer that cites its source is auditable and an answer from memory is not."
  );
}

// ============================================================ 23. VALUE MF
{
  const s = light("What Meridian is worth to a household", "Value & impact · App 2");
  badge(s, "mf");
  const tiles = [
    ["13", "anomalies planted", "and every one detected by the app itself"],
    ["3", "actionable findings", "across a full year, with zero false positives"],
    ["79", "periods reconciled", "in under a minute, unattended"],
  ];
  tiles.forEach(([v, l, d], i) => {
    const x = M + i * 4.15;
    card(s, x, 1.6, 3.9, 1.65, MF_WASH);
    s.addText(v, { x: x + 0.35, y: 1.74, w: 3.2, h: 0.68, fontSize: 34, bold: true, color: MF, fontFace: HEAD, margin: 0 });
    s.addText(l, { x: x + 0.35, y: 2.38, w: 3.2, h: 0.3, fontSize: 13, bold: true, color: INK, fontFace: TEXT, margin: 0 });
    s.addText(d, { x: x + 0.35, y: 2.68, w: 3.2, h: 0.45, fontSize: 11, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 14 });
  });

  card(s, M, 3.5, 5.9, 2.85, WASH);
  heading(s, "The value is the errors nobody would have found", M + 0.35, 3.75, 5.2, MF);
  body(s, "A duplicate restaurant charge two days apart. A cheque that cleared on paper and never reached " +
       "the account feed, leaving a balance permanently overstated by $230. A hold that never released. " +
       "Each is small. Each would have sat there for years, because checking by hand costs more than the error.",
       M + 0.35, 4.1, 5.2, 1.6, { size: 12.5, lineSpacing: 17 });
  s.addText("An hour of statement-checking a month is the realistic alternative, and almost nobody does it.", {
    x: M + 0.35, y: 5.78, w: 5.2, h: 0.5, fontSize: 11.5, italic: true, color: MF, fontFace: TEXT, margin: 0,
  });

  card(s, 6.95, 3.5, W - M - 6.95, 2.85, PAPER);
  heading(s, "Where it goes commercially", 7.3, 3.75, 5.3, MF);
  const biz = [
    ["Bookkeepers and small firms", "The same reconciliation, run against client accounts, is billable work today."],
    ["Privacy as the product", "A finance tool that provably never sends data off the machine has a market that cloud tools cannot serve."],
    ["Cost to run", "Zero while idle on scale-to-zero hosting; a hosted database is roughly nine dollars a month."],
  ];
  biz.forEach(([t, d], i) => {
    const y = 4.1 + i * 0.78;
    s.addShape(pres.ShapeType.ellipse, { x: 7.3, y: y + 0.06, w: 0.17, h: 0.17, fill: { color: MF } });
    s.addText(t, { x: 7.62, y, w: 5.0, h: 0.28, fontSize: 13, bold: true, color: INK, fontFace: TEXT, margin: 0 });
    s.addText(d, { x: 7.62, y: y + 0.28, w: 5.0, h: 0.5, fontSize: 11.5, color: MUTED, fontFace: TEXT, margin: 0, lineSpacing: 14.5 });
  });
  s.addNotes(
    "The three tiles are measured, not estimated. Thirteen anomalies were planted in the generated dataset and the application detects every one, surfacing three as actionable with no false positives.\n\n" +
    "Zero false positives is the number I would lead with commercially. A reconciliation tool that cries wolf gets switched off in a week.\n\n" +
    "On the right, the privacy angle is the real commercial argument. Every competing tool asks you to upload a year of transaction history. This one refuses to send it anywhere, and that refusal is enforced in code."
  );
}

// ============================================================ 24. CONCLUSION
{
  const s = dark("Two applications, live, and what comes next", "Conclusion");
  const road = [
    [GP, "GridPilot AI", ["Real retrieval: managed vector store, embeddings, hybrid search",
                          "A hosted model for synthesis, with a guardrail against uncited claims",
                          "Okta SSO with role mapping, CIP-appropriate hosting and audit logging"]],
    [MF, "Meridian Financial", ["A hosted database, so the live URL keeps what people put into it",
                                "A real provider integration behind the interface the mock already implements",
                                "A rules screen, so a correction becomes a rule the user can see and edit"]],
  ];
  road.forEach(([colour, name, items], i) => {
    const x = M + i * 6.2;
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.65, w: 5.85, h: 3.0, rectRadius: 0.1, fill: { color: INK2 }, line: { color: colour, width: 1 } });
    s.addText(name, { x: x + 0.38, y: 1.9, w: 5.1, h: 0.4, fontSize: 19, bold: true, color: colour, fontFace: HEAD, margin: 0 });
    s.addText("Roadmap", { x: x + 0.38, y: 2.32, w: 5.1, h: 0.26, fontSize: 10.5, bold: true, color: "9AA6B8", fontFace: TEXT, margin: 0, charSpacing: 1 });
    items.forEach((t, j) => {
      const y = 2.68 + j * 0.62;
      node(s, x + 0.38, y, 0.28, j + 1, colour);
      s.addText(t, { x: x + 0.8, y: y - 0.04, w: 4.7, h: 0.55, fontSize: 11.5, color: "C6CFDC", fontFace: TEXT, margin: 0, lineSpacing: 15 });
    });
  });

  s.addShape(pres.ShapeType.roundRect, { x: M, y: 4.95, w: 5.85, h: 1.0, rectRadius: 0.09, fill: { color: "1A2230" }, line: { color: "2E3A4B", width: 0.75 } });
  s.addText("gridpilot-ai-fb150.web.app", { x: M + 0.38, y: 5.18, w: 5.1, h: 0.35, fontSize: 15, bold: true, color: GP, fontFace: TEXT, margin: 0 });
  s.addText("Pick a role in the sidebar and ask it something", { x: M + 0.38, y: 5.53, w: 5.1, h: 0.3, fontSize: 11, color: "9AA6B8", fontFace: TEXT, margin: 0 });

  s.addShape(pres.ShapeType.roundRect, { x: M + 6.2, y: 4.95, w: 5.85, h: 1.0, rectRadius: 0.09, fill: { color: "1A2230" }, line: { color: "2E3A4B", width: 0.75 } });
  s.addText("meridian-792468836580.us-central1.run.app", { x: M + 6.58, y: 5.18, w: 5.1, h: 0.35, fontSize: 13.5, bold: true, color: "5FBF9B", fontFace: TEXT, margin: 0 });
  s.addText("Sign in with one click and open Reconciliation", { x: M + 6.58, y: 5.53, w: 5.1, h: 0.3, fontSize: 11, color: "9AA6B8", fontFace: TEXT, margin: 0 });

  s.addText("Two problems framed, two applications built, tested, deployed, shown to users, and changed because of what they said.", {
    x: M, y: 6.35, w: W - 2 * M, h: 0.4, fontSize: 13, italic: true, color: "9AA6B8", fontFace: TEXT, margin: 0, align: "center",
  });
  s.addNotes(
    "Both applications are live right now, and both URLs are on this slide. Please open them.\n\n" +
    "The roadmaps are honest about what each one is missing. GridPilot needs real retrieval to be more than a convincing prototype. Meridian needs a hosted database before anyone could keep their own data in it.\n\n" +
    "What I take from running this lifecycle twice is that the second time was faster for one reason: the decisions that hurt the first time were made first the second time. Deployment shape, testing surface, and where the model is allowed to be authoritative."
  );
}

pres.writeFile({ fileName: "AI_Capstone_Presentation.pptx" }).then((f) => console.log("wrote", f));
