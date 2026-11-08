# WIP — Sviluppo Preventivi acquisti (RFQ): Backend + Frontend

> Stato: **DA IMPLEMENTARE**
>
> Data: aprile 2026 — scorporato da `sviluppo-preventivi.md` il 2026-06-03.
>
> **Scorporo**: la direzione **vendita** (`vendite.preventivi`) è stata
> completata (BE+FE) e archiviata in
> [../work-done/sviluppo-preventivi.md](../work-done/sviluppo-preventivi.md).
> Questo documento copre la sola direzione **acquisto** (RFQ —
> `acquisti.preventivi`), ancora da avviare (tabelle DB da creare).
>
> Prerequisiti DB:
>
> * Schema `acquisti` operativo: ordini, ordini_righe, ddt (pattern fornitore via `soggetto_ruolo_id`)
> * Schema `config` operativo: stati documento, termini_pagamento, valute, iva
> * Schema `catalogo` operativo: articoli, articoli_uom_operativa, unita_misura
>
> Riferimenti:
>
> * [../work-done/sviluppo-preventivi.md](../work-done/sviluppo-preventivi.md) — preventivo vendita completato (pattern documentale di riferimento: stati, revisioni, note, indirizzi snapshot, integrazione pratiche)
> * [gestione-commesse-v2.md](../work-done/gestione-commesse-v2.md) — architettura commesse e pipeline
> * [docs/it/dev/api.md](../api.md) — linee guida API
> * [docs/it/dev/frontend/frontend-standards.md](../frontend/frontend-standards.md) — standard frontend

---

## Contesto

Il **preventivo di acquisto** (`acquisti.preventivi`) è la richiesta di
preventivo al fornitore (RFQ). Tabelle DB **da creare**, seguendo il
pattern già consolidato in `acquisti.ordini` (controparte via
`soggetto_ruolo_id` del fornitore). Si predispone alla **generazione
ordine fornitore** (`acquisti.ordini`).

Condivide con il preventivo di vendita (già implementato): articoli da
catalogo, UoM operative, macchina a stati, revisioni, note, indirizzi
snapshot. Per il pattern documentale di dettaglio vedere il documento
vendita in work-done.

### Due schemi, stesso pattern anagrafico

### Due schemi, stesso pattern anagrafico

| Aspetto | Preventivo vendita | Preventivo acquisto |
|---------|-------------------|---------------------|
| Schema | `vendite` | `acquisti` |
| Controparte | `billing_account_id` (cliente/BA) | `soggetto_ruolo_id` (fornitore) |
| Contesto | `utility_id`, `istanza_utility_id` | Opzionale (dipende dal tipo fornitura) |
| Downstream | Commessa → AF → fatturazione | Ordine fornitore (`acquisti.ordini`) |
| Pratiche | Si (esecuzione operativa) | Si (es. sopralluogo, verifica tecnica) |
| App Django | `apps/vendite/` | `apps/acquisti/` |
| Endpoint | `/api/v1/vendite/preventivi/` | `/api/v1/acquisti/preventivi/` |

---

---

---

## 9. Perimetro funzionale acquisti

### 9.1 Contesto

Lo schema `acquisti` ha gia' ordini e DDT con il pattern fornitore consolidato:
controparte via `soggetto_ruolo_id` (ruolo FORNITORE), serie/numero/anno,
`sorgente_tipo_id` + `sorgente_uid` per tracciabilita' documento sorgente.

> ⚠️ **Allineamento (2026-11-08).** La provenienza ha ora un modello solo (`brief-db-sorgente-documento-e-riga`,
> guida [Sorgente polimorfa](../../guide/sorgente-polimorfa.md), `linee-guida-sql` §6e): il tipo, **una** chiave
> del documento tipizzata (`sorgente_id` o `sorgente_uid`, secondo il tipo), la riga in `sorgente_riga`, il `CHECK`
> di forma, il BB che scrive e il guard unico. Le tabelle d'acquisto di oggi sono ancora nella grammatica precedente
> e passano al modello col cantiere `acquisti` (`analisi-simmetria-ordini-acquisto` §4.6-bis): il preventivo
> d'acquisto nasce già nel modello, e il legame ordine → preventivo qui sotto si legge così.

