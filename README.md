# Skóla Royale Python

Þetta er fyrsta keyrsluhæfa útgáfa af Skóla Royale sem Python/FastAPI vefkerfi.

## Hvað er komið?

- Innskráning fyrir kennara og nemendur.
- Kennari getur stofnað nemendur.
- Aðeins virkir skráðir notendur komast inn.
- Nemendur fá verkefni úr blönduðum greinum.
- XP, level, coins, streak, búð og hjálparhlutir.
- Svör og framvinda vistast í SQLite gagnagrunni.
- Kennari fær mælaborð með nemendum, réttum svörum, nákvæmni og greinayfirliti.

## Keyrsla á tölvunni þinni

1. Settu upp Python 3.11 eða nýrra.
2. Opnaðu Terminal/Command Prompt í þessari möppu.
3. Búðu til sýndarumhverfi:

   macOS/Linux:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   Windows:
   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   ```

4. Settu upp pakkana:
   ```bash
   pip install -r requirements.txt
   ```

5. Ræstu vefinn:
   ```bash
   uvicorn app.main:app --reload
   ```

6. Opnaðu:
   ```text
   http://127.0.0.1:8000
   ```

## Fyrsti kennariaðgangur

- Notandanafn: `kennari`
- Lykilorð: `kennari123`

Mikilvægt: breyttu þessu áður en þú setur kerfið á opinn vef.

## Öruggari kennaralykilorð við fyrstu ræsingu

Þú getur sett annað lykilorð áður en gagnagrunnurinn er búinn til:

macOS/Linux:
```bash
export TEACHER_PASSWORD="mitt-sterka-lykilord"
uvicorn app.main:app --reload
```

Windows PowerShell:
```powershell
$env:TEACHER_PASSWORD="mitt-sterka-lykilord"
uvicorn app.main:app --reload
```

## Næstu skref

- Flytja fleiri verkefni úr gamla HTML-kóðanum inn í `app/static/app.js`.
- Bæta við innflutningi úr CSV til að stofna marga nemendur í einu.
- Bæta við kennarahópum/bekkjum.
- Setja upp á vefþjón, t.d. Render, Railway, Fly.io eða eigin skólaþjóni.
- Skipta SQLite út fyrir PostgreSQL þegar margir nemendur nota kerfið samtímis.


## Uppfærsla v0.2

Þessi útgáfa bætir við:

- fleiri verkefnagerðum í öllum greinum
- Daily Quest
- Afrek/Battle Pass
- fleiri hlutum í búð
- flottara viðmóti og confetti
- betri nemendaupplýsingum í mælaborði kennara

## Ef þú ert með eldri útgáfu í gangi

1. Stoppaðu þjóninn með `Ctrl + C`.
2. Afritaðu skrárnar úr þessari útgáfu yfir eldri möppuna, eða keyrðu þessa möppu sérstaklega.
3. Keyrðu aftur:

```powershell
python -m uvicorn app.main:app --reload
```

Gagnagrunnurinn er áfram `app/skola_royale.db`.
Ef þú setur nýju skrárnar yfir gömlu möppuna heldurðu nemendum og framvindu.


## Uppfærsla v0.3 - Kennara-verkfæri

Nýtt:

- bekkur/hópur á nemendum
- sía mælaborð eftir bekk
- stofna marga nemendur í einu
- endurstilla lykilorð nemanda
- virkja/óvirkja nemanda
- opna nánari nemendaskýrslu
- sjá síðustu svör og stöðu í greinum

### Dæmi um lista til að stofna marga nemendur

```text
nem1,Anna,1234,5A
nem2,Birkir,1234,5A
nem3,Kata,1234,5B
```

### Uppfærsla úr eldri útgáfu

Ef þú vilt halda gömlu nemendunum:

1. Stoppaðu þjóninn með Ctrl + C.
2. Afritaðu þessar skrár úr v0.3 yfir gömlu möppuna:
   - app/main.py
   - app/static/index.html
   - app/static/app.js
   - app/static/style.css
3. Keyrðu aftur:

```powershell
python -m uvicorn app.main:app --reload
```

Kerfið bætir sjálfkrafa við dálki fyrir bekk/hóp í gamla gagnagrunninn.


## Uppfærsla v0.4 - Alvöru verkefnabanki

Nýtt:

- Sérstök verkefnaskrá: `app/static/questions.json`
- 743 verkefni í verkefnabankanum
- Verkefni merkt með:
  - `subject`
  - `skill`
  - `difficulty`
  - `hint`
  - `options`
- Vefurinn hleður verkefnabankanum sjálfkrafa.
- Ef verkefnabankinn finnst ekki notar kerfið enn eldri innbyggðu verkefnin.

### Hvernig þú bætir við verkefni

Opnaðu:

```text
app/static/questions.json
```

Bættu við nýju verkefni í listann `questions`:

```json
{
  "id": "q9999",
  "subject": "math",
  "skill": "margföldun",
  "difficulty": 1,
  "text": "Hvað er 7 × 8?",
  "answer": "56",
  "hint": "7 × 8 er í 7 sinnum töflunni.",
  "options": ["56", "54", "63", "48"]
}
```

### Flokkar

- `math` = stærðfræði
- `icelandic` = íslenska
- `english` = enska
- `science` = náttúrufræði
- `geo` = landafræði

### Uppfærsla úr eldri útgáfu

1. Stoppaðu þjóninn með `Ctrl + C`.
2. Afritaðu þessar skrár yfir gömlu möppuna:
   - `app/static/app.js`
   - `app/static/questions.json`
3. Mælt er líka með að afrita:
   - `app/static/index.html`
   - `app/static/style.css`
   - `app/main.py`
4. Keyrðu aftur:

```powershell
python -m uvicorn app.main:app --reload
```


## Uppfærsla v0.5 - Kennari getur bætt spurningum beint inn á vefnum

Nýtt:

- Kennari fær nýjan valmyndahnapp: `✍️ Spurningabanki`
- Kennari getur búið til spurningar í vafranum
- Spurningar vistast í gagnagrunninum `skola_royale.db`
- Nemendur hlaða kennaraspurningum sjálfkrafa
- Kennaraspurningar fá aukna líkur svo nemendur sjái nýtt efni fljótt
- Kennari getur virkjað/óvirkjað spurningar
- Kennari getur eytt spurningum

### Hvernig á að nota

1. Skráðu þig inn sem kennari.
2. Farðu í `✍️ Spurningabanki`.
3. Veldu grein.
4. Settu inn:
   - spurningu
   - rétt svar
   - vísbendingu
   - svarmöguleika, einn í hverri línu
5. Ýttu á `Vista spurningu`.

Ef þú skilur svarmöguleika eftir auða verður spurningin textasvar.

### Uppfærsla úr eldri útgáfu

Stoppaðu þjóninn með Ctrl + C og afritaðu þessar skrár yfir gömlu möppuna:

```text
app/main.py
app/static/index.html
app/static/app.js
app/static/style.css
```

Ekki eyða:

```text
app/skola_royale.db
```

Keyrðu síðan:

```powershell
python -m uvicorn app.main:app --reload
```

Kerfið býr sjálfkrafa til nýja töflu fyrir kennaraspurningar í gagnagrunninum.


## Uppfærsla v0.6 - Færnimælaborð

Nýtt:

- Kerfið vistar nú `skill` og `difficulty` með hverju svari.
- Kennari sér færniyfirlit fyrir allan hópinn.
- Kennari sér hvaða færni hópurinn þarf helst að æfa.
- Nemendaskýrsla sýnir nú árangur eftir færni.
- Hægt er að sía færnimælaborð eftir bekk/hóp.

### Dæmi um færni

- `margföldun`
- `deiling`
- `flatarmál`
- `orðflokkar`
- `stafsetning`
- `lesskilningur`
- `kortalestur`

### Mikilvægt

Gömul svör sem voru skráð áður en v0.6 var sett inn fá færnina `almennt`.
Ný svör fá rétta færni úr `questions.json` eða úr kennaraspurningum.

### Uppfærsla úr eldri útgáfu

Stoppaðu þjóninn með Ctrl + C og afritaðu þessar skrár yfir gömlu möppuna:

```text
app/main.py
app/static/index.html
app/static/app.js
app/static/style.css
```

Ekki eyða:

```text
app/skola_royale.db
```

Keyrðu síðan:

```powershell
python -m uvicorn app.main:app --reload
```

Kerfið bætir sjálfkrafa við dálkum fyrir færni og erfiðleikastig í gagnagrunninn.


## Uppfærsla v0.7 - Verkefnapakkar

Nýtt:

- Kennari fær nýjan hnapp: `📦 Verkefnapakkar`
- Kennari getur búið til pakka úr kennaraspurningum
- Hægt er að tengja pakka við ákveðinn bekk/hóp, t.d. `5A`
- Ef bekkur er skilinn eftir auður fá allir nemendur pakkann
- Nemendur fá spurningar úr virkum verkefnapökkum mun oftar í mission
- Hægt er að virkja/óvirkja og eyða verkefnapökkum
- Spurningarnar sjálfar eyðast ekki þótt pakka sé eytt

### Dæmi um notkun

1. Farðu í `✍️ Spurningabanki`.
2. Búðu til 10 spurningar um margföldun.
3. Farðu í `📦 Verkefnapakkar`.
4. Búðu til pakka:
   - Heiti: `Margföldun 6–9`
   - Bekkur: `5A`
   - Veldu spurningarnar 10
5. Nemendur í 5A fá þessar spurningar oftar í mission.

### Uppfærsla úr eldri útgáfu

Stoppaðu þjóninn með Ctrl + C og afritaðu þessar skrár yfir gömlu möppuna:

```text
app/main.py
app/static/index.html
app/static/app.js
app/static/style.css
```

Ekki eyða:

```text
app/skola_royale.db
```

Keyrðu síðan:

```powershell
python -m uvicorn app.main:app --reload
```

Kerfið býr sjálfkrafa til töflur fyrir verkefnapakka í gagnagrunninum.


## Uppfærsla v0.8 - Epic nemendaviðmót

Nýtt:

- Mission-kort með flottum svæðum
- Boss Fight kerfi
- Boss-síða með lífsstiku og reglum
- Dagleg verðlaunasíða
- Innskráningarbónus með daglegu streak
- Loot modal fyrir verðlaun
- Streak loot
- Flottari búð með rarity-flokkum
- Nýir hlutir:
  - Rafmagns XP
  - Dreka-avatar
  - Ninja-avatar
- Verkefnapakkar sjást sem `📦 pakkaheiti` í spurningum
- Stöðuspjöld fyrir svæði, pakka, streak og daily quest

### Boss Fight

Boss Fight opnast þegar nemandi nær annað hvort:

- level 3
- eða 10 réttum svörum

Nemandi þarf 5 rétt svör til að sigra boss. Sigur gefur:

- coins
- XP
- 2 loot kassa

### Dagleg verðlaun

Nemandi getur sótt daglegan innskráningarbónus einu sinni á dag. Ef nemandi kemur marga daga í röð hækkar bónusinn.

### Uppfærsla úr eldri útgáfu

Stoppaðu þjóninn með Ctrl + C og afritaðu þessar skrár yfir gömlu möppuna:

```text
app/static/index.html
app/static/app.js
app/static/style.css
```

Mælt er með að afrita líka `app/main.py` ef þú ert ekki þegar með v0.7.

Ekki eyða:

```text
app/skola_royale.db
```

Keyrðu síðan:

```powershell
python -m uvicorn app.main:app --reload
```


## Uppfærsla v0.9 - Skýrslur og útflutningur

Nýtt:

- Kennari fær nýjan hnapp: `📊 Skýrslur`
- CSV útflutningur fyrir bekk
- CSV útflutningur fyrir færni
- CSV útflutningur fyrir einn nemanda
- Prentvæn nemendaskýrsla
- Yfirlit yfir nemendur sem gætu þurft stuðning
- Sía eftir bekk/hóp

### CSV skrár

Kerfið býr til CSV skrár sem opnast í Excel eða Google Sheets.

### Uppfærsla úr eldri útgáfu

Stoppaðu þjóninn með Ctrl + C og afritaðu þessar skrár yfir gömlu möppuna:

```text
app/main.py
app/static/index.html
app/static/app.js
app/static/style.css
```

Ekki eyða:

```text
app/skola_royale.db
```

Keyrðu síðan:

```powershell
python -m uvicorn app.main:app --reload
```


## v1.0 Production Ready

Þessi útgáfa bætir við:

- Render deployment skrám
- `render.yaml`
- `Procfile`
- `.gitignore`
- `.env.example`
- `/health` endpoint
- environment variables fyrir kennaralykilorð og secret key
- persistent disk stuðning með `DATA_DIR`
- production guard sem kemur í veg fyrir að `kennari123` sé notað á opnum vef
- öryggishausa

Sjá nánar í:

```text
DEPLOYMENT.md
```


## v1.1 - Þyngdarstig og vistun

- Þyngdarstig fyrir 5., 6. og 7. bekk
- Sjálfvirkt þyngdarstig eftir árangri
- Kennari getur merkt eigin spurningar með bekkjarstigi
- Svör vista bekkjarstig
- Sjá `PERSISTENCE.md` fyrir varanlega vistun á Render


## v1.2 - Epic Content & Shop

Nýtt í þessari útgáfu:

- Stækkaður verkefnabanki: 142 ný verkefni
- Fleiri 7. bekkjar verkefni
- Ný verkefnagerð: Finndu villuna
- Ný verkefnagerð: Fylla í eyður
- Fleiri stærðfræðiþættir:
  - prósentur
  - hlutföll
  - neikvæðar tölur
  - jöfnur
  - meðaltal
  - flatarmál þríhyrninga
  - rúmmál
- Fleiri íslenskuverkefni fyrir 7. bekk
- Fleiri enskuverkefni með óreglulegum sögnum
- Fleiri náttúrufræði- og samfélagsfræðiverkefni
- Stórbætt búð:
  - lukkudýr/pets
  - þemu
  - fleiri kraftar
  - safngripir úr loot kössum
- Greinabossar með mismunandi verðlaunum

### Uppfærsla

Afritaðu þessar skrár yfir núverandi verkefni og ýttu svo á GitHub:

```text
app/static/questions.json
app/static/app.js
app/static/index.html
app/static/style.css
README.md
```

Síðan:

```cmd
git add .
git commit -m "Skola Royale v1.2 epic content and shop"
git push
```

Render deploy-ar þá sjálfkrafa.


## v1.3 - Adaptive Learning og stærri verkefnabanki

Nýtt:

- 80 ný verkefni
- Sérstakur fókus á 7. bekk
- Snjallæfing / Adaptive Learning:
  - nemandi getur kveikt á 🧠 Snjallæfingu
  - kerfið skoðar færni þar sem nemandi er undir 75%
  - slík færni birtist oftar í verkefnum
- Nýr API endapunktur:
  - `/api/me/skills`
- Meiri fjölbreytni:
  - prósentubreyting
  - almenn brot
  - líkur
  - hnitakerfi
  - fallbeyging
  - greinarmerki
  - present perfect
  - conditionals
  - frumur, DNA, kraftar
  - lýðræði, viðskipti og lífskjör

### Uppfærsla

Afritaðu yfir núverandi verkefni og ýttu á GitHub:

```cmd
git add .
git commit -m "Skola Royale v1.3 adaptive learning"
git push
```

Render deploy-ar sjálfkrafa.


## v1.4 - Kennari stjórnar námsleið

Nýtt:

- Kennari getur búið til námsleiðir
- Námsleið getur verið tengd bekk/hópi
- Námsleið hefur bekkjarstig og grein
- Hver námsleið hefur skref:
  - æfing
  - áskorun
  - boss
  - lokapróf
- Nemandi sér námsleið sem ævintýrakort
- Nemandi getur byrjað einstök skref
- Skref geta stillt grein, þyngdarstig og boss

### Uppfærsla

Afritaðu yfir núverandi verkefni og ýttu á GitHub:

```cmd
git add .
git commit -m "Skola Royale v1.4 learning paths"
git push
```

Render deploy-ar sjálfkrafa.


## v1.5 - Námsleiðar-framvinda

Nýtt:

- Nemandi getur byrjað skref í námsleið
- Kerfið vistar framvindu:
  - rétt svör
  - svör alls
  - lokið/ólokið
  - verðlaun sótt/ósótt
- Skref læsast þar til fyrra skref er klárað
- Nemandi fær framvindustiku í hverju skrefi
- Nemandi getur sótt verðlaun þegar skrefi er lokið
- Kennari getur skoðað framvindu námsleiðar fyrir nemendur

### Uppfærsla

Afritaðu yfir núverandi verkefni og ýttu á GitHub:

```cmd
git add .
git commit -m "Skola Royale v1.5 learning path progress"
git push
```

Render býr sjálfkrafa til nýju töfluna `learning_path_progress` við næsta deploy.


## v1.6 - Lokapróf úr námsleið + meiri náttúrufræði

Nýtt:

- Kennari getur búið til lokapróf úr námsleið
- Nemendur fá sérstaka síðu: `📝 Lokapróf`
- Próf velur spurningar út frá námsleið, grein, færni og bekkjarstigi
- Nemandi sendir inn próf og fær niðurstöðu strax
- Kerfið vistar prófniðurstöður
- Kennari sér niðurstöður prófa
- Nemandi fær verðlaun ef hann stenst próf
- Bætt við 39 náttúrufræðiverkefnum fyrir 5., 6. og 7. bekk

### Uppfærsla

```cmd
git add .
git commit -m "Skola Royale v1.6 path quizzes and science"
git push
```

Render býr sjálfkrafa til nýju töflurnar `path_quizzes` og `path_quiz_attempts`.


## v1.7 - AI-verkefnasmiður kennara

Nýtt:

- Kennari fær hnapp: `🤖 Verkefnasmiður`
- Kennari skrifar beiðni eins og:
  - `Búðu til 20 verkefni um rafmagn fyrir 6. bekk`
  - `Búðu til 15 verkefni um prósentur fyrir 7. bekk`
  - `Búðu til 10 verkefni um irregular verbs fyrir 7. bekk`
- Verkefnasmiður býr til spurningar í réttum strúktúr
- Kennari getur yfirfarið og breytt spurningum
- Kennari getur vistað allar spurningar beint í spurningabankann
- Hægt að afrita JSON

Athugið: v1.7 notar innbyggðan verkefnasmið sem virkar án OpenAI/API lykils. Seinna má bæta við alvöru AI-tengingu.

### Uppfærsla

Afritaðu yfir núverandi verkefni og ýttu á GitHub:

```cmd
git add .
git commit -m "Skola Royale v1.7 AI question builder"
git push
```
