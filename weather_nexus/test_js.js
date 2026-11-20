
/* ── Plotly base layout ── */
const DARK = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor:  '#12122a',
  font: { family: 'Outfit, sans-serif', color: '#dde1f0', size: 12 },
  margin: { l: 50, r: 30, t: 40, b: 50 },
  colorway: ['#4facfe','#f6d365','#ff6b6b','#00c9a7','#f093fb','#51cf66'],
  xaxis: { gridcolor: '#1e2040' },
  yaxis: { gridcolor: '#1e2040' },
};

function layout(extra) { return Object.assign({}, DARK, extra); }
const CFG = { responsive: true, displayModeBar: false };

/* ── Populate sidebar selects (read from data island) ── */
const _DJ = JSON.parse(document.getElementById('djData').textContent);
const AQI_CITIES   = _DJ.aqi_cities;
const W_CITIES     = _DJ.w_cities;
const REGIONS      = _DJ.regions;
const DEFAULT_CITY  = _DJ.default_city;
const DEFAULT_WCITY = _DJ.default_wcity;

function populateSel(id, items, defaultVal) {
  const sel = document.getElementById(id);
  sel.innerHTML = '';
  items.forEach(c => {
    const o = document.createElement('option');
    o.value = o.text = c;
    if (+c === +defaultVal) o.selected = true;
    sel.appendChild(o);
  });
}

function populateChecks(id, items, preselectCount=0) {
  const cont = document.getElementById(id);
  cont.innerHTML = '';
  items.forEach((v, i) => {
    const lbl = document.createElement('label');
    lbl.className = 'check-item';
    lbl.innerHTML = `<input type="checkbox" value="${v}" ${i < preselectCount ? 'checked' : ''} onchange="applyFilters()"> ${v}`;
    cont.appendChild(lbl);
  });
}

const YEARS = Array.from({length: _DJ.year_max - _DJ.year_min + 1}, (_, i) => i + _DJ.year_min);

populateSel('selGlobalCity', AQI_CITIES, DEFAULT_CITY);
populateSel('selYearStart',  YEARS,      _DJ.year_min);
populateSel('selYearEnd',    YEARS,      _DJ.year_max);
populateChecks('checkRegions', REGIONS, 5);

/* ── Tab switching ── */
function switchTab(id, btn) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');

  // Sidebar Intelligence
  const citySect = document.getElementById('filter-city');
  const yearSect = document.getElementById('filter-years');
  const regSect  = document.getElementById('filter-regions');

  if (id === 'tab1') {
    citySect.style.display = 'block';
    yearSect.style.display = 'block';
    regSect.style.display  = 'none';
  } else if (id === 'tab2' || id === 'tab3') {
    citySect.style.display = 'block';
    yearSect.style.display = 'none';
    regSect.style.display  = 'none';
  } else if (id === 'tab4') {
    citySect.style.display = 'none';
    yearSect.style.display = 'none';
    regSect.style.display  = 'block';
  }

  // Trigger resize to fix potentially hidden chart layout issues
  const chartId = id === 'tab1' ? 'chartAqiTs' : id === 'tab2' ? 'chartPollCorr' : id === 'tab3' ? 'chartComp' : 'chartMacro';
  Plotly.relayout(chartId, {});
}

/* ── Fetch helpers ── */
async function fetchJSON(url) {
  const r = await fetch(url);
  return r.json();
}

/* ── KPI bootstrap via weather/regional API ── */
async function loadKPIs() {
  const city = document.getElementById('selGlobalCity').value;
  const d = await fetchJSON(`/api/weather/?city=${encodeURIComponent(city)}`);
  
  const setV = (id, val, unit='') => {
     const el = document.getElementById(id);
     if (el) el.textContent = (val !== null && val !== undefined) ? val + unit : '—';
  };

  // Header
  setV('headerCities', AQI_CITIES.length);
  setV('headerTemp',   d.gauges?.temp, '°C');
  setV('headerHum',    d.gauges?.humidity, '%');
  setV('headerPm',     d.gauges?.pm2_5);

  // Tab 3
  setV('tabKpiTemp',   d.gauges?.temp, '°C');
  setV('tabKpiHum',    d.gauges?.humidity, '%');
  setV('tabKpiPm25',   d.gauges?.pm2_5);
  setV('tabKpiWind',   d.gauges?.wind, ' kmh');
}

