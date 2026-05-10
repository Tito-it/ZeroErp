# Brief DB — Bug `fn_available_actions_preventivo`: meta delle transizioni manuali persi (null)

> **Tipo**: bug logico DB function. Causa crash render UI quando il
> preventivo e' in stato `ACCETTATO`.
> **Branch**: `dev/db-tid`.
> **Autore brief**: backend agent (Tid, sessione 2026-05-11 00:30) emerso
> dopo il seed del nuovo stato `EVASO` + transizione automatica
> ACCETTATO→EVASO con `meta={"manuale": false}`.
> **Trigger**: aprire un preventivo `ACCETTATO` nell'UI →
> `[Vue warn] Unhandled error during execution of render function ... SyntaxError: Invalid arguments` da `t()` di vue-i18n,
> drawer renderizzato vuoto.

## Diagnosi (da SELECT diagnostica su DB live)

`script.fn_available_actions_preventivo(104)` per il preventivo
PRV0000034 (stato `ACCETTATO`) ritorna:

```json
{
  "stato_codice": "ACCETTATO",
  "can_edit_righe": false,
  "can_edit_testata": false,
  "available_actions": [
    {
      "key": null,
      "icon": null,
      "severity": null,
      "label_key": null,
      "target_state": "ANNULLATO",
      "requires_confirm": false
    }
  ],
  "can_push_commessa": true,
  ...
}
```

**Atteso**: una sola azione manuale (ACCETTATO → ANNULLATO, transizione
id=7) con i campi popolati dal `meta` JSONB della riga `transizioni_stati_preventivi`:

```text
meta = {
  "icon": "pi pi-times",
  "manuale": true,
  "severity": "danger",
  "label_key": "preventivi.azione_annulla",
  "action_key": "annulla",
  "requires_confirm": true
}
```

**Effettivo**: `target_state` corretto ("ANNULLATO") ma tutti gli altri
campi `null`. Il `meta` non viene letto/estratto dalla fn DB. Inoltre
la transizione **automatica** ACCETTATO → EVASO (id appena seedato con
`meta={"manuale": false}`) **non dovrebbe comparire** in
`available_actions` (le azioni manuali sono solo per UI button), ma in
realta' la fn ritorna comunque 1 sola azione → puo' essere che la fn
filtri "una transizione qualsiasi in uscita dallo stato corrente" senza
distinguere manuale/auto, e ritorni solo la prima (ANNULLATO).

## Sospetti tecnici (da verificare lato team DB)

* La fn potrebbe leggere campi che non esistono come colonne
  (`label_key`, `icon`, `severity`, `action_key`) invece di
  `meta->>'label_key'` ecc. → tutti i valori risultano NULL.
* Filtro mancante `WHERE meta->>'manuale' = 'true'` (la transizione
  auto verso EVASO non andrebbe inclusa, ma comunque le altre dovrebbero
  avere i campi popolati).
* Possibile regressione introdotta nel seed odierno (`EVASO`): se il
  team DB ha aggiornato `fn_available_actions_preventivo` insieme al
  seed e ha cambiato la struttura della query, ha rotto la proiezione
  dei campi `meta`.

## Azione richiesta al team DB (su `dev/db-tid`)

1. **Verifica** definizione attuale di `script.fn_available_actions_preventivo`
   (likely `pg_get_functiondef`).
2. **Correggere** la proiezione dei campi `available_actions[]` per
   leggere correttamente da `transizioni_stati_preventivi.meta`:
   ```sql
   jsonb_build_object(
     'key',             t.meta->>'action_key',
     'icon',            t.meta->>'icon',
     'severity',        t.meta->>'severity',
     'label_key',       t.meta->>'label_key',
     'target_state',    sa.codice_interno,
     'requires_confirm', COALESCE((t.meta->>'requires_confirm')::boolean, FALSE)
   )
   ```
   (Pseudo-codice — il team DB conosce la struttura interna della fn.)
3. **Filtro `manuale`**: includere in `available_actions` solo le
   transizioni con `meta->>'manuale' = 'true'`. Le transizioni
   automatiche (ACCETTATO→EVASO) non sono pulsanti UI, vengono
   scatenate dal codice BE Python (`preventivi_service.push_a_commessa`).

## Test pgTAP

* `fn_available_actions_preventivo(<preventivo ACCETTATO>)` ritorna
  azioni con `key`, `icon`, `severity`, `label_key` **tutti
  valorizzati** (ANNULLATO action).
* `fn_available_actions_preventivo(<preventivo DRAFT>)` ritorna 2 azioni
  manuali (`emetti`, `annulla`) entrambe valorizzate.
* Nessuna `available_actions` ha `meta->>'manuale' = 'false'`
  (transizioni auto sono escluse dalla UI).

## Smoke post-fix DB

```bash
# Sul webserver, niente da fare lato BE/FE (le mitigazioni FE difensive
# restano per robustezza, vedi sotto).
# Test: apri drawer preventivo ACCETTATO → vedi pulsante "Annulla" rosso
# (severity=danger, icon=pi pi-times). Niente warning Vue in console.
```

## Mitigazione FE gia' applicata (sessione 2026-05-11)

Il composable `useEntityCapabilities` ([useEntityCapabilities.js](../../../../frontend/src/core/composables/useEntityCapabilities.js))
ora **filtra le azioni con `label_key` mancante**:

```js
const availableActions = computed(() => {
  const raw = detailRef.value?.available_actions || []
  return raw.filter((a) => a && typeof a.label_key === 'string' && a.label_key)
})
```

Defense-in-depth: anche dopo il fix DB, se in futuro un'azione viene
fornita con `label_key` mancante (es. nuovo seed mal formato),
l'interfaccia non crasha — l'azione semplicemente non viene
renderizzata come pulsante.

## Riferimenti

* Memoria progetto: `feedback_bug_logici_modello` — bug del modello =
  priorita' MASSIMA, segnalazione proattiva.
* Brief gemello: [brief-db-stato-preventivo-evaso.md](brief-db-stato-preventivo-evaso.md)
  (introduzione stato EVASO + transizione auto ACCETTATO→EVASO).
* Stack trace browser: `vue-i18n.mjs:570 → core-base.mjs:1476 → PreventiviDrawer.vue:694 t(action.label_key)`.

## Note di rollback

La fn DB e' modificata in place via migration `runOnChange: true` o
nuova versione. Rollback = ripristinare la versione precedente. La
mitigazione FE non va rimossa anche dopo il fix DB: difesa permanente
contro regressioni future.