Il preventivo di acquisto (RFQ — Richiesta di Preventivo) segue lo stesso pattern.
E' il documento che precede l'ordine fornitore, come il preventivo di vendita
precede la commessa/fatturazione.

### 9.2 Tabelle DB da creare

```
acquisti.preventivi                    -- testata RFQ
acquisti.preventivi_righe              -- righe articoli richiesti
acquisti.preventivi_indirizzi          -- indirizzi snapshot (consegna, fatturazione)
acquisti.note_preventivi               -- note (partizione note system)
```

#### 9.2.1 Testata `acquisti.preventivi`

Modello allineato a `acquisti.ordini` per la parte fornitore e a `vendite.preventivi` per la parte documentale:

| Campo | Tipo | Note |
|-------|------|------|
| `id` | bigint PK | |
| `uid` | uuid, default uuidv7() | Identificatore universale |
| `soggetto_ruolo_id` | bigint NOT NULL FK | **Fornitore** — ruolo FORNITORE, come `acquisti.ordini` |
| `serie` | varchar NULL | Serie documento |
| `numero` | varchar | Codice documento (trigger-generated) |
| `rev` | integer, default 0 | Revisione (come vendite.preventivi) |
| `anno` | smallint | Anno documento |
| `data` | date, default CURRENT_DATE | Data emissione |
| `stato_doc_preventivo_acq_id` | bigint NOT NULL FK | FK a `config.stati_doc_preventivi_acq` |
| `valuta_id` | integer FK | |
| `tasso_cambio` | numeric, default 1 | Per fornitori esteri |
| `modalita_pagamento_id` | integer FK | Dal fornitore o override |
| `termine_pagamento_id` | bigint FK | |
| `validita_dal` | date | Validita' offerta fornitore |
| `validita_al` | date | Scadenza offerta |
| `competenza_mese` | date | Primo del mese |
| `totale_imponibile` | numeric | |
| `totale_iva` | numeric | |
| `totale_documento` | numeric | |
| `sorgente_tipo_id` | bigint FK | Tracciabilita' (es. da pratica, da richiesta interna) |
| `sorgente_uid` | uuid | |
| `indirizzo_consegna_id` | bigint FK | Come acquisti.ordini |
| `indirizzo_cons_snapshot` | jsonb | |
| `note_generali` | text | Note libere |
| `meta` | jsonb | |
| `tx_id` | uuid | |
| `storicizza` | boolean, default true | |
| audit columns | | |

**Revisione attiva — pattern derivato (simmetrico a `vendite.preventivi`):**

Nessuna colonna `is_revision_attiva` persistita sulla tabella: tutto derivato in
`acquisti.vw_preventivi`.

⛔ **AGGIORNATO 2026-08-28 — la forma scritta qui prima era quella VECCHIA, e
riproduceva due difetti gia' corretti su vendite.** Diceva `is_attiva = NOT EXISTS
(rev superiore non abortita)`: (1) senza il termine sullo stato **proprio**,
un annullato in cima si auto-dichiara attivo e l'unicita' salta (fix vendite
`20260708-07`); (2) con un flag solo, «e' l'ultima revisione?» e «non e'
annullato?» restano in AND e non sono piu' separabili a valle — il difetto del
brief `brief-db-revisione-attiva-due-domande` (2026-08-28). Il gemello acquisti
nasce con la forma **corretta**, non con quella da correggere dopo.

Le colonne da esporre sono **quattro**:

```sql
-- «e' annullato?» — lo stato PROPRIO e' abortito
EXISTS (SELECT 1 FROM config.stati_doc_preventivi_acq s0
         WHERE s0.id = p.stato_doc_preventivo_acq_id
           AND s0.is_abortito IS TRUE)                    AS is_abortito,

