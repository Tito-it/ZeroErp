# Brief DB — `script.fn_available_actions_offerta`

> **Stato**: ✅ **CHIUSO** — fn applicata al DB 2026-05-26
> (migration `20260526-01-create-fn-available-actions-offerta-mctit.yaml`).
> Seed `stati_doc_offerte_transizioni.csv` aggiornato con
> `requires_motivazione` su transizioni manuali, severity corretti
> (success su `emetti`, `requires_confirm: true` su `accetta`).
> 9 test pgTAP `test-fn-available-actions-offerta-v1.sql` passati.
> Doc manuale DB `fn_available_actions_offerta.md` creata.
>
> **Cablaggio applicativo eseguito in giornata 2026-05-26**:
>
> - BE: `repo.get_available_actions` wrapper + merge in `get_offerta`;
>   estesi `crea_offerta`/`aggiorna_offerta` con sub-oggetto `utility`
>   inline atomico; SELECT con alias `billing_account_display` /
>   `utility_display` + LEFT JOIN `vendite.contratti` per
>   `contratto_id`/`contratto_numero`. Suite test 38 → 42.
> - FE: `OffertaDrawer.vue` refactor data-driven con
>   `useEntityCapabilities` + `mapAvailableActionsToDrawerActions`,
>   dispatch unico `onActionDispatch(action.key)`. Rimossi
>   `isBozza`/`isEmessa`/`isAccettata` hardcoded e tutto il computed
>   `drawerActions` di stato-machine. Dialog parlante
>   `E_OFFERTA_CONTRATTO_GIA_GENERATO` con link al contratto esistente.
>   Deep-link `/vendite/contratti?open=<id>` post-push.
>
> **Owner concettuale**: Tid (Michele Carlo Titini).
> **Data brief**: 2026-05-25. **Data consegna DB + cablaggio**: 2026-05-26.
>
> **Sorgente di contesto**:
>
> - [analisi-offerta-commerciale-be-fe.md](analisi-offerta-commerciale-be-fe.md) §8 (cantiere FE)
> - [analisi-offerta-commerciale-db.md](analisi-offerta-commerciale-db.md) §8 (suite pgTAP completa, step 1-9 chiusi)
>
> **Modelli di riferimento già implementati**:
>
> - [`script.fn_available_actions_contratto`](../../dbzero/script/manual/fn_available_actions_contratto.md) — pattern azioni hardcoded + meta da `config.stati_doc_contratti.meta`
> - [`script.fn_available_actions_preventivo`](../../dbzero/script/manual/fn_available_actions_preventivo.md) — pattern matrice `config.transizioni_stati_preventivi`
>
> **Cosa NON è questo documento**: non riformula la state machine offerta
> (decisa in `analisi-offerta-commerciale.md` §5 + addendum §A2). Non aggiunge
> tabelle: la funzione è solo lettura.

---

## 1. Inquadramento

Il dominio offerta commerciale è lato BE/DB completo (rev. f del piano BE+FE,
2026-05-25). Manca solo l'allineamento al **pattern data-driven capability
layer** già adottato da contratti e preventivi: i drawer Vue NON devono
ricalcolare lo stato lato client, ma leggere `available_actions` +
`can_edit_*` + `non_editable_fields` dal payload del detail endpoint.

Oggi il dettaglio offerta espone:

```jsonc
{
  "id": 42, "codice": "OFC-0000042", "stato_codice_interno": "BOZZA",
  "stato_descrizione": "Bozza", "...": "...",
  "eccezioni": [...], "utility": {...}
}
```

Manca:

```jsonc
{
  "available_actions": [...],   // ← da popolare
  "can_edit_testata": true,     // ← da popolare
  "can_edit_eccezioni": true,   // ← da popolare
  "can_create_revisione": false, // ← da popolare
  "can_push_contratto": false,  // ← da popolare
  "non_editable_fields": [...]  // ← da popolare
}
```

Senza questi metadata il drawer FE codifica la state machine localmente (oggi
`OffertaDrawer.vue` ha un `computed drawerActions` con switch sui 6 stati).
Funziona, ma viola il pattern "una sola definizione della state machine in DB"
(rispettato da contratti/preventivi).

## 2. Cosa serve

### 2.1 Una sola funzione nuova

**Firma:**

```sql
script.fn_available_actions_offerta(
    p_offerta_id vendite.offerte_commerciali.id%TYPE  -- bigint
) RETURNS jsonb
```

