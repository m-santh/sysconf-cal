let tabMode = "cfp";
let cfp = [];
let dates = [];

async function load() {
  cfp = await fetch("generated/cfp.json").then(r => r.json());
  dates = await fetch("generated/confdates.json").then(r => r.json());
  render();
}

function tab(t) {
  tabMode = t;
  render();
}

function render() {
  const rank = document.getElementById("rank").value;
  const sortOrder = document.getElementById("sort")?.value || "asc";
  const ascending = sortOrder === "asc";

  let data = (tabMode === "cfp" ? cfp : dates)
    .filter(d => rank === "All" || d.core_rank === rank);

  // 🔹 Apply sorting ONLY for CFP tab
  if (tabMode === "cfp") {
    data = sortByCFP(data, ascending);
  }

  let html = "<table><tr>";
  html += Object.keys(data[0] || {}).map(k => `<th>${k}</th>`).join("");
  html += "</tr>";

  data.forEach(d => {
    html += "<tr>";
    Object.values(d).forEach(v => html += `<td>${v}</td>`);
    html += "</tr>";
  });

  html += "</table>";
  document.getElementById("content").innerHTML = html;
}


function parseCFPDate(dateStr) {
  if (!dateStr || dateStr === "TBA") return null;
  dateStr = dateStr.replace("(AoE)", "").trim();

  const d = new Date(dateStr);
  return isNaN(d.getTime()) ? null : d;
}
function sortByCFP(data, ascending) {
  return data.slice().sort((a, b) => {
    const da = parseCFPDate(a.cfp_deadline);
    const db = parseCFPDate(b.cfp_deadline);

    if (!da && !db) return 0;
    if (!da) return ascending ? 1 : -1;
    if (!db) return ascending ? -1 : 1;

    return ascending ? da - db : db - da;
  });
}

window.onload = load;
