"""
admin.py — Cellyn Store Admin Panel
Jalankan: python admin.py
Akses: http://localhost:5000
Password default: cellyn123 (ubah via env ADMIN_PASSWORD)
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("ADMIN_SECRET", "cellyn-admin-secret-2024")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "cellyn123")
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "midman.db")


# ── DB ────────────────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def safe_int(val, min_val=None):
    """Konversi string ke int dengan aman. Return None jika tidak valid."""
    try:
        v = int(str(val).strip())
        if min_val is not None and v < min_val:
            return None
        return v
    except (ValueError, TypeError):
        return None


# ── AUTH ──────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── BASE TEMPLATE ─────────────────────────────────────────────────────────────
BASE = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cellyn Admin</title>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#080c14;--surface:#0e1420;--surface2:#141c2e;--surface3:#1a2438;
  --border:#1e2d47;--border2:#253550;
  --gold:#c9a84c;--gold2:#e8c96a;--gold3:#a07830;
  --text:#e8eaf0;--muted:#6a7a95;--muted2:#8a9ab5;
  --danger:#e05555;--success:#4dbb8a;--warning:#e09440;
  --sidebar-w:240px;
}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Plus Jakarta Sans',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;}
a{color:var(--gold);text-decoration:none;}

/* ── SIDEBAR ── */
.sidebar{width:var(--sidebar-w);min-height:100vh;background:var(--surface);border-right:1px solid var(--border);
  display:flex;flex-direction:column;position:fixed;top:0;left:0;z-index:200;transition:transform .25s ease;}
.sidebar-logo{padding:1.5rem 1.25rem;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:.75rem;}
.sidebar-logo img{width:38px;height:38px;border-radius:8px;object-fit:cover;}
.sidebar-logo-text{font-family:'Cormorant Garamond',serif;font-size:1.1rem;font-weight:700;letter-spacing:.04em;line-height:1.1;}
.sidebar-logo-text span{display:block;font-size:.65rem;font-weight:400;color:var(--gold);letter-spacing:.15em;text-transform:uppercase;font-family:'Plus Jakarta Sans',sans-serif;}
.sidebar-nav{flex:1;padding:1rem 0;overflow-y:auto;}
.nav-section{padding:.35rem 1.25rem;font-size:.6rem;font-weight:600;color:var(--muted);letter-spacing:.15em;text-transform:uppercase;margin-top:.75rem;}
.nav-item{display:flex;align-items:center;gap:.75rem;padding:.6rem 1.25rem;color:var(--muted2);font-size:.82rem;font-weight:500;
  transition:all .15s;cursor:pointer;border-left:2px solid transparent;margin:1px 0;}
.nav-item:hover{color:var(--text);background:var(--surface2);border-left-color:var(--border2);}
.nav-item.active{color:var(--gold);background:linear-gradient(90deg,rgba(201,168,76,.1),transparent);border-left-color:var(--gold);}
.nav-item svg{width:15px;height:15px;flex-shrink:0;opacity:.7;}
.nav-item.active svg{opacity:1;}
.sidebar-footer{padding:1rem 1.25rem;border-top:1px solid var(--border);}
.nav-logout{display:flex;align-items:center;gap:.75rem;padding:.6rem .75rem;border-radius:8px;color:var(--danger);font-size:.82rem;
  font-weight:500;transition:all .15s;cursor:pointer;background:rgba(224,85,85,.05);border:1px solid rgba(224,85,85,.15);}
.nav-logout:hover{background:rgba(224,85,85,.12);color:var(--danger);}
.nav-logout svg{width:15px;height:15px;}

/* ── TOPBAR MOBILE ── */
.topbar{display:none;height:56px;background:var(--surface);border-bottom:1px solid var(--border);
  padding:0 1rem;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:150;}
.topbar-logo{font-family:'Cormorant Garamond',serif;font-size:1rem;font-weight:700;}
.topbar-logo span{color:var(--gold);}
.hamburger{background:none;border:none;color:var(--text);cursor:pointer;padding:.4rem;}
.hamburger svg{width:22px;height:22px;}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:190;backdrop-filter:blur(2px);}
.sidebar-overlay.active{display:block;}

/* ── MAIN CONTENT ── */
.main{margin-left:var(--sidebar-w);flex:1;min-height:100vh;display:flex;flex-direction:column;}
.content{flex:1;padding:2rem;}

/* ── PAGE HEADER ── */
.page-header{margin-bottom:1.75rem;}
.page-title{font-family:'Cormorant Garamond',serif;font-size:1.8rem;font-weight:700;letter-spacing:.02em;color:var(--text);}
.page-title small{display:block;font-family:'Plus Jakarta Sans',sans-serif;font-size:.72rem;font-weight:400;color:var(--muted);margin-top:.2rem;letter-spacing:.05em;}
.page-actions{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:1rem;}

/* ── CARDS ── */
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:1.25rem;}
.card-header{padding:.85rem 1.25rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--surface2);}
.card-title{font-size:.72rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);}
.card-body{padding:1.25rem;}

/* ── STAT CARDS ── */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1rem;margin-bottom:1.5rem;}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1.25rem;position:relative;overflow:hidden;transition:border-color .2s;}
.stat-card:hover{border-color:var(--border2);}
.stat-card::after{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;}
.stat-card.ml::after{background:linear-gradient(90deg,#3498DB,transparent);}
.stat-card.ff::after{background:linear-gradient(90deg,#FF6B35,transparent);}
.stat-card.robux::after{background:linear-gradient(90deg,#E91E63,transparent);}
.stat-card.vilog::after{background:linear-gradient(90deg,var(--gold),transparent);}
.stat-card.autopost::after{background:linear-gradient(90deg,var(--success),transparent);}
.stat-icon{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;margin-bottom:.75rem;font-size:1rem;}
.stat-label{font-size:.68rem;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;font-weight:500;}
.stat-value{font-family:'Cormorant Garamond',serif;font-size:2.2rem;font-weight:700;margin-top:.15rem;line-height:1;}
.stat-sub{font-size:.72rem;color:var(--muted);margin-top:.3rem;}

/* ── TABLE ── */
table{width:100%;border-collapse:collapse;}
th{text-align:left;padding:.7rem 1.25rem;font-size:.67rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);border-bottom:1px solid var(--border);font-weight:600;}
td{padding:.8rem 1.25rem;border-bottom:1px solid rgba(30,45,71,.6);font-size:.83rem;vertical-align:middle;}
tr:last-child td{border-bottom:none;}
tr:hover td{background:rgba(201,168,76,.03);}

/* ── BADGE ── */
.badge{display:inline-flex;align-items:center;padding:.2rem .55rem;border-radius:4px;font-size:.67rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;}
.badge-gamepass{background:rgba(124,106,255,.12);color:#a090ff;border:1px solid rgba(124,106,255,.25);}
.badge-crate{background:rgba(255,107,157,.12);color:#ff8ab5;border:1px solid rgba(255,107,157,.25);}
.badge-boost{background:rgba(201,168,76,.12);color:var(--gold2);border:1px solid rgba(201,168,76,.25);}
.badge-limited{background:rgba(77,187,138,.12);color:#5dd4a0;border:1px solid rgba(77,187,138,.25);}
.badge-ml{background:rgba(52,152,219,.12);color:#60aadb;border:1px solid rgba(52,152,219,.25);}
.badge-ff{background:rgba(255,107,53,.12);color:#ff8860;border:1px solid rgba(255,107,53,.25);}
.badge-vilog{background:rgba(201,168,76,.12);color:var(--gold);border:1px solid rgba(201,168,76,.25);}
.badge-aktif{background:rgba(77,187,138,.12);color:var(--success);border:1px solid rgba(77,187,138,.25);}
.badge-nonaktif{background:rgba(224,85,85,.12);color:var(--danger);border:1px solid rgba(224,85,85,.25);}

/* ── BUTTONS ── */
.btn{display:inline-flex;align-items:center;gap:.4rem;padding:.5rem 1rem;border-radius:8px;
  font-family:'Plus Jakarta Sans',sans-serif;font-size:.78rem;font-weight:500;cursor:pointer;border:none;transition:all .15s;text-decoration:none;}
.btn-primary{background:linear-gradient(135deg,var(--gold),var(--gold3));color:#0a0c14;font-weight:600;}
.btn-primary:hover{background:linear-gradient(135deg,var(--gold2),var(--gold));color:#0a0c14;}
.btn-danger{background:rgba(224,85,85,.1);color:var(--danger);border:1px solid rgba(224,85,85,.25);}
.btn-danger:hover{background:rgba(224,85,85,.2);}
.btn-ghost{background:var(--surface2);color:var(--muted2);border:1px solid var(--border);}
.btn-ghost:hover{color:var(--text);border-color:var(--border2);}
.btn-success{background:rgba(77,187,138,.1);color:var(--success);border:1px solid rgba(77,187,138,.25);}
.btn-success:hover{background:rgba(77,187,138,.2);}
.btn-warning{background:rgba(224,148,64,.1);color:var(--warning);border:1px solid rgba(224,148,64,.25);}
.btn-warning:hover{background:rgba(224,148,64,.2);}
.btn-sm{padding:.3rem .65rem;font-size:.73rem;}

/* ── FORMS ── */
.form-grid{display:grid;gap:1rem;}.form-grid-2{grid-template-columns:1fr 1fr;}
.form-group{display:flex;flex-direction:column;gap:.4rem;}
label{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.09em;font-weight:600;}
input,select,textarea{background:var(--surface2);border:1px solid var(--border);border-radius:8px;
  padding:.6rem .9rem;color:var(--text);font-family:'Plus Jakarta Sans',sans-serif;font-size:.83rem;
  transition:border-color .15s;width:100%;}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--gold3);background:rgba(201,168,76,.04);}
select option{background:var(--surface2);}
textarea{resize:vertical;min-height:80px;}
.form-actions{display:flex;gap:.75rem;margin-top:.5rem;}

/* ── RATE DISPLAY ── */
.rate-display{background:var(--surface2);border:1px solid var(--border);border-radius:10px;
  padding:1rem 1.25rem;display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin-bottom:1.25rem;}
.rate-value{font-family:'Cormorant Garamond',serif;font-size:1.6rem;font-weight:700;color:var(--gold);}

/* ── MODAL ── */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:1000;
  align-items:center;justify-content:center;backdrop-filter:blur(5px);padding:1rem;}
.modal-overlay.active{display:flex;}
.modal{background:var(--surface);border:1px solid var(--border);border-radius:16px;
  padding:1.75rem;width:100%;max-width:480px;animation:modalIn .2s ease;}
@keyframes modalIn{from{opacity:0;transform:scale(.96) translateY(8px)}to{opacity:1;transform:scale(1) translateY(0)}}
.modal-title{font-family:'Cormorant Garamond',serif;font-size:1.2rem;font-weight:700;margin-bottom:1.5rem;color:var(--text);}

/* ── FLASH ── */
.flash-list{list-style:none;margin-bottom:1.25rem;}
.flash{padding:.7rem 1rem;border-radius:8px;font-size:.82rem;margin-bottom:.4rem;font-weight:500;}
.flash-success{background:rgba(77,187,138,.1);border:1px solid rgba(77,187,138,.25);color:var(--success);}
.flash-error{background:rgba(224,85,85,.1);border:1px solid rgba(224,85,85,.25);color:var(--danger);}

/* ── MISC ── */
.empty{text-align:center;padding:3rem;color:var(--muted);font-size:.83rem;}
.note{margin-top:1rem;padding:.9rem 1.25rem;background:var(--surface2);border-radius:8px;border:1px solid var(--border);font-size:.78rem;color:var(--muted);}
.inline-form{display:flex;gap:.5rem;align-items:center;}
.inline-form input{width:auto;min-width:80px;}
.divider{height:1px;background:var(--border);margin:1.25rem 0;}
code{background:var(--surface3);padding:.1rem .4rem;border-radius:4px;font-size:.8rem;color:var(--muted2);}

/* ── MOBILE ── */
@media(max-width:768px){
  .sidebar{transform:translateX(-100%);}
  .sidebar.open{transform:translateX(0);}
  .topbar{display:flex;}
  .main{margin-left:0;}
  .content{padding:1rem;}
  .form-grid-2{grid-template-columns:1fr;}
  .stats-grid{grid-template-columns:1fr 1fr;}
  th,td{padding:.6rem .75rem;}
  .page-title{font-size:1.4rem;}
  table{font-size:.78rem;}
}
@media(max-width:480px){
  .stats-grid{grid-template-columns:1fr;}
}
</style>
</head>
<body>
<!-- Sidebar Overlay -->
<div class="sidebar-overlay" id="sidebarOverlay" onclick="closeSidebar()"></div>

<!-- Sidebar -->
NAVPLACEHOLDER

<!-- Main -->
<div class="main">
  <!-- Topbar Mobile -->
  <div class="topbar">
    <div class="topbar-logo">CELLYN <span>ADMIN</span></div>
    <button class="hamburger" onclick="toggleSidebar()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
      </svg>
    </button>
  </div>
  <div class="content">
    FLASHPLACEHOLDER
    CONTENTPLACEHOLDER
  </div>
</div>

<script>
function toggleSidebar(){
  document.querySelector('.sidebar').classList.toggle('open');
  document.getElementById('sidebarOverlay').classList.toggle('active');
}
function closeSidebar(){
  document.querySelector('.sidebar').classList.remove('open');
  document.getElementById('sidebarOverlay').classList.remove('active');
}
function openModal(id){document.getElementById(id).classList.add('active');}
function closeModal(id){document.getElementById(id).classList.remove('active');}
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){
    document.querySelectorAll('.modal-overlay.active').forEach(m=>m.classList.remove('active'));
    closeSidebar();
  }
});
document.querySelectorAll('.modal-overlay').forEach(m=>{
  m.addEventListener('click',e=>{if(e.target===m)m.classList.remove('active');});
});
</script>
</body>
</html>"""


