# fn_available_actions_ordine

### Scopo

Restituisce in un **unico JSONB** tutte le capability dell'ordine di vendita
necessarie al detail endpoint BE. Permette al drawer Vue di eliminare qualsiasi
ricalcolo di stato/transizioni lato client e di consumare le azioni con i building
block già usati dagli altri documenti vendite (`useEntityCapabilities`,
`mapAvailableActionsToDrawerActions`).

Pattern **data-driven capability layer**: allineato a
[fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo),
[fn_available_actions_offerta](/dbzero/script/funzioni/fn_available_actions_offerta) e
[fn_available_actions_contratto](/dbzero/script/funzioni/fn_available_actions_contratto).
Dalla rev 2026-06-05 legge `available_actions[]` da `config.transizioni_stati_ordini`
invece del calcolo hardcoded in `ordini_service.py` (eliminato in fase BE).

> **Vedi anche**
>
> - [trgfn_ordini_guard_transizione](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione) — guard transizioni (enforcement del grafo, stessa matrice)
> - [transizioni_stati_ordini](/dbzero/config/tabelle/transizioni_stati_ordini) — matrice metadati UI + grafo
> - [ordini](/dbzero/vendite/tabelle/ordini) — entità sorgente
> - [fn_list_ordini_da_pushare](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare) — eleggibilità push (riusata)

## Schema

`script` (cross-dominio: legge `vendite.*` e `config.*`).

## Firma

```sql
script.fn_available_actions_ordine(
    p_ordine_id vendite.ordini.id%TYPE  -- bigint
) RETURNS jsonb
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_ordine_id` | `bigint` | Sì | ID dell'ordine. Ritorna `NULL` se non esiste (gestito dal BE come 404). |

## Output

`jsonb` con le seguenti chiavi (contratto API stabile):

```jsonc
{
    // Azioni di stato manuali (da config.transizioni_stati_ordini) +
    // push_commessa (azione applicativa appesa a mano, NON transizione).
    "available_actions": [
        {
            "key": "conferma",
            "target_state": "CONFERMATO",
            "label_key": "vendite.ordini.azione_conferma",
            "requires_confirm": true,
            "outlined": false
        }
    ],
    "can_change_state":   true,   // SOLO transizioni di stato (escluso push_commessa)
    "can_edit_testata":   true,   // true solo in DRAFT
    "can_edit_righe":     true,   // true solo in DRAFT
    "can_edit_data_consegna_confermata":            false,             // la promessa di consegna, col verbo dedicato (rev 2026-10-10)
    "can_edit_data_consegna_confermata_reason":     "ORDINE_IN_BOZZA", // null se ammesso
    "can_edit_data_consegna_confermata_reason_key": "vendite.ordini.data_consegna_confermata_reason.in_bozza",
    "can_push_commessa":  false,  // true se righe pushabili (trigger CONFERMATO, anche PARZIALMENTE_EVASO/EVASO)
    "can_push_commessa_reason":     "ORDINE_NON_CONFERMATO",                  // null se push disponibile
    "can_push_commessa_reason_key": "ordini.push_commessa_reason.non_confermato", // chiave i18n tooltip
    "non_editable_fields": [...],
    "stato_codice":       "DRAFT"
}
```

### Dettaglio `available_actions` per stato

| `stato_codice` | Azioni in `available_actions` | Note |
|---|---|---|
| `DRAFT` | `conferma`, `annulla` | Ordinate per `stati_doc_ordini.ordine` (CONFERMATO=20, ANNULLATO=60) |
| `CONFERMATO` | `push_commessa` *(se eleggibile)* | Nessuna transizione manuale: `CONFERMATO → ANNULLATO` è `attivo=false`. `push_commessa` appesa solo se l'ordine è pushabile |
| `PARZIALMENTE_EVASO` / `EVASO` | `push_commessa` *(se eleggibile)* | **Rev 2026-07-10 (decoupling)**: la spedizione non chiude la finestra di push per il trigger CONFERMATO (fix «orfano») |
| `ANNULLATO` | `[]` | Terminale |

> **`can_change_state` vs `push_commessa`** — `can_change_state` riflette le **sole**
> transizioni di stato, calcolato **prima** di appendere `push_commessa`. Per un ordine
> CONFERMATO pushabile: `can_change_state=false` ma `available_actions` contiene comunque
> `push_commessa` (che non cambia lo stato).

### Azione `push_commessa` — applicativa, non di stato

Appesa a mano (non da matrice) quando l'ordine ha almeno una riga pushabile secondo
`fn_list_ordini_da_pushare` (fonte unica: `fatturazione_trigger='CONFERMATO'`, stato
**non** `DRAFT`/`ANNULLATO`/`FATTURATO`, righe non ancora `EMESSA`). **Rev 2026-07-10
(decoupling fatturazione ↔ spedizione)**: vale anche in `PARZIALMENTE_EVASO`/`EVASO` —
la fatturazione su conferma è ortogonale alla spedizione (recupero ordine «orfano»,
piano `piano-db-fix-orfano-push-ordine-confermato.md`):