/* ══════════════════════════════════════════════════════
   TAB 1 — AQI TRENDS
══════════════════════════════════════════════════════ */
async function loadAqiTrends() {
  const city = document.getElementById('selGlobalCity').value;
  const y1   = +document.getElementById('selYearStart').value;
  const y2   = +document.getElementById('selYearEnd').value;
  const d    = await fetchJSON(`/api/aqi/?city=${encodeURIComponent(city)}&y1=${Math.min(y1,y2)}&y2=${Math.max(y1,y2)}`);
  window.lastAqi = d;

  const AQI_COLOR = {
    'Good':'#00e400','Satisfactory':'#92d050','Moderate':'#ffff00',
    'Poor':'#ff7e00','Very Poor':'#ff0000','Severe':'#7e0023'
  };
  const buckets = [...new Set(d.ts.map(r=>r.bucket))];

  /* Chart 1: time-series + SMA + Forecast + WHO Line */
  const traces1 = buckets.map(b => ({
    type:'scatter', mode:'markers', name: b,
    x: d.ts.filter(r=>r.bucket===b).map(r=>r.date),
    y: d.ts.filter(r=>r.bucket===b).map(r=>r.aqi),
    marker:{ color: AQI_COLOR[b]||'#888', size:4, opacity:.5 },
  }));

  // 7-day Rolling SMA
  if (d.sma && d.sma.length) {
    traces1.push({
      type:'scatter', mode:'lines', name:'7d Moving Avg',
      x: d.ts.map(r=>r.date), y: d.sma,
      line:{ color:'#4facfe', width:2, dash:'dash' },
      opacity:.8
    });
  }

  // Statistical Forecast
  if (d.forecast && d.forecast.length) {
    const lastDate = d.ts[d.ts.length-1].date;
    const fDates = d.forecast.map((_,i) => {
        let dc = new Date(lastDate);
        dc.setDate(dc.getDate() + i + 1);
        return dc.toISOString().split('T')[0];
    });
    traces1.push({
      type:'scatter', mode:'lines', name:'7d Forecast',
      x: fDates, y: d.forecast,
      line:{ color:'#00f2fe', width:2, dash:'dot' }
    });
  }

  Plotly.newPlot('chartAqiTs', traces1, layout({
    title:{ text:`AQI Evolution: ${city}`, font:{size:14} },
    xaxis:{ rangeslider:{visible:true} },
    yaxis:{ title:'AQI' },
    shapes: [{
      type: 'line', yref: 'y', y0: 50, y1: 50, x0: 0, x1: 1, xref: 'paper',
      line: { color: '#ff4b2b', width: 1, dash: 'dash' }
    }]
  }), CFG);

  /* Chart 2: monthly bar */
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  Plotly.newPlot('chartMonthly', [{
    type:'bar', x: d.monthly.map(r=>MONTHS[r.month-1]), y: d.monthly.map(r=>r.avg_aqi),
    marker:{ color: d.monthly.map(r=>r.avg_aqi), colorscale:'YlOrRd' },
  }], layout({ title:'Seasonal Seasonality', height:380 }), CFG);

  /* Chart 3: heatmap */
  const years  = [...new Set(d.heat.map(r=>r.year))].sort();
  if (years.length === 0) {
    document.getElementById('chartHeat').innerHTML = '<div class="spinner">No heatmap data for this range</div>';
  } else {
    const zMatrix = MONTHS.map((_, mi) =>
      years.map(yr => {
        const hit = d.heat.find(r => r.year === yr && r.month === (mi + 1));
        return hit ? hit.avg_aqi : null;
      })
    );
    Plotly.newPlot('chartHeat', [{
      type: 'heatmap', z: zMatrix, x: years, y: MONTHS, 
      colorscale: 'RdYlGn', reversescale: true, zmin: 0, zmax: 400,
      connectgaps: true
    }], layout({ title: 'Year × Month Density', height: 380 }), CFG);
  }

  /* Update Report */
  const r = d.report;
  document.getElementById('reportAqi').innerHTML = `
    🔥 <b>EXPERT INSIGHTS:</b><br/>
    Span average is <b>${r.avg || '—'}</b>. Trend is <b>${r.trend_label || '—'}</b>.
    WHO Threshold (50) was breached during <b>${r.who_who_breach_pct || 0}%</b> of the observation span.
  `;
}

