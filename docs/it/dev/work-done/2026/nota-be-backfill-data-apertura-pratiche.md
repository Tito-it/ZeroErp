# Nota per il team BE — Backfill `data_apertura` pratiche storiche: NON necessario ora

> **Tipo**: nota di hand-off (decisione) · **Destinatario**: team BE · **Data**: 2026-06-29
> **Esito**: ❎ backfill **non da eseguire** al momento. Le protezioni che contano sono già attive.

---

## Decisione

Il backfill delle pratiche storiche con `data_apertura IS NULL` **non va fatto adesso**:
abbiamo **solo DB di test**, quindi quelle righe sono dati usa-e-getta. Il problema è già
neutralizzato dove conta davvero:

- **BE — ordinamento robusto**: `ORDER BY <col> <dir> NULLS LAST, id` rende l'ordine corretto
  a prescindere dai NULL (presenti o futuri) → le pratiche senza `data_apertura` finiscono in
  fondo, non più in cima.
- **DB — ricorrenza chiusa**: il trigger con ramo INSERT (`20260613-01`, **già mergiato** su
  main/Tito-dev/backend-tid) garantisce `data_apertura` a ogni nuova pratica che nasce o entra
  in `APERTA`. Nessuna pratica nuova resterà orfana.

Quindi un backfill ora sarebbe **solo cosmetico** su dati di test: non corregge un
comportamento, abbellisce righe destinate a sparire.

## Quando rivalutarlo

Su **dati reali / produzione**, se l'ordinamento per data apertura dovesse mostrare storiche
con valore mancante. In quel caso:

- valorizzare **solo** le pratiche in stato che implica l'apertura (`APERTA / SOSPESA / CHIUSA`);
  lasciare NULL by-design `BOZZA` (mai aperte) e `ANNULLATA` (ambigua);
- usare come fonte la **transizione →APERTA dal giornale di bordo** (audit append-only), **non**
  `data_insert`: quest'ultimo è un proxy valido solo per le pratiche nate già `APERTA`, sbagliato
  per quelle nate `BOZZA` e aperte in un secondo momento.

## In sintesi

Niente azione richiesta. `NULLS LAST` (BE) + trigger INSERT (DB) coprono il caso; il backfill
è un nice-to-have su dati reali, da fare con la fonte giusta (giornale), non ora su test.
