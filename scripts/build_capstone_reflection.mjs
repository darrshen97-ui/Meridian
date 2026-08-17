// Capstone reflection paper.  node scripts/build_capstone_reflection.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, Packer,
  Paragraph, TextRun,
} from "docx";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "docs", "deliverables");
fs.mkdirSync(OUT, { recursive: true });
const LETTER = { width: 12240, height: 15840 };

const p = (t, o = {}) => new Paragraph({
  spacing: { after: o.after ?? 160, line: 300 },
  children: [new TextRun({ text: t, size: o.size ?? 22, italics: o.italics, bold: o.bold })],
});
const h1 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_1, spacing: { before: 260, after: 130 },
  children: [new TextRun({ text: t, size: 24, bold: true })],
});
const rule = () => new Paragraph({
  spacing: { after: 200 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "C9C9C6" } },
  children: [new TextRun({ text: "", size: 2 })],
});

const BODY = [
  h1("Where I started"),
  p("In Workshop 1 I built GridPilot AI as a single-file Claude Artifacts prototype: one React " +
    "component, documents inline, no build step. It answered the only question a prototype needs " +
    "to answer — is a cited-answer interface actually better than searching a PDF — and it was " +
    "impossible to test, review or deploy. Migrating it into a Vite project in Workshop 2 turned " +
    "one file into twenty-seven, and that was not tidying. Pulling retrieval out into its own " +
    "module is what made confidence banding something I could reason about."),
  p("Workshop 3 taught me that deployment is a shape question before it is a technical one. I had " +
    "assumed a deployed app meant a server; a static bundle does not need one, and choosing hosting " +
    "that matched the artifact removed most of the work instead of adding to it. Workshop 4 " +
    "produced the comment I did not expect: “How do I even run this?” I had been starting the app " +
    "with a dev server for weeks and had stopped seeing that a command line is a barrier."),

  h1("How AI assistance changed the way I work"),
  p("The difference between the two applications was not how much I used AI, but when. GridPilot " +
    "was built by conversation: ask, look at the result, adjust. Meridian Financial started with a " +
    "written brief and fifteen milestones, argued over before a single file existed, and every " +
    "later prompt could point at it. That one change removed most of the rework, because the " +
    "expensive mistakes are not bad lines of code — they are the right code in the wrong shape."),
  p("The second change was learning to treat the model as a component with failure modes rather " +
    "than an oracle. When a smaller local model was confidently wrong about cryptic merchant " +
    "descriptors, my instinct was to write a sterner prompt. It made the output worse. The fix was " +
    "a deterministic confidence cap in Python, applied after the model answered. That became the " +
    "rule I built the rest of the application around: judgment in the model, guarantees in code. " +
    "Totals, category identifiers and confidence ceilings are computed, never asked for."),
  p("The third change was economic. Assistance made tests cheap enough that I stopped rationing " +
    "them: 205 backend tests, against the first application's manual checklist."),

  h1("The most valuable lesson"),
  p("A green test run proves the code is correct in the environment the tests run in. Download, " +
    "install and deployment are each a different environment."),
  p("I learned this three times, expensively. A full suite passed while the downloaded application " +
    "showed a blank white page on Windows, because that machine's registry maps .js to text/plain " +
    "and browsers refuse to execute a module served that way. Another blank page appeared after a " +
    "rebuild, because a cached HTML file pointed at bundles that no longer existed. A third defect " +
    "would have made every document in the deployed container unreadable, because file paths were " +
    "recorded absolutely and the image builds its database in one directory and reads it from " +
    "another. None is a logic error, and no unit test would have found any of them."),
  p("What changed is that those environments are now testable things rather than assumptions. The " +
    "suite includes a poisoned MIME map, a cache-header assertion, and an absolute-path case, " +
    "because each of those reproduces the environment that actually broke."),

  h1("How I will apply this"),
  p("Three habits are coming with me. Write the brief and the decision record before the code, " +
    "because the reasoning is worth more later than the diff. Decide the deployment shape at the " +
    "start rather than the end — Meridian's database layer was portable from its first migration, " +
    "which is why deploying it was one command instead of a rewrite. And put the artifact in " +
    "someone else's hands early: the two most useful pieces of feedback across six workshops both " +
    "came from someone trying to use the thing rather than watching me demonstrate it."),
  p("The last habit is the one I would defend hardest. Both applications state their limitations " +
    "where a reader hits them first: GridPilot's README opens by saying retrieval is simulated, and " +
    "Meridian's public deployment says plainly that its AI features are unavailable because it " +
    "refuses to send financial data to a model it does not host. It would have been easy to let " +
    "either one imply more than it does. Being honest about what a thing cannot do turned out to " +
    "be a design skill rather than a disclaimer."),
];

const doc = new Document({
  title: "Capstone Reflection",
  description: "Reflection on Workshops 1-6, GridPilot AI and Meridian Financial.",
  creator: "AIML-515 Capstone",
  styles: { default: { document: { run: { font: "Calibri", size: 22 } } } },
  sections: [{
    properties: { page: { size: LETTER, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: "Capstone Reflection", size: 16, color: "9A9CA1" })] })] }) },
    children: [
      new Paragraph({ spacing: { after: 40 },
        children: [new TextRun({ text: "Reflection: two applications, one lifecycle run twice", size: 32, bold: true })] }),
      new Paragraph({ spacing: { after: 180 },
        children: [new TextRun({ text: "GridPilot AI and Meridian Financial · Workshops 1–6", size: 20, color: "6E7178" })] }),
      rule(),
      ...BODY,
    ],
  }],
});

fs.writeFileSync(path.join(OUT, "Capstone_Reflection.docx"), await Packer.toBuffer(doc));
console.log("wrote docs/deliverables/Capstone_Reflection.docx");