/* ══════════════════════════════════════════════════════
   TAB 2 — POLLUTANTS
══════════════════════════════════════════════════════ */
async function loadPollutants() {
  const city = document.getElementById('selGlobalCity').value;
  const d = await fetchJSON(`/api/pollutants/?city=${encodeURIComponent(city)}`);
  window.lastPoll = d;

  /* Chart 0: Dominant Pollutants Bar */
  try {
      const meanKeys = Object.keys(d.means || {});
      const meanVals = Object.values(d.means || {});
      if (meanKeys.length === 0) {
        document.getElementById('chartPollBar').innerHTML = '<div class="spinner">No pollutant data</div>';
      } else {
        Plotly.newPlot('chartPollBar', [{
          type: 'bar', x: meanKeys, y: meanVals,
          marker: { color: meanVals, colorscale: 'YlOrRd', showscale: false },
          text: meanVals, textposition: 'auto'
        }], layout({ title: 'Mean Concentrations', height: 400 }), CFG);
      }
  } catch (e) {
      console.error("PollBar Error:", e);
      document.getElementById('chartPollBar').innerHTML = `<div style="color:red">Error: ${e.message}</div>`;
  }


  /* Chart 1: Heatmap Correlation */
  try {
      const corrKeys = Object.keys(d.corr || {});
      if (corrKeys.length === 0) {
        document.getElementById('chartCorrHeat').innerHTML = '<div class="spinner">Insufficient data for correlation</div>';
      } else {
        const corrZ = corrKeys.map(k1 => corrKeys.map(k2 => d.corr[k1][k2] || 0));
        Plotly.newPlot('chartCorrHeat', [{
          type:'heatmap', z:corrZ, x:corrKeys, y:corrKeys, colorscale:'RdBu', reversescale:true, zmin:-1, zmax:1
        }], layout({ title:'Pollutant Synergy Matrix', height:380 }), CFG);
      }
  } catch (e) {
      console.error("CorrHeat Error:", e);
      document.getElementById('chartCorrHeat').innerHTML = `<div style="color:red">Error: ${e.message}</div>`;
  }

  /* Chart 2: PM2.5 Box Plot & Stacked Risk Bar */
  try {
      if (d.box && d.box.max !== undefined) {
        Plotly.newPlot('chartPollBox', [{
          type: 'box', y: [d.box.min, d.box.q1, d.box.med, d.box.q3, d.box.max],
          name: 'PM2.5 Distribution', marker:{color:'#4facfe'}
        }], layout({ title:'Winter Variance', height:400, showlegend:false }), CFG);
      }
  } catch(e) {
      console.error("PollBox Error:", e);
      document.getElementById('chartPollBox').innerHTML = `<div style="color:red">Error: ${e.message}</div>`;
  }

  try {
      const riskColors = {
        'Good':'#00e400','Satisfactory':'#92d050','Moderate':'#ffff00',
        'Poor':'#ff7e00','Very Poor':'#ff0000','Severe':'#7e0023'
      };
      const riskTraces = (d.buckets || []).map(b => ({
        type:'bar', orientation:'h', name:b.bucket,
        x:[b.count], y:['AQI History'], marker:{color:riskColors[b.bucket] || '#888'}
      }));
      if (riskTraces.length) {
        Plotly.newPlot('chartRiskBar', riskTraces, layout({
          title:'Ordinal Health Sequence', height:400, barmode:'stack', showlegend:false,
          xaxis:{visible:false}, yaxis:{visible:false}
        }), CFG);
      }
  } catch(e) {
      console.error("RiskBar Error:", e);
      document.getElementById('chartRiskBar').innerHTML = `<div style="color:red">Error: ${e.message}</div>`;
  }

  try {
      document.getElementById('reportPoll').innerHTML = `
        🧪 <b>CHEMICAL AUDIT:</b> Dominant pollutant is <b>${d.report.top_pollutant}</b>. 
        Health risk breach frequency: <b>${d.report.risk_pct}%</b>.
      `;
  } catch(e) {
      console.error("Report Error:", e);
  }
}