def render_page(content, **ctx):
    from flask import get_flashed_messages
    nav = ""
    if session.get("logged_in"):
        ep = request.endpoint
        def _a(label, href, icon, ep_name):
            active = "active" if ep == ep_name else ""
            return f'''<a href="{href}" class="nav-item {active}">
              {icon}<span>{label}</span>
            </a>'''
        ico_dash  = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>'
        ico_ml    = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M12 8v4l3 3"/></svg>'
        ico_ff    = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>'
        ico_robux = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>'
        ico_vilog = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/><circle cx="18" cy="5" r="3" fill="currentColor" opacity=".3"/></svg>'
        ico_auto  = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.8a19.79 19.79 0 01-3.07-8.72A2 2 0 012 1h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.09 8.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>'
        ico_out   = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>'
        nav = f'''<aside class="sidebar">
  <div class="sidebar-logo">
    <img src="https://i.imgur.com/xp2F452.png" alt="Cellyn">
    <div class="sidebar-logo-text">Cellyn Admin<span>Store Management</span></div>
  </div>
  <nav class="sidebar-nav">
    <div class="nav-section">Menu</div>
    {_a("Dashboard", "/", ico_dash, "index")}
    <div class="nav-section">Produk</div>
    {_a("Mobile Legends", "/ml", ico_ml, "page_ml")}
    {_a("Free Fire", "/ff", ico_ff, "page_ff")}
    {_a("Robux Store", "/robux", ico_robux, "page_robux")}
    {_a("Vilog", "/vilog", ico_vilog, "page_vilog")}
    <div class="nav-section">Tools</div>
    {_a("Autopost", "/autopost", ico_auto, "page_autopost")}
  </nav>
  <div class="sidebar-footer">
    <a href="/logout" class="nav-logout">{ico_out}<span>Logout</span></a>
  </div>
</aside>'''
    msgs = get_flashed_messages(with_categories=True)
    flash_html = ""
    if msgs:
        flash_html = '<ul class="flash-list">'
        for cat, msg in msgs:
            flash_html += f'<li class="flash flash-{cat}">{msg}</li>'
        flash_html += '</ul>'
    html = BASE.replace("NAVPLACEHOLDER", nav).replace("FLASHPLACEHOLDER", flash_html).replace("CONTENTPLACEHOLDER", content)
    return render_template_string(html, **ctx)


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form.get("password", "").strip() == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Password salah."
    content = f"""
<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;padding:1rem;
  background:radial-gradient(ellipse at 30% 40%,rgba(201,168,76,.06) 0%,transparent 60%),
             radial-gradient(ellipse at 80% 80%,rgba(201,168,76,.03) 0%,transparent 50%);">
  <div style="width:100%;max-width:380px;">
    <div style="text-align:center;margin-bottom:2rem;">
      <img src="https://i.imgur.com/xp2F452.png" alt="Cellyn" style="width:72px;height:72px;border-radius:16px;margin-bottom:1rem;box-shadow:0 8px 32px rgba(201,168,76,.2);">
      <div style="font-family:'Cormorant Garamond',serif;font-size:1.8rem;font-weight:700;letter-spacing:.04em;">Cellyn Admin</div>
      <div style="color:var(--muted);font-size:.75rem;margin-top:.3rem;letter-spacing:.1em;text-transform:uppercase;">Store Management Panel</div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Login</span></div>
      <div style="padding:1.5rem;">
        <form method="post">
          <div class="form-group" style="margin-bottom:1.25rem;">
            <label>Password Admin</label>
            <input type="password" name="password" placeholder="••••••••" autofocus required>
          </div>
          {'<div class="flash flash-error" style="margin-bottom:1rem;">'+error+'</div>' if error else ''}
          <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;padding:.7rem;">
            Masuk
          </button>
        </form>
      </div>
    </div>
  </div>
</div>"""
    return render_page(content)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    conn = get_conn()
    ml_count = conn.execute("SELECT COUNT(*) FROM ml_products").fetchone()[0]
    ff_count = conn.execute("SELECT COUNT(*) FROM ff_products").fetchone()[0]
    robux_count = conn.execute("SELECT COUNT(*) FROM robux_products WHERE active=1").fetchone()[0]
    vilog_count = conn.execute("SELECT COUNT(*) FROM vilog_boosts WHERE active=1").fetchone()[0]
    row = conn.execute("SELECT rate FROM robux_rate WHERE id=1").fetchone()
    rate = row[0] if row else 0
    conn.close()
    rate_str = f"Rp {rate:,}" if rate else "Belum diset"
    content = f"""
<div class="page-header">
  <div class="page-title">Dashboard <small>Ringkasan produk aktif</small></div>
</div>
<div class="stats-grid">
  <div class="stat-card ml"><div class="stat-label">Mobile Legends</div>
    <div class="stat-value">{ml_count}</div><div class="stat-sub">produk aktif</div></div>
  <div class="stat-card ff"><div class="stat-label">Free Fire</div>
    <div class="stat-value">{ff_count}</div><div class="stat-sub">produk aktif</div></div>
  <div class="stat-card robux"><div class="stat-label">Robux Store</div>
    <div class="stat-value">{robux_count}</div><div class="stat-sub">item aktif</div></div>
  <div class="stat-card vilog"><div class="stat-label">Vilog Boost</div>
    <div class="stat-value">{vilog_count}</div><div class="stat-sub">paket aktif</div></div>
</div>
<div class="card">
  <div class="card-header"><span class="card-title">Rate Robux</span></div>
  <div style="padding:1.5rem;">
    <div class="rate-display">
      <div>
        <div style="font-size:.75rem;color:var(--muted);margin-bottom:.25rem;">Rate saat ini</div>
        <div class="rate-value">{rate_str}<span style="font-size:.9rem;color:var(--muted);font-weight:400">/Robux</span></div>
      </div>
      <form method="post" action="/robux/rate" class="inline-form">
        <input type="number" name="rate" placeholder="Rate baru" min="1" style="width:140px;" required>
        <button type="submit" class="btn btn-primary btn-sm">Update</button>
      </form>
    </div>
  </div>
</div>"""
    return render_page(content)