-- «e' stata rimpiazzata?» — esiste una rev superiore NON abortita.
-- Il complemento (is_superata IS FALSE) e' «e' l'ultima revisione».
EXISTS (SELECT 1 FROM acquisti.preventivi p2
          JOIN config.stati_doc_preventivi_acq s2
            ON s2.id = p2.stato_doc_preventivo_acq_id
         WHERE p2.numero = p.numero
           AND p2.rev    > p.rev
           AND s2.is_abortito IS FALSE)                   AS is_superata,

-- «qualcuno ha PROVATO a revisionarla?» — rev superiore di qualunque stato
EXISTS (SELECT 1 FROM acquisti.preventivi p3
         WHERE p3.numero = p.numero AND p3.rev > p.rev)   AS has_next_revisione,

-- composta dalle prime due: cosi' non puo' driftare da loro
(NOT is_abortito AND NOT is_superata)                     AS is_attiva
```

⭐ Le tre `EXISTS` si calcolano una volta sola in un `CROSS JOIN LATERAL` e
`is_attiva` le compone — vedi `vendite.vw_preventivi` (changeSet `20260828-08`)
per la forma esatta.

⚠️ **Chi filtra cosa**: la lista con toggle «storico revisioni» spento usa
`is_superata IS FALSE`, **non** `is_attiva` — quest'ultima nasconde anche gli
annullati e rende vuoto per costruzione il filtro di stato «Annullato». I
cruscotti («il documento e' vivo e corrente») usano `is_attiva`.

Dipendenza: `config.stati_doc_preventivi_acq` deve esporre colonna
`is_abortito BOOLEAN NOT NULL DEFAULT FALSE` (true solo per lo stato ANNULLATO).
⚠️ **Non** serve un `is_superato`: nei preventivi il superamento e' una relazione
fra righe `(numero, rev)`, non uno stato — quella colonna esiste solo su
`config.stati_doc_offerte`, dove il superamento e' scritto da un trigger.

Razionale: vedi `docs/it/dev/work-done/brief-db-preventivi-revisione-attiva-derivata.md`
per il modello e i pgTAP applicati su vendite, e
`brief-db-revisione-attiva-due-domande` per la separazione delle due domande.
Un flag persistito mantenuto manualmente diverge dai dati strutturali appena uno
stato terminale di una revisione viene applicato (rev annullata che non rifluisce
al predecessore). Il predicato derivato chiude per costruzione tutti i casi senza
trigger di sincronizzazione.

`fn_crea_revisione_preventivo_acq` (futura): copia testata + righe + componenti
BoM (se la sorgente acquisti adotterà il modello componenti) + indirizzi.
NON tocca `is_revision_attiva` su preventivo precedente — la derivazione è
automatica.

**Differenze chiave rispetto a `vendite.preventivi`:**

| Aspetto | Vendita | Acquisto |
|---------|---------|----------|
| Controparte | `billing_account_id` (cliente) | `soggetto_ruolo_id` (fornitore) |
| Contesto utility | `utility_id` NOT NULL, `istanza_utility_id` | Assente (non pertinente) |
| Fatturazione immediata | `fatturazione_immediata` flag | Assente |
| Serie/anno | Solo numero + rev | `serie` + `numero` + `anno` (come ordini acq.) |
| Tasso cambio | `valuta_id` only | `valuta_id` + `tasso_cambio` (fornitori esteri) |
| Indirizzo consegna | Snapshot da BA | `indirizzo_consegna_id` + snapshot (come ordini acq.) |
| Downstream | Commessa → AF → fattura | Ordine fornitore (`acquisti.ordini`) |

#### 9.2.2 Righe `acquisti.preventivi_righe`

Stessa struttura di `vendite.preventivi_righe`, con in piu' il pattern acquisti:

| Campo | Tipo | Note |
|-------|------|------|
| `id` | bigint PK | |
| `preventivo_id` | bigint FK | → acquisti.preventivi |
| `articolo_id` | uuid FK | → catalogo.articoli |
| `descrizione` | varchar | Descrizione riga (override articolo) |
| `quantita` | numeric | Quantita' richiesta |
| `prezzo_unitario` | numeric | Prezzo offerto dal fornitore |
| `sconto_percentuale` | numeric, default 0 | |
| `iva_id` | integer FK | |
| `uom_operativa_id` | bigint FK | → catalogo.unita_misura |
| `qta_operativa` | numeric | Quantita' in UoM operativa |
| `factor_to_base` | numeric | Snapshot conversione |
| `ordine` | smallint | Ordine visualizzazione |
| `attivo` | boolean | |
| `meta` | jsonb | |
| audit columns | | |

### 9.3 Macchina a stati preventivo acquisto

**Tabella config**: `config.stati_doc_preventivi_acq` (separata da vendita per indipendenza ciclo di vita)

| Codice | Descrizione | Modificabile | Genera ordine |
|--------|-------------|:------------:|:-------------:|
| BOZZA | RFQ in preparazione | si | no |
| INVIATA | Inviata al fornitore | no | no |
| RICEVUTA | Offerta ricevuta (con prezzi compilati) | parziale (prezzi) | no |
| ACCETTATA | Offerta accettata internamente | no | si |
| RIFIUTATA | Offerta rifiutata | no | no |
| SCADUTA | Superata validita_al | no | no |
| ANNULLATA | Annullata dall'operatore | no | no |

**Transizioni:**

```
BOZZA ---------> INVIATA ---------> RICEVUTA ---------> ACCETTATA ---------> (genera ordine fornitore)
                    |                   |                    |
                    |                   |                    +-> ANNULLATA
                    |                   +-> RIFIUTATA
                    |                   +-> SCADUTA
                    +-> ANNULLATA