Mirror strutturale di `script.fn_available_actions_preventivo` (matrice
configurabile via `config.stati_doc_offerte_transizioni`, già seedata nello
Step 4 del brief DB offerta).

**Comportamento:**

- Se `p_offerta_id` non esiste → `RETURN NULL` (il BE lo mappa come 404,
  pattern uniforme alle altre due fn).
- Altrimenti ritorna un singolo `jsonb` con la struttura completa.

### 2.2 Output `jsonb` — contratto API

```jsonc
{
  "available_actions": [
    {
      "key": "emetti",
      "target_state": "EMESSA",
      "label_key": "vendite.offerte.azione_emetti",
      "severity": "success",
      "icon": "pi pi-send",
      "requires_confirm": true,
      "requires_motivazione": false
    }
    // ...
  ],
  "can_change_state":     true,      // true se esiste almeno un'azione
  "can_edit_testata":     true,      // true solo in BOZZA
  "can_edit_eccezioni":   true,      // true solo in BOZZA
  "can_edit_utility":     true,      // true solo in BOZZA (1:1 inline editabile come la testata)
  "can_create_revisione": false,     // true solo in EMESSA
  "can_push_contratto":   false,     // true solo in ACCETTATA + nessun contratto gia' generato
  "can_push_contratto_reason":     null,  // reason code machine-readable se can_push=false (vedi 2.4)
  "can_push_contratto_reason_key": null,  // chiave i18n associata se can_push=false
  "non_editable_fields":  [],        // vedi 2.5
  "stato_codice":         "BOZZA"
}
```

### 2.3 Matrice `available_actions` per stato

Coerente con la state machine asimmetrica decisa nell'addendum §A2 (6 stati:
`BOZZA`, `EMESSA`, `ACCETTATA`, `RIFIUTATA`, `ANNULLATA`, `SUPERATA`).

| `stato_codice` | Azione               | `target_state` | `requires_confirm` | `requires_motivazione` | Note |
|----------------|----------------------|----------------|--------------------|-----------------------|------|
| `BOZZA`        | `emetti`             | `EMESSA`       | `true`             | `false`               | severity=success, icon=`pi pi-send` |
| `BOZZA`        | `annulla`            | `ANNULLATA`    | `true`             | `true`                | severity=danger, icon=`pi pi-ban` |
| `EMESSA`       | `accetta`            | `ACCETTATA`    | `true`             | `false`               | severity=success, icon=`pi pi-check` |
| `EMESSA`       | `rifiuta`            | `RIFIUTATA`    | `true`             | `true`                | severity=danger, icon=`pi pi-times` |
| `EMESSA`       | `crea_revisione`     | `(speciale)`   | `true`             | `false`               | non e' un cambio stato: produce rev.N+1 BOZZA; severity=info, icon=`pi pi-clone`. Vedi §2.6 |
| `ACCETTATA`    | `push_contratto`     | `(speciale)`   | `true`             | `false`               | non e' un cambio stato: genera contratto DRAFT. severity=success, icon=`pi pi-arrow-right`. Vedi §2.6 |
| `RIFIUTATA`    | — | — | — | — | `available_actions = []` (terminale) |
| `ANNULLATA`    | — | — | — | — | `available_actions = []` (terminale) |
| `SUPERATA`     | — | — | — | — | `available_actions = []` (terminale, sostituita da rev.N+1) |

**Chiavi `label_key` i18n** (già esistenti in `frontend/src/locales/it.json` →
`vendite.offerte.*`):

| Azione           | `label_key` |
|------------------|---|
| `emetti`         | `vendite.offerte.azione_emetti` |
| `annulla`        | `vendite.offerte.azione_annulla` |
| `accetta`        | `vendite.offerte.azione_accetta` |
| `rifiuta`        | `vendite.offerte.azione_rifiuta` |
| `crea_revisione` | `vendite.offerte.azione_crea_revisione` |
| `push_contratto` | `vendite.offerte.azione_push_contratto` |

### 2.4 Logica `can_push_contratto` + reason

Analoga a `can_push_commessa` dei preventivi. Coppia stabile:

