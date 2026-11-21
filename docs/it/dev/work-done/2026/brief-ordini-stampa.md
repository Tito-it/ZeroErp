# Brief DB — Stampa documento ordine (PDF)

> **Origine**: richiesta Tid 2026-06-04. Estensione del §12 dell'analisi ordini
> (`analisi-ordini-vendita.md`). Questo brief copre **solo il workstream DB**
> (§12.1): è il prerequisito che BE/FE attendono
> (`feedback_be_fe_attende_prerequisiti_db`).
>
> **Principio**: ordini è il **quarto dominio** cablato sul motore `documenti`
> già usato da preventivi / offerte commerciali / contratti
> (`guide/documenti-e-stampe.md`). **Niente nuovo motore, niente nuove tabelle**:
> il lavoro DB è **un solo seed di lookup** (il tipo documento). I **template**
> HTML/CSS si creano **manualmente** (come per gli altri tre domini), fuori dal
> seed Liquibase.

---

## 1. Decisioni prese (Tid, 2026-06-04)

1. **Template → gestione manuale.** I template `documenti.template_documenti` +
   `template_documenti_versioni` per ordini si creano a mano (come finora per
   preventivo/offerta/contratto). **Non** entrano nel seed Liquibase. → il
   workstream DB si riduce al solo tipo documento (§3).
2. **Codice tipo documento = `ORDINE_VENDITA`** (non `ORDINE_CLIENTE`). Coerente
   con la sorgente `config.sorgenti.codice='ORDINE_VENDITA'` e con il
   `context_builder_code='ORDINE_VENDITA'` previsto lato BE (§12.0.2 analisi).
   Allinea ordini alla famiglia (`PREVENTIVO`/`CONTRATTO`/`OFFERTA_COMMERCIALE`:
   tipo documento = nome sorgente).

---

## 2. Stato verificato (2026-06-04)

Contro il codice attuale (`db/changelog/migrations_v2/`):

| Elemento | Stato | Azione |
| --- | --- | --- |
| `config.sorgenti` `ORDINE_VENDITA` | ✅ presente, `id=6`, attivo (`sorgenti.csv`) | **nessuna** — riuso |
| `documenti.tipi_documento_output` `ORDINE_VENDITA` | ❌ assente (CSV aveva solo PREVENTIVO/CONTRATTO/OFFERTA_COMMERCIALE) | **seed nuova riga** → §3 |
| Tabelle motore `documenti.*` | ✅ esistenti e collaudate | nessuna — riuso |
| Template ordine | gestione manuale | fuori scope DB |

> **Tabelle motore (riuso, già collaudate)**: `tipi_documento_output`,
> `template_documenti`, `template_documenti_versioni`, `documenti_generati`,
> lookup `tipi_asset_documento`/`tipi_file_documento`/`render_engine_documento`.
> Pubblicazione versione template (lato manuale):
> `documenti.fn_pubblica_template_documento_versione`
> (immutabilità post-pubblicazione via trigger protect — ogni modifica = nuova
> versione; senza versione **PUBBLICATA** la generazione fallisce,
> `documenti-e-stampe.md` §2.3).

---

## 3. Workstream DB — unico deliverable: seed tipo documento

### 3.1 Riga seedata

Aggiunta a `80_data/sql/documenti/tipi_documento_output.csv`:

```csv
4,ORDINE_VENDITA,ORDINE_VENDITA,Ordine vendita,true,{},"true",2026-06-04 00:00:00,titodb,2026-06-04 00:00:00,titodb,NULL
```

(`id=4` — prossimo libero; `codice`/`codice_interno=ORDINE_VENDITA`;
`attivo=true`; `meta={}`; `storicizza=true`.)

### 3.2 Meccanismo di applicazione

**Nessun nuovo changeset.** Il CSV è caricato dal changeset seed-base
`80_data/changelog/20260429-58-upsert-documenti-seed-base-mctit.yaml`, che è
`runOnChange: true` + `validCheckSums: ANY` (`loadUpdateData`, upsert per
`primaryKey: id`): è stato progettato apposta per la **crescita del seed**.
Aggiungendo la riga, alla prossima migrazione il changeset si ri-applica e fa
upsert della nuova riga. Una sola fonte di verità per il lookup.

