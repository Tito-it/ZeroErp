# Brief BE — Documenti: che cosa può caricare un template durante il render PDF

> **Destinatari:** backend (`dev/backend-tid`). Una domanda al team DB (§5.3),
> che può cambiare la forma della soluzione ma non la blocca. **Risposta DB
> scritta il 2026-10-01 in §5.3**: `asset:<codice_interno>`. **§4.3 deciso
> da Tid il 2026-10-01**: asset e template solo per emittente, nessun livello
> globale.
>
> **Tipo:** brief di design. Nasce il 2026-09-26 dall'accensione delle regole
> di sicurezza ruff (`S`), che ha trovato il render documentale con
> l'autoescape Jinja spento. **Quel difetto è chiuso** (§1). Questo brief tratta
> quello che resta aperto dopo, e che non è una riga di configurazione.
>
> **Stato:** 📝 da discutere — nessuna riga scritta. Servono le decisioni di
> §4 prima del codice.
>
> **Da leggere per primo: §2 — perché «i template sono fidati» non basta.**

---

## 1. Da dove viene, e che cosa è già chiuso

`documenti.services.render_service` compone il PDF in due passi: Jinja
interpola il context nell'`html_template` della versione, WeasyPrint trasforma
HTML + `css_template` in PDF.

Fino al 2026-09-26 Jinja girava con `autoescape=False`, e il commento diceva
che l'escape dei dati utente toccava ai builder del context. **Nessuno dei
quattro builder lo faceva** (fattura, DDT, ordine, preventivo). Un campo
anagrafica con dentro `<link rel="attachment" href="file:///...">` diventava
HTML vero, e WeasyPrint avrebbe **allegato al PDF un file del server**.

Chiuso con `autoescape=True` e un test che lo presidia
(`test_render_pdf_jinja_escapa_html_nei_valori_del_context`). I dati degli
utenti non possono più iniettare tag.

**Resta aperto l'altro autore dell'HTML: chi scrive il template.**

## 2. Il punto: chi scrive il template, e che cosa può fargli fare WeasyPrint

`_render_with_weasyprint` chiama `HTML(string=...)` e `CSS(string=...)` **senza
`url_fetcher`**. Il fetcher di default di WeasyPrint risolve:

- `http://` e `https://`: il server che genera il PDF fa richieste in uscita
  verso qualunque indirizzo, compresi quelli interni (SSRF);
- `file://`: legge file del filesystem del backend;
- `data:`: contenuto già dentro la stringa, senza nessun accesso.

Chi scrive un template può quindi mettere in un PDF:

- `<link rel="attachment" href="file:///.../.env.systemd">`: il file delle
  variabili d'ambiente (credenziali DB, chiave Fernet) allegato al PDF;
- `<img src="file:///<DOCUMENTI_STORAGE_ROOT>/...">` o un allegato preso dallo
  storage documentale: **documenti di un altro emittente**;
- `url(http://169.254.../...)` nel CSS: una richiesta verso la rete interna.

Il commento storico dice che i template «sono creati da admin via
Configurazione e sono fidati». Questo non regge per due motivi:

1. **I template sono per emittente fiscale** (`template_documenti`: unicità
   `emittente_fiscale + sorgente + codice`). Chi ha `documenti_template_manage`
   su un emittente non è per forza chi amministra il server. In
   un'installazione con più emittenti, il template di A può leggere lo storage
   di B.
2. **Anche l'admin del sistema** non dovrebbe poter leggere il filesystem del
   backend da un'interfaccia web. Il perimetro dell'admin applicativo è il
   database, non la macchina.

⚠️ Non è un difetto da tamponare con un `url_fetcher` che rifiuta tutto.
Chiudere tutto oggi non rompe niente: l'ho verificato, nessun template seedato
usa `src=`, `href=` o `url(`. Però chiuderebbe anche la strada per cui gli
**asset** esistono.

## 3. Gli asset: il pezzo che manca

