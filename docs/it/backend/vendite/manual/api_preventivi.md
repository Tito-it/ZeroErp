# API Preventivi vendita (Django)

## Scopo

Esporre via HTTP la gestione completa dei preventivi di vendita: CRUD testata, righe, indirizzi, cambio stato, revisioni, integrazione con commesse/fatturazione e pratiche.

## Contesto

I preventivi vendita sono il punto d'ingresso del ciclo commerciale. Dopo accettazione, alimentano la pipeline commesse/attivita_fatturabili/fatturazione. Possono anche generare pratiche operative (installazione, sopralluogo, ecc.) via tabella ponte `pratiche.pratiche_sorgenti`.

Le tabelle DB esistono gia' (`vendite.preventivi`, `preventivi_righe`, `preventivi_indirizzi`, `note_preventivo`, `config.stati_doc_preventivi`). Alcune funzioni DB sono da creare (cambio stato, revisione, ricalcolo totali).

---

## Endpoint

### 1. Lista preventivi

- Metodo: `GET`
- Path: `/api/v1/vendite/preventivi/`
- Auth: JWT, `area_funzionale = "vendite"`, `is_search_endpoint = True`
- Query param (tutti opzionali):
  - `stato` (string) — codice stato (es. `BOZZA`, `EMESSO`, `ACCETTATO`)
  - `billing_account_id` (int) — filtro per BA/cliente
  - `utility_id` (int) — filtro per utility
  - `data_da` (date ISO) — data minima
  - `data_al` (date ISO) — data massima
  - `search` (string, min 3 char) — ricerca su numero e denominazione cliente
  - `page` (int, default 1) — pagina
  - `page_size` (int, default 50, max 200) — righe per pagina
- Output `200`:
```json
{
  "data": {
    "count": 42,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [
      {
        "id": 1,
        "uid": "01970...",
        "numero": "P-0001",
        "rev": 0,
        "is_revision_attiva": true,
        "data": "2026-04-03",
        "stato_codice": "BOZZA",
        "stato_descrizione": "Bozza",
        "cliente_denominazione": "Azienda Esempio S.r.l.",
        "billing_account_id": 10,
        "utility_id": 1,
        "totale_imponibile": "1000.00",
        "totale_iva": "220.00",
        "totale_documento": "1220.00",
        "validita_dal": "2026-04-01",
        "validita_al": "2026-06-30",
        "competenza_mese": "2026-04-01",
        "fatturazione_immediata": false,
        "data_insert": "2026-04-03T10:00:00+02:00"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```
- Regole: scope emittente DB-first (`_add_scope_emittente`), filtro data obbligatorio consigliato (default anno-1 nel frontend)

---

