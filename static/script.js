document.addEventListener('DOMContentLoaded', () => {
  const scheduleList    = document.getElementById('scheduleList');
  const addEntryBtn     = document.getElementById('addEntry');
  const calcForm        = document.getElementById('calcForm');
  const resultsCtx      = document.getElementById('resultsChart').getContext('2d');
  const resultsTable    = document.getElementById('resultsTable');
  const averageDiv      = document.getElementById('averageCO2');
  const downloadBtn     = document.getElementById('downloadReport');
  let chart;

  function addEntry(speciesId = null, year = 1, trees = 1000) {
    const entry = document.createElement('div');
    entry.className = 'entry d-flex gap-2 mb-2';

    // build species dropdown
    let opts = '';
    window.SPECIES_LIST.forEach(sp => {
      opts += `<option value="${sp.species_id}"
               ${sp.species_id === speciesId ? 'selected' : ''}>
                ${sp.species_name}
              </option>`;
    });

    entry.innerHTML = `
      <select name="species_id" class="form-select">${opts}</select>
      <input name="year"  type="number" class="form-control"
             placeholder="Year"  min="1" value="${year}" required>
      <input name="trees" type="number" class="form-control"
             placeholder="Trees" min="1" value="${trees}" required>
      <button type="button" class="btn btn-outline-danger remove">&times;</button>
    `;
    scheduleList.appendChild(entry);

    entry.querySelector('.remove').onclick = () => entry.remove();
  }

  // initial row
  addEntry();
  addEntryBtn.onclick = () => addEntry();

  calcForm.onsubmit = async e => {
    e.preventDefault();
    const project_years = +document.getElementById('projectYears').value;
    const planting_schedule = Array.from(scheduleList.children).map(ent => ({
      species_id: ent.querySelector('[name=species_id]').value,
      year:       +ent.querySelector('[name=year]').value,
      trees:      +ent.querySelector('[name=trees]').value
    }));

    const backendUrl = 'https://new-carbon-calculator.onrender.com';
    const res = await fetch(`${backendUrl}/calculate`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({project_years, planting_schedule})
    });
    if (!res.ok) {
      return alert('Calculation failed:\n'+await res.text());
    }
    const {yearly_data, average_co2e} = await res.json();
    renderChart(yearly_data);
    renderTable(yearly_data);
    averageDiv.textContent = `Average annual CO₂e: ${average_co2e.toFixed(3)} t`;
  };

  function renderChart(data) {
    const labels = data.map(r=>r.project_year);
    const co2e   = data.map(r=>r.co2e_total);
    if (chart) chart.destroy();
    chart = new Chart(resultsCtx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Annual CO₂e (t)',
          data: co2e,
          borderColor: '#198754',
          backgroundColor:'rgba(25,135,84,0.2)',
          tension:0.3
        }]
      },
      options:{responsive:true}
    });
  }

  function renderTable(data) {
    resultsTable.innerHTML = '';
    data.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${r.project_year}</td>
        <td>${r.annual_agb.toFixed(2)}</td>
        <td>${r.annual_bgb.toFixed(2)}</td>
        <td>${r.annual_biomass.toFixed(2)}</td>
        <td>${r.co2e_total.toFixed(2)}</td>
        <td>${r.cumulative_co2e.toFixed(2)}</td>
      `;
      resultsTable.appendChild(tr);
    });
  }

  downloadBtn.onclick = async () => {
    const project_years = +document.getElementById('projectYears').value;
    const planting_schedule = Array.from(scheduleList.children).map(ent => ({
      species_id: ent.querySelector('[name=species_id]').value,
      year:       +ent.querySelector('[name=year]').value,
      trees:      +ent.querySelector('[name=trees]').value
    }));

    const backendUrl = 'https://new-carbon-calculator.onrender.com';
    const res = await fetch(`${backendUrl}/download_report`, {
      method: 'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({project_years, planting_schedule})
    });
    if (!res.ok) {
      return alert('Report download failed:\n'+await res.text());
    }
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = 'carbon_report_all_species.xlsx';
    a.click();
    URL.revokeObjectURL(url);
  };
});
