# Brief DB — DROP `uq_commesse_attivita_src_uid_partial` (constraint ridondante)

> **Tipo**: drop di unique index ridondante che rompe il pattern multi-riga
> per documento sorgente.
> **Branch**: `dev/db-tid`.
> **Autore brief**: backend agent (Tid, sessione 2026-05-10 23:00) emerso dopo
> il fix del bug `uom_id` (brief gemello).
> **Trigger**: smoke test push singolo preventivo dal pulsante "Invia a
> fatturazione" — dopo il deploy del fix `uom_id` (vedi
> `brief-db-fn-list-pushare-uom-id-mancante.md` (⚠️ documento non presente nel repo))
> emerge un secondo errore:
>
> ```text
> Errore batch segment_key=PREV:019de929-...:R:69:
> un valore chiave duplicato viola il vincolo univoco
> "uq_commesse_attivita_src_uid_partial"
> ```

## Diagnosi (da SELECT diagnostiche su DB live)

### Il constraint problematico

Su `vendite.commesse_attivita`:

```sql
CREATE UNIQUE INDEX uq_commesse_attivita_src_uid_partial
  ON vendite.commesse_attivita (sorgente_tipo_id, sorgente_uid)
  WHERE sorgente_tipo_id IS NOT NULL;
```

**Significato**: per ogni `(sorgente_tipo_id, sorgente_uid)` (es. `2,
'019de929-...'` = preventivo X) puo' esistere **una sola** riga
`commesse_attivita`. Il constraint e' partial (esclude righe con
`sorgente_tipo_id IS NULL`).

### Conflitto con il pattern multi-riga

Un preventivo con **4 righe** (PRV0000034 nel DB) deve generare **4 righe**
in `commesse_attivita`, una per ogni riga del documento, ognuna con
`segment_key` distinta (`PREV:UUID:R:67`, `PREV:UUID:R:69`,
`PREV:UUID:R:70`, `PREV:UUID:R:78`). Tutte e 4 condividerebbero la stessa
`(sorgente_tipo_id=2, sorgente_uid='019de929-...')` → constraint violato
appena si tenta di inserire la **2a riga**.

**Stato dati attuale dopo lo smoke test**:

```sql
SELECT id, commessa_id, segment_key, sorgente_tipo_id, sorgente_uid
FROM vendite.commesse_attivita
WHERE segment_key LIKE 'PREV:019de929-%';
```

Ritorna **1 sola riga** (id=99, R:67). Le altre 3 righe (R:69, R:70, R:78)
non sono state create perche' bloccate dal constraint. Il push e' uscito
in `stato="ERRORE"` con dettaglio per riga.

### Il constraint corretto sta gia' altrove

Il pattern progettuale "1 documento sorgente → 1 commessa con N righe"
e' gia' garantito dalla tabella **`vendite.commesse_sorgenti`** che
mappa "documento sorgente → commessa" con il vincolo:

```sql
CREATE UNIQUE INDEX uq_commesse_sorgenti_src_uid_ruolo
  ON vendite.commesse_sorgenti (sorgente_tipo_id, sorgente_uid, ruolo_link);
```

Questo dice: "per un documento sorgente, puo' esistere **un solo** link
con un dato `ruolo_link` (es. 'ROOT')". Quindi il link "1 documento →
1 commessa ROOT" e' gia' coperto a livello giusto (link table), non
duplicato sulle righe.

Verificato sul DB live: il preventivo PRV0000034 ha **1 riga in
`commesse_sorgenti`** (id=50, commessa_id=61, ruolo_link='ROOT'),
correttamente univoca via `uq_commesse_sorgenti_src_uid_ruolo`.

### `commesse_attivita` ha gia' il constraint giusto per le righe

```sql
CREATE UNIQUE INDEX uq_commesse_attivita_commessa_segment
  ON vendite.commesse_attivita (commessa_id, segment_key);
```

