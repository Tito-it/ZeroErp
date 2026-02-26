# Guida Tecnica – API Commesse (DB layer)

> Destinatari: sviluppatori backend e database di Zero ERP
>
> 👀 **Vedi anche**
>
> * [Gestione commesse v2 (architettura)](/dev/work-in-progress/gestione-commesse-v2)
> * [Guida fatturazione](/guide/fatturazione)
> * [vendite.commesse](/dbzero/vendite/tabelle/commesse)
> * [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> * [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)

---

## Panoramica

Il modello commesse centralizza tutte le attivita` fatturabili prima della
pipeline di fatturazione. Ogni sorgente (preventivo, ordine, contratto, DDT,
consumi) transita per la commessa — nessun bypass diretto verso
`attivita_fatturabili`.

```
SORGENTI (preventivi / ordini / consumi / ...)
        |
        v
    COMMESSA  <--- fn_get_or_create_commessa
        |
        | fn_upsert_commessa_attivita (righe)
        v
  COMMESSE_ATTIVITA
        |
        | fn_list_commesse_emittibili (discovery)
        | fn_emit_attivita_fatturabili_da_commessa (pull)
        v
  ATTIVITA_FATTURABILI  --->  PIPELINE FATTURAZIONE
```

---

## Ciclo di vita della commessa

### Stati

| ID | Codice | chiude | emittibile | modificabile |
|----|--------|--------|------------|--------------|
| 1 | BOZZA | false | false | true |
| 2 | APERTA | false | false | true |
| 3 | IN_ESECUZIONE | false | false | true |
| 4 | PRONTA_FATTURAZIONE | false | true | true |
| 5 | CHIUSA | true | false | false |
| 6 | ANNULLATA | true | false | false |

I flag governano le operazioni:

* **modificabile**: consente upsert righe (`fn_upsert_commessa_attivita`)
* **emittibile**: consente il pull verso AF (`fn_list_commesse_emittibili`)
* **chiude_commessa**: impedisce riuso da `fn_get_or_create_commessa`

---

## API — Funzioni DB

### 1. `fn_get_or_create_commessa`

> [Doc autogenerata](/dbzero/vendite/funzioni/fn_get_or_create_commessa) |
> [Doc concettuale](/dbzero/vendite/manual/fn_get_or_create_commessa)

**Scopo**: recupera una commessa riusabile o ne crea una nuova.

**Parametri principali**:

| Parametro | Obbligatorio | Note |
|-----------|:------------:|------|
| `p_billing_account_id` | si | FK anagrafiche.billing_account |
| `p_utility_id` | si | Deve coincidere con utility del BA |
| `p_tipo_commessa` | no | Default `AUTO` |
| `p_policy_fatturazione` | no | Default `DA_DOCUMENTO` |
| `p_emittente_soggetto_ruolo_id` | no | Fallback da `fn_get_emittente_fiscale_id` |
| `p_competenza_dal` / `_al` | no | Range competenza testata |
| `p_force_new` | no | Default `false` — forza nuova commessa |

**Ritorna**: `commessa_id` (nuova o riusata).

**Regole chiave**:

* Riuso solo su commesse con `chiude_commessa = false`
* Advisory lock transazionale per evitare doppie create concorrenti
* Emittente fallback automatico da billing account

```sql
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => 1001,
  p_utility_id => 2,
  p_force_new => false
);
```

---

### 2. `fn_upsert_commessa_attivita`

> [Doc autogenerata](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita) |
> [Doc concettuale](/dbzero/vendite/manual/fn_upsert_commessa_attivita)

**Scopo**: inserisce o aggiorna una riga attivita` nella commessa.

**Parametri principali**:

| Parametro | Obbligatorio | Note |
|-----------|:------------:|------|
| `p_commessa_id` | si | |
| `p_segment_key` | si | Chiave idempotenza (unique con commessa_id) |
| `p_articolo_id` | si | UUID catalogo.articoli |
| `p_istanza_utility_id` | si | |
| `p_uom_id` | si | |
| `p_quantita` | si | Diversa da 0, negativi ammessi |
| `p_prezzo_snapshot` | si | Negativi ammessi |
| `p_competenza_mese` | no | Normalizzato al primo del mese |
| `p_stato_approvazione` | no | Default `BOZZA` |
| `p_stato_emissione` | no | Default `NON_EMESSA` |
| `p_tipo_movimento` | no | `NORMALE` o `RETTIFICA` (salvato in meta) |
| `p_tipo_consumo` | no | `ACCONTO`, `CONGUAGLIO`, `STORNO` (salvato in meta) |

**Ritorna**: `commessa_attivita_id`.

**Guard**: la commessa deve avere `stati_commessa.modificabile = true`.

