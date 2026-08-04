# Risposta DB → BE — azioni del lotto in lista e capability

> 🟢 **CHIUSO — 2026-08-04.** Il §7 («cosa serve da voi») è stato fatto e
> validato in-app da Tid. Nota BE sui sei punti:
>
> * **1, 2, 4, 5, 6** — fatti. Le azioni di drawer e lista vivono ora in un
>   composable condiviso (`useLottoAzioni`), estratto alla seconda occorrenza.
> * **3** (`_resolve_steps_for_run` legge e azzera `riaperto_il`) — **era già
>   fatto** prima della vostra segnalazione, commit `6728e58cb` del 2026-08-03
>   (`pipeline_runner.py:541-546` + `pipeline_repository.azzera_riaperto_il`).
> * **§6.1** — avete ragione su tutti e tre i punti: la segnalazione del BE su
>   `fn_riporta_lotto_a_draft` nasceva da un albero locale indietro di due merge.
>
> Il brief di richiesta è archiviato accanto a questo documento.
>
> ---

**Chi scrive:** team DB (`dev/db-tid`), 2026-08-04.
**A chi:** BE/FE (`dev/backend-tid`).
**Riferimento:** vostro brief «azioni disponibili del lotto di fatturazione
(`fn_available_actions_lotto`)», ricevuto il 2026-08-04 — non è in repo, se lo committate
in `work-in-progress/` linkiamo · [piano-db-ritorno-lotto-a-draft](piano-db-ritorno-lotto-a-draft.md)
· [brief-be-ritorno-lotto-a-draft](brief-be-ritorno-lotto-a-draft.md).

**In una riga:** il seed è fatto, la capability c'è ed è l'ottava della famiglia, le
precondizioni dei due verbi distruttivi hanno adesso una sede sola. Il consumo **per riga
di lista** no, e sotto c'è il perché. `avanza`/`rilancia` restano vostri, per ora.

> ✅ **Tutto applicato e verde il 2026-08-04** — migrazione eseguita, pgTAP `script` e
> `vendite` senza regressioni in baseline. Dettaglio al §8; quello che serve da voi al §7.

---

## 1. Le risposte, in tabella

| § vostro | Richiesta | Risposta |
| --- | --- | --- |
| 4.4 | Riattivare `ui.lista_colonna` id 216 | ✅ **Fatto** — `attivo = t` |
| 4.1 | `fn_available_actions_lotto` | ✅ **Fatta**, consumo sul **dettaglio** (`get_lotto`), non per riga |
| 4.2 | `fn_check_lotto_annullabile` / `_riportabile_a_draft` | ✅ **Fatte**, + una terza condivisa che non avevate chiesto |
| 4.2 | `fn_check_lotto_numerabile` | ❌ **Non serve** — la matrice *è* il check (§3.4) |
| 4.2 | `fn_check_lotto_avanzabile` | ⏸️ **Non ora**, e non è un rinvio pigro (§5) |
| 4.3 | `LEFT JOIN LATERAL` per riga, o variante set-based | ❌ **No**. La riga ha già quello che serve (§3.3) |
| 8.1 | Verbi non-transizione a dato o cablati? | **Cablati**, ed è la scelta giusta (§3.4) |
| 8.2 | `blocks_next_step` scende a DB? | **Sì come direzione**, ma tutto insieme al resto del gate (§5) |
| 8.3 | La distinzione avanza/rilancio la ricostruisce il DB? | **No**, e non deve (§5) |

---

## 2. Il seed (§4.4) — fatto

`db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv`, id **216**: `attivo` da
`f` a `t`. Era l'unica riga `azioni` disattivata su **26** liste. Nessun changeSet nuovo:
il loader `20260507-07` è `runOnChange` + `validCheckSums: ANY`, cioè un mirror vivo del
CSV. Al prossimo `migrate` lo slot `#actions` di `<ListaConfigurabile>` si accende.

---

## 3. Cosa abbiamo costruito

### 3.1 — `script.fn_available_actions_lotto` (changeSet `20260804-06`)

`STABLE`, `SECURITY INVOKER`, `NULL` se il lotto non esiste. Contratto identico alle sette
sorelle, quindi `useDrawerActions` / `DrawerActionsBar` / `useEntityCapabilities` la
consumano senza adattatori.

