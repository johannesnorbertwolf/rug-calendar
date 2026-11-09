#!/usr/bin/env python3
"""Generate a self-contained web page that lets students pick their
practical groups and download a personalized .ics calendar.

Usage:
    python3 generate.py <source.ics> [output.html]

The source is the RUG Maat schedule feed (text/calendar).

Term 2 notes:
- The group marker lives in the SUMMARY (title), not DESCRIPTION.
- Letter groups are per-block; only Statistics IB matters now.
- Two modes: full calendar (from today) or just the Statistics IB practicals.
"""

import json
import re
import sys


def unfold(s: str) -> str:
    return re.sub(r"\r?\n[ \t]", "", s)


def prop(block: str, name: str) -> str:
    m = re.search(r"^" + name + r"[^:]*:(.*)$", block, re.M)
    return unfold(m.group(1).strip()) if m else ""


def parse(raw: str):
    lines = raw.splitlines()
    ul = []
    for ln in lines:
        if ln[:1] in (" ", "\t") and ul:
            ul[-1] += ln[1:]
        else:
            ul.append(ln)
    clean = "\n".join(ul) + "\n"

    events = re.findall(r"BEGIN:VEVENT.*?END:VEVENT", clean, re.DOTALL)
    header = clean[: clean.find("BEGIN:VEVENT")].rstrip("\n") + "\n"
    footer = "\n" + clean[clean.rfind("END:VEVENT") + len("END:VEVENT") :].lstrip("\n")
    return header, events, footer