```sql
SELECT vendite.fn_upsert_commessa_attivita(
  p_commessa_id => 12345,
  p_segment_key => 'ORD-1001-RIGA-1',
  p_articolo_id => '8c5ce3a9-...',
  p_istanza_utility_id => 10,
  p_data_attivita => DATE '2026-02-01',
  p_uom_id => 1,
  p_quantita => 1,
  p_competenza_mese => DATE '2026-02-01',
  p_competenza_dal => DATE '2026-02-01',
  p_competenza_al => DATE '2026-02-28',
  p_prezzo_snapshot => 100
);
```

---

### 3. `fn_get_commessa_stato`

> [Doc autogenerata](/dbzero/vendite/funzioni/fn_get_commessa_stato) |
> [Doc concettuale](/dbzero/vendite/manual/fn_get_commessa_stato)

**Scopo**: restituisce stato operativo + contatori aggregati in una singola query.

**Parametri**:

| Parametro | Obbligatorio | Note |
|-----------|:------------:|------|
| `p_commessa_id` | si | Errore se non esiste |

**Ritorna** (singola riga):

| Campo | Descrizione |
|-------|-------------|
| `stato_commessa_id` | FK stati_commessa |
| `stato_commessa` | Codice testuale (backward compat) |
| `chiude_commessa` / `emittibile` / `modificabile` | Flag operativi |
| `policy_fatturazione` / `fatturazione_immediata` / `priorita_operativa` | Config testata |
| `billing_account_id` / `utility_id` / `emittente_soggetto_ruolo_id` | Perimetro |
| `total_attivita` | Totale righe |
| `total_approvate` / `total_non_approvate` | Per stato approvazione |
| `total_emesse` / `total_non_emesse` | Per stato emissione |
| `total_prezzo_da_riallineare` | Righe con prezzo da aggiornare |
| `last_update` | Max tra testata e ultima riga |

```sql
SELECT * FROM vendite.fn_get_commessa_stato(12345);
```

---

### 4. `fn_list_commessa_attivita`

> [Doc autogenerata](/dbzero/vendite/funzioni/fn_list_commessa_attivita) |
> [Doc concettuale](/dbzero/vendite/manual/fn_list_commessa_attivita)

**Scopo**: elenca le righe `commesse_attivita` con filtri e paginazione (read-only).

**Parametri**:

| Parametro | Obbligatorio | Note |
|-----------|:------------:|------|
| `p_commessa_id` | si | Errore se non esiste |
| `p_stato_emissione` | no | Es. `NON_EMESSA` |
| `p_stato_approvazione` | no | Es. `APPROVATA` |
| `p_competenza_mese` | no | Normalizzato al primo del mese |
| `p_limit` | no | Default 1000, max 10000 |
| `p_offset` | no | Default 0 |

**Ritorna**: elenco righe con JOIN `sorgente_codice` da `config.sorgenti`.

**Indice utilizzato**: `ix_commesse_attivita_commessa_stati (commessa_id, stato_approvazione, stato_emissione)`.

```sql
SELECT *
FROM vendite.fn_list_commessa_attivita(
  p_commessa_id => 12345,
  p_stato_emissione => 'NON_EMESSA',
  p_competenza_mese => DATE '2026-02-01',
  p_limit => 200
);
```

---

### 5. `fn_list_commesse_emittibili`

> [Doc autogenerata](/dbzero/vendite/funzioni/fn_list_commesse_emittibili) |
> [Doc concettuale](/dbzero/vendite/manual/fn_list_commesse_emittibili)

**Scopo**: discovery delle commesse pronte per il pull verso AF (read-only).

**Parametri**:

| Parametro | Obbligatorio | Note |
|-----------|:------------:|------|
| `p_competenza_mese` | no | Normalizzato al primo del mese |
| `p_billing_account_id` | no | Filtro perimetro |
| `p_utility_id` | no | Filtro perimetro |
| `p_emittente_soggetto_ruolo_id` | no | Filtro emittente |
| `p_limit` | no | Default 1000, max 10000 |

**Criteri di inclusione**:

1. `stati_commessa.emittibile = true`
2. Almeno una riga `commesse_attivita` con `stato_emissione = NON_EMESSA`
3. Se `p_competenza_mese` fornito, filtra su `commesse_attivita.competenza_mese`

**Ritorna**: lista commesse con `total_non_emesse` per ciascuna.

```sql
SELECT *
FROM vendite.fn_list_commesse_emittibili(
  p_competenza_mese => DATE '2026-02-01',
  p_limit => 500
);
```

---

### 6. `fn_emit_attivita_fatturabili_da_commessa`

> [Doc autogenerata](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa) |
> [Doc concettuale](/dbzero/vendite/manual/fn_emit_attivita_fatturabili_da_commessa)

**Scopo**: esegue il pull da `commesse_attivita` verso `attivita_fatturabili` (mutante).

**Parametri**:

| Parametro | Obbligatorio | Note |
|-----------|:------------:|------|
| `p_commessa_id` | si | |
| `p_lotto_attivita_id` | no | Se presente, associa AF al lotto |
| `p_only_approved` | no | Default `true` — solo righe APPROVATA |
| `p_dry_run` | no | Default `false` — simula senza scrivere |

