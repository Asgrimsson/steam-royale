# Skóla Royale v1.0 - Uppsetning á Render

Þessi útgáfa er undirbúin fyrir vefhýsingu með:

- `render.yaml`
- `.gitignore`
- `.env.example`
- `Procfile`
- `/health` health check
- environment variables
- persistent disk á Render fyrir gagnagrunninn
- öryggishausum
- production guard sem stoppar server ef kennaralykilorð er enn `kennari123`

> Mikilvægt: Þessi v1.0 notar áfram SQLite, en á Render er það vistað á persistent disk (`/var/data`). Þetta er einfaldasta örugga fyrsta vefútgáfan. Þegar notkun stækkar er næsta skref að færa gögn í PostgreSQL.

---

## 1. Prófa v1.0 á tölvunni

Farðu í verkefnamöppuna:

```cmd
cd C:\skola_royale_python
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Opnaðu:

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

---

## 2. Afrita v1.0 yfir gömlu möppuna

Stoppaðu serverinn með:

```text
Ctrl + C
```

Afritaðu allar v1.0 skrár yfir gömlu möppuna, en passaðu að eyða ekki gagnagrunninum:

```text
app/skola_royale.db
```

Taktu öryggisafrit fyrst:

```cmd
copy C:\skola_royale_python\app\skola_royale.db C:\skola_royale_python\app\skola_royale_backup.db
```

---

## 3. Setja verkefnið á GitHub

Farðu í verkefnamöppuna:

```cmd
cd C:\skola_royale_python
git init
git add .
git commit -m "Skola Royale v1.0 production ready"
git branch -M main
git remote add origin https://github.com/NOTANDANAFN/skola-royale.git
git push -u origin main
```

Ef `git` er ekki uppsett, settu fyrst upp Git for Windows.

Athugaðu að `.gitignore` passar að gagnagrunnurinn og `.env` fari ekki á GitHub.

---

## 4. Búa til Render Web Service

1. Farðu á Render.
2. Veldu **New +**.
3. Veldu **Blueprint** ef þú vilt nota `render.yaml`, eða **Web Service** ef þú vilt stilla handvirkt.
4. Tengdu GitHub repository-ið.
5. Veldu `skola-royale`.

Ef þú notar handvirka Web Service stillingu:

### Build Command

```bash
pip install -r requirements.txt
```

### Start Command

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Health Check Path

```text
/health
```

---

## 5. Environment variables á Render

Settu þetta í Render → Environment:

```text
APP_ENV=production
DATA_DIR=/var/data
SESSION_DAYS=14
ALLOW_DEFAULT_TEACHER_PASSWORD=false
TEACHER_USERNAME=kennari
TEACHER_PASSWORD=þitt-sterka-lykilorð
SECRET_KEY=langur-random-strengur
```

Dæmi um sterkt lykilorð:

```text
SkolaRoyale!2026-Mission-45
```

Dæmi um SECRET_KEY:

```text
0d9f7a6c0e2b4f1a9c8d7e6f5b4a3c2d1e0f987654321abc
```

Ekki nota dæmin nákvæmlega. Búðu til þitt eigið.

---

## 6. Persistent Disk á Render

Ef þú notar `render.yaml` er diskurinn skilgreindur þar:

```yaml
disk:
  name: skola-royale-data
  mountPath: /var/data
  sizeGB: 1
```

Ef þú stillir handvirkt:

1. Farðu í Web Service.
2. Finndu **Disks**.
3. Bættu við disk:
   - Name: `skola-royale-data`
   - Mount path: `/var/data`
   - Size: `1 GB`

Þetta tryggir að `skola_royale.db` glatist ekki við endurræsingu þjónsins.

---

## 7. Fyrsta innskráning á Render

Þegar Render deploy er lokið færðu slóð eins og:

```text
https://skola-royale.onrender.com
```

Opnaðu hana og skráðu þig inn:

```text
Notandanafn: kennari
Lykilorð: það sem þú settir í TEACHER_PASSWORD
```

---

## 8. Prófunaráætlun

Prófaðu þetta áður en nemendur fá slóðina:

1. Skrá inn sem kennari.
2. Stofna einn prufunemanda.
3. Skrá út.
4. Skrá inn sem nemandi.
5. Svara 10 verkefnum.
6. Skrá aftur inn sem kennari.
7. Skoða:
   - mælaborð
   - færnimælaborð
   - skýrslur
   - CSV útflutning
   - verkefnapakka
   - spurningabanka

---

## 9. Persónuvernd og skólanotkun

Mælt er með:

- nota gervinotendanöfn, t.d. `nem001`, `nem002`
- geyma ekki kennitölur
- geyma ekki óþarfa persónuupplýsingar
- fá samþykki skóla/stjórnenda áður en kerfið er notað með nemendum
- nota aðeins HTTPS-slóðina frá Render
- deila ekki kennaralykilorði

---

## 10. Næsta tæknilega skref: PostgreSQL

Þessi v1.0 notar SQLite á persistent disk. Það er einfaldast til að koma kerfinu í loftið.

Þegar notkun verður meiri er næsta skref:

- færa gagnagrunn yfir í PostgreSQL
- nota `DATABASE_URL`
- setja upp migrations
- færa gögn úr SQLite yfir í PostgreSQL

Það væri v1.1.
