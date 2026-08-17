"""Render the live Operations Check-in page (Store Health + Client Churn tabs)."""
import json, calendar

CORE = ["Cassandre Matton", "Roger Aires", "Tijn van Elburg", "Gian De Meester"]
TAG = {"Henk-Jan van Steeg": "leadership"}
EXCLUDE_CHURN = {"Guy Berkhout"}


def _mlab(ym):
    return calendar.month_abbr[int(ym.split("-")[1])]


def _eur(n):
    return "€" + f"{round(n):,}"


def _churn_section(churn):
    months = churn["months"]
    data = churn["churn"]

    def total(b):
        return sum(data[b].get(m, 0) for m in months)

    buyers = [b for b in data if total(b) > 0 and b not in EXCLUDE_CHURN]
    core = sorted([b for b in buyers if b in CORE], key=total, reverse=True)
    others = sorted([b for b in buyers if b not in CORE], key=total, reverse=True)
    monthly = [sum(data[b].get(m, 0) for b in buyers) for m in months]
    grand = sum(monthly)
    maxcell = max((data[b].get(m, 0) for b in buyers for m in months), default=1) or 1
    maxtot = max((total(b) for b in buyers), default=1) or 1
    avg = grand / len(months) if months else 0
    worst_m = months[monthly.index(max(monthly))] if monthly and max(monthly) else months[0]

    def cell(v):
        if v == 0:
            return '<td class="z">·</td>'
        a = 0.12 + 0.88 * (v / maxcell)
        return f'<td class="hc" style="--a:{a:.2f}">{v}</td>'

    def row(b):
        tot = total(b)
        tagh = f'<span class="tag">{TAG[b]}</span>' if b in TAG else ''
        cells = "".join(cell(data[b].get(m, 0)) for m in months)
        return (f'<tr><td class="bname">{b}{tagh}</td>{cells}'
                f'<td class="tot"><span class="tb"><i style="width:{tot/maxtot*100:.0f}%"></i></span><b>{tot}</b></td></tr>')

    head = "".join(f'<th class="mh">{_mlab(m)}</th>' for m in months)
    rows_core = "".join(row(b) for b in core)
    rows_other = "".join(row(b) for b in others)
    mtot = "".join(f'<td class="mt">{v}</td>' for v in monthly)

    W, H, pad = 220, 44, 6
    mx = max(monthly) if monthly and max(monthly) else 1
    pts = [(pad + (i * (W - 2 * pad) / (len(monthly) - 1) if len(monthly) > 1 else 0),
            H - pad - (v / mx) * (H - 2 * pad)) for i, v in enumerate(monthly)]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4"/>' for x, y in pts)
    xlabels = "".join(f"<span>{_mlab(m)}</span>" for m in months)
    last = pts[-1] if pts else (0, 0)

    return f"""
<section class="kpis">
  <div class="kpi flag churn"><div class="n">{grand}</div><div class="l">Clients churned</div><div class="sub">{_mlab(months[0])}&ndash;{_mlab(months[-1])} {months[-1][:4]}</div></div>
  <div class="kpi"><div class="n">{avg:.1f}</div><div class="l">Avg per month</div><div class="sub">across {len(months)} months</div></div>
  <div class="kpi"><div class="n">{max(monthly) if monthly else 0}</div><div class="l">Worst month</div><div class="sub">{_mlab(worst_m)} {worst_m[:4]}</div></div>
</section>
<section class="card"><div class="tablewrap"><table class="matrix">
  <thead><tr><th class="bh">Media buyer</th>{head}<th class="th">{months[-1][:4]}</th></tr></thead>
  <tbody>{rows_core}</tbody>
  <tbody class="others">{'<tr class="divider"><td colspan="'+str(len(months)+2)+'">Leadership / former books</td></tr>'+rows_other if rows_other else ''}</tbody>
  <tfoot><tr><td class="bname">Agency total</td>{mtot}<td class="tot"><b>{grand}</b></td></tr></tfoot>
</table></div></section>
<section class="trend card">
  <div class="trend-head"><h2>Agency-wide monthly churn</h2><span class="meta">peak {_mlab(worst_m)} &middot; {max(monthly) if monthly else 0} clients</span></div>
  <svg viewBox="0 0 {W} {H}" class="spark" preserveAspectRatio="none" role="img" aria-label="Monthly churn trend">
    <polyline fill="none" points="{poly}"/><g class="dots">{dots}</g>
    <circle class="last" cx="{last[0]:.1f}" cy="{last[1]:.1f}" r="3.4"/>
  </svg>
  <div class="xlabels">{xlabels}</div>
</section>
<footer class="foot"><strong>Source.</strong> Client churn from the Icarus Engine source (<code>monday_activity_log</code>, type = Churned Client), deduplicated by client + date and attributed to the media buyer of the client's most-recent store. Guy Berkhout (former) excluded; Henk-Jan van Steeg shown as leadership.</footer>
"""


