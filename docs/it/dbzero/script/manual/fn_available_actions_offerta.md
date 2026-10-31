# fn_available_actions_offerta

### Scopo

Restituisce in un **unico JSONB** tutte le capability dell'offerta commerciale
necessarie al detail endpoint BE. Permette ai drawer Vue di eliminare qualsiasi
ricalcolo di stato/transizioni lato client.

Pattern **data-driven capability layer**: specchio strutturale di
[fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo),
adattato al dominio offerte commerciali.

Differenze rispetto al preventivo:

- Le transizioni manuali vengono lette da `config.stati_doc_offerte_transizioni`
  (stesso schema di `config.transizioni_stati_preventivi`).
- I check `can_push_contratto` e `can_genera_ordine` sono **cross-dominio**
  (`EXISTS` su `vendite.contratti.offerta_id` e su
  `vendite.ordini.documento_origine_*`), a differenza di `can_push_commessa`
  del preventivo che usa solo lo stato e rinvia il check cross-dominio a Fase 3.
- Le azioni speciali hardcoded sono `crea_revisione` (EMESSA),
  `push_contratto` e `genera_ordine` (entrambe ACCETTATA). Tutte hanno
  `target_state: null` e appaiono in `available_actions` (non solo come flag).
- **Mutua esclusività contratto/ordine (rev 2026-06-08)**: `push_contratto` e
  `genera_ordine` hanno la **stessa** condizione di abilitazione (`ACCETTATA` +
  nessun contratto + nessun ordine generati dall'offerta) e sono quindi
  **mutuamente esclusive** — un'offerta ne genera al massimo una: la prima
  generazione disabilita anche l'altra. Vedi
  [brief-db-univocita-offerta-ordine §10](/dev/work-done/brief-db-univocita-offerta-ordine).

> **Vedi anche**
>
> - [trgfn_offerte_commerciali_guard_transizione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione) — guard transizioni (regola reale)
> - [stati_doc_offerte_transizioni](/dbzero/config/tabelle/stati_doc_offerte_transizioni) — matrice transizioni + meta UI
> - [fn_push_offerta_a_contratto](/dbzero/vendite/funzioni/fn_push_offerta_a_contratto) — esegue il push (guard idempotenza reale)
> - [fn_crea_revisione_offerta](/dbzero/vendite/funzioni/fn_crea_revisione_offerta) — esegue la revisione

## Schema

`script` (cross-dominio: legge `vendite.*`, `config.*`).

## Firma

```sql
script.fn_available_actions_offerta(
    p_offerta_id vendite.offerte_commerciali.id%TYPE  -- bigint
) RETURNS jsonb
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_offerta_id` | `bigint` | Sì | ID dell'offerta. Ritorna `NULL` se non esiste (gestito dal BE come 404). |

## Output

`jsonb` con le seguenti chiavi (contratto API stabile):

```jsonc
{
    // Lista azioni manuali + speciali disponibili dallo stato corrente.
    // Vuota ([]) per stati terminali (ACCETTATA con contratto O ordine, RIFIUTATA, ANNULLATA, SUPERATA).
    // Costruita da config.stati_doc_offerte_transizioni.meta + azioni hardcoded.
    "available_actions": [
        {
            "key": "emetti",
            "target_state": "EMESSA",          // null per azioni speciali (crea_revisione, push_contratto, genera_ordine)
            "label_key": "offerte.azione_emetti",
            "requires_confirm": true,
            "requires_motivazione": false       // true per annulla e rifiuta
        }
        // ...
    ],
    "can_change_state":             true,    // true se esiste almeno un'azione
    "can_edit_testata":             true,    // true solo in BOZZA
    "can_edit_eccezioni":           true,    // true solo in BOZZA
    "can_edit_utility":             true,    // true solo in BOZZA (utility 1:1 inline)
    "can_create_revisione":         false,   // true solo in EMESSA
    // push_contratto e genera_ordine: MUTUAMENTE ESCLUSIVE — stessa abilitazione
    // (ACCETTATA + nessun contratto + nessun ordine). can_push == can_genera sempre.
    "can_push_contratto":           false,   // true solo in ACCETTATA senza contratto NE ordine
    "can_push_contratto_reason":    "OFFERTA_NON_ACCETTATA",  // null se can_push=true
    "can_push_contratto_reason_key": "offerte.push_reason.non_accettata", // null se can_push=true
    "can_genera_ordine":            false,   // true solo in ACCETTATA senza ordine NE contratto
    "can_genera_ordine_reason":     "OFFERTA_NON_ACCETTATA",  // null se can_genera=true
    "can_genera_ordine_reason_key": "offerte.push_reason.non_accettata", // null se can_genera=true
    "non_editable_fields":          [...],   // vedi dettaglio sotto
    "stato_codice":                 "BOZZA"
}
```

### Dettaglio `available_actions` per stato

| `stato_codice` | Azioni in `available_actions` | Note |
|---|---|---|
| `BOZZA` | `emetti`, `annulla` | Da matrice transizioni |
| `EMESSA` | `accetta`, `rifiuta`, `crea_revisione` | `crea_revisione` hardcoded |
| `ACCETTATA` (né contratto né ordine) | `push_contratto`, `genera_ordine` | Hardcoded, mutuamente esclusive: entrambe esposte finché l'offerta è «vergine» |
| `ACCETTATA` (con contratto **o** ordine) | `[]` | Generata una delle due, **entrambe** spariscono (mutua esclusività) |
| `RIFIUTATA` | `[]` | Terminale |
| `ANNULLATA` | `[]` | Terminale |
| `SUPERATA` | `[]` | Terminale tecnico (sostituita da revisione successiva) |

### Reason di `can_push_contratto` / `can_genera_ordine`

Le due capability condividono l'abilitazione (`ACCETTATA` + nessun contratto +
nessun ordine), quindi `can_push_contratto == can_genera_ordine` **sempre**.
Quando bloccate, il `reason` segue una priorità **own-doc first** (la propria
sorgente prima dell'altra, poi lo stato). I `reason_key` i18n sono riusati.

| Caso | `can_*` | `can_push_contratto_reason` | `can_genera_ordine_reason` |
|------|:---:|---|---|
| ACCETTATA, né contratto né ordine | `true` | `null` | `null` |
| ACCETTATA, contratto già generato | `false` | `OFFERTA_CONTRATTO_GIA_GENERATO` | `OFFERTA_CONTRATTO_GIA_GENERATO` |
| ACCETTATA, ordine già generato | `false` | `OFFERTA_ORDINE_GIA_GENERATO` | `OFFERTA_ORDINE_GIA_GENERATO` |
| Qualsiasi altro stato | `false` | `OFFERTA_NON_ACCETTATA` | `OFFERTA_NON_ACCETTATA` |

`reason_key`: `offerte.push_reason.gia_generato` (contratto),
`offerte.push_reason.ordine_gia_generato` (ordine),
`offerte.push_reason.non_accettata` (stato).

### Dettaglio `non_editable_fields`

> ⚠️ **Superato il 2026-10-10** (brief `brief-db-testata-dopo-emissione`, fase 2). Le liste
> qui sotto erano scritte a mano nella funzione: la terza copia della regola «che cosa si
> cambia ancora fuori bozza». Ora `non_editable_fields` e `can_edit_testata` si leggono dal
> montaggio del lock di testata con
> [`script.fn_doc_testata_in_stato`](/dbzero/script/funzioni/fn_doc_testata_in_stato): restano
> nella capability solo le colonne «sempre» (campi di sistema e lock assoluti, valgono anche in
> bozza), seguite da quelle che il lock blocca nello stato. Fuori bozza `can_edit_testata` è vero
> negli stati in cui una colonna resta aperta (le note di un documento vivo, `valido_al` e
> CIG/CUP del contratto attivo), falso a documento chiuso. La tabella resta per la storia.

Due famiglie di immutabilità:

| Famiglia | Campi |
|---|---|
| **Sempre immutabili** (gestiti da trigger transizione stato) | `codice`, `uid`, `revisione_numero`, `revisione_padre_id`, `stato_doc_offerta_id`, `data_emissione`, `data_accettazione`, `data_rifiuto`, `data_annullamento`, `motivazione_rifiuto` |
| **Bloccati fuori BOZZA** | `emittente_fiscale_id`, `billing_account_id`, `istanza_utility_id`, `utility_id`, `listino_id`, `listino_versione_id`, `valore_variazione_globale`, `tipo_variazione_globale`, `validita_dal`, `validita_al`, `meta` |

Risultato per stato:

| Stato | `non_editable_fields` |
|---|---|
| `BOZZA` | Solo famiglia "sempre immutabili" (10 campi) |
| Tutti gli altri | Unione delle due famiglie (21 campi) |

## Algoritmo

1. **Lookup offerta** — JOIN `vendite.offerte_commerciali` ×
   `config.stati_doc_offerte` per ottenere `stato_id` e `codice_interno`.
   `NOT FOUND` → `RETURN NULL`.
2. **Transizioni manuali** — `jsonb_agg` su `config.stati_doc_offerte_transizioni`
   filtrata per `stato_da_id = v_stato_id AND attivo IS TRUE AND manuale IS NOT FALSE`.
   I metadati UI (`label_key`, `requires_confirm`,
   `requires_motivazione`) vengono letti da `t.meta`; icona e colore li sceglie il frontend dal `key`. Ordine: `sa.ordine`.
   Filtro defense-in-depth: `AND t.meta ?? 'action_key' AND t.meta ?? 'label_key'`.
3. **Presenza documenti** — due `EXISTS` calcolati una volta:
   - `v_has_contratto` = `EXISTS` contratto con `offerta_id = p_offerta_id`.
   - `v_has_ordine` = `EXISTS` ordine con `documento_origine_tipo = 'OFFERTA'
     AND documento_origine_id = p_offerta_id`.
   «Esiste» = in qualsiasi stato (esclusività permanente).
4. **Abilitazione condivisa** —
   `v_enabled = (stato di accettazione AND NOT v_has_contratto AND NOT v_has_ordine)`;
   accettazione ed emissione dalle colonne del vocabolario (`accettazione`, `emissione`),
   non dal codice *(rev 31-10-2026)*.
5. **Azioni speciali** — aggiunte hardcoded in coda a `v_actions`:
   - `crea_revisione` se lo stato è quello di emissione.
   - `push_contratto` **e** `genera_ordine` se `v_enabled` (entrambe o nessuna).
6. **Capability derivate**:
   - `can_edit_*` = `(stato = 'BOZZA')`.
   - `can_create_revisione` = `(stato di emissione)`.
   - `can_push_contratto` = `can_genera_ordine` = `v_enabled`. Reason con priorità
     own-doc first quando bloccate (contratto>ordine per push; ordine>contratto
     per genera; poi `OFFERTA_NON_ACCETTATA`).
7. **Build JSONB** — `jsonb_build_object` con tutte le chiavi.

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.offerte_commerciali` | tabella | sorgente stato e ID |
| `config.stati_doc_offerte` | tabella | risoluzione `codice_interno` e `ordine` |
| `config.stati_doc_offerte_transizioni` | tabella | matrice transizioni + meta UI |
| `vendite.contratti` | tabella | check `v_has_contratto` (`can_push_contratto`) |
| `vendite.ordini` | tabella | check `v_has_ordine` su `documento_origine_*` (`can_genera_ordine`) |
| `20260524-22-upsert-stati-doc-offerte-transizioni-mctit` | migration 80_data | seed iniziale meta transizioni |
| `20260526-01-update-stati-doc-offerte-transizioni-meta-mctit` | migration 80_data | completa meta (requires_motivazione, severity, requires_confirm) |
| `20260607-08-update-fn-available-actions-offerta-genera-ordine-mctit` | migration 20_code | aggiunge azione/flag `genera_ordine` (allora indipendente) |
| `20260608-12-update-fn-available-actions-offerta-mutua-esclusivita-mctit` | migration 20_code | **mutua esclusività** contratto/ordine (rev corrente) |

## Note operative

- **STABLE**: solo lettura; il pianificatore può riusare il risultato nella
  stessa transazione.
- **Fallback NULL**: il BE interpreta `NULL` come offerta non trovata e
  risponde 404 prima di serializzare il payload.
- **Meta mancante**: se una transizione non ha `manuale` in meta, viene
  trattata come manuale (`COALESCE(..., true)`). Se non ha `requires_confirm`
  o `requires_motivazione`, il valore default è `false`.
- **Guard meta keys**: il WHERE esclude transizioni manuali senza
  `action_key` o `label_key` (defense-in-depth equivalente a
  `ck_transizioni_stati_prev_meta_ui` dei preventivi).
- **Idempotenza/esclusività reali a write-path**: questa funzione calcola solo
  l'abilitabilità UI. Le guard reali risiedono nelle funzioni di scrittura:
  - lato contratto, `vendite.fn_push_offerta_a_contratto` fallisce sia se esiste
    già un contratto (`E_OFFERTA_CONTRATTO_GIA_GENERATO` + `UNIQUE
    uq_contratti_offerta_id`) sia se esiste già un ordine
    (`E_OFFERTA_ORDINE_GIA_GENERATO`, guard mutua esclusività rev6);
  - lato ordine, il guard speculare (impedire l'ordine se esiste un contratto)
    vive nel BE `crea_ordine_da_offerta` (fuori scope DB). L'indice
    `uq_ordini_v_documento_origine_offerta` impedisce ordini duplicati dalla
    stessa offerta.
  - La **race cross-tab** (push + genera_ordine simultanei) non è coperta da
    alcun vincolo strutturale: scelta esplicita (back-office mono-utente).
- **Azioni speciali `target_state: null`**: il FE distingue queste azioni
  dal `key` (`crea_revisione`, `push_contratto` e `genera_ordine` usano routing
  speciale nel drawer; le transizioni standard usano l'endpoint generico
  cambio-stato).

## Rev 2026-09-24 — «Emetti» e «Accetta» spenti finché un prezzo non è autorizzato

Regola decisa da Tid: *un prezzo che nessuno ha autorizzato non esce dalla bozza*.
Un'offerta con un'eccezione o un suo componente **attivi** in attesa di approvazione
(`PENDING`) o **rifiutati** (`REJECTED`) non si emette e non si accetta.

* Le azioni di stato passano alla forma dell'**array dei motivi**: `enabled`, `reason` e
  `reason_key` discendono da una chiave **nuova**, `reasons`. `crea_revisione`, le push e
  l'ordine non cambiano.
* Verso `EMESSA`: prima il motivo del listino di prima (versione mancante o non attiva,
  stessi `reason` e `reason_key`), poi i motivi di [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati).
* Verso `ACCETTATA`: i motivi di [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati).
* Il rientro automatico `SUPERATA → EMESSA` non è un'azione manuale e non compare qui.
* È lo stesso building block che
  [`vendite.trgfn_offerte_commerciali_guard_transizione`](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione)
  usa per sollevare: pulsanti e database non possono dissentire.

Motivi nuovi: `PREZZO_PENDENTE` / `PREZZO_RIFIUTATO`, con `reason_key`
`common.azione_reason.prezzo_pendente` / `common.azione_reason.prezzo_rifiutato`.
(changeSet `20260924-28`, brief `brief-db-preventivi-congelamento-pricing`.)

---

### Rev 2026-09-24 (2) — «Crea revisione» spento con un prezzo in attesa

(`20260924-37`.) L'azione `crea_revisione` resta proposta su `EMESSA`, ma è **spenta con il
motivo** se l'offerta ha un prezzo in attesa —
[script.fn_check_prezzi_in_attesa](/dbzero/script/funzioni/fn_check_prezzi_in_attesa), la
stessa funzione con cui `fn_crea_revisione_offerta` rifiuta. `can_create_revisione` diventa
**veritiero**.

## Rev 2026-10-11 — fornitura, indirizzi e motivazione del rifiuto (brief-db-testata-dopo-emissione §11)

* **R-DB-2.** `motivazione_rifiuto` non è più fra le colonne ferme in ogni stato: la governa il
  lock di testata, aperta in EMESSA e ACCETTATA, chiusa a offerta chiusa.
* **R-DB-3.** `can_edit_utility` non è più «stato = BOZZA» scritto nella funzione: si legge dal
  lock montato sulla fornitura (`vendite.offerte_commerciali_utilities`). Nuovo
  `can_edit_indirizzi`, dal lock sugli indirizzi.
