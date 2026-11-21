# Test UI motore documentale parametrico

> Suite di test manuali per verificare il funzionamento end-to-end del
> motore documentale dopo Tranche L (Configurazione "Modelli documenti")
> e Tranche M (pulsante "Genera PDF" su preventivo). Da eseguire dopo
> aver applicato le migration DB Fase A e fatto partire backend + frontend.
>
> **Stato dipendenze**: lavoro in working tree non ancora committato.
> Eseguire i test su un branch di lavoro pulito (`dev/backend-tid` /
> `dev/frontend-tid`) dopo restart di Django + Vite.
>
> **Convenzione**:
>
> - **OK** = comportamento atteso che il test deve verificare;
> - **KO** = errore atteso (se manca, e' un bug regressivo);
> - **Note** = come confermare empiricamente (toast, valore atteso, ecc.).

---

## 0. Pre-requisiti

Prima di iniziare la suite, verificare che siano disponibili (eventualmente seedare manualmente):

- [X] Backend in esecuzione: `cd backend && python manage.py runserver` (o
  l'equivalente container) — risponde su `/api/v1/`.
- [X] Frontend in esecuzione: `cd frontend && ./node_modules/.bin/vite` —
  hot reload attivo.
- [X] Almeno 1 emittente fiscale attivo in
  `anagrafiche.emittenti_fiscali` con `id` noto (annotare l'id —
  serve per i form di Configurazione: la UI in v1 chiede l'id
  numerico).
- [X] Almeno 1 record in `config.sorgenti` con `codice='PREVENTIVO'`
  e `attivo=true`.
- [X] Almeno 1 record in `documenti.tipi_documento_output` attivo
  (es. `codice='PREVENTIVO_PDF'`).
- [X] Almeno 1 record in `documenti.render_engine_documento` con
  `codice='WEASYPRINT'` e `attivo=true`.
- [X] Seed `documenti.tipi_asset_documento`:
  `LOGO/IMMAGINE/FIRMA/PDF/CSS` attivi.
- [X] Seed `documenti.tipi_file_documento`: `PDF_FINALE` attivo.
- [X] Almeno 1 preventivo esistente in `vendite.preventivi` con stato
  >= EMESSO/ACCETTATO (oppure BOZZA va bene, l'azione "Genera PDF"
  e' disponibile su qualsiasi stato con detail caricato — il PDF
  e' una snapshot, non modifica il documento).
- [X] Permesso `documenti_template_manage` assegnato all'utente di
  test (per i CRUD di Configurazione). Per i preventivi servono i
  permessi standard `vendite_*` (l'utente che apre il drawer
  preventivo ha gia' i permessi giusti).
- [X] Browser con devtool aperti (Network + Console) — utile per
  verificare gli endpoint chiamati e gli error envelope.

**Annotare prima di iniziare** (riempire qui):

| Cosa                                          | Valore    |
| --------------------------------------------- | --------- |
| Emittente fiscale id                          | _________ |
| Tipo documento output id (es. PREVENTIVO_PDF) | _________ |
| Render engine WEASYPRINT id                   | _________ |
| Preventivo id di test                         | _________ |
| Numero preventivo                             | _________ |

---

## 1. Configurazione → Modelli documenti — Lista + drawer testata

### T1.1 — Apertura voce sidebar

1. Login con utente che ha `documenti_template_manage`.
2. Click sulla voce dominio **Configurazione** in sidebar.
3. Verificare che compaia la voce **"Modelli documenti"** con icona
   `pi pi-file-pdf` (rosso PDF).
4. Verificare che compaia anche **"Asset documentali"** con icona
   `pi pi-paperclip`.

**OK**: entrambe le voci sono presenti, cliccabili, navigano alle
rispettive route (`/config/modelli-documenti` e `/config/asset-documenti`).

---

### T1.2 — Lista template vuota (primo accesso)

**Pre**: nessun template documento ancora creato.

1. Click su "Modelli documenti".
2. Tabella vuota, paginazione 0 risultati.

**OK**: layout standard `app-page` con search + filtri tipo_output /
sorgente / attivo + `NewButton` ("Nuovo template documento") in alto
a destra. Nessun warning console.

---

### T1.3 — Creazione template testata (happy path)

1. Click **Nuovo template documento**.
2. Drawer si apre largo (`960px`) con titolo "Template documento — Nuovo".
3. Compilare:
   - **Codice**: `TPL-PREV-001`
   - **Codice interno**: `TPL_PREV_001`
   - **Descrizione**: `Preventivo standard A4`
   - **Tipo output**: selezionare il record `PREVENTIVO_PDF` dal dropdown
     (LookupSelect carica da `documenti.tipi_documento_output`).
   - **Sorgente**: selezionare `PREVENTIVO` (LookupSelect carica da
     `config.sorgenti`).
   - **ID emittente fiscale**: inserire l'id numerico annotato.
   - **Builder contesto**: selezionare **Preventivo**.
     - **OK**: nessun warning sotto il dropdown (PREVENTIVO e'
       registered lato BE).
     - Selezionare poi **Contratto (non disponibile)** o **Ordine
       (non disponibile)**: deve comparire un Message giallo
       "Builder non ancora attivo lato backend".
     - Tornare a **Preventivo** per il salvataggio.
   - **Pattern nome file**: `preventivo-{numero}.pdf`
   - **Default**: ON
   - **Attivo**: ON (default)
4. Click **Salva**.

**OK**:

- Toast verde "Template creato. Aggiungi una versione per renderlo utilizzabile."
- Il drawer **non si chiude**: evolve in modalita' edit per consentire
  l'aggiunta di versioni (pattern `feedback_drawer_create_autosave_bozza`).
- I 3 campi immutabili (Tipo output / Sorgente / ID emittente) ora sono
  disabilitati e mostrano l'hint "Non modificabile dopo la creazione."
- Sotto un Divider compare la sezione **Versioni** (vuota).

---

### T1.4 — Lista template con record + filtri

1. Chiudere il drawer (Annulla o X).
2. La tabella ora mostra 1 riga: codice `TPL-PREV-001`, tipo output,
   sorgente, emittente, default tag azzurro, attivo verde.
3. Filtrare per **Sorgente** = `PREVENTIVO`: la riga resta visibile.
4. Filtrare per **Sorgente** = altro tipo (se disponibile): tabella
   vuota.
5. Reset filtro Sorgente, filtrare per **Attivo** = `Non attivo`:
   tabella vuota (il template e' attivo).

**OK**: search + 3 filtri funzionano. Click su una riga riapre il
drawer in edit con i dati popolati.

---

### T1.5 — Update testata template

1. Apertura drawer in edit dalla lista.
2. Modificare **Descrizione** in `Preventivo standard A4 (rev. test)`.
3. Provare a modificare **Tipo output** o **Sorgente** o **ID emittente**:
   i campi devono essere disabilitati.
4. Click **Salva**.

**OK**: toast "Template aggiornato". La descrizione aggiornata appare
nella lista (chiudere e riaprire se serve refresh).

---

### T1.6 — Validazione campi obbligatori

1. Click **Nuovo template documento**.
2. Lasciare vuoto **Codice** o **Codice interno** o **Descrizione**.
3. Provare a salvare.

**OK**: il pulsante **Salva** del drawer e' disabilitato finche' tutti
gli `*` obbligatori non sono compilati. Nessun toast di errore (la
validazione e' lato FE, pre-richiesta).

---

### T1.7 — Tentativo creazione duplicato (UNIQUE codice)

**Pre**: T1.3 eseguito (esiste gia' `TPL-PREV-001`).

1. Tentare di creare un nuovo template con **lo stesso codice**
   `TPL-PREV-001` per la stessa coppia (sorgente, emittente).
2. Click Salva.

**OK**: toast rosso con messaggio parlante BE
("Esiste gia' un template con questo codice per la combinazione
emittente+sorgente" o simile mappato da
`uq_template_documenti_emittente_sorgente_codice`). Drawer resta
aperto, dati preservati.

---

## 2. Master-detail versioni dentro drawer template

### T2.1 — Sezione versioni vuota

**Pre**: drawer template aperto in edit (T1.3 o T1.5 chiuso).

1. Riaprire il template in edit.
2. Sezione **Versioni** sotto il Divider mostra DataTable vuota +
   pulsante "Nuova versione" in alto a destra.

**OK**: nessun warning, layout pulito.

---

### T2.2 — Creazione prima versione BOZZA

1. Click **Nuova versione**.
2. Si apre form inline (la DataTable scompare e compare il form).
3. Compilare:
   - **Titolo**: `v1 - Layout A4 standard`
   - **Render engine**: selezionare `WEASYPRINT`
   - **Formato sorgente**: `HTML` (default)
   - **HTML template**:
     ```html
     <html>
       <head><meta charset="utf-8"></head>
       <body>
         <h1>Preventivo {{ preventivo.numero }}</h1>
         <p>Cliente: {{ cliente.denominazione }}</p>
         <p>Data: {{ preventivo.data }}</p>
         <p>Totale: {{ preventivo.totali.documento }} {{ preventivo.totali.valuta_codice }}</p>
       </body>
     </html>
     ```
   - **CSS template**: `body { font-family: sans-serif; }`
   - **Markdown template**: lasciare vuoto.
   - Page format/orientation/margini: default.
   - Attivo: ON.
4. Click **Salva**.

**OK**:

- Toast "Versione salvata".
- Form inline si chiude e ricompare la DataTable con la nuova riga:
  numero `1`, titolo, stato `BOZZA` (tag azzurro), valido_dal/al
  vuoti, attivo verde.

---

### T2.3 — Modifica versione BOZZA

1. Click su riga versione BOZZA.
2. Form inline si apre con tutti i campi compilati (incluso HTML/CSS).
3. Modificare **Titolo** in `v1 - Layout A4 standard (test)`.
4. Salva.

**OK**: toast "Versione salvata", titolo aggiornato in lista.

---

### T2.4 — Pubblicazione versione

1. Sulla riga versione BOZZA, click sul kebab `RowActionsMenu`.
2. Click **Pubblica**.
3. Si apre il dialog "Pubblica versione" con:
   - Message giallo "Pubblicare la versione la rendera' immutabile..."
   - Campo **Valido dal** preselezionato a OGGI.
   - Campo **Valido al** vuoto (no scadenza).
4. Click **Pubblica**.

**OK**:

- Toast "Versione pubblicata".
- Riga aggiornata: stato `PUBBLICATA` (tag verde), valido_dal =
  data di oggi.

---

### T2.5 — Tentativo modifica versione PUBBLICATA

1. Click sulla riga versione PUBBLICATA.

**OK**: il form inline NON si apre (per design: solo BOZZA editabile).
La riga rimane selezionata ma nessuna azione di edit viene esposta.

> Nota: l'oggetto resta cliccabile, ma `openEdit` ha guard
> `if (row.stato !== 'BOZZA') return`. Defense-in-depth: anche se
> qualcuno bypassa, il trigger DB A1 (`protect_pubblicata`) blocca
> l'update.

---

### T2.6 — Clona versione PUBBLICATA in nuova BOZZA

1. Sulla riga versione PUBBLICATA, click kebab → **Clona**.

**OK**:

- Toast "Versione clonata in nuova bozza".
- Compare una nuova riga: numero `2`, titolo identico al sorgente,
  stato `BOZZA`, valido_dal/al vuoti.
- La PUBBLICATA originale resta intatta.

---

### T2.7 — Pubblicazione seconda versione (overlap protection)

1. Pubblicare la versione 2 (T2.4 con ripetizione, valido_dal = OGGI).

**OK** atteso: 

- 🔴 **Errore atteso**: il trigger DB EXCLUDE GiST blocca l'overlap
  con un'altra PUBBLICATA attiva sullo stesso template + valido_dal
  uguale o coincidente. Toast rosso con messaggio parlante:
  "Esiste gia' una versione PUBBLICATA per questo template nello stesso
  intervallo di validita'..." (mappato da `excl_template_documenti_versioni_overlap`).

> Per superare il blocco: prima chiudere la versione 1 (ridurre
> `valido_al` su quella PUBBLICATA — pero' in v1 NON c'e' un comando
> esplicito per chiudere una pubblicata; la documentazione progetto
> dice "Pubblicazione versione senza chiusura auto del precedente
> `valido_al`" — per il test basta verificare che l'overlap sia
> bloccato).

---

### T2.8 — Eliminazione versione BOZZA

**Pre**: avere una versione BOZZA (es. la versione 2 ancora non pubblicata,
oppure crearne una terza T2.2-style).

1. Sulla riga BOZZA, click kebab → **Elimina**.
2. Compare ConfirmDialog "Eliminare la versione N? Operazione non reversibile."
3. Click **Conferma**.

**OK**:

- Toast "Versione eliminata".
- Riga rimossa dalla lista.

---

### T2.9 — Tentativo eliminazione versione PUBBLICATA

1. Sulla riga versione PUBBLICATA, click kebab.

**OK**: la voce **Elimina** NON appare nel menu (build_row_actions
filtra per `stato === 'BOZZA'`). Defense-in-depth: anche tramite API
DELETE diretta, il trigger DB A2 `block_delete` rifiuterebbe.

---

## 3. Configurazione → Asset documentali

### T3.1 — Lista asset vuota

1. Click voce sidebar **Asset documentali**.
2. Tabella vuota, layout standard, `NewButton` "Nuovo asset" in alto a destra.

**OK**: nessun errore console.

---

### T3.2 — Upload asset LOGO (happy path)

**Pre**: avere a disposizione un file `.png` < 25MB (es. logo aziendale).

1. Click **Nuovo asset**.
2. Drawer width `STANDARD` con titolo "Asset documentale — Nuovo".
3. Compilare:
   - **Codice**: `LOGO-PRINC`
   - **Codice interno**: `LOGO_PRINC`
   - **Descrizione**: `Logo aziendale principale`
   - **Tipo asset**: `LOGO` (LookupSelect su
     `documenti.tipi_asset_documento`).
   - **ID emittente fiscale**: id annotato.
   - **Valido dal/al**: lasciare vuoti (default DB).
   - **Attivo**: ON.
   - **File**: click "Scegli file" → selezionare il PNG.
4. Verificare che sotto il file picker compaia `nome.png (NN KB)`.
5. Click **Salva**.

**OK**:

- Toast "Asset caricato".
- Drawer si chiude.
- La tabella mostra il nuovo asset con codice, descrizione, tipo,
  MIME `image/png`, file_name, dimensione human-readable, emittente,
  attivo verde.

---

### T3.3 — Upload con MIME mismatch (atteso KO BE)

1. Click Nuovo asset.
2. Compilare metadati con **Tipo asset** = `LOGO`.
3. Caricare un file `.pdf` invece che `.png`.
4. Salva.

**OK**: 🔴 toast rosso con messaggio parlante BE:
"MIME 'application/pdf' non valido per tipo asset 'LOGO'. mime_ammessi=..."
(mappato da `_guard_mime_for_tipo` Tranche G).
Drawer resta aperto, dati preservati.

---

### T3.4 — Upload con tipo `ALTRO` (atteso KO BE)

1. Click Nuovo asset.
2. Compilare metadati con **Tipo asset** = `ALTRO`.
3. Caricare un file qualsiasi.
4. Salva.

**OK**: 🔴 toast rosso "Tipo asset 'ALTRO' non ammesso per upload."
(Decisione 67: ALTRO non in whitelist v1).

---

### T3.5 — Upload duplicato (stesso file, stesso emittente)

**Pre**: T3.2 eseguito.

1. Click Nuovo asset.
2. Caricare lo **stesso PNG** di T3.2.
3. Salva (con codice/codice_interno diversi per evitare violazione di
   quei vincoli).

**OK**: 🔴 toast rosso "Esiste gia' un asset con lo stesso contenuto
(sha256) per l'emittente. Riusa quello esistente."
(Mappato da `uq_template_asset_emittente_sha256`).

---

### T3.6 — Update metadati asset (file immutabile)

1. Click su una riga asset esistente.
2. Drawer si apre in edit.
3. Verificare: i campi **Codice / Codice interno / Tipo asset / ID
   emittente** sono disabilitati. Compare hint "Tipo asset non
   modificabile dopo la creazione." e Message info "Solo metadati
   editabili. Per cambiare il file caricare un nuovo asset."
4. **NON** compare il file picker (solo in create).
5. Modificare **Descrizione** + impostare **Valido al** futuro (es.
   2027-12-31).
6. Salva.

**OK**: toast "Asset aggiornato". Riga aggiornata in lista.

---

### T3.7 — Disattivazione asset (soft via PATCH attivo=false)

1. Aprire asset in edit.
2. Disattivare il toggle **Attivo**.
3. Salva.

**OK**: tag attivo passa da verde a giallo "Non attivo". Il record
resta in tabella (default filtro Attivo=true potrebbe nasconderlo:
cambiare il filtro a "Tutti" o "Non attivo" per verificare).

> Nota: Il DELETE non e' esposto in UI (trigger DB A3 block_delete).
> La disattivazione e' soft via `attivo=false` o `valido_al` in passato.

---

## 4. Generazione documento da preventivo (Tranche M)

### T4.1 — Apertura preventivo, pulsante Genera PDF visibile

**Pre**: T1-T2 completati con almeno 1 template PUBBLICATA per
(sorgente=PREVENTIVO, emittente=X) e l'emittente del template
**coincide** con l'emittente del preventivo annotato.

1. Andare in **Vendite → Preventivi**.
2. Aprire il preventivo annotato (click su riga).
3. Drawer preventivo si apre.
4. Verificare che, sotto le azioni di stato, compaia un pulsante
   **Genera PDF** con icona `pi pi-file-pdf` rossa.

**OK**: pulsante visibile a destra. Allineato pattern `app-pdf-btn`
(rosso PDF, hover su sfondo rosso chiaro).

---

### T4.2 — Generazione con 1 solo template applicabile (download diretto)

**Pre**: 1 solo template PUBBLICATA applicabile per la coppia.

1. Click **Genera PDF**.
2. Pulsante in loading spinner.

**OK**:

- Toast verde "Documento PDF generato".
- Il browser scarica automaticamente un file
  `preventivo-{numero}.pdf` (o pattern definito in T1.3).
- Aprire il PDF: contenuto coerente con l'HTML template (numero,
  cliente, data, totale).
- Sotto la sezione Integrazione del drawer compare la sezione
  **Documenti generati** con la nuova riga (progressivo `1`,
  generato_at = adesso, titolo, nome_file, stato `GENERATO`).

---

### T4.3 — Generazione con scelta template (>1 applicabile)

**Pre**: creare un secondo template PUBBLICATA per la stessa coppia
(sorgente_tipo, emittente, output) — uno con `is_default=true`,
l'altro `is_default=false`.

> Nota: il vincolo partial-unique `is_default` per (output, sorgente,
> emittente) impedisce di averne 2 default; uno solo dei due puo'
> essere default.

1. Click **Genera PDF**.

**OK**:

- Si apre dialog "Scegli template documento" con 2 voci:
  - quella `is_default=true` con tag azzurro "Default" e
    pre-selezionata.
  - l'altra senza tag.
- Click **Genera** (o cambiare selezione e poi Genera).
- Toast "Documento PDF generato" + download automatico + lista
  aggiornata con il nuovo progressivo (numero successivo a quello
  di T4.2).

---

### T4.4 — Nessun template applicabile

**Pre**: cancellare/disattivare tutti i template per (sorgente=PREVENTIVO,
emittente=X) — oppure aprire un preventivo di un emittente che non ha
template configurati.

1. Click **Genera PDF**.

**OK**: toast giallo (warn) "Nessun template documentale configurato
per questa sorgente. Aggiungi un template in Configurazione."
Nessuna chiamata DB di INSERT, nessun documento creato.

---

### T4.5 — Download dalla lista documenti

**Pre**: T4.2 o T4.3 eseguito (almeno 1 documento generato in lista).

1. Sulla riga del documento generato, click kebab `RowActionsMenu`.
2. Click **Scarica PDF**.

**OK**:

- Il browser scarica il PDF (stesso filename salvato in DB).
- Aprire il PDF: contenuto identico a quello scaricato in T4.2/T4.3.
- (Se controlli lato BE/DB) verificare che in
  `documenti.documenti_generati_eventi` sia comparsa una nuova riga
  `evento_tipo='SCARICATO'`, `esito='OK'`, `user_id` = id utente.

---

### T4.6 — Refresh lista documenti

1. Click sull'icona refresh (`pi pi-refresh`) accanto al titolo
   "Documenti generati".

**OK**: la lista si ricarica (spinner breve), eventuali nuovi
documenti generati da altri tab/utenti appaiono.

---

### T4.7 — Pulsante NON visibile su preventivo senza emittente

**Pre**: difficile da riprodurre in UI (preventivi nel DDL hanno
`emittente_fiscale_id NOT NULL`). Questo test verifica solo lo
stato sentinel del template.

1. Aprire un preventivo qualsiasi.
2. Verificare che il pulsante "Genera PDF" sia visibile **solo**
   quando il drawer mostra il detail (post-load), non subito
   all'apertura.

**OK**: il pulsante e' rendered con `v-if="hasDetail && detail.emittente_fiscale_id"`.
Nessun pulsante visibile durante il primo loading.

---

### T4.8 — Generazione su preventivo readonly/superseded

**Pre**: avere un preventivo in stato superseded (esiste una revisione
successiva). Il drawer apre in modalita' readonly.

1. Aprire il preventivo superseded.
2. Verificare che il banner giallo "Revisione superata" sia presente.
3. Verificare che il pulsante **Genera PDF** sia comunque visibile
   (il PDF e' una snapshot, non modifica il preventivo).
4. Click Genera PDF.

**OK**: la generazione funziona normalmente; il documento generato
appare nella lista. Comportamento intenzionale: il PDF di un
preventivo storico e' utile (es. ristampa).

---

## 5. Edge case BE / errori attesi

### T5.1 — Generazione con template senza versione PUBBLICATA

**Pre**: avere un template `is_default=true` senza alcuna versione
PUBBLICATA (solo BOZZA).

1. Click Genera PDF dal preventivo.

**OK**: 🔴 toast rosso "Nessuna versione PUBBLICATA attiva per il
template." (mappato da `_resolve_versione_pubblicata` BE).
Nessun INSERT in `documenti_generati`.

---

### T5.2 — Generazione con context_builder non registrato

**Pre**: creare un template con `context_builder_code='CONTRATTO'`
(non registrato in v1) + versione PUBBLICATA.

1. Click Genera PDF.

**OK**: 🔴 toast rosso "Context builder 'CONTRATTO' non registrato
lato backend." (mappato dal registry whitelist Decisione 18+74).

---

### T5.3 — Generazione con file_name_pattern variabile mancante

**Pre**: creare un template con
`file_name_pattern='preventivo-{var_inesistente}.pdf'` + versione
PUBBLICATA.

1. Click Genera PDF.

**OK**: 🔴 toast rosso "Variabile mancante nel context per il pattern
file_name 'preventivo-{var_inesistente}.pdf'." (mappato da
`_format_nome_file` BE).

---

### T5.4 — Generazione con HTML template che usa variabile inesistente

**Pre**: creare un template con HTML che contiene
`{{ variabile_inventata }}` non presente nel context PREVENTIVO.

1. Pubblicare la versione e generare il PDF.

**OK**: 🔴 toast rosso "Errore di rendering del template HTML (Jinja).
detail=UndefinedError: 'variabile_inventata' is undefined" (mappato
da `StrictUndefined` Tranche I render_service).

---

## 6. Multi-utente / scope

### T6.1 — Scope emittente operatore non admin

**Pre**: un utente non-admin con `documenti_template_manage` ma scope
limitato a un sottoinsieme di emittenti (es. solo emittente 11).

1. Login con questo utente.
2. Vai in Configurazione → Modelli documenti.

**OK**:

- La lista mostra solo i template con `emittente_fiscale_id` nello
  scope dell'utente.
- Provando a creare un template con emittente fuori scope (compilando
  l'id manualmente) → toast rosso "emittente_fiscale_id non valido o
  non accessibile."
- Stesso comportamento per Asset documentali.

---

### T6.2 — `userScoped: true` reset al logout

**Pre**: utente A con un certo scope; utente B con scope diverso.

1. Login utente A → aprire Modelli documenti, scrollare, applicare
   filtri.
2. Logout.
3. Login utente B.
4. Aprire Modelli documenti.

**OK**: la lista mostra i template dell'utente B (non dati residui
di A). Filtri / paginazione resettati. Memoria
`feedback_pinia_userscoped` rispettata.

---

## 7. Cleanup test

Al termine della suite (per evitare di lasciare dati di test in DB):

1. **Asset**: i record asset NON si possono eliminare (trigger DB A3).
   Soft-disable: PATCH `attivo=false` dai T3.2/T3.5.
2. **Versioni template**: eliminare le BOZZE create in T2.8. Le
   PUBBLICATE non si possono eliminare (trigger DB A2). Per rimuoverle
   dal DB: passaggio diretto al team DB con DDL/migration di cleanup.
3. **Template testata**: PATCH `attivo=false` (no DELETE fisico:
   Decisione progetto, soft via attivo).
4. **Documenti generati**: NO DELETE (trigger DB block_delete su
   `documenti_generati`). Restano per audit. I file sul filesystem
   in `<DOCUMENTI_STORAGE_ROOT>/documenti/<emittente>/<sha>.pdf`
   restano. Per cleanup massivo locale: cancellare manualmente la
   cartella `var/documenti/` (default `BASE_DIR/var/documenti`)
   per i record orfani locali dopo aver fatto pulizia DB.

---

## 8. Checklist riassuntiva

| Sezione                            | Tutti OK? |
| ---------------------------------- | --------- |
| 1. Lista template + drawer testata | [ ]       |
| 2. Master-detail versioni          | [ ]       |
| 3. Asset documentali               | [ ]       |
| 4. Generazione PDF da preventivo   | [ ]       |
| 5. Edge case BE                    | [ ]       |
| 6. Multi-utente / scope            | [ ]       |

**Bug riscontrati durante la suite** (annotare qui):

| ID test | Comportamento atteso | Comportamento osservato | Note |
| ------- | -------------------- | ----------------------- | ---- |
|         |                      |                         |      |

---

*Test UI motore documentale parametrico — ZeroERP (WIP, 2026-05-04)*
