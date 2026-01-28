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
  const data = (tabMode === "cfp" ? cfp : dates)
    .filter(d => rank === "All" || d.core_rank === rank);

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

window.onload = load;
