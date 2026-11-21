# Brief DB — pulizia flussi "generici" legacy (template_flusso_id NULL)

**Area:** `pratiche` · **Tipo:** pulizia dati (+ eventuale vincolo NOT NULL)
**Branch destinazione:** `dev/db-tid`
**Richiesto da:** backend agent (per conto di Tid) · **Data:** 2026-06-14
**Stato:** ✅ **CHIUSO (2026-06-15)** — guard forward BE (`crea_flusso` esige `template_flusso_id`)
in `c4ad07b4b`; pulizia dati + `template_flusso_id NOT NULL` applicati dal DB in `fbed7dc9f`.

> Nota: questo brief descrive **cosa** deve garantire/pulire il DB, non **come**.
> La scelta implementativa (SQL, fasi, eventuale migration, nome del vincolo) è
> competenza del team DB. Le azioni DB non vengono eseguite dal backend agent.

---

## 1. Contesto

Nel modello workflow v2 ogni flusso è **template-driven**: nasce sempre da un
template del percorso (FE `PraticaPercorso`) oppure dall'auto-generazione
cross-pratica (`fn_genera_pratica_da_flusso`, che inserisce sempre con un
`template_flusso_dest` non-null). Il vecchio "flusso generico" creato senza
template è stato **rimosso**:

- **FE**: rimossa la generazione del flusso generico dalla dashboard pratiche.
- **BE** (2026-06-14): `pratiche_service.crea_flusso` ora rende
  `template_flusso_id` **obbligatorio** (`E_FLUSSO_VALIDATION` se assente/non
  valido); l'endpoint `POST /api/v1/pratiche/<id>/flussi/` non accetta più la
  creazione senza template. Il path morto è chiuso lato codice.

Restano **possibili** righe legacy in `pratiche.flussi` con `template_flusso_id
IS NULL`, create in dev dalla vecchia logica. Non sono verificabili dal backend
agent (RLS in lettura), quindi serve l'intervento del team DB.

## 2. Cosa serve

### 2.1 Diagnostica (read-only, prima di tutto)

Contare/elencare i flussi senza template, per capire se e quanti esistono:

```sql
SELECT id, pratica_id, stato_id, data_insert, user_insert
  FROM pratiche.flussi
 WHERE template_flusso_id IS NULL
 ORDER BY data_insert;
```

Se il risultato è vuoto → non c'è nulla da pulire: passare direttamente a §2.3.

### 2.2 Pulizia (solo se §2.1 trova righe)

Eliminare i flussi legacy senza template. Attenzione alle dipendenze:

- **Giornale**: i flussi hanno righe collegate in `pratiche.giornale` (eventi
  `FLUSSO_CREATO`/`FLUSSO_STATO_CAMBIATO`). Decidere se ripulire anche quelle o
  lasciarle (audit). Da concordare.
- **Flussi figli/generazione**: verificare che nessun flusso legacy sia
  `flusso_origine_id`/`flusso_padre_id` di pratiche generate (improbabile, perché
  i generici non avevano regole di generazione, ma da controllare).
- **Sospensioni**: `pratiche.sospensioni.flusso_id` eventualmente collegate.

Trattandosi di **ambiente dev**, valutare se è più rapido un `DELETE` mirato o un
reseed. La scelta sta a Tid / team DB.

### 2.3 Difesa a regime (concentrico, da valutare)

A path morto chiuso lato codice, valutare di rendere
`pratiche.flussi.template_flusso_id` **NOT NULL** così l'invariante è garantita
anche contro INSERT diretti/batch:

- Prerequisito: §2.2 completata (nessuna riga NULL residua), altrimenti il vincolo
  fallisce.
- Verificare che **nessun** path DB inserisca flussi senza template
  (`fn_genera_pratica_da_flusso` è già a posto: inserisce sempre con
  `template_flusso_dest`).
- `trgfn_flussi_generazione` ha un ramo `IF NEW.template_flusso_id IS NULL THEN
  RETURN` (no-op difensivo): con la colonna NOT NULL diventa morto ma innocuo;
  può restare o essere semplificato.

Se si preferisce mantenere la colonna NULLABLE come scelta concentrica (futuri
flussi ad-hoc senza template), **non** applicare il NOT NULL: in tal caso la
difesa resta solo il guard applicativo lato `crea_flusso`. Decisione corrente di
Tid: chiudere il path (guard BE fatto); il NOT NULL è opzionale e demandato al
team DB dopo la pulizia.

## 3. Output atteso dal team DB

1. Esito della diagnostica §2.1 (quante righe legacy).
2. Pulizia applicata (se necessaria) con nota su giornale/sospensioni collegati.
3. Decisione su NOT NULL (applicato / rinviato) con eventuale migration.