| Caso | `can_push_contratto` | `can_push_contratto_reason` | `can_push_contratto_reason_key` |
|------|----------------------|------------------------------|--------------------------------|
| Offerta in `ACCETTATA` **e** nessun contratto già generato | `true` | `null` | `null` |
| Offerta in `ACCETTATA` **ma** esiste già `vendite.contratti.offerta_id = p_offerta_id` | `false` | `'OFFERTA_CONTRATTO_GIA_GENERATO'` | `'vendite.offerte.push_reason.gia_generato'` |
| Offerta non in `ACCETTATA` | `false` | `'OFFERTA_NON_ACCETTATA'` | `'vendite.offerte.push_reason.non_accettata'` |

**Implementazione**: subquery `EXISTS (SELECT 1 FROM vendite.contratti WHERE
offerta_id = p_offerta_id)` dentro la fn. Single point: il guard idempotenza
Pattern A è già in `vendite.fn_push_offerta_a_contratto` (UNIQUE
`uq_contratti_offerta_id`); qui calcoliamo solo l'abilitabilità lato UI.

### 2.5 `non_editable_fields`

Specchio del piano BE+FE (editabilita' solo in BOZZA per testata + utility 1:1 +
eccezioni). Due famiglie:

| Famiglia | Campi | Sempre? |
|---|---|---|
| Sempre immutabili (regola di dominio) | `codice`, `uid`, `revisione_numero`, `revisione_padre_id`, `stato_doc_offerta_id`, `data_emissione`, `data_accettazione`, `data_rifiuto`, `data_annullamento`, `motivazione_rifiuto` | sì, sempre (gestiti da trigger DB di transizione) |
| Bloccati fuori BOZZA | tutti gli altri campi testata: `emittente_fiscale_id`, `billing_account_id`, `istanza_utility_id`, `utility_id`, `listino_id`, `listino_versione_id`, `valore_variazione_globale`, `tipo_variazione_globale`, `validita_dal`, `validita_al`, `meta` | solo se `stato != 'BOZZA'` |

In `BOZZA` ritorna solo i campi della prima famiglia (sempre immutabili).
Negli altri stati ritorna l'unione (TUTTI i campi testata sono bloccati).

### 2.6 Azioni "speciali" non-cambio-stato

`crea_revisione` e `push_contratto` non sono transizioni di stato dell'offerta
corrente: producono un secondo oggetto.

- `crea_revisione`: chiama `vendite.fn_crea_revisione_offerta(p_offerta_id,
  p_user)`. La rev.N corrente passa a `SUPERATA` via trigger; la rev.N+1 nasce
  in `BOZZA`. → `target_state = null` o `target_state = "(REVISIONE)"`
  (convenzione FE: il drawer riceve il dettaglio della nuova rev e ci naviga).
- `push_contratto`: chiama `vendite.fn_push_offerta_a_contratto(p_offerta_id,
  p_pratica_id)`. L'offerta resta in `ACCETTATA`, nasce un contratto in `DRAFT`.
  → stessa convenzione `target_state` "speciale".

**Convenzione richiesta**: nel `jsonb` ritornare `target_state: null` per queste
azioni. Il FE le distingue dal `key` (`crea_revisione` e `push_contratto` sono
routing speciali; le altre 4 sono cambi stato semplici).

### 2.7 Dove leggere il meta delle azioni (raccomandazione)

Il pattern preventivo legge le azioni dalla matrice
`config.transizioni_stati_preventivi.meta`. Quello contratto le ha hardcoded
nella fn perche' i contratti non hanno tabella transizioni.

L'offerta **ha già** `config.stati_doc_offerte_transizioni` (creata Step 4 del
brief DB, migration `20260524-21`, seed `20260524-22`). **Suggerimento**: come
fa il preventivo, leggere il meta direttamente dalle righe della tabella
transizioni — single source of truth, niente magic strings nella fn.

Le due azioni "speciali" (`crea_revisione`, `push_contratto`) **non** stanno in
quella tabella (non sono cambi stato): vanno aggiunte hardcoded nella fn,
condizionate al `stato_codice` corrente. Equivalente a come
`fn_available_actions_preventivo` aggiunge `crea_revisione`.

Se questo richiede di estendere il seed `config.stati_doc_offerte_transizioni`
con righe meta per `emetti`/`annulla`/`accetta`/`rifiuta` (campi
`outgoing_action`, `label_key`, `severity`, `icon`,
`requires_confirm`, `requires_motivazione`), va bene — è lo schema del
preventivo. Vedi `config.transizioni_stati_preventivi.meta` come template.