`documenti.template_asset` esiste già (Tranche G). È caricabile con upload e
whitelist MIME per tipo (`LOGO`, `FIRMA`, `IMMAGINE`, `PDF`, `CSS`), va nello
storage con `storage_key` e sha256, è immutabile (Decisione 66) e non si
cancella.

**Nel render però nessuno li collega.** `render_service` non li risolve, e il
commento su `_render_with_weasyprint` dice solo che «il template dovrebbe usare
URL assolute per risorse esterne (asset documentali via storage_uri
risolvibile)». Oggi quindi un template non ha un modo previsto per mostrare il
logo dell'emittente. L'unica strada che funziona è quella da chiudere: l'URL
esterna o il `file://`.

La decisione sul fetcher e quella su come un template richiama un asset sono
**la stessa decisione**. Per questo stanno in un brief solo.

## 4. Decisioni da prendere

### 4.1 Come un template richiama un asset

Proposta: uno **schema dedicato** risolto dal nostro `url_fetcher`, per
esempio `asset:LOGO` o `asset:<codice>`. Il fetcher lo traduce nella lettura
dallo storage, **dentro il perimetro dell'emittente del template**.

Alternative considerate:
- *Il builder mette l'asset nel context come `data:` URI.* Funziona, ma il
  context deve sapere quali asset servono a ogni template (accoppiamento), e
  un PDF con dieci immagini gonfia la stringa HTML.
- *URL HTTP del backend (`/api/.../asset/<id>`).* Il render farebbe una
  richiesta HTTP a sé stesso, con autenticazione da inventare. È la strada
  più fragile.

### 4.2 Che cosa il fetcher ammette

Proposta, lista chiusa:
- `asset:<codice_interno>` → storage, solo asset **attivi e validi**
  (`validita @> current_date`) con lo **stesso** `emittente_fiscale_id` del
  template (§4.3);
- `data:` → ammesso, perché non accede a niente;
- **tutto il resto rifiutato**: `file:`, `http(s):`, schemi ignoti.

⚠️ Il rifiuto deve essere un errore parlante (`E_DOCUMENTI_RENDER_FAILED` con
l'URL rifiutata nel `detail`), non un'immagine mancante in silenzio.
WeasyPrint, se il fetcher fallisce, di default logga e va avanti: il PDF esce
senza logo e nessuno sa perché. È lo stesso tipo di difetto che non dà errore.

### 4.3 Asset di sistema e asset dell'emittente — ✅ deciso

**Deciso da Tid il 2026-10-01: solo per emittente.** Il modello non ha un
livello globale, né per gli asset né per i template (`emittente_fiscale_id`
`NOT NULL` su entrambi, §5.3), e per ora non se ne aggiunge uno. Non c'è
quindi nessuna regola di risoluzione e nessun ripiego. Un template vede
soltanto gli asset del suo emittente. Se il template chiede un `asset:` che
non esiste, il fetcher alza l'errore parlante di §4.2: un logo generico al
suo posto sarebbe un PDF sbagliato senza nessun errore.

Un livello globale dei template (per esempio un'impaginazione di base per un
emittente nuovo) resta fuori da questo brief. Se tornerà a servire, sarà una
domanda di modello con un brief DB apposito.

### 4.4 Il CSS

`css_template` e gli asset di tipo `CSS` passano dallo stesso fetcher (`url()`,
`@import`), quindi sono coperti da §4.2. Va però deciso se un asset `CSS` può
fare `@import` di un altro asset. È ricorsione: il fetcher la gestisce, ma
serve un limite.

### 4.5 SVG

`image/svg+xml` è ammesso per `LOGO`, `FIRMA` e `IMMAGINE`. Un SVG può a sua
volta referenziare risorse esterne (`<image href="...">`). WeasyPrint le
risolve con lo stesso fetcher, quindi §4.2 le copre. Va comunque scritto un
test con un SVG che punta a `file://`.

## 5. Ricadute

### 5.1 Backend
- `url_fetcher` in `render_service`: BB unico, testato caso per caso (`asset:`
  valido, fuori perimetro, non attivo, `data:`, `file:`, `http:`, SVG annidato,
  CSS `@import`).
- Risoluzione `asset:` → lettura storage con il BB `percorso_allegato`, che già
  impedisce di uscire dalla radice.
- Il context del render deve portare l'emittente del template, per il
  perimetro.

### 5.2 Frontend
- L'editor dei template dovrebbe mostrare come si richiama un asset (elenco
  dei codici disponibili). È fuori da questo brief: si decide dopo §4.1.