def natural_key(value: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", value)]


LETTER_RE = re.compile(r"\[GR-[A-Z]\]")
NUMBER_RE = re.compile(r"\[GR\d{4}\]")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "/tmp/schedule.raw"
    out = sys.argv[2] if len(sys.argv) > 2 else "index.html"

    raw = open(src, encoding="utf-8", errors="replace").read().replace("\r\n", "\n")
    header, events, footer = parse(raw)

    data = []
    for e in events:
        summary = prop(e, "SUMMARY")
        date = prop(e, "DTSTART")[:8]
        data.append([summary, date, e])

    ib_letters = sorted(
        {
            LETTER_RE.search(s).group(0)
            for s, _, _ in data
            if "Statistics IB" in s and LETTER_RE.search(s)
        },
        key=natural_key,
    )
    number_groups = sorted(
        {NUMBER_RE.search(s).group(0) for s, _, _ in data if NUMBER_RE.search(s)},
        key=natural_key,
    )

    payload = {
        "header": header,
        "events": data,
        "footer": footer,
        "ib_letters": ib_letters,
        "number_groups": number_groups,
    }

    js = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    html = TEMPLATE.replace("__DATA__", js)

    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"wrote {out}")
    print(f"  events: {len(events)}")
    print(f"  Statistics IB letter groups: {len(ib_letters)}")
    print(f"  numbered groups: {len(number_groups)}")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Psychology (Bachelor, year 1) — my timetable</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f4f6f8; color: #1a1a2e; display: flex; justify-content: center; padding: 24px;
  }
  .card { background: #fff; border-radius: 14px; box-shadow: 0 6px 24px rgba(0,0,0,.08);
          max-width: 460px; width: 100%; padding: 32px; }
  @keyframes hero-pop { 0% { transform: scale(.5) rotate(-3deg); opacity: 0; }
                        60% { transform: scale(1.08) rotate(1deg); }
                        100% { transform: scale(1) rotate(0); opacity: 1; } }
  h1 { font-size: 22px; margin: 0 0 6px; }
  p.sub { color: #5b6470; font-size: 14px; margin: 0 0 20px; }
  .mode { border: 1px solid #e0e4e8; border-radius: 10px; overflow: hidden; margin-bottom: 20px; }
  .mode label { display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px;
                font-weight: 500; font-size: 14px; cursor: pointer; }
  .mode label + label { border-top: 1px solid #e0e4e8; }
  .mode label input { margin-top: 3px; }
  .mode .desc { display: block; font-weight: 400; color: #5b6470; font-size: 12px; margin-top: 2px; }
  .field label { display: block; font-weight: 600; font-size: 14px; margin: 16px 0 6px; }
  select { width: 100%; padding: 12px; font-size: 16px; border: 1px solid #cbd2d9;
           border-radius: 8px; background: #fff; }
  button { width: 100%; margin-top: 24px; padding: 14px; font-size: 16px; font-weight: 700;
           color: #fff; background: #c8102e; border: none; border-radius: 8px; cursor: pointer; }
  button:hover { background: #a50d26; }
  button:disabled { background: #cbd2d9; cursor: not-allowed; }
  .count { text-align: center; color: #5b6470; font-size: 13px; margin-top: 14px; min-height: 18px; }
  .hint { font-size: 13px; color: #5b6470; background: #f0f4ff; border-left: 3px solid #3b6fe0;
          padding: 10px 12px; border-radius: 6px; margin-top: 20px; }
  .foot { margin-top: 22px; font-size: 12px; color: #9aa1a9; text-align: center; }
  .disclaimer { margin-top: 16px; font-size: 12px; color: #8a6d1a; background: #fff8e1;
                border: 1px dashed #e0c068; border-radius: 8px; padding: 10px 12px; text-align: center; }
  .thanks { margin-bottom: 22px; padding: 20px 16px; border-radius: 12px; text-align: center;
            background: linear-gradient(135deg, #c8102e, #ff5e7e); color: #fff;
            box-shadow: 0 6px 20px rgba(200, 16, 46, .35);
            animation: hero-pop .8s cubic-bezier(.175,.885,.32,1.275) both; }
  .thanks-title { font-size: 30px; font-weight: 900; letter-spacing: .5px; text-shadow: 0 2px 6px rgba(0,0,0,.2); }
  .thanks-sub { font-size: 13px; margin-top: 6px; opacity: .92; }
  .confetti { position: fixed; top: -14px; width: 10px; height: 14px; z-index: 9999;
              animation: fall 2.4s linear forwards; pointer-events: none; }
  @keyframes fall { to { transform: translateY(110vh) rotate(720deg); opacity: .6; } }
</style>
</head>
<body>
<div class="card">
  <div class="thanks" id="thanks" hidden>
    <div class="thanks-title">Dankjewel, Johannes!</div>
    <div class="thanks-sub">Your calendar is on its way. May your attendance be statistically significant.</div>
  </div>
  <h1>Psychology — Bachelor, year 1</h1>
  <p class="sub">Pick your groups and download a calendar with only <em>your</em> practicals.</p>

  <div class="mode">
    <label>
      <input type="radio" name="mode" value="full" checked>
      <span>Full calendar<span class="desc">Everything from today on — lectures, exams and my practicals.</span></span>
    </label>
    <label>
      <input type="radio" name="mode" value="practical">
      <span>Only my Statistics IB practicals<span class="desc">If you already have a calendar and are just missing the IB tutorials.</span></span>
    </label>
  </div>

  <div class="field">
    <label for="letter">Statistics IB group</label>
    <select id="letter"></select>
  </div>

  <div class="field" id="numberField">
    <label for="number">Practical group (Academic Skills &amp; Research Methods)</label>
    <select id="number"></select>
  </div>

  <button id="download" disabled>Download my calendar (.ics)</button>
  <div class="count" id="count"></div>

  <div class="hint">
    Not sure of your groups? They look like <b>GR-N</b> (Statistics IB) and <b>GR2610</b> (practical)
    and are shown on Brightspace.
  </div>

  <div class="foot">Download the .ics file, then double-click it to add it to your calendar app.</div>
  <div class="disclaimer">No psychologists were harmed in the making of this calendar.<br>One statistician was mildly inconvenienced.</div>
</div>

<script>
const DATA = __DATA__;

const letterSel = document.getElementById("letter");
const numberSel = document.getElementById("number");
const numberField = document.getElementById("numberField");
const downloadBtn = document.getElementById("download");
const countEl = document.getElementById("count");
const thanksEl = document.getElementById("thanks");
const modeRadios = document.querySelectorAll('input[name="mode"]');

function confetti() {
  for (let i = 0; i < 90; i++) {
    const d = document.createElement("div");
    d.className = "confetti";
    d.style.left = Math.random() * 100 + "vw";
    d.style.background = `hsl(${Math.random() * 360}, 80%, 60%)`;
    d.style.animationDelay = Math.random() * 0.5 + "s";
    d.style.width = (6 + Math.random() * 8) + "px";
    d.style.height = (8 + Math.random() * 8) + "px";
    document.body.appendChild(d);
    setTimeout(() => d.remove(), 3000);
  }
}

function fill(sel, groups) {
  const none = document.createElement("option");
  none.value = "";
  none.textContent = "Choose your group…";
  none.disabled = true;
  none.selected = true;
  sel.appendChild(none);
  for (const g of groups) {
    const o = document.createElement("option");
    o.value = g;
    o.textContent = g.replace(/[[\]]/g, "");
    sel.appendChild(o);
  }
}

fill(letterSel, DATA.ib_letters);
fill(numberSel, DATA.number_groups);

function todayStr() {
  const d = new Date();
  return d.getFullYear() + String(d.getMonth() + 1).padStart(2, "0") + String(d.getDate()).padStart(2, "0");
}

function mode() {
  for (const r of modeRadios) if (r.checked) return r.value;
  return "full";
}

function groupMarker(summary) {
  const m = summary.match(/\[GR[^\]]*\]/);
  return m ? m[0] : null;
}
function isLetter(marker) { return /^\[GR-[A-Z]\]$/.test(marker); }

function keepEvent(summary, date, letter, number, m) {
  const marker = groupMarker(summary);
  if (m === "practical") {
    return summary.indexOf("Statistics IB") !== -1 &&
           summary.indexOf("Computer practical") !== -1 &&
           marker === letter;
  }
  if (date < todayStr()) return false;
  if (!marker) return true;
  if (isLetter(marker)) {
    return summary.indexOf("Statistics IB") !== -1 && marker === letter;
  }
  return marker === number;
}

function refresh() {
  const letter = letterSel.value;
  const number = numberSel.value;
  const m = mode();
  numberField.style.display = m === "full" ? "" : "none";
  const ready = m === "full" ? (letter !== "" && number !== "") : (letter !== "");
  downloadBtn.disabled = !ready;
  if (!ready) {
    countEl.textContent = m === "full" ? "Choose both groups to continue." : "Choose your Statistics IB group.";
    return;
  }
  let n = 0;
  for (const [summary, date] of DATA.events) {
    if (keepEvent(summary, date, letter, number, m)) n++;
  }
  countEl.textContent = m === "full"
    ? `${n} events will be in your calendar (from today).`
    : `${n} practical sessions will be added.`;
}

for (const r of modeRadios) r.addEventListener("change", refresh);
letterSel.addEventListener("change", refresh);
numberSel.addEventListener("change", refresh);

downloadBtn.addEventListener("click", () => {
  const letter = letterSel.value;
  const number = numberSel.value;
  const m = mode();
  const parts = [DATA.header];
  for (const [summary, date, block] of DATA.events) {
    if (keepEvent(summary, date, letter, number, m)) parts.push(block);
  }
  parts.push(DATA.footer);
  const ics = parts.join("\n");

  const name = m === "full"
    ? "rug-schedule-" + letter.replace(/[[\]]/g, "") + "-" + number.replace(/[[\]]/g, "") + ".ics"
    : "rug-statistics-ib-" + letter.replace(/[[\]]/g, "") + ".ics";
  const blob = new Blob([ics], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  thanksEl.hidden = false;
  thanksEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  confetti();
});

refresh();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