def render_page(payload, user=None):
    H = payload["health"]
    churn_html = _churn_section(payload["churn"])
    churn_pill = sum(payload["churn"]["churn"][b].get(m, 0)
                     for b in payload["churn"]["churn"] if b not in EXCLUDE_CHURN
                     for m in payload["churn"]["months"])
    user_bar = (f'<span class="who">{user} · <a href="/logout">sign out</a></span>' if user else '')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Operations Check-in · Icarus</title>
<style>{_CSS}</style></head><body><div class="wrap">
<header class="masthead"><div class="rail"></div>
  <div class="topbar"><div class="brandline">ICARUS · OPERATIONS</div>{user_bar}</div>
  <h1>Operations Check-in</h1>
  <p class="lede">Store health and client churn across the media-buyer team — live from the database.</p>
  <div class="meta">Data as of {H['today']} &nbsp;·&nbsp; refreshed {payload['generated_at']} &nbsp;·&nbsp; health: {H['count']} running stores (zero-spend excluded)</div>
</header>
<div class="tabs" role="tablist">
  <button class="tab-btn" role="tab" data-tab="health" aria-selected="true">Store Health <span class="pillct">{H['count']}</span></button>
  <button class="tab-btn" role="tab" data-tab="churn" aria-selected="false">Client Churn <span class="pillct">{churn_pill}</span></button>
</div>
<section class="panel active" id="panel-health" role="tabpanel">
  <div class="rulebox"><span class="rule-k">The&nbsp;rule</span><span class="rule-v">Once a store passes <strong>3 months</strong> in the agency it should run <strong>&ge;&thinsp;&euro;1,000&thinsp;/&thinsp;day</strong>. Below that &rarr; assign the <strong>buddy system</strong>.</span></div>
  <section class="kpis" id="kpis-health"></section>
  <section class="controls"><div class="filtergroup" id="buyerFilter"></div><div class="filtergroup" id="statusFilter"></div></section>
  <main id="buyers"></main>
  <footer class="foot"><strong>How to read this.</strong> <span class="pill on">On target</span> &ge;&euro;1k/day &nbsp;·&nbsp; <span class="pill buddy">Buddy system</span> &ge;3&nbsp;months &amp; under &euro;1k/day &nbsp;·&nbsp; <span class="pill ramp">Ramp-up</span> &lt;3&nbsp;months. Stores with no recent ad spend are excluded. Click a column header to sort.</footer>