I tre verbi di **stato** nascono data-driven da `config.stati_doc_fiscale_transizioni`,
dal `meta` seedato oggi:

| Transizione | riga CSV | `action_key` |
| --- | --- | --- |
| `EMESSA → DEFINITIVA` | 3 | `numera` |
| `EMESSA → DRAFT` | 2 | `riporta_a_draft` |
| `DRAFT → ANNULLATA` | 11 | `annulla` |

Il filtro sulla matrice è **lo stesso predicato del guard vivo**
`vendite.trgfn_fatturazione_lotti_guard_stato` (`ammesso`, `solo_fattura = false`,
`meta.tipo_lotto` compatibile). Se domani la matrice cambia, cambiano insieme il guard e i
pulsanti: non ci sono due posti da tenere allineati. È la parte del vostro §4.1 su cui
avevate ragione senza riserve.

`ristampa` è cablata, e va bene così: non è una transizione perché stampare è leggere
(I-4). Stesso trattamento di `push_commessa` in `fn_available_actions_ddt`.

### 3.2 — Le funzioni pure (changeSet `20260804-01/02/03`)

| Funzione | Verdetto | Consumatori |
| --- | --- | --- |
| `script.fn_check_lotto_fatture_pre_fiscali` | nessuna fattura oltre il pre-fiscale | le due sotto |
| `script.fn_check_lotto_annullabile` | stato `DRAFT` + fatture demolibili | `fn_annulla_lotto_da_draft` + capability |
| `script.fn_check_lotto_riportabile_a_draft` | stato pre-fiscale + fatture demolibili + nessun numero | `fn_riporta_lotto_a_draft` + capability |

La terza non era nella vostra lista ed è quella che ci interessava di più: la definizione
di «pre-fiscale» era scritta **due volte** e stava per diventare tre. Ora sta in un posto.

Le due funzioni di mutazione (`20260804-04/05`) non ricalcolano più niente: chiamano il
check e sollevano il codice del **primo** motivo, con l'elenco completo nel context.

> ⚠️ **Breaking voluto, per voi.** I codici errore diventano parlanti al posto del generico
> `E_PARAMETRO_INVALIDO`: `E_LOTTO_NON_ANNULLABILE` (798),
> `E_LOTTO_FATTURE_NON_PRE_FISCALI` (799), `E_LOTTO_NON_RIPORTABILE_A_DRAFT` (800),
> `E_LOTTO_FATTURE_NUMERATE` (801), e `E_LOTTO_NON_TROVATO` (143) al posto di
> `E_VALORE_MANCANTE`. Vanno **registrati in `error_policies.py`**. Abbiamo verificato che
> nessun `known_markers` di `pipeline_repository.py` dipendesse dai codici vecchi.

### 3.3 — Perché **non** per riga di lista (§4.3)

Non è una questione di costo, è che il pattern non esiste e non serve.

1. **Nessuna lista del progetto consuma una capability per riga.** Tutte e sette le
   `fn_available_actions_*` sono chiamate sul dettaglio, un id alla volta, via
   `call_jsonb_fn`. Il vostro `LEFT JOIN LATERAL` sarebbe il primo.
2. **La riga ha già la verità che serve.** `_LOTTO_SELECT_COLS` espone già
   `stato_doc_fiscale_codice`, `stato_lotto` e `tipo_lotto` — esattamente i tre campi su
   cui il drawer gate oggi. Il pattern della lista DDT (`buildRowActions(data)` su
   `data.stato_codice_interno`) funziona identico qui, senza contratto nuovo.
3. **Il costo c'è comunque**, e su una funzione dichiarata `STABLE` sarebbe pure una
   bugia: `fn_get_lotto_segnalazioni_summary` è `VOLATILE`.

Il click sulla riga apre il drawer, che ha il blob completo. La lista rende e naviga.

### 3.4 — Perché `numera` non ha bisogno di un `fn_check` (§4.2)

La sua unica precondizione è «lotto in EMESSA», e l'azione **nasce dalla riga di matrice
che parte da EMESSA**: se il lotto non è in quello stato l'azione non compare affatto.
`enabled` è vero per costruzione, e non esiste nessuna seconda copia da tenere allineata.
Idem per `ristampa` su `DEFINITIVA`. Aggiungere una `fn_check` lì significherebbe
riscrivere in PL/pgSQL una condizione che la matrice esprime già.

