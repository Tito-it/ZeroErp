# API titoli_iva_soggetto (Django)

## Scopo

Esporre via HTTP il **registro dei titoli IVA di un soggetto** — le condizioni
documentate che cambiano il trattamento fiscale delle sue righe (dichiarazioni
d'intento, esportatore abituale, split payment, reverse charge) — con i loro
**ambiti** di applicazione e il **registro dei movimenti** che consuma il
plafond.

## Contesto

Famiglia di endpoint di area `anagrafiche`, permesso `("anagrafiche", "soggetto")`
(il titolo IVA e' un dato anagrafico del soggetto, non un oggetto di permesso a sé).
Il modello è quello della Fase 2 del cantiere IVA:

```text
anagrafiche.soggetti_titoli_iva              il titolo (validità, plafond, iva_id, ambito)
  └─ ..._ambiti                              su cosa si applica, quando l'ambito non è TUTTO
  └─ ..._movimenti                           il registro che consuma il plafond
```

⭐ **`imponibile_utilizzato` è un accumulatore**: non lo scrive nessuno a mano —
è la somma del registro, riportata da un trigger. È la ragione per cui l'annullo
di un movimento è un **contro-movimento** e non una cancellazione (vedi sotto).

⚠️ **Tutte queste tabelle hanno la RLS.** Senza il contesto operatore un
conteggio torna **zero** e sembra un dato: «non c'è niente» e «non vedo niente»
non si distinguono. Gli endpoint girano sempre sotto JWT, quindi il contesto c'è.

## Le rotte

| Metodo | Path (sotto `/api/v1/anagrafiche/`) | Cosa |
|---|---|---|
| `GET`/`POST` | `soggetti/{soggetto_id}/titoli-iva/` | elenco e creazione |
| `GET`/`PATCH`/`DELETE` | `soggetti/{soggetto_id}/titoli-iva/{titolo_id}/` | dettaglio, modifica, eliminazione (solo senza movimenti) |
| `GET`/`POST` | `.../{titolo_id}/ambiti/` | gli ambiti del titolo |
| `DELETE` | `.../{titolo_id}/ambiti/{ambito_id}/` | toglie una riga di ambito (unico metodo) |
| `GET`/`POST` | `.../{titolo_id}/movimenti/` | il registro, e la **forzatura** |
| `POST` | `.../{titolo_id}/movimenti/{movimento_id}/annulla/` | ⭐ l'**annullo** di una forzatura |
| `GET` | `soggetti/{soggetto_id}/titoli-iva/export/` | ⭐ export CSV/XLSX della lista del soggetto (DEF-1) |
| `GET` | `soggetti/{soggetto_id}/titoli-iva/tipi/lookup/` | ⭐ i tipi di titolo che la natura del soggetto ammette (lookup del drawer) |
| `GET` | `titoli-iva/sfondati/` | presidio cross-soggetto: i titoli oltre il tetto |

⚠️ **`titoli-iva/sfondati/` sta PRIMA delle rotte con `{soggetto_id}`** nel
`urlpatterns`: con l'ordine invertito `sfondati` verrebbe letto come un
`soggetto_id`.

## Le due liste, dal 2026-09-02 — contratto aggiornato

Entrambe alimentano una `<ListaConfigurabile>` e dichiarano il **conteggio**
accanto alle righe. ⛔ Il `count` viene da una valutazione **indipendente**, mai
da `len(results)`: vedi [api.md §«Il `count` non si deriva mai dalle righe»](../../../dev/api.md).

### `GET soggetti/{soggetto_id}/titoli-iva/` — 🔴 ORA PAGINATA

```json
{ "data": { "results": [...], "count": 7 } }
```

⛔ **Contratto cambiato il 2026-09-02** (rilievo di Tid in collaudo: il drawer
era fuori standard — niente pagine, niente scelta delle colonne, niente export).
Ora accetta `limit` / `offset` come ogni altra lista configurabile.

- Pagina e totale arrivano da **una** valutazione (`COUNT(*) OVER()` via
  `fetch_paged_with_total`), con `fallback_count_sql` per il rientro su una
  pagina stantia. ⭐ `count_titoli_soggetto` **non esiste più**: era una seconda
  query sullo stesso predicato, e due valutazioni possono non concordare se una
  riga entra fra l'una e l'altra — il totale racconterebbe una popolazione
  diversa da quella mostrata.
- Via HTTP la pagina c'e' sempre: senza `limit` vale il default di
  `parse_list_params` (**25** righe, max 200). Solo il **secondo consumatore**,
  `SoggettiService`, che incorpora i titoli nel dettaglio del soggetto, chiama il
  repository senza `limit` e li riceve tutti. Il metodo è uno solo, la query è una sola.
- Ordinamento opzionale: `order_by` / `order_dir`, whitelist
  `_ORDER_COLS_TITOLI_SOGGETTO` chiavata sui `campo_sorgente` fisici
  (`tipo_descrizione`, `emittente_ragione_sociale`, `iva_codice`, `residuo`).
  ⚠️ `residuo` si ordina per **alias** — è un `CASE` che vale NULL sui tipi
  senza tetto, e riscriverne l'espressione ordinerebbe diversamente da come si
  legge.
- ⚠️ **Senza `order_by` resta l'ordine storico** (`COALESCE(valido_al,'infinity')
  DESC`), e va preservato: `list_titoli_soggetto` ha un **secondo consumatore**,
  `SoggettiService`, che la incorpora nel dettaglio di un soggetto e non passa
  ordinamento.
- ⛔ `order_by` si legge **grezzo** (`qp_str`), non da `parse_list_params`: il
  bundle ha un default suo (`"descrizione"`) che qui non è una colonna di
  niente. Passandolo, l'assenza di ordinamento arriverebbe al repository come
  una richiesta — che lui scarta perché fuori whitelist, cioè la cosa giusta per
  il motivo sbagliato.

### `GET soggetti/{soggetto_id}/titoli-iva/export/` — il file (DEF-1)

- `?formato=csv|xlsx` (⚠️ **`formato`**, non `format`: quest'ultimo è un
  parametro magico di DRF e collide col content negotiation).
- Le colonne del file sono quelle che l'operatore **vede** — preferenza + preset
  + permessi, risolte da `build_export_response` sulla config runtime della
  lista `anagrafiche.soggetto_titoli_iva`. ⛔ Non un elenco cablato nella view,
  che divergerebbe alla prima colonna aggiunta a catalogo.
- Chiede il **dataset**, non la pagina: `limit = EXPORT_MAX_ROWS + 1`. Il `+1` è
  quello che permette al guard di rispondere **422
  `E_UI_EXPORT_LIMIT_EXCEEDED`** invece di consegnare un file troncato in
  silenzio — che sarebbe indistinguibile da un export corretto.
- `filtri_applicati = None`: questa lista non ha filtri. Il soggetto è nel
  **path**, non è una scelta dell'operatore, e dichiararlo come filtro nell'
  intestazione del file sarebbe inventarne uno.

### `GET soggetti/{soggetto_id}/titoli-iva/tipi/lookup/` — i tipi ammessi (dal 2026-10-10)

Lookup dedicato (api.md §Lookup, pattern 2): il generico `config.tipi_titolo_iva`
non sa filtrare per la natura del soggetto. Risponde `{"data": {"results": [...]}}`,
senza paginazione; ogni voce porta `id`, `codice`, `codice_interno`,
`descrizione`, `attivo`, `ha_plafond`.

- Il filtro è il **predicato del guard**, `anagrafiche.fn_titolo_iva_ammesso`
  (brief-db-dati-fiscali-e-societari-del-soggetto, parte D): nessuna riga di
  matrice = nessun tipo, soggetto senza natura = nessun tipo. Un privato ha la
  sola `AGEVOLATA_104`; una società l'intento e l'uso industriale.
- ⚠️ È una **comodità del form**: un tipo non ammesso lo rifiuta comunque il DB,
  `E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO` (400, `error.fields =
  ["tipo_titolo_iva_id"]`).
- Un soggetto inesistente torna la lista vuota, non un 404: è un lookup.

### `GET titoli-iva/sfondati/` — 🔴 ORA PAGINATA

⛔ **Contratto cambiato.** Prima restituiva i primi **500** (`_SFONDATI_LIMIT`)
e non lo dichiarava: su una lista di **presidio** — che esiste perché una
forzatura di plafond non sfugga — dal 501-esimo caso in poi il difetto non si
vedeva, e nessuno poteva accorgersene. Il cap è stato **rimosso**.

- Query string: `limit` / `offset` / `order_by` / `order_dir`
  (`parse_list_params`, `default_order="eccedenza"`).
- `order_dir` dal bundle: assente è `None` (dal 2026-09-26 `parse_list_params`
  non lo normalizza più ad `"asc"`), e decide il default DESC: la lista deve
  aprirsi dalla **più grave**.
- Risposta: `{ "results": [...], "count": N }` — pagina e totale in **una**
  valutazione (`COUNT(*) OVER()` via `fetch_paged_with_total`), con
  `fallback_count_sql` per il rientro su una pagina stantia. ⚠️ Senza quel
  fallback la schermata direbbe «nessun caso» a chi è solo rimasto su una pagina
  che si è accorciata — su un presidio, il difetto che esiste per evitare.
- ⭐ **`eccedenza` è ora una colonna vera** (alias SQL `imponibile_utilizzato -
  plafond), non più calcolata dal frontend: è l'ordinamento che dà senso alla
  lista, e una colonna calcolata dal client non si può ordinare.
- Whitelist `_ORDER_COLS_SFONDATI`, 7 colonne, chiavata sui campi fisici;
  tiebreak `t.id` **allineato alla direzione primaria**.

## `PATCH` / `DELETE` del titolo

- `PATCH`: chiavi ammesse `tipo_titolo_iva_id`, `iva_id`, `ambito`, `valido_dal`,
  `valido_al`, `protocollo`, `data_ricezione`, `riferimento`, `plafond`, `attivo`,
  `note`; una chiave estranea o un corpo senza campi → 400 `E_ANAG_VALIDAZIONE`.
  Risposta `{"updated": true}`.
- `attivo` (in creazione e in modifica), se presente, deve essere un booleano
  JSON: `null` o un altro tipo → 400 (2026-10-20).
- `DELETE` è una **cancellazione vera**, ammessa solo se il titolo non ha
  movimenti di plafond; altrimenti 400 `E_ANAG_VALIDAZIONE` («non si elimina, si
  disattiva»: `PATCH {"attivo": false}`). Risposta `{"deleted": true}`.

## ⭐ `POST .../movimenti/{movimento_id}/annulla/`

Annulla una **forzatura** del registro scrivendo un **contro-movimento**.

- Body: `motivo` (string) — **obbligatorio**
- `200`: `{"id": <id del contro-movimento creato>}`
- `400 E_ANAG_VALIDAZIONE`: `motivo` mancante o vuoto (`context.field = "motivo"`)
- `404 E_ANAG_NOT_FOUND`: titolo non del soggetto, o movimento non di questo titolo
- `409`: annullo non ammesso (`E_TITOLO_IVA_ANNULLO_NON_AMMESSO`)

⛔ **`annulla` come ultimo segmento e NON un `DELETE`**, perché l'azione **non
cancella niente**: aggiunge una riga. Il verbo nomina ciò che è, ed è la
grammatica URL delle azioni di dominio (`API.md`).

⭐ **E il contro-movimento non è una scelta stilistica**: `imponibile_utilizzato`
è la `SUM` di tutto il registro, quindi la riga opposta **riporta
l'accumulatore da sola**. Un flag `annullato` avrebbe richiesto a ogni lettore
di ricordarsi di filtrarlo — e il primo che se ne dimentica ottiene un plafond
sbagliato senza nessun errore. Inoltre resta **traccia**: la riga originale non
sparisce.

### La capability, e perché le precondizioni non sono qui

Le righe di `GET .../movimenti/` arrivano da
`anagrafiche.vw_stiva_movimenti_dettaglio` e portano:

| Campo | Cosa |
|---|---|
| `is_annullo` | questa riga **è** l'annullo di un'altra |
| `is_annullato` | questa riga **è stata** annullata |
| `annulla_movimento_id` | il legame, nei due versi |
| `annullo_blocco_codice` | ⭐ il motivo per cui l'annullo **non** è ammesso, o `NULL` se lo è |
| `annullo_blocco_reason_key` | la chiave i18n del motivo (`anagrafiche.titoli_iva.annullo_blocco.*`) |

⛔ **Le cinque precondizioni NON sono ricopiate nel backend**, ed è deliberato:
vivono in `script.fn_check_annullo_movimento_titolo_iva`, la **stessa** funzione
da cui la vista prende il motivo per spegnere il pulsante e da cui la madre
prende il codice per rifiutare. Riscriverle qui vorrebbe dire che il tooltip e
il rifiuto possono divergere — e divergerebbero in silenzio.

| # | Codice | Significato |
|---|---|---|
| 1 | `MOVIMENTO_NON_TROVATO` | il movimento non esiste |
| 2 | `NON_FORZATURA` | è il riflesso di un documento: si corregge **dal documento**, con una nota di credito |
| 3 | `RIGA_DI_ANNULLO` | è esso stesso l'annullo di un'altra riga |
| 4 | `GIA_ANNULLATO` | esiste già una riga che lo annulla |
| 5 | `PLAFOND_NEGATIVO` | annullarlo porterebbe l'usato **sotto zero** |

⚠️ **L'ordine è il contratto**: la superficie mostra il **primo** motivo e la
madre solleva il **primo** codice. Se divergessero, il tooltip direbbe una cosa
e l'errore un'altra.

📌 Il terzo si chiamava `E_UN_ANNULLO` fino al 2026-08-31: non nasceva come
«E\_ di errore» ma come «è un annullo», e quel prefisso lo faceva leggere come un
**codice errore** dal cancello che cerca i letterali `E_*`. Il `reason_key`
**non** è cambiato — è un indirizzo i18n, e il testo a video è lo stesso.

## Regole comuni alla famiglia

- Area `anagrafiche`, permesso `("anagrafiche", "soggetto")`; v1, JWT obbligatorio.
- **Ownership a due livelli** su tutte le rotte annidate: il titolo deve
  appartenere al `soggetto_id` del path, e il movimento/ambito al `titolo_id`.
  ⚠️ Senza il secondo livello, un id di un altro soggetto passerebbe il primo
  controllo e agirebbe su un registro che non è il suo.
- Le scritture passano dalle **madri DB**, che tengono lock e invarianti; il
  service fa ownership, normalizzazione e traduzione errori.
- ⛔ **`emittente_fiscale_id` è la PK** di `anagrafiche.emittenti_fiscali`, non
  il `soggetto_ruolo_id`. Il ponte
  `anagrafiche.emittenti_fiscali_billing_account` lega invece il
  **soggetto-ruolo**: sbagliare fra i due qui non dà zero righe per caso — dà un
  errore di colonna, ma su una JOIN sintatticamente valida darebbe **zero righe
  in silenzio**.
- Disattivazione: **figli prima del padre** (i trigger DB lo impongono). L'eliminazione del titolo è ammessa solo senza movimenti (sopra).

## Dipendenze DB

- `anagrafiche.soggetti_titoli_iva`, `..._ambiti`, `..._movimenti` (tutte RLS)
- `anagrafiche.vw_stiva_movimenti_dettaglio` (lettura del registro + capability)
- `anagrafiche.fn_annulla_movimento_titolo_iva` (madre dell'annullo)
- `script.fn_check_annullo_movimento_titolo_iva` (`STABLE`, pura — le cinque
  precondizioni, lette **sia** dalla vista **sia** dalla madre)
- `anagrafiche.fn_consuma_plafond_titolo_iva_righe` (il consumo sotto lock, sul
  netto della fattura, chiamato dalla fatturazione — non da questi endpoint)
- `config.tipi_titolo_iva` (`ha_plafond`), `config.iva`

## Note di migrazione

- Fase 2 del cantiere IVA:
  [brief-be-fe-titoli-iva-soggetto.md](../../../dev/work-done/brief-be-fe-titoli-iva-soggetto.md).
  L'annullo (`T3-b`) è del 2026-08-31.
- ⚠️ Al 2026-08-31 `anagrafiche.soggetti_titoli_iva` è **vuota**: nessun titolo
  è ancora stato registrato. Uno smoke che *cercasse* il caso passerebbe a
  vuoto — quello in repo
  (`backend/scripts/tests/smoke-titoli-iva-annullo-movimento.py`) lo
  **costruisce**.
- ✅ **Dal 2026-08-31 il consumo del plafond dalla fatturazione è in
  esercizio**: il task `consuma_plafond_lotto` gira in testa allo step
  DEFINITIVA, prima della numerazione — cioè mentre la fattura è ancora
  `EMESSA` e il guard di congelamento lascia scrivere. ⇒ Il registro non si
  popola più solo con le **forzature** manuali: ci arrivano i movimenti delle
  fatture, e quando il plafond copre solo una quota la riga **si spezza in due**
  (`vendite.fatture_righe.riga_capofila_id`).
  Smoke: `backend/scripts/tests/smoke-consuma-plafond-lotto.py`.