```jsonc
{
    "key": "push_commessa",
    "target_state": null,            // non cambia stato
    "label_key": "vendite.ordini.azione_push_commessa",
    "requires_confirm": true,
    "outlined": false
}
```

L'eleggibilità riusa la funzione canonica
[`vendite.fn_list_ordini_da_pushare`](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare)
(no logica pushable duplicata). Quando `push_commessa` non è disponibile, la funzione
valorizza la coppia motivo/chiave i18n per il tooltip:

| Condizione | `can_push_commessa` | `can_push_commessa_reason` | `can_push_commessa_reason_key` |
|---|:---:|---|---|
| stato `DRAFT`/`ANNULLATO` | `false` | `ORDINE_NON_CONFERMATO` | `ordini.push_commessa_reason.non_confermato` |
| `fatturazione_trigger` ≠ CONFERMATO | `false` | `ORDINE_FATTURA_DA_DDT` | `ordini.push_commessa_reason.fattura_da_ddt` |
| ≥1 riga pushabile (`fn_list_ordini_da_pushare`) | `true` | `null` | `null` |
| 0 righe pushabili, ≥1 segmento `EMESSA` | `false` | `ORDINE_GIA_FATTURATO` | `ordini.push_commessa_reason.gia_fatturato` |
| 0 righe pushabili, nessun segmento emesso | `false` | `ORDINE_NESSUNA_RIGA_PUSHABILE` | `ordini.push_commessa_reason.nessuna_riga_pushabile` |

> **`ORDINE_GIA_EVASO` rimosso (rev 2026-07-10).** Asseriva «EVASO = già fatturato», in
> collisione con «EVASO = spedizione completa» del flusso DDT. La verità di billing è
> `vendite.commesse_attivita.stato_emissione='EMESSA'` (stessa usata dal `NOT EXISTS`
> di `fn_list_ordini_da_pushare`), non lo stato documento.

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

| Stato | `can_edit_testata` | `can_edit_righe` | `non_editable_fields` |
|---|:---:|:---:|---|
| `DRAFT` | `true` | `true` | `["billing_account_id","soggetto_ruolo_id"]` — solo cliente |
| `CONFERMATO` / terminali | `false` | `false` | Tutta la testata aggiornabile + cliente |

Il **cliente** (`billing_account_id`, `soggetto_ruolo_id`) è immutabile **anche in DRAFT**
(lock columns via `script.trgfn_lock_columns`, errore `E_ORD_CLIENTE_IMMUTABILE`). Fuori
da DRAFT è bloccata tutta la testata, allineata a `_UPDATE_KEYS_ORDINE` di
`ordini_service.py`:

```json
["billing_account_id","soggetto_ruolo_id","utility_id","valuta_id",
 "modalita_pagamento_id","termine_pagamento_id","fatturazione_trigger",
 "agente_soggetto_ruolo_id","data","meta"]
```

## Algoritmo

1. **Lookup ordine** — JOIN `vendite.ordini` × `config.stati_doc_ordini` per ottenere
   `stato_id`, `codice_interno`. `NOT FOUND` → `RETURN NULL`.
2. **Transizioni manuali** — `jsonb_agg` su `config.transizioni_stati_ordini` filtrata per
   `stato_da_id = v_stato_id AND attivo IS TRUE AND manuale IS NOT FALSE`. Metadati UI
   (`label_key`, `requires_confirm`, `outlined`) da `t.meta`; icona e colore li sceglie
   il frontend dal `key`. Ordine:
   `sa.ordine`. Guard defense-in-depth: `AND t.meta ? 'action_key' AND t.meta ? 'label_key'`.
3. **`can_change_state`** — `jsonb_array_length(v_actions) > 0` calcolato **qui**, prima di
   appendere `push_commessa`.
4. **push_commessa** — cascata (rev 2026-07-10): stato `DRAFT`/`ANNULLATO` → reason;
   `fatturazione_trigger ≠ 'CONFERMATO'` → `ORDINE_FATTURA_DA_DDT`; `EXISTS` su
   `fn_list_ordini_da_pushare(p_ordine_id)` → eleggibile; ≥1 segmento
   `ORD:{uid}:R:{riga_id}` con `stato_emissione='EMESSA'` → `ORDINE_GIA_FATTURATO`;
   fallback → `ORDINE_NESSUNA_RIGA_PUSHABILE`.
5. **Capability editabilità** — da `v_stato_cod`: `can_edit_testata/righe = (stato='DRAFT')`;
   `non_editable_fields` via `CASE` con costanti PL/pgSQL.