## 3. Cosa NON cambia

- **State machine guard**: resta in
  `trgfn_offerte_commerciali_guard_transizione` (BEFORE UPDATE). Questa fn e'
  pura lettura: NON modifica stati, NON solleva errori (al massimo ritorna
  `NULL` su offerta inesistente).
- **Idempotenza push**: resta su `vendite.fn_push_offerta_a_contratto`
  (UNIQUE `uq_contratti_offerta_id`). Qui calcoliamo solo `can_push_contratto`.
- **Codici errore**: nessun nuovo codice. La fn non solleva.
- **Test pgTAP**: aggiungere casi a `db/pgtap/script/` o
  `db/pgtap/vendite/offerte_commerciali/` (a scelta del team DB):
  - offerta inesistente → `IS NULL`
  - offerta BOZZA → `available_actions` contiene `emetti` + `annulla`,
    `can_edit_testata=true`, `non_editable_fields` = lista corta
  - offerta EMESSA → 3 azioni (`accetta`/`rifiuta`/`crea_revisione`),
    `can_edit_testata=false`, `non_editable_fields` = lista lunga
  - offerta ACCETTATA + senza contratto generato →
    `available_actions=[push_contratto]`, `can_push_contratto=true`,
    `reason=null`
  - offerta ACCETTATA + contratto già generato →
    `available_actions=[]`, `can_push_contratto=false`,
    `reason='OFFERTA_CONTRATTO_GIA_GENERATO'`
  - offerta RIFIUTATA/ANNULLATA/SUPERATA → `available_actions=[]`,
    tutti i `can_*=false`, `non_editable_fields` = lista lunga

## 4. Integrazione lato BE (post-consegna)

Dopo che la fn è applicata su `dev/db-tid`, il backend agente cabla:

- `offerte_repository.py` → metodo `get_available_actions(offerta_id)` che chiama
  `SELECT script.fn_available_actions_offerta(%s)` con `call_jsonb_fn` (helper
  già usato per contratto/preventivo).
- `offerte_service.py` → `get_offerta()` arricchisce il dettaglio con il blob
  capability (mirror `contratti_service.get_contratto` post-Fase 1.B2).
- `OffertaDrawer.vue` → sostituisce il `computed drawerActions` hardcoded con
  `mapAvailableActionsToDrawerActions({ availableActions, t, onAction })`. È una
  sostituzione **additiva**, niente refactor strutturale.

Lo `useEntityCapabilities` (composable centralizzato già in uso per contratti
+ preventivi) accetta `editFlag` parametrizzabile: per l'offerta useremo
`editFlag: 'can_edit_testata'` come per il contratto. Niente lavoro nuovo lato
core FE.

## 5. Sequenza

I 5 punti seguenti sono indipendenti:

1. Aggiungere meta in `config.stati_doc_offerte_transizioni` (o equivalente,
   vedi §2.7) per `emetti`/`annulla`/`accetta`/`rifiuta`. Migration nuova,
   numerazione successiva all'ultima (per esempio `20260526-01`).
2. Implementare `script.fn_available_actions_offerta` (`runOnChange: true`).
   Migration nuova.
3. Test pgTAP (vedi §3 bullet finale).
4. Verifica `make db-migrate` locale.
5. Push su `dev/db-tid` + PR verso `Tito-dev`.

Nessun blocco lato BE/FE: il drawer corrente funziona con state machine
codificata FE. La consegna di questa fn permette solo di rimuovere quel
computed e allineare l'offerta al pattern data-driven.

## 6. Cosa NON includere in questo brief

- **Pacchetto commerciale multi-contratto** (predisposto in §5.1-bis del
  modello, non v1).
- **Job notturno scadenza offerte**: la scadenza è attributo calcolato
  (`validita_al < today`), nessun job che muta `stato_doc_offerta_id`.
- **Note offerta**: il cablaggio del building block `PartitionedNoteRepository`
  per `target_tipo='OFFERTA'` è competenza BE (Django), non DB. La tabella
  `vendite.note_offerte_commerciali` esiste già (Step 3 brief DB,
  `20260524-07`).

---

*Brief DB Offerta — fn_available_actions. Pronto per il team DB su
`dev/db-tid`. Quando la fn è applicata + testata, il backend cabla in
giornata (refactor additivo, ~50 righe BE + ~30 FE per drop del computed).*
