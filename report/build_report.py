"""Build the Lenovo Problem C round-1 report. Body word count excludes cover, contact, sources, and figures."""

from pathlib import Path

import matplotlib.pyplot as plt
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

OUT_DIR = Path(__file__).resolve().parent
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCX = OUT_DIR / "ShreedharGupta_IITK_ProblemC.docx"

SECTIONS = [
    (
        "1. Summary",
        """SourceDesk is a private workbench for contracts, salary files, and policies. Every answer on the screen is a quote already on the laptop, with the file and the page or cell beside it. A language model may join those quotes into one short sentence. It may not add a number, a name, or a date. If the check fails, or the index is unsure, the screen says the documents do not say.

A language model is a next-token distribution (CS781 Module 1.5), so perplexity measures fit, not whether a salary is the right cell. On a prior case-retrieval task, document 5-gram BM25 scored 0.42 development micro-F1@7, and every strong blend kept the encoder weight at 0.25. Generated summaries of long judgments reached about 0.23 ROUGE-L. An extract of the source sentences reached 0.30. A weaker laptop drops the stitcher. It keeps the quote check.""",
    ),
    (
        "2. The users and the problem",
        """The illustrative set is 48 files and about 180 MB: 20 PDF contracts, 12 Word policies, 10 Excel workbooks, and 6 scanned PDFs. Extracted text is on the order of 25 million characters. At about four characters per subword token, that is about 6 million tokens. The hardest file is the scan, because one wrong OCR digit is a different salary. The workbook is the next hardest, because the usual false number is the neighbouring cell.

Neha, an HR partner, asks for one bonus among several hundred employees. Rahul, a legal associate, compares two vendor contracts. A finance analyst, on a deadline, asks a figure from a quarterly pack that includes a scanned page. Search inside one open file is not the hard part. Trust is. A cloud model is often forbidden, because the file cannot leave the machine. A local model still emits numbers that are not in the file. Next-token prediction is a generative process, not a lookup. The user needs the cell or the clause, and a refusal when the set does not contain the answer.""",
    ),
    (
        "3. Your solution and its method",
        """Retrieval is a hard lookup, and only then a soft one. Module 2.3 opens the transformer as a database: a query matches a key and returns a value. Attention is that lookup in vector form. Module 4.1 notes that an in-context prompt pays quadratic attention and runs out of context. The corpus stays in an index. Attention, when it runs, stays inside a span of 512 tokens.

Each span is stored twice, as Module 1.3 combines a neural model with an n-gram model. BM25 runs on words and on 5-grams. Module 1.1 trusts a higher-order gram when its count is large and falls back when the count is small, so a 5-gram hit on a name or a figure is specific and a word hit still recalls a paraphrase. The other view is a 256-dimensional mean pool of the span, so bank in a cheque clause is not bank by a river. The blend is 0.75 lexical and 0.25 dense, the encoder weight kept on the earlier task. That task was prior-case retrieval. The weight will be retuned here, and until then the lexical term leads.

The blender keeps the top 8 spans. No shared content word means the documents do not say. A second span appears only if it clears a held-out cutoff and states another number. A salary is not a mean of two cells.

The sentence on the screen is extractive. Each quoted line is a substring of its span. A stitcher may add one sentence, decoded greedily. Temperature does not change greedy decoding except on ties, while sampling can change a digit, so the decoder does not sample. The stitcher only joins quotes. A checker pulls every number, date, and capitalised name from the sentence. Each must occur in the cited span. A failure drops the sentence. The quotes remain. Smoothing, in Module 1.1, gives leftover probability to unseen grams so a model still answers. A string absent from the span is a refusal.

A summary is at most five source sentences, each cited. A version compare returns sentences that the two files do not share, still as quotes. A draft uses those quotes only. A drafted sentence that fails the checker is deleted.

Neha asks for Rahul Verma's bonus. The cited cell holds 1,50,000. A stitch that writes 1,80,000, the next row, fails the checker and is not shown. Rahul asks the notice period. Version 1 says 30 days and version 2 says 60 days. Both clauses are shown. A changed file is reparsed from its path and modified time, and only its postings are replaced. The result cache is keyed by the question and the file hashes, and it drops when a hash changes.""",
    ),
    (
        "4. Architecture and technology choices",
        """The pieces are a parser, a chunker, two indexes, a blender, an extractor, a stitcher, and the checker. All of them run on the laptop. The question path does not open a socket.

The parser reads a PDF or a Word file as text with page numbers, an Excel workbook as one record per cell with the sheet and the address, and a scan as text plus an OCR confidence. A page whose confidence is below 0.8 is marked uncertain. It cannot, alone, support a numeric answer. The chunker cuts 512 subword tokens with an overlap of 64, and it does not separate an Excel row from its header. Module 1.4 uses subwords because a word vocabulary is large and a rare party name would otherwise be an unknown token.

Figure 1 is the flow. Words and 5-grams go to BM25. The same spans go to the mean pool. The question hits both. The blender returns eight spans. The extractor copies lines. The stitcher may join them. The checker accepts or refuses.

The prototype is Python. Parsing uses pypdf, python-docx, and openpyxl. BM25 is local, so the score is visible. The pool and the stitcher are PyTorch. The product path for a Copilot+ NPU is an ONNX Runtime session of the same graph, selected at startup by the tier probe.

I set aside a cloud model, because the file would leave the laptop. I set aside placing the corpus in the prompt. Attention cost grows with the square of that length, and the database lookup already exists. I set aside full fine-tuning. Module 3.4 accounts an FP16 Adam step as 2|P| bytes of weights, 2|P| bytes of gradients, and 12|P| bytes of optimizer state. For 7 billion parameters that is about 112 GB. That is a training cluster. A later adaptation, if one is justified by the tests in section 7, is LoRA of rank 16 and alpha 32 on the stitcher only. Module 4.1 merges those matrices into the base weights at inference, so a second model is not served. It does not train.""",
    ),
    (
        "5. Resource budget and performance",
        """The three tiers use one checker. Tier A is the smallest laptop I would support: 16 GB of RAM, a 256 GB SSD, Windows 11, and a CPU. Below 16 GB the set is refused. Tier A answers from BM25 and quotes. Tier B is a Copilot+ PC, an NPU of at least 40 TOPS and 16 to 32 GB of RAM, with an INT4 model of about 1.5 billion parameters. Tier C has a discrete GPU. This machine is an RTX 4060 with 8 GB. INT4 stores 0.5|P| bytes, so 7 billion parameters are 3.5 GB and load only when free video memory holds the weights and the cache. Otherwise Tier C uses the smaller stitcher.

One sequence of cache, at 2 FP16 bytes per value, is 2 × layers × key-value heads × head size × length × 2. For 28 layers, 2 key-value heads, head size 128, and 2,048 tokens, that is about 56 MB. The 1.5 billion weights are 1.5×10^9 × 0.5 = 0.75 GB, so Tier B uses about 0.8 GB while answering and then unloads. Idle is the index: about 48 MB for 6 million postings at 8 bytes, and about 7 MB for 15,000 pools of 256 dimensions at 2 bytes. Idle stays under about 200 MB.

The times are estimates from these rates. Parsing 180 MB at 10 MB/s takes 18 seconds. Sixty scanned pages take 60 seconds at 1 second on the CPU and 18 seconds at 0.3 seconds on the GPU. BM25 at 2 microseconds a token takes 12 seconds. Embedding 15,000 spans takes 600 seconds at 40 ms on the CPU and 60 seconds at 4 ms on the GPU. If the GPU is busy, the battery is under 20 percent, or free disk is under 2 GB, embedding pauses and the stitcher unloads. The process stays at low priority and resumes when the GPU, the battery, and the disk recover. Quotes and the checker remain. The screen says the mode is reduced.""",
    ),
    (
        "6. Privacy, safety and reliability",
        """A local model still invents, because it continues text, and smoothing gives probability to grams the files never contained. SourceDesk answers only from retrieved spans, quotes them, checks numbers, names, and dates, and says the documents do not say when they do not. Conflicting spans stay as two quotes. Figure 3 is the card: the sentence, the quote, the location, and a mark. Green means the checker passed. Amber means low OCR confidence or a score near the threshold. Red means a refusal. Every salary, bonus, and clause that changes money or time asks a person to confirm it.

Logs store a document id and a latency, not passage text. The index key is sealed by Windows Hello, and BitLocker covers a lost laptop. A temporary parse file is removed in a finally block. Crash upload is off, so a dump is not a second contract. The clipboard takes one quote after an explicit copy, then clears. Model and policy files are signed and checked locally. The fetch contains no document bytes, so IT can replace the stitcher and the threshold without seeing the index. If the checker fails, the result is a refusal.""",
    ),
    (
        "7. Measuring success",
        """A person builds about 200 questions from the corpus. The threshold is fit on one half and scored on the other, then the halves swap. Forty questions have no answer in the files. Twenty are files that disagree. Each answerable question has a gold span marked by hand.

Recall at 8 is the share whose gold span is among the eight. The exact-quote rate is the share of quotes that are substrings of the cited span. The unsupported-number rate is the share of shown answers that contain a number absent from the citation. Refusal accuracy is the share of absent and contradictory items that refuse, or that show both sides, instead of one invented figure.

For a salary or an operative clause, a wrong displayed figure is acceptable only at a rate of zero, and only after a person confirms it. A miss is allowed. The miss is the sentence that the documents do not say. Higher recall that admits one false salary is a worse system. Each index change is timed on the same questions, before and after, for probe latency as well as for recall, exact quotes, and unsupported numbers.""",
    ),
    (
        "8. Trade-offs and what you left out",
        """I left out a new foundation model, a cloud fallback, and a full document system. Section 5 is why a foundation model is not a laptop job. I also left out handwriting and any path onto the web. The dense index can miss a paraphrase that shares no words with the span. The 0.25 weight is only a prior from another task, and section 7 is the test. LoRA on the stitcher is specified and is not trained. The resource figures are products of the sizes and rates above. They are estimates. Cursor assisted the drafting. The design and the measurements are mine.""",
    ),
]