Questo e' l'unique CORRETTO sulle righe: per una data commessa, ogni
`segment_key` e' univoco. `fn_upsert_commessa_attivita` fa proprio
`ON CONFLICT (commessa_id, segment_key) DO UPDATE` — idempotenza per
riga, multi-riga per commessa. Funziona bene.

## Azione richiesta al team DB (su `dev/db-tid`)

**Drop dell'indice unique ridondante**:

```sql
DROP INDEX IF EXISTS vendite.uq_commesse_attivita_src_uid_partial;
```

In una nuova migration (numerazione successiva, mai modificare
migrations gia' mergiate). Suggerimento naming:
`YYYYMMDD-NN-drop-uq-commesse-attivita-src-uid-partial-<author>.yaml`.

### Verifiche pre-drop

Prima del drop, verificare che nessun trigger/check function dipenda
dall'indice:

```sql
-- Verifica dipendenze
SELECT * FROM pg_depend
WHERE refobjid = 'vendite.uq_commesse_attivita_src_uid_partial'::regclass;
```

Atteso: solo dipendenza dalla tabella stessa (cascading) — niente
trigger/function che cita esplicitamente l'indice. Se cosi' non fosse,
brief separato per quei consumer.

### Test pgTAP

* Smoke regressione: dopo il drop, INSERT di 2+ righe `commesse_attivita`
  con stessa `(sorgente_tipo_id, sorgente_uid)` ma `segment_key` distinte
  → tutte accettate.
* Smoke "1 link per documento" ancora rispettato: tentativo di INSERT
  in `commesse_sorgenti` con `(sorgente_tipo_id, sorgente_uid,
  ruolo_link='ROOT')` duplicata → ancora bloccato (test esistente).

## Cleanup dati post-drop — non necessario

Le 4 righe del preventivo si auto-completano al prossimo push:

* `commesse_attivita` id=99 (R:67) gia' presente: `fn_upsert_commessa_attivita`
  fa UPSERT su `(commessa_id=61, segment_key=R:67)` → UPDATE no-op se
  i dati sono uguali, altrimenti aggiornamento campi snapshot.
* `commesse_sorgenti` id=50 (ROOT): gia' linked, `link_sorgente`
  e' idempotente.
* Le 3 righe mancanti (R:69, R:70, R:78) verranno create dall'INSERT.

Niente DELETE manuale richiesto.

## Smoke post-fix

```bash
# Sul webserver, hard refresh + click "Invia a fatturazione" sul preventivo PRV0000034
# Atteso: toast verde "Push completato (log #N)", 4 righe in commesse_attivita.
```

Verifica DB:

```sql
SELECT count(*) FROM vendite.commesse_attivita
WHERE segment_key LIKE 'PREV:019de929-%';
-- Atteso: 4
```

## Perche' e' emerso solo ora?

Stesso motivo del bug `uom_id`: il batch globale `pr_run_commesse_push`
non e' mai stato eseguito su preventivi reali con > 1 riga pushable —
oppure i conflict finivano nei `result.errors[]` del handler senza
nessun consumer che li leggesse. Il pulsante UI di push singolo (PR1
2026-05-10) e' il primo consumer che amplifica gli errori al toast.

## Riferimenti

* Memoria progetto: `feedback_bug_logici_modello` — bug del modello =
  priorita' MASSIMA, segnalazione proattiva con linguaggio diretto.
* Schema: `vendite.commesse_sorgenti` (link giusto, vincolo univoco
  corretto), `vendite.commesse_attivita` (righe commessa, vincolo
  corretto su `commessa_id+segment_key`).
* Brief gemello (atterrato 2026-05-10):
  `brief-db-fn-list-pushare-uom-id-mancante.md` (⚠️ documento non presente nel repo).
* Brief gemello (atterrato 2026-05-10):
  [brief-db-fn-list-preventivi-push-singolo.md](brief-db-fn-list-preventivi-push-singolo.md).

## Note di rollback

Il drop dell'indice e' reversibile: per rollback, ricreare l'indice
con stessa definizione in una nuova migration. Nessun cliente Python
si rompe: il pattern di consumo non dipende dal constraint, anzi e'
attualmente bloccato da esso.