</section>
<section class="panel" id="panel-churn" role="tabpanel">{churn_html}</section>
</div>
<script>const DATA={json.dumps(H)};{_JS}</script>
</body></html>"""


_CSS = r"""
:root{--ink:#0a1024;--paper:#f5f6f9;--card:#fff;--line:#e2e5ee;--muted:#5a6480;--faint:#8b93a8;
--brand:#FD5E35;--navy:#001137;--on:#12805C;--on-bg:#e5f3ec;--buddy:#D6432E;--buddy-bg:#fbe8e4;
--ramp:#B26A00;--ramp-bg:#fbf0dd;--unk:#6b7280;--unk-bg:#eceef2;--churn:#D6432E;--track:#eceef4;
--shadow:0 1px 2px rgba(10,16,36,.06),0 6px 20px rgba(10,16,36,.05);}
@media (prefers-color-scheme:dark){:root{--ink:#eef1f8;--paper:#0a1024;--card:#121a33;--line:#26304f;
--muted:#9aa4c0;--faint:#6b7599;--on:#4cc79a;--on-bg:#123128;--buddy:#ff7a63;--buddy-bg:#3a1a15;
--ramp:#e6a53c;--ramp-bg:#33270f;--unk:#9aa2b8;--unk-bg:#20273d;--churn:#ff7a63;--track:#1c2540;
--shadow:0 1px 2px rgba(0,0,0,.3),0 8px 26px rgba(0,0,0,.35);}}
:root[data-theme=light]{--ink:#0a1024;--paper:#f5f6f9;--card:#fff;--line:#e2e5ee;--muted:#5a6480;--faint:#8b93a8;--on:#12805C;--on-bg:#e5f3ec;--buddy:#D6432E;--buddy-bg:#fbe8e4;--ramp:#B26A00;--ramp-bg:#fbf0dd;--unk:#6b7280;--unk-bg:#eceef2;--churn:#D6432E;--track:#eceef4;}
:root[data-theme=dark]{--ink:#eef1f8;--paper:#0a1024;--card:#121a33;--line:#26304f;--muted:#9aa4c0;--faint:#6b7599;--on:#4cc79a;--on-bg:#123128;--buddy:#ff7a63;--buddy-bg:#3a1a15;--ramp:#e6a53c;--ramp-bg:#33270f;--unk:#9aa2b8;--unk-bg:#20273d;--churn:#ff7a63;--track:#1c2540;}
*{box-sizing:border-box}body{margin:0}
.wrap{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--paper);padding:0 clamp(14px,3vw,40px) 60px;line-height:1.5;-webkit-font-smoothing:antialiased}
.masthead{position:relative;padding:26px 0 18px}
.masthead .rail{position:absolute;left:calc(-1*clamp(14px,3vw,40px));top:0;bottom:0;width:6px;background:var(--brand)}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:12px}
.brandline{font-size:12px;font-weight:700;letter-spacing:.22em;color:var(--brand)}
.who{font-size:12px;color:var(--faint)}.who a{color:var(--brand);text-decoration:none}
h1{font-size:clamp(25px,4.2vw,38px);line-height:1.05;margin:.28em 0 .12em;letter-spacing:-.02em;text-wrap:balance}
.lede{margin:0;color:var(--muted);max-width:66ch;font-size:15px}
.meta{font-size:12.5px;color:var(--faint);margin-top:8px}
.tabs{display:flex;gap:6px;margin:22px 0 20px;border-bottom:1px solid var(--line)}
.tab-btn{font:inherit;font-size:15px;font-weight:650;cursor:pointer;background:none;border:none;color:var(--muted);padding:11px 18px;border-bottom:2.5px solid transparent;margin-bottom:-1px;display:flex;align-items:center;gap:9px}
.tab-btn:hover{color:var(--ink)}.tab-btn[aria-selected=true]{color:var(--ink);border-bottom-color:var(--brand)}
.tab-btn .pillct{font-size:11.5px;font-weight:700;background:var(--track);color:var(--muted);padding:1px 8px;border-radius:999px}
.tab-btn[aria-selected=true] .pillct{background:var(--brand);color:#fff}
.panel{display:none}.panel.active{display:block}
.rulebox{display:flex;gap:14px;align-items:baseline;margin:0 0 20px;padding:13px 16px;background:var(--card);border:1px solid var(--line);border-left:4px solid var(--brand);border-radius:10px;box-shadow:var(--shadow);max-width:74ch}
.rule-k{font-size:11px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:var(--brand);white-space:nowrap}
.rule-v{font-size:14px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:22px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:15px 17px;box-shadow:var(--shadow);position:relative;overflow:hidden}
.kpi .n{font-size:32px;font-weight:800;letter-spacing:-.03em;font-variant-numeric:tabular-nums;line-height:1}
.kpi .l{font-size:12.5px;color:var(--muted);margin-top:6px}.kpi .sub{font-size:11.5px;color:var(--faint);margin-top:2px}
.kpi.flag{border-color:color-mix(in srgb,var(--buddy) 40%,var(--line))}.kpi.flag .n{color:var(--buddy)}
.kpi.flag::after{content:"";position:absolute;top:0;left:0;width:4px;height:100%;background:var(--buddy)}
.kpi.good .n{color:var(--on)}.kpi.churn.flag .n{color:var(--churn)}.kpi.churn.flag::after{background:var(--churn)}
.controls{display:flex;flex-wrap:wrap;gap:14px 20px;justify-content:space-between;align-items:center;margin-bottom:20px}
.filtergroup{display:flex;flex-wrap:wrap;gap:8px}
.fbtn{font:inherit;font-size:12.5px;font-weight:600;cursor:pointer;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--muted);transition:.12s}
.fbtn:hover{border-color:var(--brand);color:var(--ink)}
.fbtn[aria-pressed=true]{background:var(--navy);color:#fff;border-color:var(--navy)}
@media (prefers-color-scheme:dark){.fbtn[aria-pressed=true]{background:var(--brand);border-color:var(--brand);color:#1a0a04}}
.fbtn .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle}
.buyer{margin-bottom:22px;background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);overflow:hidden}
.buyer-head{display:flex;flex-wrap:wrap;align-items:center;gap:12px 18px;padding:15px 20px;border-bottom:1px solid var(--line)}
.buyer-head h2{margin:0;font-size:18px;letter-spacing:-.01em}
.buyer-count{font-size:12.5px;color:var(--faint);font-variant-numeric:tabular-nums}
.breakdown{display:flex;height:8px;border-radius:999px;overflow:hidden;flex:1;min-width:150px;max-width:320px;background:var(--track)}
.breakdown span{display:block}
.mini-legend{display:flex;gap:12px;font-size:11.5px;color:var(--muted);flex-wrap:wrap}.mini-legend b{font-variant-numeric:tabular-nums}
.tablewrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;min-width:620px}
thead th{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--faint);text-align:left;font-weight:700;padding:10px 14px;border-bottom:1px solid var(--line);white-space:nowrap}
.buyer thead th{cursor:pointer;user-select:none}.buyer thead th:hover{color:var(--ink)}
thead th.num{text-align:right}
tbody td{padding:10px 14px;border-bottom:1px solid var(--line);font-size:14px;vertical-align:middle}
.buyer tbody tr:last-child td{border-bottom:none}
.buyer tbody tr:hover td{background:color-mix(in srgb,var(--brand) 5%,transparent)}
.st-stripe{width:4px;padding:0!important;border-bottom:none!important}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.store-name{font-weight:600}
.tenure-badge{display:inline-block;font-size:11px;font-variant-numeric:tabular-nums;color:var(--muted);background:var(--track);padding:2px 8px;border-radius:6px;white-space:nowrap}
.spendcell{display:flex;align-items:center;gap:8px;justify-content:flex-end}
.spendbar{width:70px;height:6px;border-radius:3px;background:var(--track);overflow:hidden;flex:none}.spendbar i{display:block;height:100%}
.spendval{min-width:50px;text-align:right}
.pill{display:inline-block;font-size:11.5px;font-weight:700;padding:3px 9px;border-radius:999px;white-space:nowrap}
.pill.on{background:var(--on-bg);color:var(--on)}.pill.buddy{background:var(--buddy-bg);color:var(--buddy)}
.pill.ramp{background:var(--ramp-bg);color:var(--ramp)}.pill.unk{background:var(--unk-bg);color:var(--unk)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);margin-bottom:22px}
table.matrix{border-collapse:collapse;width:100%;min-width:620px}
.matrix th{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--faint);font-weight:700;padding:14px 10px 12px}
.matrix th.bh{text-align:left;padding-left:20px}.matrix th.mh{text-align:center;width:52px}.matrix th.th{text-align:right;padding-right:20px}
.matrix td{padding:9px 10px;text-align:center;font-variant-numeric:tabular-nums;font-size:14px;border-top:1px solid var(--line)}
.matrix .bname{text-align:left;padding-left:20px;font-weight:600;white-space:nowrap}
.tag{display:inline-block;margin-left:8px;font-size:10px;font-weight:600;letter-spacing:.03em;color:var(--faint);background:var(--track);padding:2px 7px;border-radius:6px;text-transform:uppercase}
.hc{color:#fff;font-weight:700;border-radius:6px;background:color-mix(in srgb,var(--churn) calc(var(--a)*100%),transparent)}
td.z{color:var(--faint)}
.tot{text-align:right;padding-right:20px;white-space:nowrap}.tot b{font-weight:800;font-size:15px}
.tb{display:inline-block;width:44px;height:6px;border-radius:3px;background:var(--track);overflow:hidden;vertical-align:middle;margin-right:8px}.tb i{display:block;height:100%;background:var(--brand)}
.divider td{text-align:left;padding:8px 20px;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--faint);background:color-mix(in srgb,var(--ink) 3%,transparent);border-top:1px solid var(--line)}
tfoot td{border-top:2px solid var(--ink);font-weight:700;padding-top:11px;padding-bottom:12px}.matrix .mt{font-weight:700}
.trend{padding:16px 20px 18px}
.trend-head{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px}.trend-head h2{font-size:15px;margin:0}.trend .meta{margin:0}
.spark{width:100%;height:64px;display:block}.spark polyline{stroke:var(--churn);stroke-width:2;vector-effect:non-scaling-stroke}
.spark .dots circle{fill:var(--churn);opacity:.55}.spark .last{fill:var(--brand)}
.xlabels{display:flex;justify-content:space-between;font-size:11px;color:var(--faint);margin-top:2px}
.foot{margin-top:8px;font-size:12.5px;color:var(--muted);border-top:1px solid var(--line);padding-top:16px;max-width:95ch}
.empty{padding:26px;text-align:center;color:var(--faint);font-size:14px}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.92em;background:var(--track);padding:1px 5px;border-radius:4px}
"""

_JS = r"""
const CLS={ontarget:{k:'on',label:'On target',color:'var(--on)'},buddy:{k:'buddy',label:'Buddy system',color:'var(--buddy)'},ramp:{k:'ramp',label:'Ramp-up',color:'var(--ramp)'},unknown:{k:'unk',label:'No date',color:'var(--unk)'}};
const ORDER={buddy:0,ontarget:1,ramp:2,unknown:3};const TARGET=DATA.target;const eur=n=>'€'+Math.round(n).toLocaleString('en-US');
let buyerSel='all',statusSel='all',sortKey='status',sortDir=1;
function byBuyer(){const m={};DATA.rows.forEach(r=>{(m[r.buyer]=m[r.buyer]||[]).push(r)});return m;}
const t=DATA.totals;
document.getElementById('kpis-health').innerHTML=[{n:DATA.count,l:'Running stores',s:Object.keys(byBuyer()).length+' media buyers',c:''},{n:t.buddy,l:'Need buddy system',s:'≥3 mo & under €1k/day',c:'flag'},{n:t.ontarget,l:'On target',s:'≥€1,000/day',c:'good'},{n:t.ramp,l:'In ramp-up',s:'<3 months',c:''}].map(k=>`<div class="kpi ${k.c}"><div class="n">${k.n}</div><div class="l">${k.l}</div><div class="sub">${k.s}</div></div>`).join('');
const buyers=Object.keys(byBuyer()).sort();
const bf=document.getElementById('buyerFilter');
bf.innerHTML=['all',...buyers].map(b=>`<button class="fbtn" data-buyer="${b}" aria-pressed="${b==='all'}">${b==='all'?'All buyers':b}</button>`).join('');
bf.addEventListener('click',e=>{const b=e.target.closest('[data-buyer]');if(!b)return;buyerSel=b.dataset.buyer;[...bf.children].forEach(c=>c.setAttribute('aria-pressed',c.dataset.buyer===buyerSel));renderH();});
const sf=document.getElementById('statusFilter');
sf.innerHTML=[['all','All statuses',null],['buddy','Buddy system','var(--buddy)'],['ontarget','On target','var(--on)'],['ramp','Ramp-up','var(--ramp)']].map(([k,l,c])=>`<button class="fbtn" data-status="${k}" aria-pressed="${k==='all'}">${c?`<span class="dot" style="background:${c}"></span>`:''}${l}</button>`).join('');
sf.addEventListener('click',e=>{const b=e.target.closest('[data-status]');if(!b)return;statusSel=b.dataset.status;[...sf.children].forEach(c=>c.setAttribute('aria-pressed',c.dataset.status===statusSel));renderH();});
function sortRows(rows){const key=sortKey;return rows.slice().sort((a,b)=>{let av,bv;if(key==='status'){av=ORDER[a.cls];bv=ORDER[b.cls];if(av===bv)return b.avg14-a.avg14;}else if(key==='name'){av=a.name.toLowerCase();bv=b.name.toLowerCase();}else if(key==='tenure'){av=a.months??-1;bv=b.months??-1;}else if(key==='avg14'){av=a.avg14;bv=b.avg14;}else if(key==='avg7'){av=a.avg7;bv=b.avg7;}if(av<bv)return -1*sortDir;if(av>bv)return 1*sortDir;return 0;});}
function spendBar(v){const pct=Math.max(2,Math.min(100,v/TARGET*100));let col='var(--buddy)';if(v>=TARGET)col='var(--on)';else if(v>=TARGET*0.5)col='var(--ramp)';return `<span class="spendbar" title="${Math.round(v/TARGET*100)}% of €1k target"><i style="width:${pct}%;background:${col}"></i></span>`;}
function renderH(){const grouped=byBuyer();const showBuyers=buyerSel==='all'?buyers:[buyerSel];const main=document.getElementById('buyers');main.innerHTML='';let shown=0;
showBuyers.forEach(b=>{let rows=grouped[b]||[];if(statusSel!=='all')rows=rows.filter(r=>r.cls===statusSel);if(!rows.length)return;shown+=rows.length;
const cnt={ontarget:0,buddy:0,ramp:0,unknown:0};(grouped[b]||[]).forEach(r=>cnt[r.cls]++);const total=(grouped[b]||[]).length;
const seg=c=>cnt[c]?`<span style="width:${cnt[c]/total*100}%;background:${CLS[c].color}"></span>`:'';
const rowsHtml=sortRows(rows).map(r=>{const c=CLS[r.cls];const tenure=r.months==null?'—':`${r.months} mo`;
return `<tr><td class="st-stripe" style="background:${c.color}"></td><td class="store-name">${r.name}</td><td>${r.onboarding}</td><td><span class="tenure-badge">${tenure}</span></td><td class="num"><div class="spendcell">${spendBar(r.avg14)}<span class="spendval">${eur(r.avg14)}</span></div></td><td class="num">${eur(r.avg7)}</td><td><span class="pill ${c.k}">${c.label}</span></td></tr>`;}).join('');
main.insertAdjacentHTML('beforeend',`<section class="buyer"><div class="buyer-head"><h2>${b}</h2><span class="buyer-count">${total} store${total!==1?'s':''}</span><div class="breakdown">${['buddy','ontarget','ramp','unknown'].map(seg).join('')}</div><div class="mini-legend"><span style="color:var(--buddy)">● <b>${cnt.buddy}</b> buddy</span><span style="color:var(--on)">● <b>${cnt.ontarget}</b> on target</span><span style="color:var(--ramp)">● <b>${cnt.ramp}</b> ramp</span></div></div><div class="tablewrap"><table><thead><tr><th class="st-stripe"></th><th data-sort="name">Store</th><th>Onboarded</th><th data-sort="tenure">Tenure</th><th class="num" data-sort="avg14">Avg €/day · 14d</th><th class="num" data-sort="avg7">7d</th><th data-sort="status">Status</th></tr></thead><tbody>${rowsHtml}</tbody></table></div></section>`);});
if(!shown)main.innerHTML='<div class="empty">No stores match this filter.</div>';
main.querySelectorAll('th[data-sort]').forEach(th=>th.addEventListener('click',()=>{const k=th.dataset.sort;if(sortKey===k)sortDir*=-1;else{sortKey=k;sortDir=(k==='name')?1:-1;}renderH();}));}
renderH();
document.querySelectorAll('.tab-btn').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('.tab-btn').forEach(b=>b.setAttribute('aria-selected',b===btn));document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active',p.id==='panel-'+btn.dataset.tab));}));
"""