> ⚠️ **Da confermare col team DB** (`feedback_db_actions_passaggio_team`):
> append al CSV canonico (scelta attuale) **oppure** CSV+changeset dedicato.
> La scelta non cambia il dato finale, solo l'organizzazione del seed.

### 3.3 Test pgTAP

`db/pgtap/documenti/test-documenti-tipo-ordine-vendita.sql` (4 test):

1. `ORDINE_VENDITA` presente in `tipi_documento_output`;
2. `ORDINE_VENDITA` attivo;
3. sorgente `ORDINE_VENDITA` presente e attiva in `config.sorgenti` (guardia riuso);
4. nessun `codice` duplicato (idempotenza seed).

Esecuzione: `scripts/testpgtap.sh db/pgtap/documenti/test-documenti-tipo-ordine-vendita.sql`.

---

## 4. Stato implementazione — ✅ EVASO (DB), 2026-06-04

- [x] Riga `ORDINE_VENDITA` aggiunta a `tipi_documento_output.csv`
- [x] Test pgTAP `test-documenti-tipo-ordine-vendita.sql`
- [x] Migrazione locale applicata (`make db-migrate`)
- [x] Test pgTAP eseguito e **verde**
- [ ] Commit / PR — **attende "procedi"** (`feedback_no_commit_autonomo`)

> Il workstream DB di questo brief è **chiuso**: il tipo documento
> `ORDINE_VENDITA` è seedato e risolvibile. Resta solo il commit/PR su conferma.
> Tutto il resto (template manuale, context builder BE, view stampa, azione FE)
> è **fuori scope DB** → §5.

---

## 5. Confini e seguito (fuori da questo brief)

- **Indipendente** dall'estensione modello ordini A+E (§3.0 analisi): parallelo.
- **A valle** (coperti da §12.2/§12.3 analisi, lato BE/FE):
  - context builder BE con `CODE='ORDINE_VENDITA'` nel registry
    (`apps/documenti/services/context_builders/`);
  - view stampa ordini con `_CODICE_SORGENTE_ORDINE = "ORDINE_VENDITA"`;
  - creazione **manuale** del template + versione PUBBLICATA (HTML conferma
    d'ordine: clone layout preventivo/offerta, senza revisioni/listino testata,
    `+fatturazione_trigger`, eventuali chip `documento_origine`/`agente`);
  - azione FE "Stampa" sul dominio ordini.
  - BE/FE **attendono** la delivery di questo seed.

---

## 6. Piano di completamento — rettifica flusso documentale ordine

> **Rettifica 2026-06-05**: la scelta descritta in
> `analisi-ordini-vendita.md` §12.4 come "stampa disaccoppiata dallo stato"
> non è allineata al pattern già usato da preventivi, contratti e offerte.
> Il comportamento target per gli ordini deve seguire lo stesso schema:
> in `DRAFT` solo anteprima; nel passaggio `DRAFT -> CONFERMATO` generazione
> automatica del documento con possibilità di allegare file; dalla lista,
> icona documenti disabilitata in bozza e abilitata dopo bozza per aprire la
> gestione documentale dei documenti già generati.
>
> **Perché si cambia (contesto)**: la modalità (a) "anteprima on-demand" non era
> una dimenticanza né legata alla provenienza da offerte/preventivi
> (`documento_origine`, tracciabilità — tema indipendente dalla stampa). Era una
> scelta MVP **deliberata** (analisi §12.4): l'ordine ha già `numero` in BOZZA e
> senza un punto di persistenza il dialog "documenti generati" sarebbe stato
> vuoto, quindi si era partiti anteprima-only — **lasciando esplicitamente la
> porta aperta al caso (b)** (gli endpoint BE genera/lista/download/allegati erano
> già stati predisposti). Questa §6 adotta il caso (b), che è la soluzione
> migliore sul merito (`feedback_no_quick_fix_soluzione_assoluta`): la conferma
> d'ordine è l'atto formale verso il cliente (ed è il trigger del push a
> commessa), quindi è il momento naturale in cui il PDF va generato e archiviato.

