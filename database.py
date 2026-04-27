import sqlite3
from datetime import datetime

DB_FILE = "koopbot.db"

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            full_name   TEXT,
            joined_at   TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS koop_bekleyen (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            koop_kodu   TEXT,
            para        REAL,
            eklenme     TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ekipler (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            koop_kodu   TEXT,
            olusturma   TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ekip_uyeleri (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ekip_id     INTEGER,
            user_id     INTEGER,
            para        REAL,
            FOREIGN KEY(ekip_id) REFERENCES ekipler(id),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)

    conn.commit()
    conn.close()

# ── Kullanıcı ─────────────────────────────────────────────
def kayit_et(user_id, username, full_name):
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO users (user_id, username, full_name, joined_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, full_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def kullanici_getir(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row

# ── Koop bekleme listesi ──────────────────────────────────
def koop_ekle(user_id, koop_kodu, para):
    """Kullanıcıyı bekleme listesine ekler. Zaten varsa günceller."""
    conn = get_conn()
    mevcut = conn.execute(
        "SELECT id FROM koop_bekleyen WHERE user_id=? AND koop_kodu=?",
        (user_id, koop_kodu)
    ).fetchone()
    if mevcut:
        conn.execute(
            "UPDATE koop_bekleyen SET para=?, eklenme=? WHERE id=?",
            (para, datetime.now().isoformat(), mevcut["id"])
        )
    else:
        conn.execute(
            "INSERT INTO koop_bekleyen (user_id, koop_kodu, para, eklenme) VALUES (?,?,?,?)",
            (user_id, koop_kodu, para, datetime.now().isoformat())
        )
    conn.commit()
    conn.close()

def koop_bekleyenleri_getir(koop_kodu):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM koop_bekleyen WHERE koop_kodu=? ORDER BY eklenme ASC",
        (koop_kodu,)
    ).fetchall()
    conn.close()
    return rows

def koop_sil(user_id, koop_kodu):
    conn = get_conn()
    conn.execute(
        "DELETE FROM koop_bekleyen WHERE user_id=? AND koop_kodu=?",
        (user_id, koop_kodu)
    )
    conn.commit()
    conn.close()

def koop_listeden_cikar(user_id):
    """Kullanıcının tüm bekleyen kayıtlarını sil."""
    conn = get_conn()
    conn.execute("DELETE FROM koop_bekleyen WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

# ── Ekip oluşturma ────────────────────────────────────────
def ekip_olustur(koop_kodu, uyeler):
    """uyeler: [(user_id, para), ...]"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ekipler (koop_kodu, olusturma) VALUES (?,?)",
        (koop_kodu, datetime.now().isoformat())
    )
    ekip_id = cur.lastrowid
    for uid, para in uyeler:
        cur.execute(
            "INSERT INTO ekip_uyeleri (ekip_id, user_id, para) VALUES (?,?,?)",
            (ekip_id, uid, para)
        )
        # Bekleme listesinden çıkar
        cur.execute(
            "DELETE FROM koop_bekleyen WHERE user_id=? AND koop_kodu=?",
            (uid, koop_kodu)
        )
    conn.commit()
    conn.close()
    return ekip_id

def ekip_getir(ekip_id):
    conn = get_conn()
    ekip = conn.execute("SELECT * FROM ekipler WHERE id=?", (ekip_id,)).fetchone()
    uyeler = conn.execute(
        """SELECT eu.para, u.user_id, u.username, u.full_name
           FROM ekip_uyeleri eu JOIN users u ON eu.user_id=u.user_id
           WHERE eu.ekip_id=?""",
        (ekip_id,)
    ).fetchall()
    conn.close()
    return ekip, uyeler

def tum_ekipler():
    conn = get_conn()
    rows = conn.execute(
        "SELECT e.id, e.koop_kodu, e.olusturma, COUNT(eu.id) as uye_sayisi "
        "FROM ekipler e LEFT JOIN ekip_uyeleri eu ON e.id=eu.ekip_id "
        "GROUP BY e.id ORDER BY e.olusturma DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return rows
