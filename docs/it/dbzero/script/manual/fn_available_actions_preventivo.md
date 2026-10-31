# fn_available_actions_preventivo

### Scopo

Restituisce in un **unico JSONB** tutte le capability del preventivo
necessarie al detail endpoint BE (Fase 1 refactor frontend vendite,
2026-04-30). Permette ai drawer Vue di eliminare qualsiasi ricalcolo
di stato/transizioni lato client: il FE legge il payload e renderizza
di conseguenza.

> **Vedi anche**
>
> - [fn_cambia_stato_preventivo](/dbzero/vendite/funzioni/fn_cambia_stato_preventivo) — esegue la transizione (guard reale)
> - [transizioni_stati_preventivi](/dbzero/config/tabelle/transizioni_stati_preventivi) — matrice configurabile da cui si leggono le azioni
> - [preventivi](/dbzero/vendite/tabelle/preventivi) — entità sorgente

## Schema

`script` (cross-dominio: legge `vendite.*` e `config.*`).

## Firma

```sql
script.fn_available_actions_preventivo(
    p_preventivo_id vendite.preventivi.id%TYPE  -- bigint
) RETURNS jsonb
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_preventivo_id` | `bigint` | Sì, `> 0` | ID del preventivo. Ritorna `NULL` se non esiste (gestito dal BE come 404). |

## Output

`jsonb` con le seguenti chiavi (contratto API stabile):

```jsonc
{
    // Lista azioni manuali disponibili dallo stato corrente.
    // Vuota ([]) per stati terminali (ANNULLATO, RIFIUTATO, SCADUTO).
    // Costruita dalla matrice config.transizioni_stati_preventivi.meta.
    "available_actions": [
        {
            "key": "emetti",                       // chiave semantica
            "target_state": "EMESSO",              // codice_interno stato destinazione
            "label_key": "preventivi.azione_emetti", // chiave i18n per il label bottone
            "requires_confirm": false              // se true → dialog conferma
        }
    ],
    "can_edit_testata":             true,    // true solo in DRAFT
    "can_edit_righe":               true,    // true solo in DRAFT
    "can_push_commessa":            false,   // ACCETTATO + residuo servizi (rev 12-06-2026)
    "can_push_commessa_reason":     "PREVENTIVO_NON_ACCETTATO",         // reason code machine-readable; null se can_push=true
    "can_push_commessa_reason_key": "preventivi.push_commessa_reason.non_accettato", // chiave i18n associata; null se can_push=true
    "can_genera_ordine":            false,   // ACCETTATO + residuo merce (rev 09-06-2026)
    "can_genera_ordine_reason":     "PREVENTIVO_NON_ACCETTATO",
    "can_genera_ordine_reason_key": "preventivi.genera_ordine_reason.non_accettato",
    "can_create_revisione":         false,   // true solo in EMESSO
    "non_editable_fields":          ["utility_id", "emittente_fiscale_id"],  // in bozza; vedi dettaglio sotto
    "stato_codice":                 "DRAFT"  // codice_interno stato corrente
}
```

### Coppie `can_*_reason` / `can_*_reason_key`

- **`reason`** = reason code stabile machine-readable, usato in log e da BE per logica condizionale.
- **`reason_key`** = chiave i18n pronta per `$t()` lato FE.

Le due chiavi sono sempre coerenti (entrambe `null` quando la capability è
`true`, entrambe valorizzate altrimenti). Il BE usa il reason, il FE traduce
via key.

**Reason di `can_push_commessa`** (rev 12-06-2026, brief smistamento — ordine
di verifica: fase chiusa → stato → righe, la reason racconta il primo ostacolo da
rimuovere; il ramo «testata incompleta» è stato ritirato il 2026-10-10, perché
BA e utility del preventivo sono `NOT NULL` — `brief-db-istanza-nasce-col-ba-residui` R-1):

| Reason | Key | Quando |
|---|---|---|
| `PREVENTIVO_STATO_CHIUSO` | `vendite.preventivi.push_commessa_reason.stato_chiuso` | Stato di fase `CHIUSO` (evaso, annullato, rifiutato, scaduto) |
| `PREVENTIVO_NON_ACCETTATO` | `vendite.preventivi.push_commessa_reason.non_accettato` | Non ancora ACCETTATO (bozza, emesso) |
| `PREVENTIVO_NESSUNA_RIGA_COMMESSA` | `vendite.preventivi.push_commessa_reason.nessuna_riga` | Nessun residuo servizi (nessuna riga o tutte già instradate) |

**Reason di `can_genera_ordine`** (rev 09-06-2026):

| Reason | Key | Quando |
|---|---|---|
| `PREVENTIVO_STATO_CHIUSO` | `vendite.preventivi.genera_ordine_reason.stato_chiuso` | Stato di fase `CHIUSO` |
| `PREVENTIVO_NON_ACCETTATO` | `vendite.preventivi.genera_ordine_reason.non_accettato` | Non ancora ACCETTATO |
| `PREVENTIVO_NESSUNA_RIGA_ORDINE` | `vendite.preventivi.genera_ordine_reason.nessuna_riga` | Nessun residuo merce (nessuna riga o tutte già allocate) |