6. **Build JSONB** — `jsonb_build_object` con tutte le chiavi.

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.ordini` | tabella | sorgente stato |
| `config.stati_doc_ordini` | tabella | risoluzione `codice_interno` e `ordine` |
| `config.transizioni_stati_ordini` | tabella | matrice metadati UI (rev 2026-06-05) |
| `vendite.fn_list_ordini_da_pushare` | funzione | eleggibilità push (riuso, no duplicazione) |
| `vendite.commesse_attivita` | tabella | predicato «già fatturato» su `segment_key`+`stato_emissione` (rev 2026-07-10) |
| `vendite.ordini_righe` | tabella | costruzione `segment_key` per il predicato «già fatturato» |
| `20260605-08-create-transizioni-stati-ordini-mctit` | migration 00_schema | crea la matrice |
| `20260605-11-seed-transizioni-stati-ordini-mctit` | migration 80_data | popola le 3 transizioni |

## Note operative

- **STABLE**: solo lettura; il pianificatore può riusare il risultato nella stessa transazione.
- **Fallback NULL**: il BE interpreta `NULL` come ordine non trovato e risponde 404.
- **Meta mancante**: se una transizione non ha `manuale` → trattata come manuale
  (`COALESCE(..., true)`). Se non ha `requires_confirm` o `outlined` → default `false`.
- **`can_conferma` deprecato**: il vecchio flag booleano del payload BE è eliminato; la
  conferma è ora una entry di `available_actions` (`key="conferma"`).
- **Enforcement separato**: questa funzione è il **lato lettura**. La validità della
  transizione all'esecuzione è garantita dal guard
  [`trgfn_ordini_guard_transizione`](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione),
  che legge la **stessa** matrice.

## Rev 2026-09-24 — «Conferma» spento finché un prezzo non è autorizzato

Regola decisa da Tid: *un prezzo che nessuno ha autorizzato non esce dalla bozza*. Un
ordine con un componente BoM **attivo** in attesa di approvazione (`PENDING`) o
**rifiutato** (`REJECTED`) non si conferma.

* **Dalla bozza**, i motivi dell'azione verso `CONFERMATO` sommano a quelli di
  [`script.fn_check_ordine_confermabile`](/dbzero/script/funzioni/fn_check_ordine_confermabile)
  i motivi di [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati). `enabled`, `reason` e `reason_key` discendono dallo stesso array.
* **Solo dalla bozza**, come la Regola 5 di
  [`vendite.trgfn_ordini_guard_transizione`](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione)
  che li solleva: il rientro in `CONFERMATO` da `EVASO` / `PARZIALMENTE_EVASO` è automatico
  e non conferma niente di nuovo. Per questo il prezzo **non** sta in
  `fn_check_ordine_confermabile`, che vale per ogni ingresso in `CONFERMATO`.

Motivi nuovi: `PREZZO_PENDENTE` / `PREZZO_RIFIUTATO`, con `reason_key`
`common.azione_reason.prezzo_pendente` / `common.azione_reason.prezzo_rifiutato`.
(changeSet `20260924-30`, brief `brief-db-preventivi-congelamento-pricing`.)

## Rev 2026-10-10 — la promessa di consegna dopo la conferma

Dopo la conferma le righe dell'ordine non si toccano più, salvo la **data di consegna
confermata**, che si sposta finché c'è merce da evadere. Il backend la cambia con un verbo
dedicato, e la terna dice quando proporlo (famiglia 1: motivo e chiave dal nome del flag).

| Stato | `can_edit_data_consegna_confermata` | `_reason` | `_reason_key` |
|---|:---:|---|---|
| `DRAFT` | `false` | `ORDINE_IN_BOZZA` | `vendite.ordini.data_consegna_confermata_reason.in_bozza` — in bozza la data si scrive modificando la riga |
| stati dell'eccezione del lock (oggi `CONFERMATO`, `PARZIALMENTE_EVASO`) | `true` | `null` | `null` |
| tutti gli altri | `false` | `STATO_NON_AMMETTE` | `vendite.ordini.data_consegna_confermata_reason.stato_non_ammette` |

⭐ Gli stati **non sono scritti qui**: li dice il montaggio del lock delle righe d'ordine,
letto da [`script.fn_check_ordine_data_consegna_confermata`](/dbzero/script/funzioni/fn_check_ordine_data_consegna_confermata).
Il flag discende dal motivo. Capability di documento, non di riga: la regola guarda solo
lo stato della testata.
(changeSet `20261010-67`, brief `brief-db-testata-dopo-emissione`, fase 1.)

## Rev 2026-10-11 — gli indirizzi (brief-db-testata-dopo-emissione §11, R-DB-3)

Nuovo `can_edit_indirizzi`: vero se gli indirizzi si possono scrivere nello stato del
documento, letto dal lock montato sui suoi indirizzi (in bozza sì, fuori no). Il backend li
rifiutava da sé fuori DRAFT: ora la regola sta nel lock.