def words(text: str) -> int:
    return len(text.split())


def shade(cell, hex_color: str) -> None:
    tc = cell._tePr if hasattr(cell, "_tePr") else cell._tc
    tc_pr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    tc_pr.append(shd)


def set_run_font(run, name="Calibri", size=11, bold=False, color=None, italic=False):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)


def add_body(doc, text):
    for block in text.split("\n\n"):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.line_spacing = 1.08
        run = p.add_run(block.replace("\n", " "))
        set_run_font(run)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def add_heading_styled(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    set_run_font(run, size=14, bold=True, color=(20, 33, 61))


def add_caption(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(10)
    run = p.add_run(text)
    set_run_font(run, size=9, italic=True, color=(70, 70, 70))
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def draw_flow(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.6, 2.15), dpi=160)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 2.2)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    labels = [
        "Files",
        "Parse\nor OCR",
        "512-token\nspans",
        "BM25\n+ pool",
        "Top 8",
        "Quotes",
        "Check\nor refuse",
    ]
    xs = [0.15, 1.75, 3.35, 4.95, 6.55, 8.15, 9.75]
    for i, (x, lab) in enumerate(zip(xs, labels)):
        color = "#14213D" if i < 6 else "#9B2226"
        ax.add_patch(
            plt.Rectangle((x, 0.55), 1.45, 1.15, facecolor=color, edgecolor="none", joinstyle="round")
        )
        ax.text(x + 0.72, 1.12, lab, ha="center", va="center", color="white", fontsize=8, fontname="Calibri")
        if i < len(labels) - 1:
            ax.annotate(
                "",
                xy=(xs[i + 1] - 0.02, 1.12),
                xytext=(x + 1.48, 1.12),
                arrowprops=dict(arrowstyle="-|>", color="#6C757D", lw=1.2),
            )
    fig.tight_layout(pad=0.15)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close()