---

## 4. Il contratto, per voi

```jsonc
{
  "available_actions": [
    {
      "key":              "riporta_a_draft",
      "target_state":     "DRAFT",
      "label_key":        "vendite.lotti.azione_riporta_a_draft",
      "severity":         "warn",
      "icon":             "pi pi-undo",
      "requires_confirm": true,
      "outlined":         true,
      "enabled":          false,
      "reasons": [
        { "codice":     "E_LOTTO_FATTURE_NUMERATE",
          "reason":     "FATTURE_NUMERATE",
          "reason_key": "vendite.lotti.azione_reason.fatture_numerate",
          "dettaglio":  3 }
      ]
    }
  ],
  "can_change_state": false,
  "stato_codice":     "EMESSA",
  "tipo_lotto":       "MASSIVO"
}
```

⚠️ **`can_change_state` è calcolato sulle sole azioni ABILITATE e sulle sole transizioni**
(la ristampa non cambia stato). E vale il contratto della commessa: la presenza di
un'azione **non** significa eseguibile — leggete `enabled`, mostrate `reasons` a tooltip.

**Le chiavi i18n che dovete creare** (le etichette esistono già, sotto altri nomi):

| Nuova chiave | Testo, dalla chiave esistente |
| --- | --- |
| `vendite.lotti.azione_annulla` | `vendite.lotti.reset` → «Annulla lotto» |
| `vendite.lotti.azione_numera` | `vendite.lotti.numera` → «Rendi definitive» |
| `vendite.lotti.azione_ristampa` | `vendite.lotti.ristampa` → «Ristampa documenti» |
| `vendite.lotti.azione_riporta_a_draft` | **nuova** — «Riporta in bozza» |
| `vendite.lotti.azione_reason.stato_non_draft` | nuova |
| `vendite.lotti.azione_reason.stato_non_pre_fiscale` | nuova |
| `vendite.lotti.azione_reason.fatture_non_pre_fiscali` | nuova |
| `vendite.lotti.azione_reason.fatture_numerate` | nuova |

---

## 5. `avanza` / `rilancia`: perché restano vostri (§4.2, §8.2, §8.3)

La direzione che indicate è giusta e non la discutiamo: il gate del bottone e il gate
dell'esecuzione devono essere lo stesso codice. È **come** ci si arriva che non va.

Quel gate è fatto di tre pezzi:

| Pezzo | Dove vive oggi | Il DB lo saprebbe? |
| --- | --- | --- |
| criticità attive (`blocks_next_step`) | `lotto_segnalazioni_service` somma i conteggi | **Sì**, i conteggi sono già DB |
| esiste uno step successivo | `_resolve_steps_for_run` | in parte: il registry è DB, i rami no |
| è il rilancio dello **stesso** step (D-Q p.1) | solo il runner | **No** |

Se scendesse solo il primo pezzo, il DB avrebbe un verdetto parziale che il runner
dovrebbe comunque completare: due copie della stessa regola, cioè esattamente il difetto
che questo lavoro chiude. Per questo `fn_available_actions_lotto` **non espone**
`avanza_step` né `rilancia_step`: finché quel gate sta in Python, il DB non finge di
possederlo.

Nel frattempo il FE li gate come oggi (`isErrore` per il rilancio, permesso, criticità dal
banner). Quando vorrete farlo scendere, apriamo un brief suo: serve portare giù anche
`_resolve_steps_for_run`, e quella è una decisione sull'architettura del runner — non una
capability.

---

## 6. Due segnalazioni, per voi

1. **Il ⚠️ del vostro §3 è sbagliato su tutti e tre i punti.**
   `vendite.fn_riporta_lotto_a_draft` **è** in `migrations_v2` (`20260803-08`, `-09`,
   `-12`, più `20260803-07` per `riaperto_il`), **è** in `db/pgtap`
   (`vendite/test-riporta-lotto-a-draft-v1.sql`, plan 10) e **è** nella doc auto-generata
   (`dbzero/vendite/funzioni/fn_riporta_lotto_a_draft.md`). La slice 6-A è chiusa dal
   2026-08-03. Il verbo `riporta_a_draft` esce quindi dalle capability **abilitato**, non
   disabilitato con motivo.