### 2. Crea preventivo

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/`
- Body JSON:
  - `utility_id` (int, **obbligatorio**)
  - `billing_account_id` (int, opzionale)
  - `istanza_utility_id` (int, opzionale)
  - `valuta_id` (int, opzionale)
  - `termine_pagamento_id` (int, opzionale)
  - `validita_dal` (date, opzionale)
  - `validita_al` (date, opzionale)
  - `competenza_mese` (date, opzionale — primo del mese)
  - `fatturazione_immediata` (bool, default false)
- Output `200`: `{ "data": { "id": 1, "uid": "...", "numero": "P-0001" } }`
- Regole: crea sempre in stato BOZZA, numero generato da trigger `trgfn_preventivi_gen_codice`
- Errori: `E_PREV_VALIDAZIONE` (400), `E_CONFIG_MANCANTE` (500 se BOZZA non configurato)

---

### 3. Dettaglio preventivo

- Metodo: `GET`
- Path: `/api/v1/vendite/preventivi/{id}/`
- Output `200`: testata completa con decodifiche (stato, cliente, utility, valuta, termini) + `righe[]` + `indirizzi[]`
- Errori: `E_PREV_NOT_FOUND` (404)

---

### 4. Aggiorna preventivo

- Metodo: `PATCH`
- Path: `/api/v1/vendite/preventivi/{id}/`
- Body JSON: campi modificabili (billing_account_id, utility_id, istanza_utility_id, valuta_id, termine_pagamento_id, validita_dal, validita_al, competenza_mese, fatturazione_immediata, meta). Passare `null` per azzerare campi nullable.
- Regole: ammesso solo in stato BOZZA
- Errori: `E_PREV_NOT_FOUND` (404), `E_PREV_STATO_NON_MODIFICABILE` (409)

---

### 5. Cambio stato

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/stato/`
- Auth: `post_permission = "cambia_stato_preventivi"`
- Body JSON: `{ "nuovo_stato": "EMESSO" }`
- Regole: delega a `vendite.fn_cambia_stato_preventivo()` che valida transizioni e prerequisiti
- Transizioni: BOZZA→EMESSO (richiede righe), EMESSO→ACCETTATO/RIFIUTATO/SCADUTO/ANNULLATO, BOZZA→ANNULLATO
- **Guard L3 verso ACCETTATO (Sprint E)**: il trigger DB `trg_preventivi_a10_guard_transizione_approvazione_upd` blocca la transizione verso ACCETTATO se esiste almeno una riga con `stato_approvazione_prezzo='PENDING'`. Errore `E_PREVENTIVO_RIGHE_PRICING_PENDENTI` (409). L'admin deve attendere esito approvazione (vedi `api_approvazioni_prezzo.md`) o annullare la richiesta prima di accettare.
- Errori: `E_PREV_STATO_TRANSIZIONE` (409), `E_PREV_NESSUNA_RIGA` (400), `E_PREVENTIVO_RIGHE_PRICING_PENDENTI` (409)

---

### 6. Nuova revisione

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/revisione/`
- Regole: delega a `vendite.fn_crea_revisione_preventivo()` — copia testata+righe, rev+1, nuova rev in BOZZA, disattiva precedente
- Errori: `E_PREV_REVISIONE_ATTIVA` (409)

---

### 7. Lista righe

- Metodo: `GET`
- Path: `/api/v1/vendite/preventivi/{id}/righe/`
- Output `200`: lista righe con JOIN articolo (codice, descrizione), UoM (codice), IVA (codice, aliquota)

---

### 8. Aggiungi riga

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/righe/`
- Body JSON:
  - `articolo_id` (uuid string, **obbligatorio**)
  - `descrizione` (string, opzionale — override descrizione articolo)
  - `quantita` (decimal, opzionale)
  - `prezzo_unitario` (decimal, opzionale — **auto-fill dal resolver pricing v5 se omesso**)
  - `sconto_percentuale` (decimal, opzionale, default 0)
  - `iva_id` (int, opzionale)
  - `uom_operativa_id` (int, opzionale)
  - `ordine` (int, opzionale)
  - `richiesta_approvazione` (bool, opzionale, default `false`) — **L3 workflow Sprint E**: se `true` e il prezzo viola L2, invece di sollevare `E_PREV_SCONTO_ECCESSIVO`/`E_PREV_MAGGIORAZIONE_ECCESSIVA` la riga viene salvata con `stato_approvazione_prezzo='PENDING'` collegata a una pratica `APPROVAZIONE_PREZZO` aperta automaticamente