def draw_card(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.6, 2.5), dpi=160)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3.1)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.add_patch(plt.Rectangle((0.15, 0.15), 11.7, 2.8, facecolor="#F7F4EF", edgecolor="#14213D", lw=1.2))
    ax.add_patch(plt.Rectangle((0.15, 2.35), 0.18, 0.6, facecolor="#2D6A4F", edgecolor="none"))
    ax.text(0.55, 2.62, "Green  ·  checker passed  ·  a person still confirms pay", fontsize=8, color="#1B4332", fontname="Calibri", va="center")
    ax.text(0.5, 2.05, "Rahul Verma's bonus in the FY25 sheet is 1,50,000.", fontsize=11, color="#14213D", fontname="Calibri")
    ax.text(0.5, 1.45, "Quote  ·  FY25.xlsx  ·  Sheet Payroll  ·  cell D14", fontsize=8.5, color="#6C757D", fontname="Calibri")
    ax.text(0.5, 0.95, "“Rahul Verma    1,50,000”", fontsize=10, color="#14213D", fontname="Calibri", style="italic")
    ax.text(0.5, 0.42, "The stitch 1,80,000 matched cell D15, not D14. It was dropped.", fontsize=8, color="#9B2226", fontname="Calibri")
    fig.tight_layout(pad=0.15)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close()