async function loadWeather() {
  const city = document.getElementById('selGlobalCity').value;
  const d = await fetchJSON(`/api/weather/?city=${encodeURIComponent(city)}`);
  window.lastWeather = d;

  if (!d.gauges) return;
  
  // Tab 3 text updates (using new safe IDs)
  const setV = (id, val, unit='') => {
     const el = document.getElementById(id);
     if (el) el.textContent = (val !== null && val !== undefined) ? val + unit : '—';
  };
  setV('tabKpiTemp',   d.gauges.temp, '°C');
  setV('tabKpiHum',    d.gauges.humidity, '%');
  setV('tabKpiPm25',   d.gauges.pm2_5);
  setV('tabKpiWind',   d.gauges.wind, ' kmh');

  /* Chart 2: chem bar */
  const chemK = Object.keys(d.chem || {});
  const chemV = Object.values(d.chem || {});
  if (chemK.length) {
    Plotly.newPlot('chartChem', [{
      type:'bar', x:chemK, y:chemV,
      marker:{ color:chemV, colorscale:'Plasma', showscale:true, colorbar:{title:'Level'} },
      text: chemV.map(v=>`${v}`), textposition:'outside',
    }], layout({ title:'Current Chemical Composition', height:380,
                 xaxis:{ gridcolor:'#1e2040' },
                 yaxis:{ title:'Concentration', gridcolor:'#1e2040' } }), CFG);
  }

  /* Chart 3: city vs region avg */
  const cmp = d.comparison;
  if (cmp && cmp.metrics) {
    Plotly.newPlot('chartComp', [
      { type:'bar', name:city, x:cmp.metrics, y:cmp.city, marker:{color:'#4facfe'} },
      { type:'bar', name:`${cmp.region_name} Avg`, x:cmp.metrics, y:cmp.region_avg, marker:{color:'#ff6b6b'} },
    ], layout({ barmode:'group', title:`${city} vs Regional Average`, height:380,
                yaxis:{ gridcolor:'#1e2040' }, xaxis:{ gridcolor:'#1e2040' } }), CFG);
  }

  /* Update Report */
  const r = d.report;
  document.getElementById('reportWeather').innerHTML = `
    🌤️ <b>WEATHER BENCHMARK:</b><br/>
    Currently, ${city} has a PM2.5 level that is <b>${r.pm_diff} μg/m³ ${r.verdict}</b> 
    than the average for the <b>${r.region}</b> region. 
    Current climate: <b>${d.gauges.condition}</b>.
  `;
}