# ── ML ─────────────────────────────────────────────────────────────────────────
@app.route("/ml")
@login_required
def page_ml():
    conn = get_conn()
    # Safe migration: buat tabel wdp_products kalau belum ada
    conn.execute("""CREATE TABLE IF NOT EXISTS wdp_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        qty INTEGER NOT NULL,
        label TEXT NOT NULL,
        harga INTEGER NOT NULL
    )""")
    # Seed data default kalau kosong
    if conn.execute("SELECT COUNT(*) FROM wdp_products").fetchone()[0] == 0:
        conn.executemany("INSERT INTO wdp_products (qty, label, harga) VALUES (?,?,?)", [
            (1, "1x Weekly Diamond Pass", 29000),
            (2, "2x Weekly Diamond Pass", 57000),
            (3, "3x Weekly Diamond Pass", 86000),
        ])
    conn.commit()
    products = conn.execute("SELECT * FROM ml_products ORDER BY dm").fetchall()
    wdp_products = conn.execute("SELECT * FROM wdp_products ORDER BY qty").fetchall()
    conn.close()
    rows = "".join(f"""<tr>
      <td style="color:var(--muted)">{i+1}</td>
      <td><span class="badge badge-ml">{p['dm']} DM</span></td>
      <td>Rp {p['harga']:,}</td>
      <td><div style="display:flex;gap:.5rem;">
        <button class="btn btn-ghost btn-sm" onclick="openEditML({p['id']},{p['dm']},{p['harga']})">Edit</button>
        <form method="post" action="/ml/delete/{p['id']}" style="display:inline;" onsubmit="return confirm('Hapus produk ini?')">
          <button type="submit" class="btn btn-danger btn-sm">Hapus</button>
        </form>
      </div></td>
    </tr>""" for i, p in enumerate(products)) or '<tr><td colspan="4" class="empty">Belum ada produk ML</td></tr>'
    content = f"""
<div class="page-header">
  <div class="page-title">Mobile Legends <small>{len(products)} produk</small></div>
  <button class="btn btn-primary" onclick="openModal('modal-add-ml')">+ Tambah Produk</button>
</div>
<div class="card"><table>
  <thead><tr><th>#</th><th>Diamond (DM)</th><th>Harga</th><th>Aksi</th></tr></thead>
  <tbody>{rows}</tbody>
</table></div>
<div class="page-header" style="margin-top:2rem;">
  <div class="page-title" style="font-size:1.2rem;">Weekly Diamond Pass <small>Harga WDP</small></div>
  <button class="btn btn-primary" onclick="openModal('modal-add-wdp')">+ Tambah WDP</button>
</div>
<div class="card"><table>
  <thead><tr><th>#</th><th>Label</th><th>Qty Pass</th><th>Harga</th><th>Aksi</th></tr></thead>
  <tbody>WDP_ROWS_PLACEHOLDER</tbody>
</table></div>
<div class="modal-overlay" id="modal-add-wdp"><div class="modal">
  <div class="modal-title">Tambah Paket WDP</div>
  <form method="post" action="/ml/wdp/add">
    <div class="form-grid">
      <div class="form-group"><label>Label</label><input type="text" name="label" placeholder="contoh: 1x Weekly Diamond Pass" required></div>
      <div class="form-grid form-grid-2">
        <div class="form-group"><label>Qty Pass</label><input type="number" name="qty" placeholder="contoh: 1" min="1" required></div>
        <div class="form-group"><label>Harga (Rp)</label><input type="number" name="harga" placeholder="contoh: 29000" min="1" required></div>
      </div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-add-wdp')">Batal</button>
    </div>
  </form>
</div></div>
<div class="modal-overlay" id="modal-edit-wdp"><div class="modal">
  <div class="modal-title">Edit Paket WDP</div>
  <form method="post" action="/ml/wdp/edit">
    <input type="hidden" name="id" id="edit-wdp-id">
    <div class="form-grid">
      <div class="form-group"><label>Label</label><input type="text" name="label" id="edit-wdp-label" required></div>
      <div class="form-grid form-grid-2">
        <div class="form-group"><label>Qty Pass</label><input type="number" name="qty" id="edit-wdp-qty" min="1" required></div>
        <div class="form-group"><label>Harga (Rp)</label><input type="number" name="harga" id="edit-wdp-harga" min="1" required></div>
      </div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-edit-wdp')">Batal</button>
    </div>
  </form>
</div></div>
<script>
function openEditWDP(id,label,qty,harga){{
  document.getElementById('edit-wdp-id').value=id;
  document.getElementById('edit-wdp-label').value=label;
  document.getElementById('edit-wdp-qty').value=qty;
  document.getElementById('edit-wdp-harga').value=harga;
  openModal('modal-edit-wdp');
}}
</script>
<div class="modal-overlay" id="modal-add-ml"><div class="modal">
  <div class="modal-title">Tambah Produk ML</div>
  <form method="post" action="/ml/add">
    <div class="form-grid form-grid-2">
      <div class="form-group"><label>Diamond (DM)</label><input type="number" name="dm" placeholder="contoh: 150" min="1" required></div>
      <div class="form-group"><label>Harga (Rp)</label><input type="number" name="harga" placeholder="contoh: 35000" min="1" required></div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-add-ml')">Batal</button>
    </div>
  </form>
</div></div>
<div class="modal-overlay" id="modal-edit-ml"><div class="modal">
  <div class="modal-title">Edit Produk ML</div>
  <form method="post" action="/ml/edit">
    <input type="hidden" name="id" id="edit-ml-id">
    <div class="form-grid form-grid-2">
      <div class="form-group"><label>Diamond (DM)</label><input type="number" name="dm" id="edit-ml-dm" min="1" required></div>
      <div class="form-group"><label>Harga (Rp)</label><input type="number" name="harga" id="edit-ml-harga" min="1" required></div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-edit-ml')">Batal</button>
    </div>
  </form>
</div></div>
<script>
function openEditML(id,dm,harga){{
  document.getElementById('edit-ml-id').value=id;
  document.getElementById('edit-ml-dm').value=dm;
  document.getElementById('edit-ml-harga').value=harga;
  openModal('modal-edit-ml');
}}
</script>"""
    wdp_rows = "".join(f"""<tr>
      <td style="color:var(--muted)">{i+1}</td>
      <td><span class="badge badge-ml">{p['label']}</span></td>
      <td>{p['qty']}x</td>
      <td>Rp {p['harga']:,}</td>
      <td><div style="display:flex;gap:.5rem;">
        <button class="btn btn-ghost btn-sm" onclick="openEditWDP({p['id']},'{p['label']}',{p['qty']},{p['harga']})">Edit</button>
        <form method="post" action="/ml/wdp/delete/{p['id']}" style="display:inline;" onsubmit="return confirm('Hapus paket WDP ini?')">
          <button type="submit" class="btn btn-danger btn-sm">Hapus</button>
        </form>
      </div></td>
    </tr>""" for i, p in enumerate(wdp_products)) or '<tr><td colspan="5" class="empty">Belum ada paket WDP</td></tr>'
    content = content.replace("WDP_ROWS_PLACEHOLDER", wdp_rows)
    return render_page(content)


