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
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#0a0a0f;--surface:#12121a;--surface2:#1a1a26;--border:#2a2a3a;
  --accent:#7c6aff;--accent2:#ff6b9d;--accent3:#6affb0;
  --text:#e8e8f0;--muted:#6b6b80;--danger:#ff4d6d;--success:#4dffb0;--warning:#ffb74d;}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'DM Mono',monospace;background:var(--bg);color:var(--text);min-height:100vh;
  background-image:radial-gradient(ellipse at 20% 50%,rgba(124,106,255,.05) 0%,transparent 60%),
                   radial-gradient(ellipse at 80% 20%,rgba(255,107,157,.03) 0%,transparent 50%);}
a{color:var(--accent);text-decoration:none;}a:hover{color:var(--accent2);}
nav{background:var(--surface);border-bottom:1px solid var(--border);padding:0 2rem;
  display:flex;align-items:center;justify-content:space-between;height:60px;position:sticky;top:0;z-index:100;}
.nav-brand{font-family:'Syne',sans-serif;font-weight:800;font-size:1.1rem;letter-spacing:.05em;color:var(--text);}
.nav-brand span{color:var(--accent);}
.nav-links{display:flex;gap:.25rem;}
.nav-links a{color:var(--muted);padding:.4rem .8rem;border-radius:6px;font-size:.8rem;transition:all .15s;}
.nav-links a:hover,.nav-links a.active{background:var(--surface2);color:var(--text);}
.nav-logout{color:var(--danger)!important;border:1px solid rgba(255,77,109,.3);}
.nav-logout:hover{background:rgba(255,77,109,.1)!important;border-color:var(--danger);}
.container{max-width:1100px;margin:0 auto;padding:2rem;}
.page-header{margin-bottom:2rem;display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:1rem;}
.page-title{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;}
.page-title small{display:block;font-size:.75rem;font-weight:400;color:var(--muted);font-family:'DM Mono',monospace;margin-top:.2rem;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden;}
.card-header{padding:1rem 1.5rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--surface2);}
.card-title{font-family:'Syne',sans-serif;font-weight:700;font-size:.9rem;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);}
table{width:100%;border-collapse:collapse;}
th{text-align:left;padding:.75rem 1.5rem;font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);border-bottom:1px solid var(--border);}
td{padding:.85rem 1.5rem;border-bottom:1px solid rgba(42,42,58,.5);font-size:.85rem;vertical-align:middle;}
tr:last-child td{border-bottom:none;}tr:hover td{background:rgba(124,106,255,.03);}
.badge{display:inline-block;padding:.2rem .6rem;border-radius:4px;font-size:.7rem;font-weight:500;letter-spacing:.05em;text-transform:uppercase;}
.badge-gamepass{background:rgba(124,106,255,.15);color:var(--accent);border:1px solid rgba(124,106,255,.3);}
.badge-crate{background:rgba(255,107,157,.15);color:var(--accent2);border:1px solid rgba(255,107,157,.3);}
.badge-boost{background:rgba(255,183,77,.15);color:var(--warning);border:1px solid rgba(255,183,77,.3);}
.badge-limited{background:rgba(106,255,176,.15);color:var(--accent3);border:1px solid rgba(106,255,176,.3);}
.badge-ml{background:rgba(52,152,219,.15);color:#3498DB;border:1px solid rgba(52,152,219,.3);}
.badge-ff{background:rgba(255,107,53,.15);color:#FF6B35;border:1px solid rgba(255,107,53,.3);}
.badge-vilog{background:rgba(230,126,34,.15);color:#E67E22;border:1px solid rgba(230,126,34,.3);}
.btn{display:inline-flex;align-items:center;gap:.4rem;padding:.5rem 1rem;border-radius:8px;
  font-family:'DM Mono',monospace;font-size:.8rem;cursor:pointer;border:none;transition:all .15s;text-decoration:none;}
.btn-primary{background:var(--accent);color:#fff;}.btn-primary:hover{background:#6a58e8;color:#fff;}
.btn-danger{background:rgba(255,77,109,.15);color:var(--danger);border:1px solid rgba(255,77,109,.3);}
.btn-danger:hover{background:rgba(255,77,109,.25);color:var(--danger);}
.btn-ghost{background:var(--surface2);color:var(--muted);border:1px solid var(--border);}
.btn-ghost:hover{color:var(--text);border-color:var(--accent);}
.btn-success{background:rgba(77,255,176,.15);color:var(--success);border:1px solid rgba(77,255,176,.3);}
.btn-success:hover{background:rgba(77,255,176,.25);}
.btn-sm{padding:.3rem .65rem;font-size:.75rem;}
.form-grid{display:grid;gap:1rem;}.form-grid-2{grid-template-columns:1fr 1fr;}
.form-group{display:flex;flex-direction:column;gap:.4rem;}
label{font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;}
input,select{background:var(--surface2);border:1px solid var(--border);border-radius:8px;
  padding:.65rem .9rem;color:var(--text);font-family:'DM Mono',monospace;font-size:.85rem;
  transition:border-color .15s;width:100%;}
input:focus,select:focus{outline:none;border-color:var(--accent);background:rgba(124,106,255,.05);}
select option{background:var(--surface2);}
.form-actions{display:flex;gap:.75rem;margin-top:.5rem;}
.inline-form{display:flex;gap:.5rem;align-items:center;}
.inline-form input{width:auto;min-width:80px;}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;
  align-items:center;justify-content:center;backdrop-filter:blur(4px);}
.modal-overlay.active{display:flex;}
.modal{background:var(--surface);border:1px solid var(--border);border-radius:16px;
  padding:2rem;width:100%;max-width:480px;animation:modalIn .2s ease;}
@keyframes modalIn{from{opacity:0;transform:scale(.95) translateY(10px)}to{opacity:1;transform:scale(1) translateY(0)}}
.modal-title{font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;margin-bottom:1.5rem;}
.flash-list{list-style:none;margin-bottom:1.5rem;}
.flash{padding:.75rem 1rem;border-radius:8px;font-size:.85rem;margin-bottom:.5rem;}
.flash-success{background:rgba(77,255,176,.1);border:1px solid rgba(77,255,176,.3);color:var(--success);}
.flash-error{background:rgba(255,77,109,.1);border:1px solid rgba(255,77,109,.3);color:var(--danger);}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-bottom:2rem;}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1.25rem 1.5rem;position:relative;overflow:hidden;}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;}
.stat-card.ml::before{background:#3498DB;}.stat-card.ff::before{background:#FF6B35;}
.stat-card.robux::before{background:#E91E63;}.stat-card.vilog::before{background:#E67E22;}
.stat-label{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;}
.stat-value{font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;margin-top:.25rem;}
.stat-sub{font-size:.75rem;color:var(--muted);margin-top:.2rem;}
.rate-display{background:var(--surface2);border:1px solid var(--border);border-radius:10px;
  padding:1rem 1.5rem;display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin-bottom:1.5rem;}
.rate-value{font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:700;color:var(--accent);}
.empty{text-align:center;padding:3rem;color:var(--muted);font-size:.85rem;}
.note{margin-top:1rem;padding:1rem 1.5rem;background:var(--surface2);border-radius:8px;border:1px solid var(--border);font-size:.8rem;color:var(--muted);}
@media(max-width:768px){.form-grid-2{grid-template-columns:1fr;}nav{padding:0 1rem;}.container{padding:1rem;}.nav-links a{padding:.3rem .5rem;font-size:.75rem;}}
</style>
</head>
<body>
NAVPLACEHOLDER
<div class="container">
FLASHPLACEHOLDER
CONTENTPLACEHOLDER
</div>
<script>
function openModal(id){document.getElementById(id).classList.add('active');}
function closeModal(id){document.getElementById(id).classList.remove('active');}
document.addEventListener('keydown',e=>{
  if(e.key==='Escape') document.querySelectorAll('.modal-overlay.active').forEach(m=>m.classList.remove('active'));
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
        nav = f"""<nav>
  <div class="nav-brand">CELLYN <span>ADMIN</span></div>
  <div class="nav-links">
    <a href="/" {"class='active'" if ep=='index' else ""}>Dashboard</a>
    <a href="/ml" {"class='active'" if ep=='page_ml' else ""}>ML</a>
    <a href="/ff" {"class='active'" if ep=='page_ff' else ""}>FF</a>
    <a href="/robux" {"class='active'" if ep=='page_robux' else ""}>Robux</a>
    <a href="/vilog" {"class='active'" if ep=='page_vilog' else ""}>Vilog</a>
    <a href="/logout" class="nav-logout">Logout</a>
  </div>
</nav>"""
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
<div style="min-height:80vh;display:flex;align-items:center;justify-content:center;">
  <div style="width:100%;max-width:360px;">
    <div style="text-align:center;margin-bottom:2rem;">
      <div style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;letter-spacing:.05em;">
        CELLYN <span style="color:var(--accent)">ADMIN</span></div>
      <div style="color:var(--muted);font-size:.8rem;margin-top:.5rem;">Store Management Panel</div>
    </div>
    <div class="card"><div style="padding:2rem;">
      <form method="post">
        <div class="form-group" style="margin-bottom:1.25rem;">
          <label>Password</label>
          <input type="password" name="password" placeholder="Masukkan password admin" autofocus required>
        </div>
        {'<div class="flash flash-error" style="margin-bottom:1rem;">'+error+'</div>' if error else ''}
        <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;">Masuk</button>
      </form>
    </div></div>
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
    products = conn.execute("SELECT * FROM ml_products ORDER BY dm").fetchall()
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


if __name__ == "__main__":
    port = int(os.environ.get("ADMIN_PORT", 5000))
    print(f"[ADMIN] Cellyn Store Admin Panel berjalan di http://localhost:{port}")
    print(f"[ADMIN] Password: {ADMIN_PASSWORD}")
    app.run(host="0.0.0.0", port=port, debug=False)
