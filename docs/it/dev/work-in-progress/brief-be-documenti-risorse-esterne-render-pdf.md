# Brief BE — Documenti: che cosa può caricare un template durante il render PDF

> **Destinatari:** backend (`dev/backend-tid`). Una domanda al team DB (§5.3),
> che può cambiare la forma della soluzione ma non la blocca.
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
- `asset:` → storage, solo asset **attivi e validi** dell'emittente del
  template (quelli di sistema, `emittente` NULL, da decidere in §4.3);
- `data:` → ammesso, perché non accede a niente;
- **tutto il resto rifiutato**: `file:`, `http(s):`, schemi ignoti.

⚠️ Il rifiuto deve essere un errore parlante (`E_DOCUMENTI_RENDER_FAILED` con
l'URL rifiutata nel `detail`), non un'immagine mancante in silenzio.
WeasyPrint, se il fetcher fallisce, di default logga e va avanti: il PDF esce
senza logo e nessuno sa perché. È lo stesso tipo di difetto che non dà errore.

### 4.3 Asset di sistema e asset dell'emittente

Un template di sistema (senza emittente) può usare solo asset di sistema?
Un template di emittente può usare quelli di sistema come ripiego (per esempio
un logo generico)? Serve la regola di risoluzione, in modo simmetrico a quella
dei template stessi (§«risoluzione» di `template_documenti.md`).

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

## 6. Fuori perimetro

- L'autoescape Jinja: chiuso (§1).
- Il motore di render alternativo: `_ENGINE_WHITELIST` resta `WEASYPRINT`.
- La sanitizzazione dell'HTML del template in fase di salvataggio. Il fetcher
  chiude l'accesso alle risorse, che è il rischio concreto. Filtrare i tag al
  salvataggio sarebbe un secondo cancello, da valutare solo se emerge un caso
  che il fetcher non copre.