**Ritorna**: contatori (`total_candidate`, `inserted_rows`, `updated_rows`, `skipped_rows`).

**Regole chiave**:

* ROOT source obbligatoria sulla commessa
* Sorgente AF = `COMMESSA` + hash deterministico `segment_key` -> UUID
* Idempotenza su chiave `(sorgente_tipo_id, sorgente_uid)`
* Blocco se riga AF gia` fatturata
* Aggiorna `stato_emissione = EMESSA` sulle righe processate
* Propaga `sorgente_origine_tipo_id` (sorgente business originale)

```sql
SELECT *
FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => 12345,
  p_lotto_attivita_id => 100,
  p_only_approved => true,
  p_dry_run => false
);
```

---

### 7. Funzioni di supporto

| Funzione | Scopo |
|----------|-------|
| [`fn_link_commessa_sorgente`](/dbzero/vendite/funzioni/fn_link_commessa_sorgente) | Collega una sorgente (ROOT/CONTRIBUENTE) alla commessa |
| [`fn_log_commessa_push_run`](/dbzero/vendite/funzioni/fn_log_commessa_push_run) | Registra esito push sorgente -> commessa |
| [`fn_resolve_commessa_prezzi`](/dbzero/vendite/funzioni/fn_resolve_commessa_prezzi) | Riallinea prezzi da listino sulle righe attivita` |

---

## Flusso tipo — Backend handler PULL_COMMESSA

Lo step `PULL_COMMESSA` (ordine 5) della pipeline `attivita_fatturabili_pipeline`
esegue:

```python
# 1. Discovery commesse pronte
rows = db.call_fn("vendite.fn_list_commesse_emittibili",
    p_competenza_mese=competenza_mese,
    p_emittente_soggetto_ruolo_id=emittente_id
)

# 2. Per ogni commessa, pull verso AF
for row in rows:
    result = db.call_fn("vendite.fn_emit_attivita_fatturabili_da_commessa",
        p_commessa_id=row.commessa_id,
        p_lotto_attivita_id=lotto_id,
        p_only_approved=True
    )
    log.info(f"Commessa {row.commessa_id}: {result.inserted_rows} ins, "
             f"{result.updated_rows} upd")
```

**Catena pipeline completa**:

```
PULL_COMMESSA (ordine 5)  -->  RACCOLTA_INPUT (ordine 10)  -->  NORMALIZZAZIONE (ordine 20)
```

---

## Flusso tipo — Push sorgente -> commessa

```python
# 1. Ottieni/crea commessa
commessa_id = db.call_fn("vendite.fn_get_or_create_commessa",
    p_billing_account_id=ba_id,
    p_utility_id=utility_id,
    p_competenza_dal=dal,
    p_competenza_al=al
)

# 2. Collega sorgente (se primo push)
db.call_fn("vendite.fn_link_commessa_sorgente",
    p_commessa_id=commessa_id,
    p_sorgente_tipo_id=sorgente_id,
    p_sorgente_uid=doc_uid,
    p_ruolo_link='ROOT'
)

# 3. Upsert righe
for riga in righe_documento:
    db.call_fn("vendite.fn_upsert_commessa_attivita",
        p_commessa_id=commessa_id,
        p_segment_key=riga.segment_key,
        p_articolo_id=riga.articolo_id,
        ...
    )

# 4. Log esito push
db.call_fn("vendite.fn_log_commessa_push_run",
    p_commessa_id=commessa_id,
    p_sorgente_tipo_id=sorgente_id,
    ...
)
```

---

## Error handling

Tutte le funzioni usano `script.fn_log_and_raise_error` con:

* Scope `COMMESSE`
* Severity `C` (critico) per guard violations
* Context JSONB strutturato per diagnostica

Errori comuni:

| Errore | Funzione | Causa |
|--------|----------|-------|
| commessa_id obbligatorio | Tutte | Parametro NULL o <= 0 |
| commessa non trovata | get_stato, list_attivita, emit | ID inesistente |
| commessa non modificabile | upsert_attivita | Stato CHIUSA/ANNULLATA |
| riga AF gia` fatturata | emit_da_commessa | Tentativo update su riga fatturato=true |
| ROOT source mancante | emit_da_commessa | Nessun link ROOT in commesse_sorgenti |
| sorgente COMMESSA non attiva | emit_da_commessa | config.sorgenti COMMESSA disabilitata |

---

## Test pgTAP

| File test | Copertura |
|-----------|-----------|
| `test-commesse-stati-commessa-v1.sql` | DDL stati_commessa, flag, fn_get_commessa_stato, fn_upsert guard, fn_list_commesse_emittibili (20 test) |
| `test-fn-list-commessa-attivita-v1.sql` | fn_list_commessa_attivita: filtri, paginazione, guard (14 test) |

---

*Documento generato — febbraio 2026*