### 6.1 DB — nessuna modifica, solo una verifica di configurazione

> **Esito analisi 2026-06-05**: la §6 **non richiede sviluppo DB** (niente
> migration, seed, DDL o pgTAP nuovi). Verificato contro il codice attuale:

- **Stati**: `config.stati_doc_ordini` contiene **già tutti** gli stati richiesti
  (`DRAFT, CONFERMATO, ALLOCATO, SPEDITO, CONSEGNATO, ANNULLATO, FATTURATO`).
  `STATI_ORDINE_CON_DOCUMENTO` (post-bozza) usa stati esistenti → **niente seed**.
- **Azioni/transizioni — ora allineate alla famiglia** (aggiornato 2026-06-05):
  preventivi/offerte modellano le azioni con un sistema **data-driven a DB**
  (`fn_available_actions_*` + matrici transizioni). Gli ordini, che ne erano privi,
  sono stati **uniformati** (brief
  [brief-ordini-azioni-data-driven.md](brief-ordini-azioni-data-driven.md),
  consegnato): esiste `script.fn_available_actions_ordine` + matrice
  `config.transizioni_stati_ordini` + guard `trgfn_ordini_guard_transizione`, e
  `get_ordine` legge le capability dal DB. → l'azione di emissione **non sarà una
  `can_emetti` hardcoded** ma l'azione `conferma` (transizione `DRAFT→CONFERMATO`)
  già presente in matrice: la §6 la aggancia alla generazione documento.
- **Tipo documento + motore**: `documenti.tipi_documento_output.ORDINE_VENDITA`
  già seedato (questo brief §3) e collegato a `config.sorgenti.ORDINE_VENDITA`;
  tabelle `documenti.*` già collaudate. Nessuna modifica.
- **Unica verifica al team DB** (configurazione/dati, **non** migration): che
  esista una **versione template `ORDINE_VENDITA` PUBBLICATA** e `is_default` per
  la tripla (tipo documento, sorgente, emittente). Creata manualmente il
  2026-06-04 → confermare che è ancora pubblicata: senza versione PUBBLICATA
  l'`emetti` fallisce (come per gli altri domini, `documenti-e-stampe.md` §2.3).
- **Vincolo "no CONFERMATO senza documento" → NON serve** (chiuso): l'atomicità è
  garantita dal **savepoint BE** dell'`emetti` (generazione fallita → rollback
  della conferma, §6.2), coerente con la famiglia (preventivi/offerte non hanno un
  vincolo DB equivalente). Il DB resta sui guard esistenti.

> **Nota di simmetria — PREREQUISITO EVASO (aggiornato 2026-06-05)**: gli ordini
> erano l'unico documento vendite senza modello azioni data-driven. Il
> prerequisito è stato **realizzato** (DB + BE + FE): matrice
> `config.transizioni_stati_ordini`, `script.fn_available_actions_ordine`, guard
> `trgfn_ordini_guard_transizione`; `get_ordine` espone `available_actions` e il
> drawer le consuma via `useEntityCapabilities` + `mapAvailableActionsToDrawerActions`.
> Brief: [brief-ordini-azioni-data-driven.md](brief-ordini-azioni-data-driven.md).
> → quando si realizza la §6, l'azione `conferma` (`DRAFT→CONFERMATO`) è **già**
> data-driven: la §6.2/§6.3 vanno scritte appoggiando l'emissione su quell'azione
> (non su una capability hardcoded).

### 6.2 BE — ✅ EVASO (2026-06-05)