@app.route("/ml/add", methods=["POST"])
@login_required
def ml_add():
    dm = safe_int(request.form.get("dm"), min_val=1)
    harga = safe_int(request.form.get("harga"), min_val=1)
    if dm is None or harga is None:
        flash("Input tidak valid. DM dan Harga harus angka positif.", "error")
        return redirect(url_for("page_ml"))
    conn = get_conn()
    if conn.execute("SELECT id FROM ml_products WHERE dm=?", (dm,)).fetchone():
        flash(f"Produk {dm} DM sudah ada. Gunakan Edit untuk mengubah harga.", "error")
        conn.close(); return redirect(url_for("page_ml"))
    conn.execute("INSERT INTO ml_products (dm, harga) VALUES (?,?)", (dm, harga))
    conn.commit(); conn.close()
    flash(f"Produk {dm} DM berhasil ditambahkan.", "success")
    return redirect(url_for("page_ml"))


@app.route("/ml/edit", methods=["POST"])
@login_required
def ml_edit():
    pid = safe_int(request.form.get("id"), min_val=1)
    dm = safe_int(request.form.get("dm"), min_val=1)
    harga = safe_int(request.form.get("harga"), min_val=1)
    if None in (pid, dm, harga):
        flash("Input tidak valid.", "error")
        return redirect(url_for("page_ml"))
    conn = get_conn()
    conn.execute("UPDATE ml_products SET dm=?, harga=? WHERE id=?", (dm, harga, pid))
    conn.commit(); conn.close()
    flash("Produk ML berhasil diupdate.", "success")
    return redirect(url_for("page_ml"))


