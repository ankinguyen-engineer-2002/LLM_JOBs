// ============================================
// Job Radar — Cyberpunk Dashboard Logic
// ============================================

// === STATE ===
let allJobs = [], filteredJobs = [], currentPage = 1, currentView = 'table';
const PAGE_SIZE = 25;
let savedIds = new Set(JSON.parse(localStorage.getItem('savedJobs') || '[]'));
let activeFilters = { sources: new Set(), tags: new Set(), levels: new Set(), categories: new Set(), types: new Set(), locations: new Set() };
let charts = {};
let debounceTimer = null;

const SRC = {
  itviec:       { label:'ITviec',       color:'#e11d48', bg:'rgba(225,29,72,0.12)' },
  vietnamworks: { label:'VietnamWorks',  color:'#0284c7', bg:'rgba(2,132,199,0.12)' },
  topcv:        { label:'TopCV',         color:'#16a34a', bg:'rgba(22,163,74,0.12)' },
  linkedin:     { label:'LinkedIn',      color:'#63c8ff', bg:'rgba(99,200,255,0.12)' },
  indeed:       { label:'Indeed',        color:'#b06cff', bg:'rgba(176,108,255,0.12)' },
  google:       { label:'Google',        color:'#fbbf24', bg:'rgba(251,191,36,0.12)' },
  remoteok:     { label:'RemoteOK',      color:'#00ffb2', bg:'rgba(0,255,178,0.12)' },
  himalayas:    { label:'Himalayas',     color:'#0891b2', bg:'rgba(8,145,178,0.12)' },
  jobicy:       { label:'Jobicy',        color:'#ea580c', bg:'rgba(234,88,12,0.12)' },
  wellfound:    { label:'Wellfound',     color:'#9333ea', bg:'rgba(147,51,234,0.12)' },
  turing:       { label:'Turing',        color:'#059669', bg:'rgba(5,150,105,0.12)' },
};

// === CUSTOM CURSOR ===
const cursor = document.getElementById('cursor');
const ring = document.getElementById('cursorRing');
let mx = 0, my = 0, rx = 0, ry = 0;
document.addEventListener('mousemove', e => {
  mx = e.clientX; my = e.clientY;
  cursor.style.left = mx + 'px'; cursor.style.top = my + 'px';
});
function animateRing() {
  rx += (mx - rx) * 0.12; ry += (my - ry) * 0.12;
  ring.style.left = rx + 'px'; ring.style.top = ry + 'px';
  requestAnimationFrame(animateRing);
}
animateRing();

// Cursor hover effects
function setupCursorHovers() {
  document.querySelectorAll('a, button, .card, .job-row, .compact-row, .chip, tr, .chart-card').forEach(el => {
    el.addEventListener('mouseenter', () => {
      ring.style.width = '50px'; ring.style.height = '50px';
      ring.style.borderColor = 'rgba(99,200,255,0.8)';
    });
    el.addEventListener('mouseleave', () => {
      ring.style.width = '36px'; ring.style.height = '36px';
      ring.style.borderColor = 'rgba(99,200,255,0.5)';
    });
  });
}

// === SCROLL REVEAL ===
function setupReveal() {
  const reveals = document.querySelectorAll('.reveal');
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); observer.unobserve(e.target); } });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
  reveals.forEach(el => observer.observe(el));
}

// === INIT ===
async function init() {
  try {
    const resp = await fetch('./jobs.json');
    if (resp.ok) allJobs = await resp.json();
  } catch(e) { console.warn('No jobs data'); }
  if (allJobs.length && allJobs[0].scraped_at) {
    document.getElementById('last-updated').textContent = 'Updated ' + timeAgo(allJobs[0].scraped_at);
  }
  switchTab(localStorage.getItem('lastTab') || 'dashboard');
  updateSavedBadge();
  lucide.createIcons();
  setupCursorHovers();
  setupReveal();
}

// === TABS ===
function switchTab(name) {
  document.querySelectorAll('.tab-section').forEach(s => s.classList.add('hidden'));
  const el = document.getElementById('tab-' + name);
  if (el) el.classList.remove('hidden');
  document.querySelectorAll('.tab-btn[data-tab]').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  localStorage.setItem('lastTab', name);
  if (name === 'dashboard') renderDashboard();
  else if (name === 'browse') renderBrowse();
  else if (name === 'analytics') renderAnalytics();
  else if (name === 'saved') renderSaved();
  else if (name === 'about') renderAbout();
  lucide.createIcons();
  setTimeout(setupCursorHovers, 100);
}