### 5.3 Domanda al team DB
- Il `codice` dell'asset è unico per emittente e quindi può reggere
  `asset:<codice>`, oppure serve un `codice_interno` immutabile, come per i
  template? Se l'asset si rinomina, i template che lo citano si rompono. La
  risposta decide la sintassi di §4.1.

**Risposta DB (2026-10-01, verificata sui changeSet, non sul DB vivo):**

- **Il `codice_interno` c'è già, e non serve nessun lavoro DB.**
  `documenti.template_asset` (changeSet `20260429-55`) ha `codice_interno
  varchar(120) NOT NULL`, unico per emittente
  (`uq_template_asset_emittente_codice_interno`) e non vuoto. È immutabile
  grazie al lock automatico (linee-guida-sql §6b/§6c): la regola
  `LOCK_COLUMNS` di `dbops.automation_rules_tbl` vale per tutte le tabelle
  (`*all`), lo schema `documenti` è in `dbops.automation_scope`, e la sola
  presenza della colonna fa nascere il lock. Una modifica dà
  `E_CODICE_NON_MODIFICABILE`.
- **Il `codice` invece si può modificare.** È unico per emittente, ma non
  c'è nessun lock: il guard A4 (`trgfn_template_asset_protect_file`) blocca
  solo le colonne del file (`storage_key`, `sha256`, `file_size_bytes`,
  `mime_type`, `file_name`). È un'etichetta da mostrare (§6c).
- **Quindi la sintassi è `asset:<codice_interno>`.** Lo dice la regola d'oro
  di §6c: la logica si aggancia solo a `codice_interno`. La chiave del fetcher
  è `(emittente del template, codice_interno)`, e corrisponde esattamente al
  vincolo unico.

⚠️ **Una premessa di §4.2 e §4.3 non regge sul modello: gli asset di sistema
non esistono.** In `template_asset` la colonna `emittente_fiscale_id` è `NOT
NULL`, e lo è anche in `template_documenti` (changeSet `20260429-53`).
Inoltre il trigger `a10_default_emittente_ins` (changeSet `20260915-45`,
modo `SOLLEVA`) solleva `E_EMITTENTE_NON_RISOLTO` invece di lasciare NULL.
Non c'è quindi né un «template di sistema» né un «asset di sistema», e in
`template_documenti.md` non esiste la sezione «risoluzione» a cui rimanda
§4.3. Per il BE, oggi:

- in §4.2 il perimetro è uno solo: gli asset con lo **stesso**
  `emittente_fiscale_id` del template. La parentesi su `emittente` NULL va
  tolta;
- §4.3 non era una regola di risoluzione da scegliere, ma una **domanda di
  modello**. Tid l'ha chiusa il 2026-10-01: solo per emittente (vedi §4.3).

Nota per §4.2 («attivi e validi»): la validità si legge da `validita @>
current_date`, colonna `GENERATED ALWAYS … STORED` (changeSet `20260514-27`).
Va letta così, senza ricalcolarla da `valido_dal`/`valido_al`.

## 6. Fuori perimetro

- L'autoescape Jinja: chiuso (§1).
- Il motore di render alternativo: `_ENGINE_WHITELIST` resta `WEASYPRINT`.
- La sanitizzazione dell'HTML del template in fase di salvataggio. Il fetcher
  chiude l'accesso alle risorse, che è il rischio concreto. Filtrare i tag al
  salvataggio sarebbe un secondo cancello, da valutare solo se emerge un caso
  che il fetcher non copre.