BOZZA ---------> ANNULLATA
```

**Differenza rispetto a vendita:** lo stato RICEVUTA consente la compilazione dei prezzi
offerti dal fornitore (la RFQ parte senza prezzi o con prezzi indicativi, il fornitore
risponde con i prezzi reali).

### 9.4 Flusso downstream: da preventivo a ordine fornitore

```
PREVENTIVO ACQUISTO (ACCETTATA)
    |
    | genera ordine fornitore
    v
ACQUISTI.ORDINI
    |-- soggetto_ruolo_id (stesso fornitore)
    |-- sorgente_tipo_id = 'PREVENTIVO_ACQ'
    |-- sorgente_uid = preventivo_acq.uid
    |-- righe copiate da preventivi_righe (prezzi confermati)
    v
CICLO ACQUISTI (DDT ingresso, fattura passiva...)
```

Il collegamento ordine → preventivo usa il pattern `sorgente_tipo_id` + `sorgente_uid`
gia' presente su `acquisti.ordini` (FK `fk_ao_sorgente_tipo`, indice `uq_ordini_v_sorgente_fk`).

### 9.5 Integrazione pratiche

Il preventivo acquisto puo' generare pratiche operative (es. sopralluogo tecnico prima
dell'ordine, verifica campioni, audit fornitore) con lo stesso meccanismo della vendita:

- Link via `pratiche.pratiche_sorgenti` con `sorgente_tipo = 'PREVENTIVO_ACQ'`
- Contesto pratica: `soggetto_ruolo_id` del fornitore (non del BA)
- Catena handler invariata (§1.4.3): `pratica_id` → `pratiche_sorgenti` → `acquisti.preventivi`

### 9.6 Architettura backend acquisti

```
apps/acquisti/
  api/
    preventivi_views.py           # View per preventivi acquisto
    preventivi_urls.py            # /api/v1/acquisti/preventivi/...
  services/
    preventivi_acq_service.py     # Orchestrazione RFQ
  db/
    preventivi_acq_repository.py  # Accesso DB preventivi acquisto
  tests/
    api/
      test_preventivi_acq_api.py
    services/
      test_preventivi_acq_service.py