// === UTILS ===
function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return Math.floor(diff/60) + 'm ago';
  if (diff < 86400) return Math.floor(diff/3600) + 'h ago';
  if (diff < 604800) return Math.floor(diff/86400) + 'd ago';
  return new Date(dateStr).toLocaleDateString();
}
function esc(s) { if(!s) return ''; const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
function isToday(j) { const d = j.first_seen||j.scraped_at; if(!d) return false; return new Date(d).toDateString() === new Date().toDateString(); }
function isWithin(j, days) { const d = j.first_seen||j.scraped_at; if(!d) return false; return (Date.now() - new Date(d).getTime()) < days*86400000; }
function srcBadge(s) { const c=SRC[s]||{color:'#6b6b7e',bg:'rgba(107,107,126,0.12)',label:s}; return `<span class="src-badge" style="background:${c.bg};color:${c.color}" onclick="addSourceFilter('${s}')">${c.label}</span>`; }
function freshBadge(f) {
  const m = {today:'fresh-today','3d':'fresh-3d','7d':'fresh-7d','14d':'fresh-14d','30d':'fresh-30d','>30d':'fresh-old',unknown:'fresh-old'};
  const labels = {today:'Today','3d':'3 days','7d':'1 week','14d':'2 weeks','30d':'1 month','>30d':'>30d',unknown:'N/A'};
  return `<span class="src-badge ${m[f]||'fresh-old'}">${labels[f]||f}</span>`;
}
function levelBadge(l) {
  const m = {Junior:'level-junior',Mid:'level-mid',Senior:'level-senior',Lead:'level-lead',Manager:'level-manager'};
  return `<span class="${m[l]||''}" style="font-family:var(--font-mono);font-weight:700;font-size:11px;letter-spacing:0.04em">${l||'N/A'}</span>`;
}
function debounceFilter() { clearTimeout(debounceTimer); debounceTimer = setTimeout(applyFilters, 300); }

// === DASHBOARD ===
function renderDashboard() {
  const today = allJobs.filter(isToday);
  const week = allJobs.filter(j => isWithin(j,7));
  const remote = allJobs.filter(j => j.is_remote);
  const sources = new Set(allJobs.map(j => j.source));
  const hasSalary = allJobs.filter(j => j.salary && j.salary !== 'N/A').length;
  
  document.getElementById('stats-cards').innerHTML = [
    statCard('database','Total Jobs',allJobs.length,'#63c8ff'),
    statCard('zap','Today',today.length,'#00ffb2'),
    statCard('globe','Remote',remote.length,'#b06cff'),
    statCard('layers','Sources',sources.size,'#fbbf24'),
    statCard('banknote','Has Salary',hasSalary,'#f472b6'),
    statCard('trending-up','This Week',week.length,'#63c8ff'),
  ].join('');
  
  const todaySorted = [...today].sort((a,b)=>(b.scraped_at||'').localeCompare(a.scraped_at||'')).slice(0,5);
  document.getElementById('top-today').innerHTML = todaySorted.length ? todaySorted.map((j,i)=>jobRow(j,i+1)).join('') : '<p style="color:var(--text-faint);font-family:var(--font-mono);font-size:12px;padding:20px 0">No new jobs today yet.</p>';
  
  const ws=[...week].sort((a,b)=>(b.scraped_at||'').localeCompare(a.scraped_at||'')).slice(0,10);
  const ms=allJobs.filter(j=>isWithin(j,30)).sort((a,b)=>(b.scraped_at||'').localeCompare(a.scraped_at||'')).slice(0,10);
  document.getElementById('top-week').innerHTML = ws.length ? ws.map((j,i)=>compactRow(j,i+1)).join('') : '<p style="color:var(--text-faint)">No jobs this week.</p>';
  document.getElementById('top-month').innerHTML = ms.length ? ms.map((j,i)=>compactRow(j,i+1)).join('') : '<p style="color:var(--text-faint)">No jobs this month.</p>';
  renderDashCharts();
  lucide.createIcons();
  setTimeout(setupCursorHovers, 50);
}

function statCard(icon, label, value, color) {
  return `<div class="stat-card"><div style="display:flex;align-items:center;gap:14px">
    <div style="width:40px;height:40px;display:flex;align-items:center;justify-content:center"><i data-lucide="${icon}" style="width:22px;height:22px;color:${color}"></i></div>
    <div><p class="stat-value" style="color:${color}">${value.toLocaleString()}</p><p class="stat-label">${label}</p></div>
  </div></div>`;
}

function jobRow(j, rank) {
  const saved = savedIds.has(j.id);
  return `<div class="job-row" onclick='openDetail(${JSON.stringify(j).replace(/'/g,"&#39;")})'>
    <span class="rank">${rank}</span>
    <div class="info"><p class="name">${esc(j.title)}</p><p class="meta">${esc(j.company)} · ${esc(j.location)}</p></div>
    ${srcBadge(j.source)} <span style="font-family:var(--font-mono);font-size:10px;color:var(--text-faint);letter-spacing:0.04em" class="mobile-hide">${timeAgo(j.scraped_at)}</span>
    <button class="save-btn ${saved?'saved':''}" onclick="event.stopPropagation();toggleSave('${j.id}')"><i data-lucide="heart" style="width:16px;height:16px" ${saved?'fill="currentColor"':''}></i></button>
  </div>`;
}

function compactRow(j, rank) {
  return `<div class="compact-row" onclick='openDetail(${JSON.stringify(j).replace(/'/g,"&#39;")})'>
    <span style="color:var(--text-faint);width:20px;font-family:var(--font-mono);font-size:10px">${rank}</span>
    <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px">${esc(j.title)}</span>
    <span style="font-size:11px;color:var(--text-faint);max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" class="mobile-hide">${esc(j.company)}</span>
    ${srcBadge(j.source)}
  </div>`;
}

function renderDashCharts() {
  // Chart colors for cyberpunk theme
  const chartDefaults = {
    scales: {
      x: { ticks: { color: '#2e2e3a', font: { family: 'Space Mono', size: 9 } }, grid: { display: false } },
      y: { ticks: { color: '#2e2e3a', font: { family: 'Space Mono', size: 9 } }, grid: { color: 'rgba(255,255,255,0.03)' } }
    }
  };

  const days = {};
  for(let i=13; i>=0; i--) { const d = new Date(); d.setDate(d.getDate()-i); days[d.toISOString().slice(0,10)] = 0; }
  allJobs.forEach(j => { const d=(j.first_seen||j.scraped_at||'').slice(0,10); if(d in days) days[d]++; });
  destroyChart('chart-daily');
  charts['chart-daily'] = new Chart(document.getElementById('chart-daily'), {
    type:'bar', data:{labels:Object.keys(days).map(d=>d.slice(5)),datasets:[{data:Object.values(days),backgroundColor:'rgba(99,200,255,0.5)',borderRadius:2,borderSkipped:false}]},
    options:{responsive:true,plugins:{legend:{display:false}}, ...chartDefaults}
  });

  const srcC = {}; allJobs.forEach(j => { srcC[j.source] = (srcC[j.source]||0)+1; });
  const sk = Object.keys(srcC).sort((a,b) => srcC[b]-srcC[a]);
  destroyChart('chart-source-dash');
  charts['chart-source-dash'] = new Chart(document.getElementById('chart-source-dash'), {
    type:'doughnut', data:{labels:sk.map(s=>(SRC[s]||{}).label||s),datasets:[{data:sk.map(s=>srcC[s]),backgroundColor:sk.map(s=>(SRC[s]||{}).color||'#6b6b7e'),borderWidth:0}]},
    options:{responsive:true,plugins:{legend:{position:'right',labels:{color:'#6b6b7e',font:{family:'Space Mono',size:10},padding:8,usePointStyle:true}}},cutout:'65%'}
  });
}
function destroyChart(id) { if(charts[id]) { charts[id].destroy(); delete charts[id]; } }

// === BROWSE (multi-dimensional filters) ===
function renderBrowse() { buildFilterUI(); applyFilters(); }

function buildFilterUI() {
  // Sources
  const sources = [...new Set(allJobs.map(j=>j.source))].sort();
  document.getElementById('f-sources').innerHTML = sources.map(s => {
    const c = SRC[s]||{label:s}; const act = activeFilters.sources.has(s)?'active':'';
    return `<button class="chip ${act}" onclick="toggleFilter('sources','${s}')">${c.label}<span class="count">${allJobs.filter(j=>j.source===s).length}</span></button>`;
  }).join('');

  // Levels
  const levels = {}; allJobs.forEach(j => { const l=j.level||'N/A'; levels[l]=(levels[l]||0)+1; });
  document.getElementById('f-levels').innerHTML = Object.entries(levels).sort((a,b)=>b[1]-a[1]).map(([l,c]) => {
    const act = activeFilters.levels.has(l)?'active':'';
    return `<button class="chip ${act}" onclick="toggleFilter('levels','${l}')">${l}<span class="count">${c}</span></button>`;
  }).join('');

  // Categories
  const cats = {}; allJobs.forEach(j => { const c=j.job_category||'Other'; cats[c]=(cats[c]||0)+1; });
  document.getElementById('f-categories').innerHTML = Object.entries(cats).sort((a,b)=>b[1]-a[1]).map(([c,n]) => {
    const act = activeFilters.categories.has(c)?'active':'';
    return `<button class="chip ${act}" onclick="toggleFilter('categories','${c}')">${c}<span class="count">${n}</span></button>`;
  }).join('');

  // Employment Types
  const etypes = {}; allJobs.forEach(j => { const t=j.employment_type||'N/A'; etypes[t]=(etypes[t]||0)+1; });
  document.getElementById('f-types').innerHTML = Object.entries(etypes).sort((a,b)=>b[1]-a[1]).map(([t,n]) => {
    const act = activeFilters.types.has(t)?'active':'';
    return `<button class="chip ${act}" onclick="toggleFilter('types','${t}')">${t}<span class="count">${n}</span></button>`;
  }).join('');

  // Locations (top 10)
  const locs = {}; allJobs.forEach(j => { const l=(j.location||'N/A').split(',')[0].trim(); locs[l]=(locs[l]||0)+1; });
  const topLocs = Object.entries(locs).sort((a,b)=>b[1]-a[1]).slice(0,10);
  document.getElementById('f-locations').innerHTML = topLocs.map(([l,c]) => {
    const act = activeFilters.locations.has(l)?'active':'';
    return `<button class="chip ${act}" onclick="toggleFilter('locations','${l}')">${l}<span class="count">${c}</span></button>`;
  }).join('');

  // Tags (clean_tags, top 15)
  const tagC = {}; allJobs.forEach(j => (j.clean_tags||j.tags||[]).forEach(t => { tagC[t]=(tagC[t]||0)+1; }));
  const topTags = Object.entries(tagC).sort((a,b)=>b[1]-a[1]).slice(0,15);
  document.getElementById('f-tags').innerHTML = topTags.map(([t,c]) => {
    const act = activeFilters.tags.has(t)?'active':'';
    return `<button class="chip ${act}" onclick="toggleFilter('tags','${esc(t)}')">${t}<span class="count">${c}</span></button>`;
  }).join('');
}

function toggleFilter(type,val) { activeFilters[type].has(val)?activeFilters[type].delete(val):activeFilters[type].add(val); renderBrowse(); }
function addSourceFilter(s) { activeFilters.sources.clear(); activeFilters.sources.add(s); switchTab('browse'); }
function clearFilters() { Object.values(activeFilters).forEach(s=>s.clear()); document.getElementById('search-input').value=''; document.getElementById('f-freshness').value='all'; document.getElementById('f-remote').checked=false; document.getElementById('f-salary').checked=false; renderBrowse(); }

function applyFilters() {
  const search = (document.getElementById('search-input').value||'').toLowerCase();
  const freshness = document.getElementById('f-freshness').value;
  const remoteOnly = document.getElementById('f-remote').checked;
  const hasSalary = document.getElementById('f-salary').checked;
  const sortBy = document.getElementById('sort-select').value;

  filteredJobs = allJobs.filter(j => {
    if(search) { const s=`${j.title} ${j.company} ${(j.clean_tags||j.tags||[]).join(' ')} ${j.description_snippet||''}`.toLowerCase(); if(!s.includes(search)) return false; }
    if(activeFilters.sources.size>0 && !activeFilters.sources.has(j.source)) return false;
    if(activeFilters.levels.size>0 && !activeFilters.levels.has(j.level||'N/A')) return false;
    if(activeFilters.categories.size>0 && !activeFilters.categories.has(j.job_category||'Other')) return false;
    if(activeFilters.types.size>0 && !activeFilters.types.has(j.employment_type||'N/A')) return false;
    if(activeFilters.locations.size>0) { const loc=(j.location||'').split(',')[0].trim(); if(!activeFilters.locations.has(loc)) return false; }
    if(activeFilters.tags.size>0) { const t=(j.clean_tags||j.tags||[]).map(x=>x.toLowerCase()); if(![...activeFilters.tags].every(f=>t.includes(f))) return false; }
    if(remoteOnly && !j.is_remote) return false;
    if(hasSalary && (!j.salary || j.salary==='N/A')) return false;
    if(freshness !== 'all') {
      const daysMap = {today:1,'3d':3,'7d':7,'14d':14,'30d':30};
      const days = daysMap[freshness]||999;
      const dateStr = j.posted_date||j.scraped_at||j.first_seen||'';
      if(!dateStr) return false;
      if((Date.now()-new Date(dateStr).getTime()) > days*86400000) return false;
    }
    return true;
  });

  filteredJobs.sort((a,b) => {
    if(sortBy==='title') return (a.title||'').localeCompare(b.title||'');
    if(sortBy==='company') return (a.company||'').localeCompare(b.company||'');
    if(sortBy==='level') { const o={Junior:1,Mid:2,Senior:3,Lead:4,Manager:5}; return (o[b.level]||0)-(o[a.level]||0); }
    if(sortBy==='posted_date') return (b.posted_date||'').localeCompare(a.posted_date||'');
    return (b.scraped_at||'').localeCompare(a.scraped_at||'');
  });
  currentPage = 1;
  renderJobsList();
}

function renderJobsList() {
  document.getElementById('job-count').textContent = filteredJobs.length;
  const start = (currentPage-1)*PAGE_SIZE, end = start+PAGE_SIZE;
  const page = filteredJobs.slice(start, end);
  const container = document.getElementById('jobs-container');

  if(currentView === 'table') {
    container.innerHTML = `<div style="overflow-x:auto"><table class="data-table"><thead><tr>
      <th onclick="sortCol('title')">Title</th><th class="mobile-hide" onclick="sortCol('company')">Company</th>
      <th class="mobile-hide" onclick="sortCol('level')">Level</th><th class="mobile-hide">Location</th>
      <th class="mobile-hide">Salary</th><th>Source</th><th class="mobile-hide">Freshness</th>
      <th class="mobile-hide">Posted</th><th style="width:32px"></th>
    </tr></thead><tbody>${page.map(j=>tableRow(j)).join('')}</tbody></table></div>`;
  } else {
    container.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px">${page.map(j=>jobCard(j)).join('')}</div>`;
  }
  renderPagination();
  lucide.createIcons();
  setTimeout(setupCursorHovers, 50);
}

function tableRow(j) {
  const saved = savedIds.has(j.id);
  const tags = (j.clean_tags||j.tags||[]).slice(0,3);
  const postedDisplay = j.posted_date||'—';
  return `<tr onclick='openDetail(${JSON.stringify(j).replace(/'/g,"&#39;")})'>
    <td class="title-cell"><span class="title">${esc(j.title)}</span><div class="tags">${tags.map(t=>`<span class="tag-sm">${t}</span>`).join('')}</div></td>
    <td class="mobile-hide" style="color:var(--text-dim);max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px">${esc(j.company)}</td>
    <td class="mobile-hide">${levelBadge(j.level)}</td>
    <td class="mobile-hide" style="color:var(--text-faint);font-size:11px">${esc(j.location)}</td>
    <td class="mobile-hide" style="font-size:11px;${j.salary&&j.salary!=='N/A'?'color:#00ffb2':'color:var(--text-faint)'}">${esc(j.salary||'N/A')}</td>
    <td>${srcBadge(j.source)}</td>
    <td class="mobile-hide">${freshBadge(j.freshness||'unknown')}</td>
    <td class="mobile-hide" style="font-family:var(--font-mono);font-size:9px;color:var(--text-faint)">${postedDisplay}</td>
    <td><button class="save-btn ${saved?'saved':''}" onclick="event.stopPropagation();toggleSave('${j.id}')"><i data-lucide="heart" style="width:14px;height:14px" ${saved?'fill="currentColor"':''}></i></button></td>
  </tr>`;
}

function jobCard(j) {
  const saved = savedIds.has(j.id);
  const tags = (j.clean_tags||j.tags||[]).slice(0,4);
  return `<div class="card" style="padding:20px;cursor:none" onclick='openDetail(${JSON.stringify(j).replace(/'/g,"&#39;")})'>
    <div style="display:flex;justify-content:space-between;margin-bottom:10px"><div style="flex:1;min-width:0"><p style="font-weight:700;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(j.title)}</p><p style="font-size:12px;color:var(--text-faint);margin-top:2px">${esc(j.company)}</p></div>
    <button class="save-btn ${saved?'saved':''}" onclick="event.stopPropagation();toggleSave('${j.id}')"><i data-lucide="heart" style="width:16px;height:16px" ${saved?'fill="currentColor"':''}></i></button></div>
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap">${levelBadge(j.level)} <span style="color:var(--text-faint);font-size:10px">·</span> <span style="font-size:11px;color:var(--text-faint)">${esc(j.location)}</span>${j.is_remote?'<span style="font-family:var(--font-mono);font-size:9px;color:var(--accent3);border:1px solid rgba(0,255,178,0.2);padding:1px 6px">REMOTE</span>':''}</div>
    <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:10px">${tags.map(t=>`<span class="tag-sm">${t}</span>`).join('')}</div>
    <div style="display:flex;justify-content:space-between;align-items:center">${srcBadge(j.source)} ${freshBadge(j.freshness||'unknown')}</div>
    ${j.salary&&j.salary!=='N/A'?`<p style="font-family:var(--font-mono);font-size:11px;color:var(--accent3);margin-top:8px">${esc(j.salary)}</p>`:''}
  </div>`;
}

function renderPagination() {
  const total = Math.ceil(filteredJobs.length/PAGE_SIZE);
  if(total<=1) { document.getElementById('pagination').innerHTML=''; return; }
  let html = `<button class="page-btn" onclick="goPage(${currentPage-1})" ${currentPage===1?'disabled':''}>‹ Prev</button>`;
  for(let i=1; i<=total; i++) {
    if(total>7 && i>2 && i<total-1 && Math.abs(i-currentPage)>1) { if(i===3||i===total-2) html+='<span style="color:var(--text-faint)">…</span>'; continue; }
    html += `<button class="page-btn ${i===currentPage?'active':''}" onclick="goPage(${i})">${i}</button>`;
  }
  html += `<button class="page-btn" onclick="goPage(${currentPage+1})" ${currentPage===total?'disabled':''}>Next ›</button>`;
  document.getElementById('pagination').innerHTML = html;
}

function goPage(p) { const t=Math.ceil(filteredJobs.length/PAGE_SIZE); if(p<1||p>t) return; currentPage=p; renderJobsList(); window.scrollTo({top:200,behavior:'smooth'}); }
function setView(v) { currentView=v; document.getElementById('view-table-btn').className=v==='table'?'tab-btn active':'tab-btn'; document.getElementById('view-cards-btn').className=v==='cards'?'tab-btn active':'tab-btn'; renderJobsList(); }
function sortCol(col) { document.getElementById('sort-select').value=col; applyFilters(); }

// === ANALYTICS ===
function renderAnalytics() {
  const chartFont = { family: 'Space Mono', size: 9 };
  const gridColor = 'rgba(255,255,255,0.03)';

  const days30 = {};
  for(let i=29;i>=0;i--) { const d=new Date();d.setDate(d.getDate()-i);days30[d.toISOString().slice(0,10)]=0; }
  allJobs.forEach(j => { const d=(j.first_seen||j.scraped_at||'').slice(0,10); if(d in days30) days30[d]++; });
  destroyChart('chart-daily-30');
  charts['chart-daily-30'] = new Chart(document.getElementById('chart-daily-30'), {
    type:'bar',data:{labels:Object.keys(days30).map(d=>d.slice(5)),datasets:[{data:Object.values(days30),backgroundColor:'rgba(99,200,255,0.4)',borderRadius:2,borderSkipped:false}]},
    options:{responsive:true,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#2e2e3a',font:chartFont},grid:{display:false}},y:{ticks:{color:'#2e2e3a',font:chartFont},grid:{color:gridColor}}}}
  });

  // Clean Tags chart
  const tagC = {}; allJobs.forEach(j => (j.clean_tags||[]).forEach(t => { tagC[t]=(tagC[t]||0)+1; }));
  const topT = Object.entries(tagC).sort((a,b)=>b[1]-a[1]).slice(0,15);
  destroyChart('chart-tags');
  charts['chart-tags'] = new Chart(document.getElementById('chart-tags'), {
    type:'bar',data:{labels:topT.map(t=>t[0]),datasets:[{data:topT.map(t=>t[1]),backgroundColor:'rgba(176,108,255,0.5)',borderRadius:2,borderSkipped:false}]},
    options:{indexAxis:'y',responsive:true,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#2e2e3a',font:chartFont},grid:{color:gridColor}},y:{ticks:{color:'#6b6b7e',font:{...chartFont,size:10}},grid:{display:false}}}}
  });

  // Level distribution
  const lvlC = {}; allJobs.forEach(j => { lvlC[j.level||'N/A']=(lvlC[j.level||'N/A']||0)+1; });
  const lvlK = Object.keys(lvlC).sort((a,b)=>lvlC[b]-lvlC[a]);
  const lvlColors = {Junior:'#00ffb2',Mid:'#63c8ff',Senior:'#b06cff',Lead:'#f472b6',Manager:'#fbbf24','N/A':'#2e2e3a'};
  destroyChart('chart-levels');
  charts['chart-levels'] = new Chart(document.getElementById('chart-levels'), {
    type:'doughnut',data:{labels:lvlK,datasets:[{data:lvlK.map(k=>lvlC[k]),backgroundColor:lvlK.map(k=>lvlColors[k]||'#2e2e3a'),borderWidth:0}]},
    options:{responsive:true,plugins:{legend:{position:'right',labels:{color:'#6b6b7e',font:{family:'Space Mono',size:10},padding:8,usePointStyle:true}}},cutout:'65%'}
  });

  // Category distribution
  const catC = {}; allJobs.forEach(j => { catC[j.job_category||'Other']=(catC[j.job_category||'Other']||0)+1; });
  const catK = Object.keys(catC).sort((a,b)=>catC[b]-catC[a]);
  const catColors = ['#63c8ff','#00ffb2','#b06cff','#fbbf24','#f472b6','#ea580c'];
  destroyChart('chart-categories');
  charts['chart-categories'] = new Chart(document.getElementById('chart-categories'), {
    type:'doughnut',data:{labels:catK,datasets:[{data:catK.map(k=>catC[k]),backgroundColor:catColors.slice(0,catK.length),borderWidth:0}]},
    options:{responsive:true,plugins:{legend:{position:'right',labels:{color:'#6b6b7e',font:{family:'Space Mono',size:10},padding:8,usePointStyle:true}}},cutout:'65%'}
  });

  // Source bar
  const srcC = {}; allJobs.forEach(j => { srcC[j.source]=(srcC[j.source]||0)+1; });
  const srcK = Object.keys(srcC).sort((a,b)=>srcC[b]-srcC[a]);
  destroyChart('chart-source');
  charts['chart-source'] = new Chart(document.getElementById('chart-source'), {
    type:'bar',data:{labels:srcK.map(s=>(SRC[s]||{}).label||s),datasets:[{data:srcK.map(s=>srcC[s]),backgroundColor:srcK.map(s=>(SRC[s]||{}).color||'#6b6b7e'),borderRadius:2,borderSkipped:false}]},
    options:{responsive:true,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#6b6b7e',font:{...chartFont,size:10}},grid:{display:false}},y:{ticks:{color:'#2e2e3a',font:chartFont},grid:{color:gridColor}}}}
  });
  lucide.createIcons();
}

// === SAVED ===
function toggleSave(id) { savedIds.has(id)?savedIds.delete(id):savedIds.add(id); localStorage.setItem('savedJobs',JSON.stringify([...savedIds])); updateSavedBadge(); rerender(); }
function updateSavedBadge() { const b=document.getElementById('saved-badge'); if(b) { b.textContent=savedIds.size; b.style.display=savedIds.size>0?'inline-flex':'none'; } }
function renderSaved() {
  const saved = allJobs.filter(j=>savedIds.has(j.id));
  document.getElementById('saved-total').textContent = saved.length;
  document.getElementById('saved-empty').style.display = saved.length?'none':'block';
  document.getElementById('saved-container').innerHTML = saved.length ? saved.map((j,i)=>jobRow(j,i+1)).join('') : '';
  lucide.createIcons();
  setTimeout(setupCursorHovers, 50);
}
function clearSaved() { if(!confirm('Clear all saved jobs?')) return; savedIds.clear(); localStorage.setItem('savedJobs','[]'); updateSavedBadge(); renderSaved(); }
function exportCSV() {
  const saved = allJobs.filter(j=>savedIds.has(j.id));
  if(!saved.length) return alert('No saved jobs.');
  const h = ['Title','Company','Level','Category','Employment Type','Location','Salary','Source','URL','Tags','Posted','Scraped'];
  const rows = saved.map(j => [j.title,j.company,j.level,j.job_category,j.employment_type,j.location,j.salary,j.source,j.url,(j.clean_tags||[]).join(';'),j.posted_date,j.scraped_at].map(v=>'"'+(v||'').replace(/"/g,'""')+'"'));
  const csv = [h.join(','),...rows.map(r=>r.join(','))].join('\n');
  const blob = new Blob([csv],{type:'text/csv'});
  const a = document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='job_radar_export.csv'; a.click();
}

// === ABOUT ===
function renderAbout() {
  document.getElementById('sources-list').innerHTML = Object.entries(SRC).map(([k,v]) => {
    const cnt = allJobs.filter(j=>j.source===k).length;
    return `<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--bg);border:1px solid var(--border);transition:border-color 0.2s" onmouseover="this.style.borderColor='rgba(99,200,255,0.25)'" onmouseout="this.style.borderColor='rgba(255,255,255,0.06)'"><span class="src-badge" style="background:${v.bg};color:${v.color}">${v.label}</span><span style="font-family:var(--font-mono);font-size:10px;color:var(--text-faint)">${cnt} jobs</span></div>`;
  }).join('');
}

// === DETAIL PANEL ===
function openDetail(j) {
  const saved = savedIds.has(j.id);
  const tags = (j.clean_tags||j.tags||[]);
  document.getElementById('detail-content').innerHTML = `
    <div style="display:flex;justify-content:space-between;margin-bottom:24px">
      <button onclick="closeDetail()" style="background:none;border:none;color:var(--text-faint);cursor:none;padding:4px"><i data-lucide="x" style="width:20px;height:20px"></i></button>
      <button class="save-btn ${saved?'saved':''}" onclick="toggleSave('${j.id}');openDetail(${JSON.stringify(j).replace(/'/g,'&#39;')})"><i data-lucide="heart" style="width:20px;height:20px" ${saved?'fill="currentColor"':''}></i></button>
    </div>
    <h2 style="font-family:var(--font-display);font-size:22px;font-weight:800;letter-spacing:-0.03em;margin-bottom:6px">${esc(j.title)}</h2>
    <p style="color:var(--text-dim);font-size:14px;margin-bottom:20px">${esc(j.company)}</p>
    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">${levelBadge(j.level)} ${freshBadge(j.freshness||'unknown')} ${srcBadge(j.source)} <span class="src-badge" style="background:rgba(176,108,255,0.1);color:#b06cff;border:1px solid rgba(176,108,255,0.2)">${j.job_category||'Other'}</span> ${j.employment_type&&j.employment_type!=='N/A'?`<span class="src-badge" style="background:rgba(251,191,36,0.1);color:#fbbf24;border:1px solid rgba(251,191,36,0.2)">${j.employment_type}</span>`:''}</div>
    <div style="display:grid;gap:12px;margin-bottom:20px;padding:16px;background:var(--surface);border:1px solid var(--border)">
      <div style="display:flex;align-items:center;gap:10px;font-size:13px"><i data-lucide="map-pin" style="width:16px;height:16px;color:var(--text-faint)"></i>${esc(j.location)} ${j.is_remote?'<span style="color:var(--accent3);font-family:var(--font-mono);font-size:10px">(Remote)</span>':''}</div>
      <div style="display:flex;align-items:center;gap:10px;font-size:13px"><i data-lucide="banknote" style="width:16px;height:16px;color:var(--text-faint)"></i><span style="${j.salary&&j.salary!=='N/A'?'color:var(--accent3)':''}">${esc(j.salary||'N/A')}</span></div>
      <div style="display:flex;align-items:center;gap:10px;font-size:13px"><i data-lucide="calendar" style="width:16px;height:16px;color:var(--text-faint)"></i>Posted: ${j.posted_date||'N/A'}</div>
      <div style="display:flex;align-items:center;gap:10px;font-size:13px"><i data-lucide="clock" style="width:16px;height:16px;color:var(--text-faint)"></i>Scraped: ${j.scraped_at?j.scraped_at.slice(0,16).replace('T',' '):'N/A'}</div>
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:20px">${tags.map(t=>`<span class="tag-sm">${t}</span>`).join('')}</div>
    ${j.description_snippet?`<div style="background:var(--surface);border:1px solid var(--border);padding:16px;font-size:13px;color:var(--text-dim);line-height:1.7;margin-bottom:20px">${esc(j.description_snippet)}</div>`:''}
    <div style="display:flex;gap:8px">
      <a href="${j.url}" target="_blank" rel="noopener" style="flex:1;padding:12px;background:var(--accent);color:var(--bg);text-align:center;font-family:var(--font-mono);font-size:11px;font-weight:700;text-decoration:none;letter-spacing:0.08em;text-transform:uppercase;display:flex;align-items:center;justify-content:center;gap:6px;transition:box-shadow 0.2s" onmouseover="this.style.boxShadow='0 0 30px rgba(99,200,255,0.4)'" onmouseout="this.style.boxShadow='none'"><i data-lucide="external-link" style="width:14px;height:14px"></i>Apply</a>
      <button onclick="navigator.clipboard.writeText('${j.url}');this.textContent='Copied!'" style="padding:12px 20px;background:transparent;color:var(--text-dim);border:1px solid var(--border-lit);font-family:var(--font-mono);font-size:11px;letter-spacing:0.06em;cursor:none">Copy Link</button>
    </div>`;
  document.getElementById('detail-panel').classList.add('open');
  document.getElementById('backdrop').classList.add('open');
  lucide.createIcons();
}
function closeDetail() { document.getElementById('detail-panel').classList.remove('open'); document.getElementById('backdrop').classList.remove('open'); }
document.addEventListener('keydown', e => { if(e.key==='Escape') closeDetail(); });
function rerender() { switchTab(localStorage.getItem('lastTab')||'dashboard'); }

// Boot
init();