@app.route("/ml/delete/<int:pid>", methods=["POST"])
@login_required
def ml_delete(pid):
    conn = get_conn()
    conn.execute("DELETE FROM ml_products WHERE id=?", (pid,))
    conn.commit(); conn.close()
    flash("Produk ML berhasil dihapus.", "success")
    return redirect(url_for("page_ml"))


# ── WDP ────────────────────────────────────────────────────────────────────────
@app.route("/ml/wdp/add", methods=["POST"])
@login_required
def wdp_add():
    qty = safe_int(request.form.get("qty"), min_val=1)
    label = request.form.get("label", "").strip()
    harga = safe_int(request.form.get("harga"), min_val=1)
    if qty is None or not label or harga is None:
        flash("Input tidak valid.", "error")
        return redirect(url_for("page_ml"))
    conn = get_conn()
    conn.execute("INSERT INTO wdp_products (qty, label, harga) VALUES (?,?,?)", (qty, label, harga))
    conn.commit(); conn.close()
    flash(f"Paket WDP {label} berhasil ditambahkan.", "success")
    return redirect(url_for("page_ml"))


@app.route("/ml/wdp/edit", methods=["POST"])
@login_required
def wdp_edit():
    pid = safe_int(request.form.get("id"), min_val=1)
    qty = safe_int(request.form.get("qty"), min_val=1)
    label = request.form.get("label", "").strip()
    harga = safe_int(request.form.get("harga"), min_val=1)
    if None in (pid, qty, harga) or not label:
        flash("Input tidak valid.", "error")
        return redirect(url_for("page_ml"))
    conn = get_conn()
    conn.execute("UPDATE wdp_products SET qty=?, label=?, harga=? WHERE id=?", (qty, label, harga, pid))
    conn.commit(); conn.close()
    flash("Paket WDP berhasil diupdate.", "success")
    return redirect(url_for("page_ml"))


@app.route("/ml/wdp/delete/<int:pid>", methods=["POST"])
@login_required
def wdp_delete(pid):
    conn = get_conn()
    conn.execute("DELETE FROM wdp_products WHERE id=?", (pid,))
    conn.commit(); conn.close()
    flash("Paket WDP berhasil dihapus.", "success")
    return redirect(url_for("page_ml"))


# ── FF ─────────────────────────────────────────────────────────────────────────
@app.route("/ff")
@login_required
def page_ff():
    conn = get_conn()
    products = conn.execute("SELECT * FROM ff_products ORDER BY dm").fetchall()
    conn.close()
    rows = "".join(f"""<tr>
      <td style="color:var(--muted)">{i+1}</td>
      <td><span class="badge badge-ff">{p['dm']} DM</span></td>
      <td>Rp {p['harga']:,}</td>
      <td><div style="display:flex;gap:.5rem;">
        <button class="btn btn-ghost btn-sm" onclick="openEditFF({p['id']},{p['dm']},{p['harga']})">Edit</button>
        <form method="post" action="/ff/delete/{p['id']}" style="display:inline;" onsubmit="return confirm('Hapus produk ini?')">
          <button type="submit" class="btn btn-danger btn-sm">Hapus</button>
        </form>
      </div></td>
    </tr>""" for i, p in enumerate(products)) or '<tr><td colspan="4" class="empty">Belum ada produk FF</td></tr>'
    content = f"""
<div class="page-header">
  <div class="page-title">Free Fire <small>{len(products)} produk</small></div>
  <button class="btn btn-primary" onclick="openModal('modal-add-ff')">+ Tambah Produk</button>
</div>
<div class="card"><table>
  <thead><tr><th>#</th><th>Diamond (DM)</th><th>Harga</th><th>Aksi</th></tr></thead>
  <tbody>{rows}</tbody>
</table></div>
<div class="modal-overlay" id="modal-add-ff"><div class="modal">
  <div class="modal-title">Tambah Produk FF</div>
  <form method="post" action="/ff/add">
    <div class="form-grid form-grid-2">
      <div class="form-group"><label>Diamond (DM)</label><input type="number" name="dm" placeholder="contoh: 100" min="1" required></div>
      <div class="form-group"><label>Harga (Rp)</label><input type="number" name="harga" placeholder="contoh: 12000" min="1" required></div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-add-ff')">Batal</button>
    </div>
  </form>
</div></div>
<div class="modal-overlay" id="modal-edit-ff"><div class="modal">
  <div class="modal-title">Edit Produk FF</div>
  <form method="post" action="/ff/edit">
    <input type="hidden" name="id" id="edit-ff-id">
    <div class="form-grid form-grid-2">
      <div class="form-group"><label>Diamond (DM)</label><input type="number" name="dm" id="edit-ff-dm" min="1" required></div>
      <div class="form-group"><label>Harga (Rp)</label><input type="number" name="harga" id="edit-ff-harga" min="1" required></div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-edit-ff')">Batal</button>
    </div>
  </form>
</div></div>
<script>
function openEditFF(id,dm,harga){{
  document.getElementById('edit-ff-id').value=id;
  document.getElementById('edit-ff-dm').value=dm;
  document.getElementById('edit-ff-harga').value=harga;
  openModal('modal-edit-ff');
}}
</script>"""
    return render_page(content)


@app.route("/ff/add", methods=["POST"])
@login_required
def ff_add():
    dm = safe_int(request.form.get("dm"), min_val=1)
    harga = safe_int(request.form.get("harga"), min_val=1)
    if dm is None or harga is None:
        flash("Input tidak valid. DM dan Harga harus angka positif.", "error")
        return redirect(url_for("page_ff"))
    conn = get_conn()
    if conn.execute("SELECT id FROM ff_products WHERE dm=?", (dm,)).fetchone():
        flash(f"Produk {dm} DM FF sudah ada. Gunakan Edit.", "error")
        conn.close(); return redirect(url_for("page_ff"))
    conn.execute("INSERT INTO ff_products (dm, harga) VALUES (?,?)", (dm, harga))
    conn.commit(); conn.close()
    flash(f"Produk {dm} DM FF berhasil ditambahkan.", "success")
    return redirect(url_for("page_ff"))


@app.route("/ff/edit", methods=["POST"])
@login_required
def ff_edit():
    pid = safe_int(request.form.get("id"), min_val=1)
    dm = safe_int(request.form.get("dm"), min_val=1)
    harga = safe_int(request.form.get("harga"), min_val=1)
    if None in (pid, dm, harga):
        flash("Input tidak valid.", "error")
        return redirect(url_for("page_ff"))
    conn = get_conn()
    conn.execute("UPDATE ff_products SET dm=?, harga=? WHERE id=?", (dm, harga, pid))
    conn.commit(); conn.close()
    flash("Produk FF berhasil diupdate.", "success")
    return redirect(url_for("page_ff"))