- Regole:
  - Ammesso solo in stato BOZZA
  - **Auto-fill prezzo**: se `prezzo_unitario` non e' nel payload e la testata ha BA+utility+data validi, il service chiama `PricingService.resolve_prezzo` e popola il prezzo dal resolver v5 (3 stadi: promo/contratto/categoria)
  - **L1 override**: se `prezzo_unitario` e' passato e differisce dal resolver, serve l'azione di processo `prezzo_override_manuale`; altrimenti `E_PREV_OVERRIDE_NON_AUTORIZZATO` (403). Superuser bypassato
  - **L2 limite variazione (Sprint D)**: dopo L1, se `prezzo_resolver` e' noto e non zero, calcola `delta_pct` firmato; sconto > `VENDITE_MAX_SCONTO_PCT` o maggiorazione > `VENDITE_MAX_MAGGIORAZIONE_PCT` -> `E_PREV_SCONTO_ECCESSIVO`/`E_PREV_MAGGIORAZIONE_ECCESSIVA` (403). Parametri risolti via `ParameterService` cascata user→group→emittente→default. Superuser bypass.
  - **L3 workflow approvazione (Sprint E)**: se `richiesta_approvazione=true` e L2 viola, l'errore L2 viene catturato, viene creata pratica `APPROVAZIONE_PREZZO` (stato APERTA) e la riga inserita con `stato_approvazione_prezzo='PENDING'` + `pratica_approvazione_prezzo_id`. Email best-effort al recipient configurato in parameter `VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL`. La pratica e' visibile nella coda approver via `GET /vendite/approvazioni-prezzo/`.
  - **Meta audit**: popolato sempre con `origine_prezzo` (PROMO/CONTRATTO_OVERRIDE/CONTRATTO_LISTINO/CATEGORIA/MANUALE) + `prezzo_resolver_context` (listino/contratto/promo + variazione). Se override manuale: anche `prezzo_base_resolver`, `delta_override`, `delta_override_pct`, `override_user_id`. Se workflow L3: anche `richiesta_approvazione_pending=true` + `violazione_l2` (tipo, variazione_abs_pct, limite_pct).
  - Ricalcolo totali automatico dopo insert (trigger DB)
- Errori: `E_PREV_VALIDAZIONE` (400), `E_PREV_STATO_NON_MODIFICABILE` (409), `E_PREV_OVERRIDE_NON_AUTORIZZATO` (403), `E_PREV_SCONTO_ECCESSIVO` (403), `E_PREV_MAGGIORAZIONE_ECCESSIVA` (403)

---

### 8b. Suggerisci prezzo riga

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/righe/suggerisci-prezzo/`
- Body JSON:
  - `articolo_id` (uuid string, **obbligatorio**)
  - `uom_id` (int, **obbligatorio**)
- Scopo: calcola il prezzo suggerito dal resolver v5 senza creare la riga. Usato dal FE per pre-compilare il campo prezzo all'apertura del drawer. Nessun side-effect
- Output `200`: `{ "data": { "prezzo_finale": "50.00", "prezzo_base_snapshot": "52.50", "origine": "CATEGORIA", "listino_id": 100, "contratto_id": null, "promo_id": null, "tipo_variazione_applicata": "PERCENTUALE", "valore_variazione_applicata": "-5.00" } }`
- Contesto derivato: BA, utility, data dalla testata preventivo; emittente dal JWT operatore
- Area: `vendite` livello LETTURA sufficiente (pura lettura)
- Errori: `E_PREV_NOT_FOUND` (404), `E_PREV_VALIDAZIONE` (400 — testata senza BA/utility/data o utente senza emittenti autorizzati), errori applicativi del resolver (`E_PREZZO_LISTINO_NON_TROVATO`, `E_CATEGORIA_LISTINO_NON_MAPPATA`, ...)

---

### 9. Aggiorna riga

- Metodo: `PATCH`
- Path: `/api/v1/vendite/preventivi/{id}/righe/{rid}/`
- Body JSON: campi modificabili (`quantita`, `prezzo_unitario`, `sconto_percentuale`, `descrizione`, `uom_operativa_id`, `iva_id`, `ordine`, `richiesta_approvazione`)
- Regole: ammesso solo in stato BOZZA, ricalcolo totali dopo update
- **L1+L2+L3 su PATCH**: se il payload tocca `prezzo_unitario`, scattano gli stessi check dell'insert (autorizzazione + audit meta + L2 limite + L3 workflow opzionale via flag `richiesta_approvazione=true`). L'articolo/UoM della riga esistente sono usati come contesto resolver
- **Trigger DB guard riga PENDING**: se la riga ha `stato_approvazione_prezzo='PENDING'`, il trigger `trg_preventivi_righe_a10_guard_pending_upd` (Sprint E) blocca modifica di campi struttura (prezzo, qta, articolo, sconto, ecc.) con `E_RIGA_PREZZO_PENDENTE` (409). Solo `stato_approvazione_prezzo`, `pratica_approvazione_prezzo_id` e `meta` sono ammessi. Per modificare prezzo: prima chiudere il workflow (approva/rifiuta) o annullare la pratica.
- Errori: `E_PREV_RIGA_NOT_FOUND` (404), `E_PREV_STATO_NON_MODIFICABILE` (409), `E_PREV_OVERRIDE_NON_AUTORIZZATO` (403), `E_PREV_SCONTO_ECCESSIVO` (403), `E_PREV_MAGGIORAZIONE_ECCESSIVA` (403), `E_RIGA_PREZZO_PENDENTE` (409)

---

### 10. Elimina riga

- Metodo: `DELETE`
- Path: `/api/v1/vendite/preventivi/{id}/righe/{rid}/`
- Regole: soft delete (attivo=false), ammesso solo in stato BOZZA, ricalcolo totali
- Errori: `E_PREV_RIGA_NOT_FOUND` (404), `E_PREV_STATO_NON_MODIFICABILE` (409)

---

### 11. Lista indirizzi

- Metodo: `GET`
- Path: `/api/v1/vendite/preventivi/{id}/indirizzi/`
- Output `200`: lista indirizzi con tipo e snapshot JSONB

---

### 12. Upsert indirizzo

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/indirizzi/`
- Body JSON:
  - `tipo_indirizzo_id` (int, **obbligatorio**)
  - `snapshot` (object, **obbligatorio**)
  - `origine_indirizzo_id` (int, opzionale)
  - `origine_soggetto_ruolo_id` (int, opzionale)
