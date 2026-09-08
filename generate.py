#!/usr/bin/env python3
"""Generate a self-contained web page that lets students pick their
practical groups and download a personalized .ics calendar.

Usage:
    python3 generate.py <source.ics> [output.html]

The source is the RUG Maat schedule feed (text/calendar)."""

import json
import re
import sys


def parse(raw: str):
    events = re.findall(r"BEGIN:VEVENT.*?END:VEVENT", raw, re.DOTALL)
    header = raw[: raw.find("BEGIN:VEVENT")].rstrip("\n") + "\n"
    footer = "\n" + raw[raw.rfind("END:VEVENT") + len("END:VEVENT") :].lstrip("\n")
    return header, events, footer


def desc_of(event: str) -> str:
    m = re.search(r"^DESCRIPTION[^:]*:(.*)$", event, re.M)
    return m.group(1).strip() if m else ""


def natural_key(value: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", value)]


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "/tmp/schedule.raw"
    out = sys.argv[2] if len(sys.argv) > 2 else "index.html"

    raw = open(src, encoding="utf-8", errors="replace").read().replace("\r\n", "\n")

    header, events, footer = parse(raw)
    data = [[desc_of(e), e] for e in events]

    letter_groups = sorted(
        {d for d, _ in data if re.fullmatch(r"\[GR-[A-Z]\]", d)}, key=natural_key
    )
    number_groups = sorted(
        {d for d, _ in data if re.fullmatch(r"\[GR\d{4}\]", d)}, key=natural_key
    )

    payload = {
        "header": header,
        "events": data,
        "footer": footer,
        "letter_groups": letter_groups,
        "number_groups": number_groups,
    }

    js = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    html = TEMPLATE.replace("__DATA__", js)

    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"wrote {out}")
    print(f"  events: {len(events)}")
    print(f"  letter groups: {len(letter_groups)}")
    print(f"  number groups: {len(number_groups)}")


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
  h1 { font-size: 22px; margin: 0 0 6px; }
  p.sub { color: #5b6470; font-size: 14px; margin: 0 0 24px; }
  label { display: block; font-weight: 600; font-size: 14px; margin: 18px 0 6px; }
  select { width: 100%; padding: 12px; font-size: 16px; border: 1px solid #cbd2d9;
           border-radius: 8px; background: #fff; }
  button { width: 100%; margin-top: 28px; padding: 14px; font-size: 16px; font-weight: 700;
           color: #fff; background: #c8102e; border: none; border-radius: 8px; cursor: pointer; }
  button:hover { background: #a50d26; }
  button:disabled { background: #cbd2d9; cursor: not-allowed; }
  .count { text-align: center; color: #5b6470; font-size: 13px; margin-top: 14px; min-height: 18px; }
  .hint { font-size: 13px; color: #5b6470; background: #f0f4ff; border-left: 3px solid #3b6fe0;
          padding: 10px 12px; border-radius: 6px; margin-top: 20px; }
  .foot { margin-top: 22px; font-size: 12px; color: #9aa1a9; text-align: center; }
  .tagline { font-size: 13px; color: #8a6d1a; background: #fff8e1; border-radius: 6px;
             padding: 8px 12px; margin-top: 16px; text-align: center; transition: opacity .4s; }
  .thanks { margin-top: 22px; padding: 20px 16px; border-radius: 12px; text-align: center;
            background: #e8f5e9; border: 2px dashed #66bb6a; animation: pop .5s ease; }
  .thanks-title { font-size: 22px; font-weight: 800; color: #2e7d32; }
  .thanks-sub { font-size: 13px; color: #558b2f; margin-top: 6px; }
  .confetti { position: fixed; top: -14px; width: 10px; height: 14px; z-index: 9999;
              animation: fall 2.4s linear forwards; pointer-events: none; }
  @keyframes fall { to { transform: translateY(110vh) rotate(720deg); opacity: .6; } }
  @keyframes pop { 0% { transform: scale(.8); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }
</style>
</head>
<body>
<div class="card">
  <h1>Psychology — Bachelor, year 1</h1>
  <p class="sub">Pick your groups and download a calendar with only <em>your</em> practicals
  (plus all lectures that are for everyone).</p>
  <div class="tagline" id="tagline">Loading wit…</div>

  <label for="letter">Statistics Ia computer practical group</label>
  <select id="letter"></select>

  <label for="number">Academic Skills practical group</label>
  <select id="number"></select>

  <button id="download" disabled>Download my calendar (.ics)</button>
  <div class="count" id="count"></div>

  <div class="hint">
    Not sure of your groups? They look like <b>GR-L</b> (letter) and <b>GR2610</b> (number)
    and are shown on Brightspace.
  </div>

  <div class="foot">Download the .ics file, then double-click it to add it to your calendar app.</div>

  <div class="thanks" id="thanks" hidden>
    <div class="thanks-title">Denkjewel, Johannes!</div>
    <div class="thanks-sub">Your calendar is on its way. May your attendance be statistically significant.</div>
  </div>
</div>

<script>
const DATA = __DATA__;

const letterSel = document.getElementById("letter");
const numberSel = document.getElementById("number");
const downloadBtn = document.getElementById("download");
const countEl = document.getElementById("count");
const taglineEl = document.getElementById("tagline");
const thanksEl = document.getElementById("thanks");

const WISDOM = [
  "Your superego fully approves of this calendar.",
  "Freud would have a lot to say about how tidy this is.",
  "Correlation with actually attending lectures: r = 1.00.",
  "No statistics were harmed in the making of this calendar.",
  "Warning: may cause you to know where you're supposed to be.",
  "Clinically reviewed by the id, the ego & the superego.",
  "Free will not included. Please attend the lecture to find out why.",
  "This timetable was not repressed. Mostly.",
  "100% of students who use a calendar also experience time.",
];

let wi = 0;
function rotateWisdom() {
  taglineEl.style.opacity = 0;
  setTimeout(() => {
    taglineEl.textContent = WISDOM[wi % WISDOM.length];
    taglineEl.style.opacity = 1;
    wi++;
  }, 400);
}
taglineEl.textContent = WISDOM[0];
setInterval(rotateWisdom, 4500);

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

fill(letterSel, DATA.letter_groups);
fill(numberSel, DATA.number_groups);

function refresh() {
  const letter = letterSel.value;
  const number = numberSel.value;
  const ready = letter !== "" && number !== "";
  downloadBtn.disabled = !ready;
  if (!ready) {
    countEl.textContent = "Choose both groups to continue.";
    return;
  }
  let n = 0;
  for (const [desc] of DATA.events) {
    if (desc.startsWith("[GR")) {
      if (desc === letter || desc === number) n++;
    } else {
      n++;
    }
  }
  countEl.textContent = `${n} events will be in your calendar.`;
}

letterSel.addEventListener("change", refresh);
numberSel.addEventListener("change", refresh);

downloadBtn.addEventListener("click", () => {
  const letter = letterSel.value;
  const number = numberSel.value;
  const parts = [DATA.header];
  for (const [desc, block] of DATA.events) {
    if (desc.startsWith("[GR")) {
      if (desc === letter || desc === number) parts.push(block);
    } else {
      parts.push(block);
    }
  }
  parts.push(DATA.footer);
  const ics = parts.join("\n");

  const name = "rug-schedule" +
    (letter ? "-" + letter.replace(/[[\]]/g, "") : "") +
    (number ? "-" + number.replace(/[[\]]/g, "") : "") +
    ".ics";
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