### Dettaglio `non_editable_fields`

Le colonne della testata che il form non lascia cambiare **nello stato del preventivo**. Non
sono scritte nella funzione: le dice il montaggio del lock di testata
(`trg_preventivi_a05_lock_fuori_bozza_upd`), letto con
[`script.fn_doc_testata_in_stato`](/dbzero/script/funzioni/fn_doc_testata_in_stato). Così il
form e il lock che rifiuta l'aggiornamento non possono dire due cose diverse.

* **Sempre**, bozza compresa: `utility_id` ed `emittente_fiscale_id`. In bozza si cambia il
  cliente, dentro la stessa utility e dello stesso emittente.
* **Fuori bozza**: in più le colonne che il montaggio ferma in quello stato (cliente,
  identità, condizioni); `competenza_mese` e le note restano aperte in `EMESSO` e `ACCETTATO`.

`can_edit_testata` è vero se nello stato almeno una colonna del montaggio si cambia.

> Storia: fino al 2026-10-10 le liste erano scritte a mano qui (la terza copia della regola);
> fino al 2026-10-18 la funzione teneva una sua lista «sempre» con la sola `utility_id`.
> Brief: `brief-db-testata-dopo-emissione` (fase 2), `brief-db-indirizzi-documento-seguono-il-cliente` (§8.7).

### Dettaglio `available_actions` per stato

| `stato_codice` | Azioni in `available_actions` | Note |
|---|---|---|
| `DRAFT` | `emetti`, `annulla` | Da matrice transizioni |
| `EMESSO` | `accetta`, `rifiuta`, `crea_revisione` | `crea_revisione` hardcoded (rev 28-05-2026) |
| `ACCETTATO` | `push_commessa` (se residuo servizi), `genera_ordine` (se residuo merce) | Hardcoded, gate con residuo per ramo (rev 09/12-06-2026): su preventivo solo-merce appare solo `genera_ordine`, su solo-servizi solo `push_commessa` |
| `ANNULLATO` / `RIFIUTATO` / `SCADUTO` | `[]` | Terminali |

La transizione `EMESSO → SCADUTO` è **automatica** (job notturno) e
marcata `manuale=false` in `transizioni_stati_preventivi.meta`: viene
esclusa dalla lista.

Le transizioni `EMESSO → ANNULLATO` e `ACCETTATO → ANNULLATO` sono
**disattivate** (`attivo = false` in `config.transizioni_stati_preventivi`,
righe id=6 e id=7, aggiornamento 2026-05-22). L'annullamento è ammesso
solo da `DRAFT`. Razionale: un preventivo emesso si rifiuta (dal cliente)
o si fa scadere; uno accettato ha già attivato downstream (pipeline
fatturazione, push commessa).

## Algoritmo

1. **Lookup preventivo** — JOIN `vendite.preventivi` × `config.stati_doc_preventivi`
   per ottenere `stato_id` e `codice_interno`. `NOT FOUND` → `RETURN NULL`.
2. **Transizioni manuali** — `jsonb_agg` su `config.transizioni_stati_preventivi`
   filtrata per `stato_da_id = v_stato_id AND attivo IS TRUE AND manuale IS NOT FALSE`.
   I metadati UI (`label_key`, `requires_confirm`) vengono
   letti direttamente da `t.meta`; icona e colore li sceglie il frontend dal `key`. Ordine: `sa.ordine` (ordine stati config).
3. **Azioni speciali hardcoded** — aggiunte in coda a `v_actions` (pattern
   `fn_available_actions_offerta`, rev 28-05-2026):
   - `crea_revisione` se `v_stato_cod = 'EMESSO'`: `target_state null`.
   - `push_commessa` se `v_can_push` (ACCETTATO + residuo servizi).
   - `genera_ordine` se `v_can_ordine` (ACCETTATO + residuo merce).
   Il FE distingue queste azioni dal `key` e usa routing speciale nel drawer.
4. **Capability derivate**:
   - `can_edit_testata / can_edit_righe = (stato = 'DRAFT')`
   - `can_push_commessa = (stato di accettazione) AND vendite.fn_preventivo_ha_residuo_commessa(id)` *(rev 12-06-2026)*
   - `can_genera_ordine = (stato di accettazione) AND vendite.fn_preventivo_ha_residuo_ordine(id)` *(rev 09-06-2026)*
   - `can_create_revisione = (stato di emissione)`
   - Accettazione, emissione e annullo si leggono dalle colonne del vocabolario
     (`accettazione`, `emissione`, `is_abortito`), non dal codice *(rev 31-10-2026)*
   - `non_editable_fields`: dal montaggio del lock di testata, nello stato.
5. **Build JSONB** — `jsonb_build_object` con tutte le chiavi.