@app.route("/ff/delete/<int:pid>", methods=["POST"])
@login_required
def ff_delete(pid):
    conn = get_conn()
    conn.execute("DELETE FROM ff_products WHERE id=?", (pid,))
    conn.commit(); conn.close()
    flash("Produk FF berhasil dihapus.", "success")
    return redirect(url_for("page_ff"))


# ── ROBUX ──────────────────────────────────────────────────────────────────────
@app.route("/robux")
@login_required
def page_robux():
    conn = get_conn()
    products = conn.execute("SELECT * FROM robux_products ORDER BY category, id").fetchall()
    categories = [r[0] for r in conn.execute(
        "SELECT DISTINCT category FROM robux_products ORDER BY category").fetchall()]
    conn.close()
    cat_opts = "".join(f'<option value="{c}">' for c in categories)
    rows = "".join(f"""<tr>
      <td style="color:var(--muted)">{p['id']}</td>
      <td><span class="badge badge-{p['category'].lower()}">{p['category']}</span></td>
      <td>{p['name']}</td>
      <td style="color:var(--accent)">{p['robux']:,} Robux</td>
      <td><span style="color:{'var(--success)' if p['active'] else 'var(--danger)'};font-size:.8rem;">{'Aktif' if p['active'] else 'Nonaktif'}</span></td>
      <td><div style="display:flex;gap:.5rem;flex-wrap:wrap;">
        <button class="btn btn-ghost btn-sm" onclick="openEditRobux({p['id']},'{p['category']}','{p['name'].replace(chr(39), chr(92)+chr(39))}',{p['robux']})">Edit</button>
        <form method="post" action="/robux/toggle/{p['id']}" style="display:inline;">
          <button type="submit" class="btn btn-sm {'btn-danger' if p['active'] else 'btn-success'}">{'Nonaktifkan' if p['active'] else 'Aktifkan'}</button>
        </form>
        <form method="post" action="/robux/delete/{p['id']}" style="display:inline;" onsubmit="return confirm('Hapus item ini?')">
          <button type="submit" class="btn btn-danger btn-sm">Hapus</button>
        </form>
      </div></td>
    </tr>""" for p in products) or '<tr><td colspan="6" class="empty">Belum ada produk Robux</td></tr>'
    content = f"""
<div class="page-header">
  <div class="page-title">Robux Store <small>{len(products)} item</small></div>
  <button class="btn btn-primary" onclick="openModal('modal-add-robux')">+ Tambah Item</button>
</div>
<div class="card"><table>
  <thead><tr><th>#</th><th>Kategori</th><th>Nama Item</th><th>Robux</th><th>Status</th><th>Aksi</th></tr></thead>
  <tbody>{rows}</tbody>
</table></div>
<datalist id="cat-list">{cat_opts}</datalist>
<div class="modal-overlay" id="modal-add-robux"><div class="modal">
  <div class="modal-title">Tambah Item Robux</div>
  <form method="post" action="/robux/add">
    <div class="form-grid">
      <div class="form-group"><label>Kategori</label>
        <input type="text" name="category" placeholder="GAMEPASS / CRATE / BOOST / LIMITED" required list="cat-list"></div>
      <div class="form-grid form-grid-2">
        <div class="form-group"><label>Nama Item</label><input type="text" name="name" placeholder="contoh: VIP + LUCK" required></div>
        <div class="form-group"><label>Harga Robux</label><input type="number" name="robux" placeholder="contoh: 445" min="1" required></div>
      </div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-add-robux')">Batal</button>
    </div>
  </form>
</div></div>
<div class="modal-overlay" id="modal-edit-robux"><div class="modal">
  <div class="modal-title">Edit Item Robux</div>
  <form method="post" action="/robux/edit">
    <input type="hidden" name="id" id="edit-robux-id">
    <div class="form-grid">
      <div class="form-group"><label>Kategori</label><input type="text" name="category" id="edit-robux-cat" list="cat-list" required></div>
      <div class="form-grid form-grid-2">
        <div class="form-group"><label>Nama Item</label><input type="text" name="name" id="edit-robux-name" required></div>
        <div class="form-group"><label>Harga Robux</label><input type="number" name="robux" id="edit-robux-robux" min="1" required></div>
      </div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-edit-robux')">Batal</button>
    </div>
  </form>
</div></div>
<script>
function openEditRobux(id,cat,name,robux){{
  document.getElementById('edit-robux-id').value=id;
  document.getElementById('edit-robux-cat').value=cat;
  document.getElementById('edit-robux-name').value=name;
  document.getElementById('edit-robux-robux').value=robux;
  openModal('modal-edit-robux');
}}
</script>"""
    return render_page(content)


@app.route("/robux/add", methods=["POST"])
@login_required
def robux_add():
    category = request.form.get("category", "").strip().upper()
    name = request.form.get("name", "").strip()
    robux = safe_int(request.form.get("robux"), min_val=1)
    if not category or not name or robux is None:
        flash("Input tidak valid. Semua field wajib diisi dengan benar.", "error")
        return redirect(url_for("page_robux"))
    conn = get_conn()
    conn.execute("INSERT INTO robux_products (category, name, robux) VALUES (?,?,?)", (category, name, robux))
    conn.commit(); conn.close()
    flash(f"Item {name} berhasil ditambahkan.", "success")
    return redirect(url_for("page_robux"))


@app.route("/robux/edit", methods=["POST"])
@login_required
def robux_edit():
    pid = safe_int(request.form.get("id"), min_val=1)
    category = request.form.get("category", "").strip().upper()
    name = request.form.get("name", "").strip()
    robux = safe_int(request.form.get("robux"), min_val=1)
    if pid is None or not category or not name or robux is None:
        flash("Input tidak valid.", "error")
        return redirect(url_for("page_robux"))
    conn = get_conn()
    conn.execute("UPDATE robux_products SET category=?, name=?, robux=? WHERE id=?", (category, name, robux, pid))
    conn.commit(); conn.close()
    flash("Item Robux berhasil diupdate.", "success")
    return redirect(url_for("page_robux"))


@app.route("/robux/toggle/<int:pid>", methods=["POST"])
@login_required
def robux_toggle(pid):
    conn = get_conn()
    row = conn.execute("SELECT active FROM robux_products WHERE id=?", (pid,)).fetchone()
    if row:
        conn.execute("UPDATE robux_products SET active=? WHERE id=?", (0 if row[0] else 1, pid))
        conn.commit()
    conn.close()
    return redirect(url_for("page_robux"))


@app.route("/robux/delete/<int:pid>", methods=["POST"])
@login_required
def robux_delete(pid):
    conn = get_conn()
    conn.execute("DELETE FROM robux_products WHERE id=?", (pid,))
    conn.commit(); conn.close()
    flash("Item Robux berhasil dihapus.", "success")
    return redirect(url_for("page_robux"))


@app.route("/robux/rate", methods=["POST"])
@login_required
def robux_rate():
    rate = safe_int(request.form.get("rate"), min_val=1)
    if rate is None:
        flash("Rate tidak valid. Masukkan angka lebih dari 0.", "error")
        return redirect(url_for("index"))
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO robux_rate (id, rate) VALUES (1, ?)", (rate,))
    conn.commit(); conn.close()
    flash(f"Rate berhasil diupdate ke Rp {rate:,}/Robux.", "success")
    return redirect(url_for("index"))