def set_cell_text(cell, text, bold=False, size=9, color=(20, 33, 61), fill=None):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, color=color)
    if fill:
        shade(cell, fill)


def add_tier_table(doc):
    rows = [
        ["", "Tier A  ·  smallest", "Tier B  ·  Copilot+", "Tier C  ·  discrete GPU"],
        ["Machine", "16 GB RAM, CPU, 256 GB SSD", "NPU ≥ 40 TOPS, 16–32 GB", "RTX 4060 class, 8 GB"],
        ["What answers", "BM25 and quotes", "INT4 stitcher, ~1.5B", "INT4 up to ~7B if VRAM remains"],
        ["Weights", "none loaded", "0.75 GB  (1.5e9 × 0.5)", "3.5 GB  (7e9 × 0.5), else 0.75 GB"],
        ["KV cache", "none", "~56 MB at 2,048 tokens", "same 56 MB, or the 7B cache if loaded"],
        ["While answering", "index, under ~200 MB", "~0.8 GB, then unload", "3.5 GB + cache, else Tier B path"],
        ["Dense index", "background, or skipped", "built on the NPU or CPU", "~60 s at 4 ms per span"],
        ["Checker", "always on", "always on", "always on"],
    ]
    table = doc.add_table(rows=len(rows), cols=4)
    table.style = "Table Grid"
    table.autofit = True
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            fill = "14213D" if r == 0 else ("F4F1EA" if r % 2 == 0 else "FFFFFF")
            color = (255, 255, 255) if r == 0 else (20, 33, 61)
            set_cell_text(table.rows[r].cells[c], val, bold=(r == 0 or c == 0), size=8, color=color, fill=fill)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_page_number(paragraph):
    run = paragraph.add_run()
    fld_char_1 = OxmlElement("w:fldChar")
    fld_char_1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_char_2 = OxmlElement("w:fldChar")
    fld_char_2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char_1)
    run._r.append(instr)
    run._r.append(fld_char_2)