- Regole: upsert ON CONFLICT su constraint `uq_preventivi_indirizzi_uno_per_tipo_`

---

### 13. Push in commessa (fatturazione)

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/push-commessa/`
- Auth: `post_permission = "push_commessa_preventivi"`, `Idempotency-Key` obbligatoria
- Regole: ammesso solo in stato ACCETTATO, verifica righe eleggibili via `fn_list_preventivi_da_pushare`
- Output `200`: `{ "data": { "righe_pushable": 3, "preventivo_id": 1 } }`
- Errori: `E_PREV_STATO_TRANSIZIONE` (409), `E_PREV_NESSUNA_RIGA` (400)
- TODO: orchestrazione completa push commessa (oggi solo discovery)

---

### 14. Stato fatturazione

- Metodo: `GET`
- Path: `/api/v1/vendite/preventivi/{id}/stato-fatturazione/`
- Output `200`:
```json
{
  "data": {
    "preventivo_uid": "...",
    "righe_totali": 5,
    "righe_in_commessa": 3,
    "righe_emesse_af": 3,
    "righe_fatturate": 1
  }
}
```
- Regole: query cross-schema (commesse_sorgenti → commesse_attivita → attivita_fatturabili), filtrata per sorgente_tipo PREVENTIVO_VENDITA

---

### 15. Genera pratica

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/genera-pratica/`
- Auth: `post_permission = "genera_pratica_preventivi"`, `Idempotency-Key` obbligatoria
- Body JSON:
  - `tipo_prestazione_id` (int, **obbligatorio**)
  - `priorita_id` (int, **obbligatorio**)
  - `descrizione` (string, opzionale)
- Regole:
  - Ammesso solo in stato ACCETTATO con `billing_account_id` valorizzato
  - Risolve contesto anagrafico dal BA (emittente default, soggetto, ruolo)
  - Crea pratica via BB `pratiche_service.crea_pratica` (riutilizzabile cross-dominio)
  - Crea link `pratiche.pratiche_sorgenti` con `sorgente_tipo = 'PREVENTIVO_VENDITA'`
- Output `200`: `{ "data": { "pratica_id": 42, "preventivo_id": 1 } }`
- Errori: `E_PREV_PRATICA_STATO` (409), `E_PREV_VALIDAZIONE` (400), `E_CONFIG_MANCANTE` (500)

---

### 16. Pratiche collegate

- Metodo: `GET`
- Path: `/api/v1/vendite/preventivi/{id}/pratiche/`
- Output `200`: lista pratiche con codice, descrizione, stato, ruolo_link
- Regole: filtrata per `sorgente_tipo = 'PREVENTIVO_VENDITA'` per evitare match spuri