# ── VILOG ──────────────────────────────────────────────────────────────────────
@app.route("/vilog")
@login_required
def page_vilog():
    conn = get_conn()
    boosts = conn.execute("SELECT * FROM vilog_boosts ORDER BY id").fetchall()
    conn.close()
    rows = "".join(f"""<tr>
      <td style="color:var(--muted)">{i+1}</td>
      <td><span class="badge badge-vilog">{b['nama']}</span></td>
      <td style="color:var(--accent)">{b['robux']:,} Robux</td>
      <td><span style="color:{'var(--success)' if b['active'] else 'var(--danger)'};font-size:.8rem;">{'Aktif' if b['active'] else 'Nonaktif'}</span></td>
      <td><div style="display:flex;gap:.5rem;flex-wrap:wrap;">
        <button class="btn btn-ghost btn-sm" onclick="openEditVilog({b['id']},'{b['nama']}',{b['robux']})">Edit</button>
        <form method="post" action="/vilog/toggle/{b['id']}" style="display:inline;">
          <button type="submit" class="btn btn-sm {'btn-danger' if b['active'] else 'btn-success'}">{'Nonaktifkan' if b['active'] else 'Aktifkan'}</button>
        </form>
        <form method="post" action="/vilog/delete/{b['id']}" style="display:inline;" onsubmit="return confirm('Hapus paket ini?')">
          <button type="submit" class="btn btn-danger btn-sm">Hapus</button>
        </form>
      </div></td>
    </tr>""" for i, b in enumerate(boosts)) or '<tr><td colspan="5" class="empty">Belum ada paket Vilog</td></tr>'
    content = f"""
<div class="page-header">
  <div class="page-title">Vilog Boosts <small>{len(boosts)} paket</small></div>
  <button class="btn btn-primary" onclick="openModal('modal-add-vilog')">+ Tambah Paket</button>
</div>
<div class="card"><table>
  <thead><tr><th>#</th><th>Nama Paket</th><th>Harga Robux</th><th>Status</th><th>Aksi</th></tr></thead>
  <tbody>{rows}</tbody>
</table></div>
<div class="note">Nomor pilihan (1/2/3) di modal Discord otomatis menyesuaikan urutan paket aktif.</div>
<div class="modal-overlay" id="modal-add-vilog"><div class="modal">
  <div class="modal-title">Tambah Paket Vilog</div>
  <form method="post" action="/vilog/add">
    <div class="form-grid form-grid-2">
      <div class="form-group"><label>Nama Paket</label><input type="text" name="nama" placeholder="contoh: X8 48 JAM" required></div>
      <div class="form-group"><label>Harga Robux</label><input type="number" name="robux" placeholder="contoh: 5000" min="1" required></div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-add-vilog')">Batal</button>
    </div>
  </form>
</div></div>
<div class="modal-overlay" id="modal-edit-vilog"><div class="modal">
  <div class="modal-title">Edit Paket Vilog</div>
  <form method="post" action="/vilog/edit">
    <input type="hidden" name="id" id="edit-vilog-id">
    <div class="form-grid form-grid-2">
      <div class="form-group"><label>Nama Paket</label><input type="text" name="nama" id="edit-vilog-nama" required></div>
      <div class="form-group"><label>Harga Robux</label><input type="number" name="robux" id="edit-vilog-robux" min="1" required></div>
    </div>
    <div class="form-actions" style="margin-top:1.5rem;">
      <button type="submit" class="btn btn-primary">Simpan</button>
      <button type="button" class="btn btn-ghost" onclick="closeModal('modal-edit-vilog')">Batal</button>
    </div>
  </form>
</div></div>
<script>
function openEditVilog(id,nama,robux){{
  document.getElementById('edit-vilog-id').value=id;
  document.getElementById('edit-vilog-nama').value=nama;
  document.getElementById('edit-vilog-robux').value=robux;
  openModal('modal-edit-vilog');
}}
</script>"""
    return render_page(content)


@app.route("/vilog/add", methods=["POST"])
@login_required
def vilog_add():
    nama = request.form.get("nama", "").strip()
    robux = safe_int(request.form.get("robux"), min_val=1)
    if not nama or robux is None:
        flash("Input tidak valid. Nama dan Robux harus diisi.", "error")
        return redirect(url_for("page_vilog"))
    conn = get_conn()
    conn.execute("INSERT INTO vilog_boosts (nama, robux) VALUES (?,?)", (nama, robux))
    conn.commit(); conn.close()
    flash(f"Paket {nama} berhasil ditambahkan.", "success")
    return redirect(url_for("page_vilog"))


@app.route("/vilog/edit", methods=["POST"])
@login_required
def vilog_edit():
    bid = safe_int(request.form.get("id"), min_val=1)
    nama = request.form.get("nama", "").strip()
    robux = safe_int(request.form.get("robux"), min_val=1)
    if bid is None or not nama or robux is None:
        flash("Input tidak valid.", "error")
        return redirect(url_for("page_vilog"))
    conn = get_conn()
    conn.execute("UPDATE vilog_boosts SET nama=?, robux=? WHERE id=?", (nama, robux, bid))
    conn.commit(); conn.close()
    flash("Paket Vilog berhasil diupdate.", "success")
    return redirect(url_for("page_vilog"))


@app.route("/vilog/toggle/<int:bid>", methods=["POST"])
@login_required
def vilog_toggle(bid):
    conn = get_conn()
    row = conn.execute("SELECT active FROM vilog_boosts WHERE id=?", (bid,)).fetchone()
    if row:
        conn.execute("UPDATE vilog_boosts SET active=? WHERE id=?", (0 if row[0] else 1, bid))
        conn.commit()
    conn.close()
    return redirect(url_for("page_vilog"))


@app.route("/vilog/delete/<int:bid>", methods=["POST"])
@login_required
def vilog_delete(bid):
    conn = get_conn()
    conn.execute("DELETE FROM vilog_boosts WHERE id=?", (bid,))
    conn.commit(); conn.close()
    flash("Paket Vilog berhasil dihapus.", "success")
    return redirect(url_for("page_vilog"))


# ── AUTOPOST ──────────────────────────────────────────────────────────────────

def _ensure_autopost_table():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS autopost_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            message TEXT NOT NULL,
            interval_minutes INTEGER NOT NULL DEFAULT 60,
            active INTEGER NOT NULL DEFAULT 1,
            last_sent TEXT DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()

_ensure_autopost_table()