> **Stato consegna BE (2026-06-05)**: implementato e verde (13/13 test
> `test_ordini_api.py`). Delta applicato su `dev/backend-tid`:
>
> - `ApiOrdineEmetti` aggiunta in `ordini_documenti_views.py` (clone di
>   `ApiPreventivoEmetti`): orchestra `ordini_service.conferma(id)` +
>   `DocumentGenerationService().genera_documento(...)` + allegati multipart in
>   `transaction.atomic()`. Fallimento generazione → rollback della conferma
>   (stato resta `DRAFT`). Niente `post_permission` (coerente con
>   `ApiOrdineConferma`/`ApiOffertaEmetti`: i guard vivono in `conferma`).
> - Rotta `vendite-ordine-emetti` (`POST /<id>/emetti/`) in `urls_ordini.py`,
>   prima di `/conferma/`.
> - Commento di testata di `ordini_documenti_views.py` riscritto (rimosso
>   "stampa DISACCOPPIATA dallo stato / niente emetti").
> - Test: classe `TestOrdineEmissione` (smoke route + integration atomica
>   conferma+genera+allegati).
> - Doc manuale `api_ordini.md` aggiornato (sezione Emetti, state machine,
>   tabella documenti).
>
> **Decisione `/conferma/` chiusa → opzione (i)**: `/emetti/` è il flusso utente
> (conferma + documento); `POST /<id>/conferma/` **resta** come API di sola
> transizione di servizio (riusata internamente da `emetti`), **non** depreciata
> lato HTTP. Il service `conferma` resta il punto di dominio.
>
> **Residuo**: §6.3 FE (`OrdineEmissioneDialog`, costanti PDF, lista, i18n) +
> verifica al team DB che la versione template `ORDINE_VENDITA` sia ancora
> PUBBLICATA (§6.1).

- **Aggiungere `ApiOrdineEmetti`** (`POST /api/v1/vendite/ordini/{id}/emetti/`,
  multipart) — **clone di `ApiPreventivoEmetti`** (`preventivi_documenti_views.py`).
  Orchestra in **transazione atomica con savepoint annidato**:
  1. `ordini_service.conferma(id)` — transizione `DRAFT -> CONFERMATO` (riusa il
     **punto di dominio esistente**, che governa anche il push a commessa: NON si
     duplica né si sposta la logica di stato);
  2. `DocumentGenerationService().genera_documento(...)` sullo stato CONFERMATO
     (lo snapshot del context riflette il nuovo stato);
  3. allegati multipart opzionali.
  Se la generazione fallisce, il savepoint **annulla la conferma** (come
  preventivi). → l'endpoint vive in `ordini_documenti_views.py` (view documentale),
  `ordini_service.conferma` resta il service di dominio.