> **Nota** — la "Fase 3" anticipata nelle revisioni precedenti è stata
> completata (rev 12-06-2026, brief-db-smistamento-preventivi.md): entrambe
> le capability di smistamento usano il check cross-dominio con residuo via
> le funzioni `fn_preventivo_ha_residuo_*` (predicato unico condiviso con le
> viste smistabili e il Pannello Smistamento), senza modifiche al contratto API.

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.preventivi` | tabella | sorgente stato, testata (BA/utility) e ID |
| `config.stati_doc_preventivi` | tabella | risoluzione `codice_interno` |
| `config.transizioni_stati_preventivi` | tabella | matrice transizioni + meta UI |
| `vendite.fn_preventivo_ha_residuo_commessa` | funzione | gate `can_push_commessa` (rev 12-06-2026) |
| `vendite.fn_preventivo_ha_residuo_ordine` | funzione | gate `can_genera_ordine` (rev 09-06-2026) |
| `20260430-60-update-transizioni-stati-preventivi-meta-ui-mctit` | migration 80_data | popola `meta` con `label_key`/`severity`/`icon`/`manuale` |

## Note operative

- **STABLE**: solo lettura; il pianificatore può riusare il risultato
  nella stessa transazione.
- **Fallback NULL**: il BE interpreta `NULL` come preventivo non trovato
  e risponde 404 prima di serializzare il payload.
- **Meta mancante**: se una transizione non ha `manuale` in meta, viene
  trattata come manuale (`COALESCE(..., true)`). Se non ha `requires_confirm`,
  il valore default è `false`.
- **Guard meta keys (rev 11-05-2026)**: la WHERE dell'aggregazione include
  `AND t.meta ? 'action_key' AND t.meta ? 'label_key'`. Questo è un layer
  defense-in-depth rispetto al CHECK `ck_transizioni_stati_prev_meta_ui`
  sulla tabella: anche se un DBA inserisse una riga manuale con meta incompleto
  bypassando il vincolo, la funzione non la esporrebbe. Sicuro in questo
  punto perché siamo già nella branch `manuale IS TRUE` (COALESCE sopra),
  quindi le transizioni automatiche (es. EMESSO→SCADUTO con `manuale=false`)
  sono già escluse prima di questo check.

## Rev 2026-09-24 — «Accetta» spento finché un prezzo non è autorizzato

Regola decisa da Tid: *un prezzo che nessuno ha autorizzato non esce dalla bozza*. Un
preventivo con una riga o un componente BoM **attivi** in attesa di approvazione
(`PENDING`) o **rifiutati** (`REJECTED`) non si emette e non si accetta.

* Sulle azioni verso `ACCETTATO` la funzione somma i motivi di [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati), nello stesso array
  `reasons` da cui discendono `enabled`, `reason` e `reason_key`. È lo stesso building block
  che la Regola 3 di [`vendite.trgfn_preventivi_guard_transizione`](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione)
  usa per sollevare: «Accetta» e database non possono dissentire.
* Verso `EMESSO` i motivi arrivano già da
  [`script.fn_check_preventivo_emettibile`](/dbzero/script/funzioni/fn_check_preventivo_emettibile),
  che dalla stessa data li contiene (MOTIVO 2).
* **Annulla non cambia**: è la via d'uscita dell'operatore.
* `can_edit_testata` / `can_edit_righe` restano quelli di prima (`DRAFT`): il blocco sta
  sulla sola riga in attesa, dal suo guard per riga.

Motivi possibili: `PREZZO_PENDENTE` / `PREZZO_RIFIUTATO`, con `reason_key`
`common.azione_reason.prezzo_pendente` / `common.azione_reason.prezzo_rifiutato`.

⭐ Con questo il backend può togliere la sua riscrittura di `available_actions` e
`can_edit_*` in `preventivi_service.get_preventivo` (richiesta al team backend, brief
`brief-db-preventivi-congelamento-pricing` §6). (changeSet `20260924-23`.)

---

### Rev 2026-09-24 (2) — «Crea revisione» spento con un prezzo in attesa

(`20260924-36`.) L'azione `crea_revisione` resta proposta su `EMESSO`, ma è **spenta con il
motivo** (`enabled`, `reason`, `reason_key`, `reasons`) se il preventivo ha un prezzo in
attesa — [script.fn_check_prezzi_in_attesa](/dbzero/script/funzioni/fn_check_prezzi_in_attesa),
la stessa funzione con cui `fn_crea_revisione_preventivo` rifiuta. `can_create_revisione`
diventa **veritiero**: vero solo se la revisione si può davvero creare.

## Rev 2026-10-11 — gli indirizzi (brief-db-testata-dopo-emissione §11, R-DB-3)

Nuovo `can_edit_indirizzi`: vero se gli indirizzi si possono scrivere nello stato del
documento, letto dal lock montato sui suoi indirizzi (in bozza sì, fuori no). Il backend li
rifiutava da sé fuori DRAFT: ora la regola sta nel lock.
