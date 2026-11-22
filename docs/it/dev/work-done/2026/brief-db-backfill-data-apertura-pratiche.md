# Brief DB — Backfill `data_apertura` pratiche storiche

> **Tipo**: brief DB (azione dati, NO DDL) · **Destinatario**: team DB (`dev/db-tid`)
> **Priorità**: 🟡 media · **Data**: 2026-06-29 · **Origine**: bug ordinamento lista
> pratiche per data apertura (segnalato da Tid).
>
> **Stato**: ✅ **CHIUSO 2026-06-29** (vedi §5).

---

## 5. Esito (CHIUSO 2026-06-29)

Backfill DB eseguito (no DDL, one-shot idempotente, ruolo BYPASSRLS) con
**raffinamento rispetto alla §2**: valorizzate solo le pratiche in uno stato che
**implica l'apertura** — whitelist `APERTA / SOSPESA / CHIUSA` risolta per
`codice_interno` — con `data_insert::date`. **17 pratiche** valorizzate.

Lasciate **NULL by-design**: le 17 in `BOZZA` (mai aperte) e 1 `ANNULLATA`
(ambigua, raggiungibile via BOZZA→ANNULLATA). Coerente col modello:
`data_apertura` esiste **solo da quando la pratica entra in APERTA**. Quindi la
§2 (`WHERE data_apertura IS NULL` senza filtro stato) è stata **corretta** in
fase di esecuzione con il filtro di stato.

**Verifica post**: 0 residui NULL fra le pratiche in APERTA.

**Ricorrenza chiusa**: trigger `_ins` + ramo `INSERT` della funzione
(migration **`20260613-01`**, già su `dev/db-tid`) garantiscono `data_apertura`
a ogni nascita/transizione in APERTA → nessuna nuova pratica resterà orfana.

**Follow-up residuo (merge, NON azione DB)**: portare le migration pratiche di
`dev/db-tid` (incl. `20260613-01`) su `backend-tid`/integrazione, così lo stato
del DB è riproducibile da zero ovunque. Nessuna nuova migration necessaria —
risolve la "Nota di disallineamento changelog" §1.

---

## 1. Contesto / causa radice

Nella lista gestione pratiche, ordinando per **Data apertura** le pratiche con
`data_apertura IS NULL` saltavano in cima (in DESC, `NULLS FIRST` è il default
PostgreSQL → effetto "come se fossero 99999999"). All'apertura automatica non si
vedeva perché il default ordinava su `data_insert` (mai NULL).

Indagine (DB vivo `dbdev`):

- Il modello è **già corretto per le pratiche nuove**: esistono **due trigger**
  su `pratiche.pratiche` che chiamano `pratiche.trgfn_pratiche_set_data_apertura()`:
  - `trg_pratiche_m50_set_data_apertura_upd` — `BEFORE UPDATE OF stato_id`
  - `trg_pratiche_m50_set_data_apertura_ins` — **`BEFORE INSERT`**
  La funzione (versione viva) ha il ramo `TG_OP = 'INSERT'` che valorizza
  `data_apertura := CURRENT_DATE` alla nascita diretta in APERTA. → le pratiche
  recenti hanno sempre `data_apertura` valorizzata.
- **Le pratiche storiche** (caricate **prima** dell'introduzione del trigger
  `_ins` + ramo INSERT) hanno `data_apertura IS NULL`. Sono quelle che rompono
  l'ordinamento.

**Nota di disallineamento changelog**: sul branch `dev/backend-tid` la migration
`db/changelog/migrations_v2/20_code/pratiche/20260329-12-create-trgfn-pratiche-set-data-apertura-mctit.yaml`
contiene **solo** la versione vecchia (trigger UPDATE-only, funzione senza ramo
INSERT). Il trigger `_ins` + la funzione aggiornata vivono nel DB ma **non
risultano in changelog su questo branch** (presumibilmente su `dev/db-tid` non
ancora mergiato). Da verificare/allineare il changelog perché lo stato del DB sia
riproducibile da zero.

## 2. Azione richiesta — backfill (one-shot, idempotente)

Valorizzare `data_apertura` per le pratiche storiche con NULL, usando la data di
inserimento come miglior proxy della data di apertura (le pratiche nascono APERTA,
quindi `data_insert::date ≈ data_apertura`):

```sql
UPDATE pratiche.pratiche
   SET data_apertura = data_insert::date
 WHERE data_apertura IS NULL;
```

- **Idempotente**: ri-eseguirlo non tocca le righe già valorizzate.
- **Coerente con l'immutabilità**: la funzione trigger preserva
  `data_apertura` se già valorizzata, quindi il backfill non confligge.
- ⚠️ Attenzione RLS/owner: eseguire con un ruolo che vede **tutte** le righe
  (la lettura come `zeroerp_app` senza GUC operatore mostra 0 righe — RLS).

## 3. Verifica post-backfill

```sql
SELECT count(*) FILTER (WHERE data_apertura IS NULL) AS residui_null
FROM pratiche.pratiche;   -- atteso: 0
```

## 4. Allineato lato applicativo (già fatto, branch backend-tid)

- **BE** [pratiche_repository.py]: `ORDER BY {order_col} {direction} NULLS LAST, p.id`
  — rende robusto l'ordine su colonne nullable (`data_apertura` **e**
  `data_scadenza`, opzionale per design) in entrambe le direzioni, anche per
  eventuali NULL residui/futuri.
- **FE** [stores/pratiche.js], [PraticheSearchTable.vue]: default lista →
  `data_apertura` discendente (era `data_insert`).

Con `NULLS LAST` il bug è già mitigato anche **prima** del backfill (le NULL
vanno in fondo invece che in cima); il backfill chiude il punto dando alle
storiche un valore sensato.
