# fn_generate_fatture_righe (Django)
  
## Scopo
Generare in Django le righe fattura a partire da `attivita_fatturabili` lockate sul lotto.

> ⚠️ **Il nome e` quello dell'entrypoint Python** (`pipeline_service.fn_generate_fatture_righe`),
> **non** di una funzione SQL. La funzione DB omonima **non esiste piu`**: rimossa
> il 2026-07-28 col changeset `20260728-21`.

## Contesto
La logica di `vendite.fn_generate_fatture_righe()` (funzione DB **rimossa**) e` stata portata in:
- `apps/vendite/services/fatture_righe_service.py` (`generate_fatture_righe`)
- `apps/vendite/services/pipeline_service.py` (`fn_generate_fatture_righe`)

## Input
- `lotto_id`
- `dry_run` (default `False`)

## Output
- numero righe elaborate
- aggiornamento `fattura_riga_id` e `fatturato` sulle attivita processate (se non dry-run)

## Regole
- Idempotenza per riga.
- Header fattura ottenuto via `fn_get_or_create_fattura_header`.
- Group key calcolata via servizio Python `group_attivita_fatturabili`.
- In `dry_run` conta gli elementi ma non esegue insert/update.
- Error handling centralizzato via `ErrorManager`.

### ⛔ Le TESTATE si creano PRIMA delle chiavi (2026-08-31, `I4`)

L'ordine dei passi e` diventato un **requisito**, non una comodita`: l'IVA della
riga la risolve ora `vendite.fn_resolve_iva_riga`, che vuole **cliente,
emittente e data** — tre cose che stanno sulla TESTATA. Costruire le chiavi
prima vorrebbe dire costruirle senza sapere l'IVA.
⭐ Lo scambio non costa niente: `batch_get_or_create_fattura_headers` dipende
solo da lotto e attivita`, mai dalle chiavi.

```text
1. mark RUNNING
2. group inputs (batch)
3. TESTATE  →  contesto IVA per fattura  →  risoluzione per attivita'
4. validazioni + chiavi di gruppo
5. aggregazione
6. riga_nr progressivo
7. INSERT righe + UPDATE attivita' (CTE)
```

⭐ **Una risoluzione per (fattura, articolo), non per attivita`.** La risposta
dipende da articolo, cliente, emittente e data, e dentro una fattura gli ultimi
tre sono fissi: un lotto massivo arriva a **50.000** attivita`, e senza cache
sarebbero 50.000 round-trip.

⛔ **Senza emittente ci si FERMA**, e non si scrive nulla — nemmeno le righe
gia` risolte. La funzione DB e` `SECURITY INVOKER` su una tabella con RLS: senza
contesto emittente leggerebbe zero titoli e risponderebbe con l'aliquota
ordinaria *senza sollevare*. Fermarsi a meta` lascerebbe una fattura con alcune
righe giuste e altre sbagliate, che e` peggio del rifiuto.

### Il `meta` della riga porta il PERCHE` dell'IVA

Ci finiscono **due** chiavi su dieci del composito: `iva_origine` e
`iva_titolo_id` — i fatti che nessuno puo` ricostruire dopo.
⚠️ Aliquota, natura e riferimento normativo **non si copiano**: si derivano da
`iva_id` col JOIN su `config.iva` che i repository fanno gia`. Copiarli
produrrebbe una frase che invecchia, ed e` il motivo per cui
`fatture_righe.iva_perc` e` stata tolta.

📌 Nel `meta` finisce anche la `group_key` per intero, quindi l'**atto** della
riga (`group_key.contratto_id`) e` gia` scritto oggi — prima che
`vendite.fatture_atti` sia popolata.

### ⛔ L'ordinamento delle righe e` per CODICE articolo, non per UUID

`riga_nr` discende da una chiave di ordinamento che fino al 2026-08-31 usava
`articolo_id`, cioe` un **UUID**: deterministico per la macchina, **rumore** per
chi guarda la fattura. Ora usa `catalogo.articoli.codice`.

⚠️ `codice` e non `codice_interno`, di proposito: qui l'ordinamento serve a chi
**legge il documento**, e chi legge vede il `codice`. Ne discende che rinominare
un articolo fra due rigenerazioni di un lotto in bozza **cambia l'ordine** — ⭐ ed
e` corretto che cambi, perche` il documento riflette i codici di adesso. Va detto,
o il prossimo lettore torna all'UUID credendo di riparare qualcosa.
ℹ️ Le righe senza articolo (rettifiche, oneri) restano in testa: chiave vuota.

## Dipendenze DB
- Tabelle `vendite.attivita_fatturabili`, `vendite.fatture_righe`, `vendite.fatture`.
- Funzione DB `vendite.fn_get_or_create_fattura_header(...)` per header.
- `vendite.fn_resolve_iva_riga` (l'IVA della riga) e
  `anagrafiche.fn_get_emittente_fiscale_pk` (il contesto della testata).
- ⚠️ `catalogo.articoli.codice` entra nella proiezione delle attivita` da
  fatturare per l'ordinamento leggibile.
- Vincoli di integrita`/consistenza restano in DB.

## Matrice responsabilita` (Python vs DB)
- Python: loop applicativo, costruzione metadati riga, gestione `dry_run`, policy errori.
- DB: locking/selezione dati, generazione header fattura, persistenza righe e regole di integrita`.

## Note di migrazione
- Stato attuale: migrazione logica completata lato Python (dal 2026-02-03, commit `ece04a5ff`).
- **La funzione SQL e` stata RIMOSSA** il 2026-07-28 (changeset `20260728-21`),
  insieme a `vendite.fn_group_attivita_fatturabili`.

  ⚠️ Qui prima si leggeva: *«la funzione SQL puo` restare per compatibilita`
  storica/transitoria»*. Quella frase e` costata una giornata di sviluppo DB: il
  2026-07-28 due requisiti di aggregazione (changeset `-12` e `-15`) sono stati
  scritti, testati e applicati **sulla funzione SQL**, cioe` su codice che
  nessuno esegue — senza alcun sintomo, perche` il trigger dell'importo funziona
  per qualunque scrittore. Il percorso vivo e` **solo** questo servizio Python.
  Storia completa: `docs/it/dev/work-in-progress/brief-db-ritiro-generatore-righe-fattura-sql.md`.
