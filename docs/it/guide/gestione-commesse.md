# Guida Tecnica – API Commesse (DB layer)

> Destinatari: sviluppatori backend e database di Zero ERP
>
> **Ultima revisione**: 23 aprile 2026 — sezione "Lifecycle prezzo" allineata
> al modello pricing v5 (resolver `fn_resolve_prezzo_listino_v2` a 3 stadi,
> snapshot 8 colonne audit Sprint F2-BE-11, espansione BoM compositi
> Sprint F2-BE-12, workflow L3 approvazione Sprint E).
>
> 👀 **Vedi anche**
>
> * Gestione commesse v2 (architettura interna di lavoro)
> * [Guida fatturazione](/guide/fatturazione)
> * [Gestione Listini e Pricing v5](/guide/gestione-listini) — modello pricing che alimenta lo snapshot commesse
> * [vendite.commesse](/dbzero/vendite/tabelle/commesse)
> * [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> * [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)
> * [BoMComponentExpander (catalogo BB backend)](/dev/backend/catalogo-building-block-backend) — espansione compositi nella pipeline push

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

## Lifecycle prezzo: dal preventivo alla fattura

Questa sezione documenta il flusso completo del prezzo dall'origine (preventivo o ordine) fino alla fattura, passando per la commessa.

### Flusso standard

```text
1. Creazione preventivo (modello pricing v5)
   L'operatore inserisce righe con prezzo. Il prezzo puo venire da:
   - Resolver pricing v5 (fn_resolve_prezzo_listino_v2) - 3 stadi:
       STADIO 0: PROMO overlay
       STADIO 1: CONTRATTO (modalita A/B/C)
       STADIO 2: CATEGORIA cliente via matrice
   - Override manuale L1 (azione processo prezzo_override_manuale)
   - Workflow L3 approvazione (Sprint E):
       Se override viola L2 (limiti VENDITE_MAX_SCONTO/MAGGIORAZIONE_PCT)
       e l'operatore richiede approvazione (richiesta_approvazione=true),
       la riga e' salvata con stato_approvazione_prezzo='PENDING'.
       Il preventivo NON puo' transitare a ACCETTATO finche' tutte le
       righe PENDING sono APPROVED o REJECTED (trigger DB).
       Solo i preventivi ACCETTATI transitano in commessa: quindi una
       riga PENDING non arriva mai alla pipeline push commesse.

2. Push in commessa
   Il push (handler PREVENTIVO/ORDINE/CONTRATTO/DDT/CONSUMI) crea
   commesse_attivita con:
   - prezzo_snapshot = prezzo risolto o manuale
   - listino_versione_id = versione usata dal resolver (NULL se manuale)
   - listino_riga_id = riga usata dal resolver (NULL se manuale)
   - prezzo_bloccato = TRUE se override manuale, FALSE se da resolver
   - pricing_mode = 'FIXED' (v1)
   - 8 colonne snapshot audit pricing v5 (vedi sezione dedicata sotto)

3. Modifica preventivo post-push
   Se il preventivo viene modificato dopo il push:
   - commesse_attivita.prezzo_da_riallineare = TRUE (segnalazione, no update automatico)
   - Il prezzo NON viene aggiornato silenziosamente
   - L'operatore deve decidere se riallineare (N5) o ignorare

4. Riallineamento su conferma esplicita (N5)
   POST .../riallinea-prezzo/ ricalcola dal resolver alla data originale
   - Se la versione listino e cambiata: richiede conferma esplicita
   - Aggiorna prezzo_snapshot + prezzo_unitario su attivita_fatturabili
   - Azzera prezzo_da_riallineare
   - prezzo_bloccato resta FALSE

5. Variazione eccezionale (N7) — alternativa a N5
   POST .../variazione-prezzo-eccezionale/ con prezzo manuale + motivo
   - Imposta prezzo_bloccato = TRUE (il resolver non ricalcolera piu)
   - Il prezzo manuale prevale su qualsiasi listino

6. Sblocco (N7-sblocco) — reversibilita di N7
   POST .../sblocca-prezzo/ ricalcola dal resolver e sblocca
   - Imposta prezzo_bloccato = FALSE

7. Conversione in ordine
   Se il preventivo non e stato riallineato (prezzo_da_riallineare = TRUE),
   il flag persiste sulla commessa. L'ordine non lo azzera automaticamente.
   L'operatore puo riallineare in qualsiasi momento prima della fatturazione.

8. Emissione fattura
   La pipeline fatturazione legge SOLO da attivita_fatturabili:
   - prezzo_unitario (snapshot gia propagato)
   - prezzo_bloccato (informativo)
   - NON rilegge mai il listino
```

### Snapshot pricing v5 — 8 colonne audit (Sprint F2-BE-11)

Ogni riga `commesse_attivita` registra l'audit completo del calcolo prezzo
all'epoca del push. Queste colonne sono **immutabili dopo emissione fattura**
e permettono ricostruzione storica del processo pricing senza dipendere da
modifiche successive a listini/contratti/promo.

| Colonna | Valore |
|---|---|
| `prezzo_base_snapshot` | Prezzo riga listino prima di qualunque variazione |
| `origine_prezzo` | `PROMO` / `CONTRATTO_OVERRIDE` / `CONTRATTO_LISTINO` / `CATEGORIA` / `MANUALE` |
| `tipo_variazione_applicata` | `PERCENTUALE` / `VALORE_FISSO` / `PREZZO_FISSO` / `NESSUNA` |
| `valore_variazione_applicata` | Valore firmato (negativo=sconto, positivo=maggiorazione) |
| `promo_id` | FK promo se origine=PROMO |
| `contratto_id` | FK contratto se origine CONTRATTO_* |
| `categoria_cliente_id_snapshot` | FK categoria cliente al momento dello snapshot (anche se categoria poi cambia) |
| `classe_utenza_id_snapshot` | FK classe utenza derivata da contratto/istanza |

Popolazione: `fn_upsert_commessa_attivita` riceve tutti gli 8 campi dal
chiamante (Python `CommessaAttivitaInput`) che li ricava dal resolver v5
o dal flusso L1 override.

### Espansione compositi BoM v5 (Sprint F2-BE-12)

Quando una sorgente (preventivo/ordine/...) contiene un articolo composito
(`catalogo.articoli.is_composito = true`) con almeno un componente
`esposto_in_fattura = true`, la pipeline push **espande** la riga padre
in N righe `commesse_attivita`, una per ogni componente attivo della BoM.

Logica orchestrata da `BoMComponentExpander` in
`apps/vendite/services/commesse_source_handlers.py`:

* 1 riga sorgente composito → N righe `commesse_attivita`
* `articolo_id` = `componente_id`
* `quantita` = `quantita_padre × coeff_qta` (no rounding sotto-componenti)
* `prezzo_snapshot` = prezzo risolto del singolo componente (resolver dedicato)
* `segment_key` = `{padre_segment_key}#CMP:{componente_id}` (idempotente per re-run)
* `meta` arricchito con `componente_di`, `esposto_in_fattura`, `coeff_qta`
* Tutti gli altri campi (BA, utility, competenza, sorgente_uid, tipo_doc_fiscale) ereditati pari pari dal padre

Componenti **non esposti**: anch'essi tracciati in `commesse_attivita` per
audit completo, ma `meta.esposto_in_fattura=false`. La pipeline fatturazione
filtra queste righe per emettere solo gli esposti in fattura.

**Caso semplice (non composito o senza componenti esposti)**: pass-through,
1 riga sorgente → 1 riga `commesse_attivita`.

**BoM immutabile**: la struttura BoM non puo' essere modificata in place
dopo essere stata pushata. Pattern admin: chiudi riga + duplica nuova
versione (vedi [gestione-listini §5.3](/guide/gestione-listini#53-immutabilita-della-bom-pattern-chiudi-nuova-versione)).
Garantisce che lo snapshot resti sempre ancorato alla struttura del momento.

### Gerarchia prezzo (riassunto)

| Priorita | Fonte | prezzo_bloccato dopo |
|---|---|---|
| 1 | Override manuale su documento (N7) | TRUE |
| 2 | Prezzo da resolver listino (standard o N5) | FALSE |

### Casi limite

| Caso | Comportamento |
|---|---|
| Preventivo modificato, commessa non riallineata, fattura emessa | La fattura usa il prezzo dello snapshot originale. Il flag `prezzo_da_riallineare` resta TRUE come segnalazione storica |
| Versione listino cambiata dopo lo snapshot | N5 detecta il cambio e richiede conferma. Senza conferma, non aggiorna |
| Riga commessa gia fatturata | N5/N7/N7-sblocco rifiutano con 409. Per correggere serve NDC/NDD (DB-L4) |

---

## Error handling

Tutte le funzioni usano `script.fn_log_and_raise_error` con:

* Ambito `COMMESSE`
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

*Documento generato — febbraio 2026. Aggiornato 23 aprile 2026 (Lifecycle prezzo allineato a pricing v5: resolver_v2, snapshot 8 colonne, BoM expander, workflow L3).*