async function loadRegional() {
  const regions = Array.from(document.querySelectorAll('#checkRegions input:checked')).map(i=>i.value);
  if (!regions.length) return;
  const params  = regions.map(r=>`regions=${encodeURIComponent(r)}`).join('&');
  const d = await fetchJSON(`/api/regional/?${params}`);
  window.lastReg = d;

  /* Chart 1: Regional Macro Metrics */
  Plotly.newPlot('chartMacro', [
    { type:'bar', name:'Avg Temp (°C)',    x:d.macro.map(r=>r.region), y:d.macro.map(r=>r.avg_temp),     marker:{color:'#f6d365'} },
    { type:'bar', name:'Avg Humidity (%)', x:d.macro.map(r=>r.region), y:d.macro.map(r=>r.avg_humidity), marker:{color:'#4facfe'} },
    { type:'bar', name:'Avg PM2.5',        x:d.macro.map(r=>r.region), y:d.macro.map(r=>r.avg_pm25),     marker:{color:'#ff6b6b'} },
  ], layout({ barmode:'group', title:'Regional Climatology Breakdown', height:420 }), CFG);

  /* NEW Chart 2: Northern India Mapbox Hotspots */
  const mapTraces = [{
    type: 'scattermapbox',
    lat: d.map_data.map(r=>r.lat),
    lon: d.map_data.map(r=>r.lon),
    mode: 'markers',
    marker: {
      size: d.map_data.map(r=>Math.min(20, 8 + (r.pm25/15))),
      color: d.map_data.map(r=>r.pm25),
      colorscale: 'YlOrRd', showscale: true,
      colorbar: { title: 'PM2.5', thickness: 15, len: 0.5, font:{color:'#eee'} }
    },
    text: d.map_data.map(r=>`${r.city}<br>PM2.5: ${r.pm25}<br>${r.condition}`),
    hoverinfo: 'text'
  }];
  Plotly.newPlot('chartMap', mapTraces, layout({
    mapbox: { style:'carto-darkmatter', center:{lat:28.6, lon:77.2}, zoom:4.5 },
    title: { text:'Northern India Pollution Hotspots', font:{color:'#eee'} },
    margin: { t:50, b:0, l:0, r:0 }, height:550
  }), CFG);

  /* Chart 3: Top 10 polluted */
  const t = [...d.top10].sort((a,b)=>b.avg_aqi-a.avg_aqi);
  Plotly.newPlot('chartTop10', [{
    type:'bar', orientation:'h',
    y: t.map(r=>r.city).reverse(), x: t.map(r=>r.avg_aqi).reverse(),
    marker:{ color:t.map(r=>r.avg_aqi).reverse(), colorscale:'Hot', reversescale:true },
    text: t.map(r=>r.avg_aqi.toFixed(0)).reverse(), textposition:'outside'
  }], layout({ title:'Historical National Rankings', height:420 }), CFG);

  /* Update Report */
  const r = d.report;
  document.getElementById('reportReg').innerHTML = `
    ⚖️ <b>REGIONAL BENCHMARK:</b><br/>
    Analyzed <b>${r.count}</b> monitoring clusters. The <b>${r.most_polluted}</b> region exhibits the highest mean intensity.
  `;
}

async function applyFilters() {
  document.getElementById('globalDetailedReport').innerHTML = '<div class="spinner">⚙️ Synthesizing cross-domain data...</div>';
  await Promise.all([loadAqiTrends(), loadPollutants(), loadWeather(), loadRegional(), loadKPIs()]);
  synthesizeGlobalReport();
}

function synthesizeGlobalReport() {
  if (!window.lastAqi || !window.lastPoll || !window.lastWeather || !window.lastReg) return;
  const a = window.lastAqi.report;
  const p = window.lastPoll.report;
  const w = window.lastWeather.report;
  const r = window.lastReg.report;
  const city = document.getElementById('selGlobalCity').value;

  document.getElementById('globalDetailedReport').innerHTML = `
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:30px;">
      <div style="background:rgba(255,255,255,0.03); padding:20px; border-radius:12px; border-left:4px solid var(--accent);">
        <h4 style="color:var(--accent); margin-bottom:10px;">📉 Trend & Risk Profile</h4>
        <p><b>${city}</b> shows an <b>${a.trend_label}</b> trend. WHO Threshold breach: <b>${a.who_who_breach_pct}%</b> days. 
        Predominant chemical threat: <b>${p.top_pollutant}</b>.</p>
      </div>
      <div style="background:rgba(255,255,255,0.03); padding:20px; border-radius:12px; border-left:4px solid var(--accent2);">
        <h4 style="color:var(--accent2); margin-bottom:10px;">🌤️ Weather & Regional</h4>
        <p>Local PM2.5 deviation: <b>${w.pm_diff} μg/m³</b>. Regional hotspot leader: <b>${r.most_polluted}</b>.</p>
      </div>
    </div>
    <div style="margin-top:20px; padding:20px; background:rgba(255,255,255,0.05); border-radius:12px; border:1px dashed var(--border);">
      <h4 style="color:#f6d365; margin-bottom:10px;">💡 Strategic Recommendation</h4>
      <p>Data-driven focus on <b>${p.top_pollutant === 'CO' ? 'Urban Mobility Control' : p.top_pollutant === 'SO2' ? 'Industrial Desulfurization' : 'Particulate Abatement'}</b> is essential.</p>
    </div>
  `;
}

// Initial load on page ready
document.addEventListener('DOMContentLoaded', applyFilters);