---

## Dipendenze DB

| Tabella/funzione | Ruolo |
|---|---|
| `vendite.preventivi` | Testata preventivo |
| `vendite.preventivi_righe` | Righe articoli |
| `vendite.preventivi_indirizzi` | Indirizzi snapshot |
| `config.stati_doc_preventivi` | Macchina a stati |
| `catalogo.articoli` | JOIN decodifica articolo |
| `catalogo.unita_misura` | JOIN decodifica UoM |
| `config.iva` | JOIN decodifica IVA |
| `anagrafiche.billing_account` → `soggetti_ruoli` → `soggetti` | JOIN cliente |
| `config.utilita` | JOIN utility |
| `config.valute` | JOIN valuta |
| `config.termini_pagamento` | JOIN termini |
| `vendite.fn_cambia_stato_preventivo()` | Transizione stato (da creare) |
| `vendite.fn_crea_revisione_preventivo()` | Copia revisione (da creare) |
| `vendite.fn_ricalcola_totali_preventivo()` | Ricalcolo totali (da creare) |
| `vendite.fn_list_preventivi_da_pushare()` | Discovery righe per commessa (esiste) |
| `vendite.commesse_sorgenti` | Link preventivo → commessa |
| `vendite.commesse_attivita` | Stato emissione righe |
| `vendite.attivita_fatturabili` | Stato fatturazione |
| `pratiche.pratiche_sorgenti` | Link preventivo → pratica (da creare) |
| `config.sorgenti` | Dizionario tipi sorgente |
| `pratiche_service.crea_pratica` | BB creazione pratica |

## Codici errore

| Codice | HTTP | Descrizione |
|---|---|---|
| `E_PREV_NOT_FOUND` | 404 | Preventivo non trovato |
| `E_PREV_VALIDAZIONE` | 400 | Validazione input fallita |
| `E_PREV_STATO_TRANSIZIONE` | 409 | Transizione stato non ammessa |
| `E_PREV_STATO_NON_MODIFICABILE` | 409 | Non modificabile nello stato corrente |
| `E_PREV_RIGA_NOT_FOUND` | 404 | Riga non trovata |
| `E_PREV_NESSUNA_RIGA` | 400 | Nessuna riga attiva/eleggibile |
| `E_PREV_GIA_IN_COMMESSA` | 409 | Gia' inviato a fatturazione |
| `E_PREV_REVISIONE_ATTIVA` | 409 | Revisione attiva esistente |
| `E_PREV_PRATICA_STATO` | 409 | Stato non ammette generazione pratica |
| `E_PREV_OVERRIDE_NON_AUTORIZZATO` | 403 | Modifica manuale del prezzo riga non autorizzata (serve azione `prezzo_override_manuale`). L1 del sistema autorizzazioni prezzi — vedi [sviluppo-autorizzazioni-prezzi](../../../dev/work-in-progress/sviluppo-autorizzazioni-prezzi) |

## Integrazione pricing v5

Le righe preventivo usano il building block centralizzato `PricingService.resolve_prezzo` ([catalogo backend §Vendite Pricing v5](../../../dev/backend/catalogo-building-block-backend)) per:

- **Auto-fill** del prezzo quando il payload lo omette (endpoint 8) — resolver 3 stadi: PROMO → CONTRATTO → CATEGORIA
- **Suggerimento diagnostico** pre-compilazione (endpoint 8b) — nessun side-effect
- **Audit override** (endpoint 8/9) — meta JSONB popolato con origine del prezzo, contesto resolver e delta override manuale

Il resolver risolve il prezzo usando BA, utility, data della testata preventivo + emittente derivato dal JWT operatore. Se la testata manca di uno di questi campi (caso legacy), il wiring e' skippato: il prezzo passa come da payload senza check ne' audit.

Per la roadmap L2 (limite sconto via parametri) e L3 (approvazione out-of-policy via pratiche), vedi [sviluppo-autorizzazioni-prezzi](../../../dev/work-in-progress/sviluppo-autorizzazioni-prezzi).