@app.route("/autopost")
@login_required
def page_autopost():
    conn = get_conn()
    tasks = conn.execute("SELECT * FROM autopost_tasks ORDER BY id DESC").fetchall()
    conn.close()
    rows = ""
    for t in tasks:
        status = "<span style='color:#2ECC71'>Aktif</span>" if t["active"] else "<span style='color:#E74C3C'>Nonaktif</span>"
        last = t["last_sent"] or "-"
        rows += f"""<tr>
            <td>{t['id']}</td>
            <td>{t['label']}</td>
            <td><code>{t['channel_id']}</code></td>
            <td style='max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>{t['message']}</td>
            <td>{t['interval_minutes']} menit</td>
            <td>{status}</td>
            <td style='font-size:12px'>{last}</td>
            <td>
                <form method='post' action='/autopost/toggle/{t['id']}' style='display:inline'>
                    <button class='btn {"btn-danger" if t["active"] else "btn-success"}' style='padding:4px 10px;font-size:12px'>
                        {"Nonaktifkan" if t["active"] else "Aktifkan"}
                    </button>
                </form>
                <button class='btn btn-warning' style='padding:4px 10px;font-size:12px'
                    onclick='openEdit({t["id"]},"{t["label"]}","{t["channel_id"]}",`{t["message"]}`,{t["interval_minutes"]})'>
                    Edit
                </button>
                <form method='post' action='/autopost/delete/{t["id"]}' style='display:inline'
                    onsubmit='return confirm("Hapus task ini?")'>
                    <button class='btn btn-danger' style='padding:4px 10px;font-size:12px'>Hapus</button>
                </form>
            </td>
        </tr>"""
    if not rows:
        rows = "<tr><td colspan='8' style='text-align:center;color:#888'>Belum ada task autopost.</td></tr>"

    content = f"""
    <div class='card'>
        <h2>Autopost</h2>
        <p style='color:#aaa;font-size:13px'>Pesan dikirim otomatis ke channel Discord dengan interval tertentu menggunakan user token.</p>
        <button class='btn btn-success' onclick="document.getElementById('addForm').style.display='block'">+ Tambah Task</button>
    </div>

    <div class='card' id='addForm' style='display:none'>
        <h3>Tambah Task Baru</h3>
        <form method='post' action='/autopost/add'>
            <div class='form-group'>
                <label>Label (nama task)</label>
                <input type='text' name='label' class='form-control' placeholder='Contoh: Promo Robux' required>
            </div>
            <div class='form-group'>
                <label>Channel ID</label>
                <input type='text' name='channel_id' class='form-control' placeholder='123456789012345678' required>
            </div>
            <div class='form-group'>
                <label>Pesan</label>
                <textarea name='message' class='form-control' rows='5' placeholder='Isi pesan yang akan dikirim...' required></textarea>
            </div>
            <div class='form-group'>
                <label>Interval (menit)</label>
                <input type='number' name='interval_minutes' class='form-control' value='60' min='1' required>
            </div>
            <button type='submit' class='btn btn-success'>Simpan</button>
            <button type='button' class='btn' onclick="document.getElementById('addForm').style.display='none'">Batal</button>
        </form>
    </div>

    <div class='card' id='editForm' style='display:none'>
        <h3>Edit Task</h3>
        <form method='post' action='/autopost/edit'>
            <input type='hidden' name='id' id='editId'>
            <div class='form-group'>
                <label>Label</label>
                <input type='text' name='label' id='editLabel' class='form-control' required>
            </div>
            <div class='form-group'>
                <label>Channel ID</label>
                <input type='text' name='channel_id' id='editChannel' class='form-control' required>
            </div>
            <div class='form-group'>
                <label>Pesan</label>
                <textarea name='message' id='editMessage' class='form-control' rows='5' required></textarea>
            </div>
            <div class='form-group'>
                <label>Interval (menit)</label>
                <input type='number' name='interval_minutes' id='editInterval' class='form-control' min='1' required>
            </div>
            <button type='submit' class='btn btn-success'>Simpan</button>
            <button type='button' class='btn' onclick="document.getElementById('editForm').style.display='none'">Batal</button>
        </form>
    </div>

    <div class='card'>
        <h3>Daftar Task</h3>
        <div style='overflow-x:auto'>
            <table>
                <thead><tr>
                    <th>ID</th><th>Label</th><th>Channel ID</th><th>Pesan</th>
                    <th>Interval</th><th>Status</th><th>Terakhir Kirim</th><th>Aksi</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>

    <script>
    function openEdit(id, label, channel, message, interval) {{
        document.getElementById('editId').value = id;
        document.getElementById('editLabel').value = label;
        document.getElementById('editChannel').value = channel;
        document.getElementById('editMessage').value = message;
        document.getElementById('editInterval').value = interval;
        document.getElementById('editForm').style.display = 'block';
        document.getElementById('editForm').scrollIntoView({{behavior:'smooth'}});
    }}
    </script>
    """
    return render_page(content)


@app.route("/autopost/add", methods=["POST"])
@login_required
def autopost_add():
    label = request.form.get("label", "").strip()
    channel_id = request.form.get("channel_id", "").strip()
    message = request.form.get("message", "").strip()
    interval = safe_int(request.form.get("interval_minutes"), min_val=1) or 60
    if not label or not channel_id or not message:
        flash("Semua field wajib diisi.", "error")
        return redirect(url_for("page_autopost"))
    conn = get_conn()
    conn.execute(
        "INSERT INTO autopost_tasks (label, channel_id, message, interval_minutes, active) VALUES (?,?,?,?,1)",
        (label, channel_id, message, interval)
    )
    conn.commit(); conn.close()
    flash(f"Task '{label}' berhasil ditambahkan.", "success")
    return redirect(url_for("page_autopost"))


@app.route("/autopost/edit", methods=["POST"])
@login_required
def autopost_edit():
    tid = safe_int(request.form.get("id"))
    label = request.form.get("label", "").strip()
    channel_id = request.form.get("channel_id", "").strip()
    message = request.form.get("message", "").strip()
    interval = safe_int(request.form.get("interval_minutes"), min_val=1) or 60
    if not tid or not label or not channel_id or not message:
        flash("Semua field wajib diisi.", "error")
        return redirect(url_for("page_autopost"))
    conn = get_conn()
    conn.execute(
        "UPDATE autopost_tasks SET label=?, channel_id=?, message=?, interval_minutes=? WHERE id=?",
        (label, channel_id, message, interval, tid)
    )
    conn.commit(); conn.close()
    flash("Task berhasil diupdate.", "success")
    return redirect(url_for("page_autopost"))


@app.route("/autopost/toggle/<int:tid>", methods=["POST"])
@login_required
def autopost_toggle(tid):
    conn = get_conn()
    task = conn.execute("SELECT active FROM autopost_tasks WHERE id=?", (tid,)).fetchone()
    if task:
        conn.execute("UPDATE autopost_tasks SET active=? WHERE id=?", (0 if task["active"] else 1, tid))
        conn.commit()
    conn.close()
    return redirect(url_for("page_autopost"))


@app.route("/autopost/delete/<int:tid>", methods=["POST"])
@login_required
def autopost_delete(tid):
    conn = get_conn()
    conn.execute("DELETE FROM autopost_tasks WHERE id=?", (tid,))
    conn.commit(); conn.close()
    flash("Task berhasil dihapus.", "success")
    return redirect(url_for("page_autopost"))


if __name__ == "__main__":
    port = int(os.environ.get("ADMIN_PORT", 5000))
    print(f"[ADMIN] Cellyn Store Admin Panel berjalan di http://localhost:{port}")
    print(f"[ADMIN] Password: {ADMIN_PASSWORD}")
    app.run(host="0.0.0.0", port=port, debug=False)