- **Riuso, non riscrittura**: gli altri endpoint documentali ordini **esistono
  già** in `ordini_documenti_views.py` (`genera`, `anteprima`, lista, `file`,
  `file-download`, `allegati`) — allineati alla famiglia. Il delta è il solo
  `emetti` + la rotta in `urls_ordini.py`. Aggiornare anche il commento di testata
  di `ordini_documenti_views.py` (oggi dichiara "stampa DISACCOPPIATA dallo stato.
  Niente emetti").
- **Decisione da chiudere — endpoint `/conferma/` semplice**: oggi esiste
  `POST /conferma/` (sola transizione). Con `emetti` come flusso target, valutare
  se (i) il FE smette di usare `/conferma/` e passa a `/emetti/` (conferma =
  emissione documento, allineato alla famiglia) lasciando `/conferma/` come API di
  servizio, oppure (ii) si deprecia `/conferma/` lato HTTP. Il **service**
  `conferma` resta comunque, riusato da `emetti`.
- Aggiornare client API e test (mock DB): emetti ok → CONFERMATO + documento
  generato + allegati associati; **fallimento generazione → rollback della
  conferma** (stato resta DRAFT); bozza senza righe resta bloccata
  (`E_ORD_NESSUNA_RIGA`, guard già in `conferma`); senza versione template
  PUBBLICATA l'emetti fallisce (§6.1); download/lista documenti coerenti.

### 6.3 FE — ✅ EVASO (2026-06-05)

> **Stato consegna FE (2026-06-05)**: implementato e verde (ESLint pulito +
> `vite build` ok). Delta applicato su `dev/backend-tid`:
>
> - `OrdineEmissioneDialog.vue` (nuovo, in `ordini/components/dialogs/`): thin
>   wrapper di dominio sul BB `DocumentoEmissioneDialog` (`advances-state`,
>   sorgente `ORDINE_VENDITA`), clone di `PreventivoEmissioneDialog`.
> - `OrdiniDrawer.vue`: l'azione `conferma` (`onAction`) apre il dialog invece
>   della `useConfirmAction` semplice; `handleEmissioneConferma({files})` →
>   `store.emetti` (POST multipart `/emetti/`) + `loadDetail` + `emit('saved')`.
> - `constants.js`: `STATI_ORDINE_ANTEPRIMA_PDF = [DRAFT]`,
>   `STATI_ORDINE_CON_DOCUMENTO = [CONFERMATO, ALLOCATO, SPEDITO, CONSEGNATO,
>   FATTURATO]` (ANNULLATO escluso). Il drawer `EntityPdfButton` ne deriva
>   preview (DRAFT) vs gestione documenti (post-bozza).
> - `ordiniApi.js`: `emettiOrdine(id, {allegati, templateId})` (multipart);
>   store `ordini.js`: action `emetti`.
> - `OrdiniSearchTable.vue` (lista): rimosso anteprima/download diretto; ora usa
>   `PdfDocumentiSorgenteDialog` con azione di riga `documenti-pdf` disabilitata
>   in DRAFT, abilitata post-bozza (tooltip dedicati).
> - i18n `vendite.ordini.*` (it+en): `emissione_titolo/_conferma/_messaggio`,
>   `pdf.tooltip_lista/_lista_disabilitato`.
>
> **Prerequisito §6.1 verificato**: template `ORDINE_VENDITA` (id 75,
> `is_default`) ha versione 1 **PUBBLICATA** → l'emissione funziona end-to-end.

- **`OrdineEmissioneDialog`**: clone del wrapper di dominio
  `PreventivoEmissioneDialog.vue` (gli altri sono `OffertaEmissioneDialog`,
  `ContrattoEmissioneDialog`), che monta il BB core
  `src/documenti/components/DocumentoEmissioneDialog.vue` (anteprima PDF, allegati
  e conferma finale verso l'endpoint multipart `/emetti/`). **Non** creare un nuovo
  dialog: solo il thin wrapper di dominio (regola del 2).
- Nel drawer ordine, l'azione "Conferma" apre `OrdineEmissioneDialog` (emissione =
  conferma + documento) invece della `useConfirmAction` semplice attuale.
- Aggiornare le costanti PDF ordine in `src/vendite/ordini/constants.js`:
  `STATI_ORDINE_ANTEPRIMA_PDF = [DRAFT]` e
  `STATI_ORDINE_CON_DOCUMENTO = [CONFERMATO, ...stati post-bozza ammessi dal
  dominio]` (oggi `STATI_ORDINE_CON_DOCUMENTO = []`). Gli stati ammessi li detta il
  modello `config.stati_doc_ordini`, **data-driven**, non hardcodati a casaccio
  (`feedback_no_hardcoded_ids`).
- Nella lista ordini, non fare anteprima/download diretto. Usare
  `PdfDocumentiSorgenteDialog` come preventivi/contratti/offerte, con azione di riga
  `documenti-pdf` disabilitata in `DRAFT` e abilitata negli stati post-bozza
  (la colonna tecnica `stato_codice_interno` è già nel catalogo lista).
- Aggiornare i18n `vendite.ordini.pdf.*` con tooltip specifici lista/drawer:
  bozza = solo anteprima nel drawer; lista disabilitata finché l'ordine non è
  confermato; stati post-bozza = gestione documenti generati.
- Verificare manualmente il flusso UI: bozza mostra solo anteprima nel drawer,
  conferma apre il dialog con allegati, ordine confermato espone il documento
  dalla lista e dal drawer tramite gestione documentale.