2. **Quello che manca è la vostra metà, ed è bloccante.** Dal brief DB della 6-A:
   leggere `riaperto_il` in `_resolve_steps_for_run` e azzerarla all'avanzamento. Senza,
   la funzione gira ma il lotto riaperto non riparte come dovrebbe. Il changeSet
   `20260803-12` ha già tolto il pezzo peggiore (i `task_run` si chiudono ad `ANNULLATO`,
   altrimenti `fn_resolve_lotto_task_execution_mode` rispondeva `SKIP` e il rilancio
   girava a vuoto), ma `riaperto_il` resta da leggere.

---

## 7. Cosa serve da voi

1. **BE** — `get_lotto` espone il blob con `call_jsonb_fn("script.fn_available_actions_lotto", lotto_id)`;
2. **BE** — registrare i 4 codici nuovi + `E_LOTTO_NON_TROVATO` in `error_policies.py`;
3. **BE** — `_resolve_steps_for_run` legge e azzera `riaperto_il` (§6.2);
4. **FE drawer** — `DrawerActionsBar` + `mapAvailableActionsToDrawerActions`: le cinque
   `computed` di `LottoDrawer.vue:107-121` spariscono;
5. **FE lista** — `<template #actions>` con `RowActionsMenu` e `buildRowActions(data)` sui
   campi di riga (`stato_doc_fiscale_codice`, `tipo_lotto`), come `DdtSearchTable`;
6. **FE** — le 8 chiavi i18n del §4.

---

## 8. Stato — ✅ applicato e verde (2026-08-04)

**La palla è vostra**: tutto quello che serviva dal DB è in vigore.

| Changeset | Cosa | Stato |
| --- | --- | --- |
| `lista_colonna.csv` id 216 | colonna azioni attiva | ✅ applicato |
| `stati_doc_fiscale_transizioni.csv` righe 2/3/11 | `meta` dei tre verbi | ✅ applicato |
| `messaggi_errore.csv` 798-801 | 4 codici nuovi | ✅ applicato |
| `20260804-01` | `fn_check_lotto_fatture_pre_fiscali` | ✅ applicato |
| `20260804-02` | `fn_check_lotto_annullabile` | ✅ applicato |
| `20260804-03` | `fn_check_lotto_riportabile_a_draft` | ✅ applicato |
| `20260804-04` | `fn_annulla_lotto_da_draft` usa il check | ✅ applicato |
| `20260804-05` | `fn_riporta_lotto_a_draft` usa il check | ✅ applicato |
| `20260804-06` | `fn_available_actions_lotto` | ✅ applicato |
| `db/pgtap/vendite/test-available-actions-lotto-v1.sql` | `plan(12)` | ✅ verde |

**pgTAP**: suite `script` e `vendite` girate contro `scripts/pgtap-baseline.sh` —
**nessuna regressione**. Il file nuovo entra verde e i test preesistenti sui due verbi
(`test-riporta-lotto-a-draft-v1`, `test-annulla-lotto-vuoto-v1`,
`test-fatturazione-reset-lotto-draft`) restano verdi: le loro asserzioni di seed guardano
`meta->>'tipo_lotto'`, che il seed di oggi lascia `NULL`, e i loro `throws_ok` guardano
`P0001` senza inchiodarsi al codice — quindi i codici errore nuovi non li hanno toccati.

I due test che contano sono l'**11** e il **12**: verificano che dove la `fn_check` dice no,
la funzione di mutazione **sollevi**. È l'unica asserzione che si accorgerebbe di qualcuno
che un domani rimettesse una precondizione a mano dentro la mutazione — un test sul solo
jsonb resterebbe verde mentre le due metà si separano.

### Nota sulla doc auto-generata

Le pagine `dbzero/script/funzioni/fn_check_lotto_*` e `fn_available_actions_lotto` e le
pagine `dbzero/vendite/funzioni/fn_annulla_lotto_da_draft` / `fn_riporta_lotto_a_draft`
si rigenerano dal DB: prendete da lì la definizione viva, mai dagli YAML. La doc
concettuale è già scritta in `dbzero/script/manual/`.