```

**Endpoint API:**

```
GET    /api/v1/acquisti/preventivi/                   → lista RFQ
POST   /api/v1/acquisti/preventivi/                   → crea RFQ
GET    /api/v1/acquisti/preventivi/{id}/              → dettaglio
PATCH  /api/v1/acquisti/preventivi/{id}/              → aggiorna (es. prezzi ricevuti)
POST   /api/v1/acquisti/preventivi/{id}/stato/        → cambio stato
POST   /api/v1/acquisti/preventivi/{id}/revisione/    → nuova revisione
GET    /api/v1/acquisti/preventivi/{id}/righe/        → lista righe
POST   /api/v1/acquisti/preventivi/{id}/righe/        → aggiungi riga
PATCH  /api/v1/acquisti/preventivi/{id}/righe/{rid}/  → aggiorna riga
DELETE /api/v1/acquisti/preventivi/{id}/righe/{rid}/  → elimina riga
POST   /api/v1/acquisti/preventivi/{id}/genera-ordine/ → genera ordine fornitore
POST   /api/v1/acquisti/preventivi/{id}/genera-pratica/ → genera pratica operativa
GET    /api/v1/acquisti/preventivi/{id}/pratiche/     → pratiche collegate
```

### 9.7 Architettura frontend acquisti

```
src/acquisti/
  preventivi/
    api/
      preventiviAcqApi.js
    components/
      PreventiviAcqList.vue
      PreventiviAcqForm.vue
      PreventiviAcqRigheTable.vue
      PreventiviAcqDrawer.vue
      PreventiviAcqStatoBadge.vue
    views/
      PreventiviAcqView.vue
```

**Differenze UX rispetto a vendita:**

- Controparte: autocomplete fornitore (da `soggetti_ruoli` con ruolo FORNITORE) invece di BA
- Stato RICEVUTA: form per inserire/aggiornare prezzi offerti dal fornitore sulle righe
- Azione "Genera ordine" invece di "Invia a fatturazione"
- Nessun campo utility/istanza_utility (non pertinente lato acquisti)
- Tasso cambio visibile per fornitori esteri

### 9.8 Errori strutturati acquisti

| Codice | HTTP | Descrizione |
|--------|------|-------------|
| `E_PREV_ACQ_NOT_FOUND` | 404 | Preventivo acquisto non trovato |
| `E_PREV_ACQ_VALIDAZIONE` | 400 | Validazione input fallita |
| `E_PREV_ACQ_STATO_TRANSIZIONE` | 409 | Transizione stato non ammessa |
| `E_PREV_ACQ_STATO_NON_MODIFICABILE` | 409 | Non modificabile nello stato corrente |
| `E_PREV_ACQ_RIGA_NOT_FOUND` | 404 | Riga non trovata |
| `E_PREV_ACQ_NESSUNA_RIGA` | 400 | Nessuna riga attiva |
| `E_PREV_ACQ_GIA_ORDINATO` | 409 | Ordine fornitore gia' generato |
| `E_PREV_ACQ_PREZZI_MANCANTI` | 400 | Prezzi non compilati (richiesti per accettazione) |

---

## Elementi condivisi con la parte vendita

Gli elementi infrastrutturali condivisi sono già atterrati con il
preventivo vendita e documentati lì — vedere
[../work-done/sviluppo-preventivi.md](../work-done/sviluppo-preventivi.md):

- **Tabella ponte pratiche** `pratiche.pratiche_sorgenti` (unica per
  entrambe le direzioni): qui va aggiunto il `sorgente_tipo`
  `PREVENTIVO_ACQ` in `config.sorgenti`.
- **Componenti frontend riusabili**: tabella righe (articolo + UoM +
  prezzo), badge stato, indirizzi snapshot, note testata/riga — stesso
  meccanismo, contesto controparte fornitore.
- **Catalogo articoli + UoM**: lookup cross-dominio, identico.

I componenti specifici (form testata, lookup controparte fornitore,
azioni downstream → ordine fornitore) restano separati per dominio.

## Note implementative

1. **Ordine di sviluppo**: modello concentrico — prima DB (tabelle/viste/
   funzioni), poi repository read, poi write, service, API, frontend.
2. **Pattern fornitore**: allineare a `acquisti.ordini` (controparte
   `soggetto_ruolo_id` ruolo FORNITORE, serie/numero/anno, `sorgente_tipo_id`
   + `sorgente_uid`).
3. **Downstream**: il push del preventivo acquisto genera/predispone
   l'ordine fornitore (`acquisti.ordini`), simmetrico al push
   preventivo→commessa lato vendita.