def build():
    counts = {title: words(body) for title, body in SECTIONS}
    total = sum(counts.values())
    print("WORD COUNTS")
    for title, n in counts.items():
        print(f"{n:4d}  {title}")
    print(f"{total:4d}  TOTAL body")

    flow = OUT_DIR / "figure1_flow.png"
    card = OUT_DIR / "figure3_card.png"
    draw_flow(flow)
    draw_card(card)

    doc = Document()
    for s in doc.sections:
        s.top_margin = Cm(1.7)
        s.bottom_margin = Cm(1.7)
        s.left_margin = Cm(1.9)
        s.right_margin = Cm(1.9)
        s.page_width = Cm(21.0)
        s.page_height = Cm(29.7)
        footer = s.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = footer.add_run("SourceDesk  ·  Problem C  ·  ")
        set_run_font(run, size=8, color=(120, 120, 120))
        add_page_number(footer)
        for r in footer.runs:
            set_run_font(r, size=8, color=(120, 120, 120))

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)

    # Cover. Reviewers in round 1 do not see this page.
    for _ in range(2):
        doc.add_paragraph()
    kicker = doc.add_paragraph()
    kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = kicker.add_run("LENOVO AI PC HACKATHON  ·  TECHKRITI, IIT KANPUR")
    set_run_font(run, size=11, bold=True, color=(155, 34, 38))

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(18)
    run = title.add_run("Problem C")
    set_run_font(run, size=28, bold=True, color=(20, 33, 61))

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub.add_run("Private AI Workbench")
    set_run_font(run, size=16, color=(20, 33, 61))

    name = doc.add_paragraph()
    name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name.paragraph_format.space_before = Pt(28)
    run = name.add_run("SourceDesk")
    set_run_font(run, size=20, bold=True, color=(20, 33, 61))

    tag = doc.add_paragraph()
    tag.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = tag.add_run("Answers are quotes. The model does not get to invent a figure.")
    set_run_font(run, size=11, italic=True, color=(70, 70, 70))

    who = doc.add_paragraph()
    who.alignment = WD_ALIGN_PARAGRAPH.CENTER
    who.paragraph_format.space_before = Pt(36)
    run = who.add_run("Shreedhar Gupta\nIndian Institute of Technology Kanpur\nRoll 240993")
    set_run_font(run, size=12, color=(20, 33, 61))

    doc.add_page_break()

    for title, body in SECTIONS:
        add_heading_styled(doc, title)
        add_body(doc, body)
        if title.startswith("4."):
            doc.add_picture(str(flow), width=Inches(6.3))
            add_caption(doc, "Figure 1. Data flow on the laptop.")
        if title.startswith("5."):
            add_tier_table(doc)
            add_caption(doc, "Figure 2. Tier arithmetic.")
        if title.startswith("6."):
            doc.add_picture(str(card), width=Inches(6.3))
            add_caption(doc, "Figure 3. A checked answer card.")

    add_heading_styled(doc, "Contact")
    add_body(
        doc,
        "Shreedhar Gupta. Roll 240993. B.Tech. student, Indian Institute of Technology Kanpur. "
        "Email: shreedhargupta20042006@gmail.com. Codabench id s_240993. "
        "The git identity on this machine stored that address without the @ sign. Please use the address with the @.",
    )

    add_heading_styled(doc, "Sources")
    sources = [
        "Ashutosh Modi, CS781 Large Language Models, IIT Kanpur. Modules 1.1 (n-gram models, interpolation, smoothing, perplexity), 1.3 (neural models combined with n-gram models; static embeddings), 1.4 (byte-pair encoding), 1.5 (a language model predicts the next token), 2.3 (database analogy for query, key, and value; attention as vector retrieval), 3.1 and 3.3 (Chinchilla, compute on the order of 6ND; Kaplan scaling), 3.4 (FP16 Adam memory: 2|P| weights, 2|P| gradients, 12|P| optimizer state), 4.1 (in-context cost, LoRA merged at inference).",
        "Hoffmann et al., Training Compute-Optimal Large Language Models, the Chinchilla scaling law, as taught in Modules 3.1 and 3.3. Kaplan et al., Scaling Laws for Neural Language Models, arXiv:2001.08361.",
        "Sennrich, Haddow, and Birch, Neural Machine Translation of Rare Words with Subword Units, arXiv:1508.07909. Cited for byte-pair encoding in Module 1.4.",
        "Robertson and Zaragoza, The Probabilistic Relevance Framework: BM25 and Beyond, Foundations and Trends in Information Retrieval, 2009.",
        "Microsoft Support, Copilot+ PCs hardware requirements: an NPU of 40 or more TOPS, 16 GB RAM, and 256 GB storage. support.microsoft.com/en-us/topic/copilot-pc-hardware-requirements-35782169-6eab-4d63-a5c5-c498c3037364.",
        "Own measurements, CS781 capstone, legal text. Phase 7 prior-case retrieval: document 5-gram BM25, development micro-F1@7 0.4213; the lexical mix without an encoder, 0.4325; the selected blends kept encoder weight 0.25 and reached 0.4336. Heavier neural rankers scored lower (partial fine-tune 0.4058, prefix tuning 0.3969). Phase 6 summarization: extractive readout ROUGE-L 0.3041 on 12 held-out documents; the best generated decoder run, 0.2278. These are a different task from this workbench. They motivate the blend. They are not a score for SourceDesk.",
    ]
    for src in sources:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.left_indent = Cm(0.4)
        run = p.add_run(src)
        set_run_font(run, size=10)

    doc.save(DOCX)
    print("wrote", DOCX)


if __name__ == "__main__":
    build()
