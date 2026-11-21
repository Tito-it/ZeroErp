# Brief DB — Seed colonna `azioni` per la lista `vendite.ddt` (righe azioni non visibili)

> **Tipo**: brief DB (target `dev/db-tid`) · **Data**: 2026-07-11 · **Owner**: Tid
> **Stato**: ✅ ESEGUITO (seed applicato) — spostato in `work-done`.
> **Azioni DB al team DB** ([[feedback_db_actions_passaggio_team]]): seed `ui.lista_colonna`.
> **Gate**: il FE è **già pronto** (azioni di riga implementate in `DdtSearchTable`); questa
> riga di seed è l'unico prerequisito per renderle visibili
> ([[feedback_be_fe_attende_prerequisiti_db]]).

## 1. Problema

Sulla lista DDT (`vendite.ddt`, `ui.lista_definizione` id **8**) le **azioni di riga non
sono visibili** (né "Documenti PDF" né "Gestisci note").

Causa individuata in `frontend/src/core/components/ListaConfigurabile.vue`: la colonna
"Azioni" (kebab `RowActionsMenu`) è renderizzata **solo se** la config lista dichiara una
colonna con `tipo_colonna='azione'` **E** il caller fornisce lo slot `#actions`:

```js
const haAzioni = computed(() =>
  colonneRender.value.some((c) => c.tipo_colonna === 'azione') && !!slots.actions,
)
```

Il caller (`DdtSearchTable`) fornisce lo slot, ma il **seed `ui.lista_colonna` per `lista_id=8`
non ha la riga `azione`** — presente invece per tutte le liste 1–7 (incl. `vendite.ordini`
id 7 = riga 113, `vendite.offerte` id 6). Quindi `haAzioni=false` → colonna assente. Questo
nasconde anche l'azione "Gestisci note" che era già presente lato FE fin dalla prima slice.

## 2. Richiesta — 1 riga di seed

Aggiungere a `db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv` una riga
**mirror della 113 (ordini)** con `lista_id=8` (DDT). Colonne CSV:
`id,lista_id,codice,etichetta,etichetta_estesa,campo_sorgente,tipo_colonna,tipo_dato,formato,larghezza_default,ordine_default,allineamento,gruppo,gruppo_ordine,filtrabile,ordinabile,esportabile,ricercabile_full,sensibile,attivo,data_insert,user_insert,etichetta_i18n_key`

Riga ordini di riferimento (id 113):

```
113,7,azioni,Azioni,,,azione,string,,60,999,center,,99,f,f,f,f,f,t,2026-06-03 00:00:00,mctit,common.col_azioni
```

Riga DDT da aggiungere (id **148** = prossimo libero; `lista_id=8`; resto identico):

```
148,8,azioni,Azioni,,,azione,string,,60,999,center,,99,f,f,f,f,f,t,2026-07-11 00:00:00,mctit,common.col_azioni
```

Il loader `ui.lista_colonna` è `loadUpdateData` idempotente per `id` → aggiungere la riga al
CSV (e, se il loader elenca le colonne, nessuna variazione: le colonne sono le stesse).
i18n `common.col_azioni` già esistente (usata dalle altre 7 liste).

## 3. Recepimento a valle (FE)

**Nessuna modifica FE**: `DdtSearchTable.vue` ha già `<template #actions>` +
`buildRowActions` (Documenti PDF + Gestisci note, gemelli offerte/contratti). Appena la
colonna `azione` è seedata, il kebab compare in automatico.

## 4. Note

- **pgTAP/verifica**: `ui.lista_colonna` per `lista_id=8` contiene esattamente una riga
  `tipo_colonna='azione'` (come le liste 1–7).
- Doc auto-gen `dbzero`: nessun impatto (solo dato di seed).
