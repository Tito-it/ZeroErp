# Brief DB — Race sul progressivo `segment_key` degli oneri manuali

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` · **Data**:
> 2026-07-23 · **Owner**: Tid · **Stato**: ☐ **DA REALIZZARE** · **Priorità**: 🔴 ALTA
> (perdita silenziosa di dati con due operatori concorrenti — entrambe le
> chiamate rispondono 200 OK).
>
> **Perimetro**: SOLO DB — `vendite.fn_aggiungi_onere_commessa`. Nessuna
> modifica BE/FE richiesta (il service `aggiungi_onere_commessa` è un wrapper
> 1:1 della madre e non deve cambiare).
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]])
> → fix restrittivo da subito, nessuna compatibilità.
> **Origine**: review critica 2026-07-23 della porta oneri
> ([brief-be-fe-immutabilita-quantita-e-porta-oneri.md](brief-be-fe-immutabilita-quantita-e-porta-oneri.md), step A1).

---

## 1. Problema

`vendite.fn_aggiungi_onere_commessa` calcola il progressivo della chiave con
un conteggio **senza lock** (righe 87–96 della doc auto-gen):

```sql
SELECT count(*) + 1 INTO v_progressivo
  FROM vendite.commesse_attivita ca
 WHERE ca.commessa_id = p_commessa_id
   AND ca.segment_key LIKE 'MAN:%';

v_segment_key := format('MAN:%s:%s', p_commessa_id, v_progressivo);
```

Due chiamate concorrenti sulla stessa commessa (due operatori, oppure un retry
di rete con Idempotency-Key **diverse**) leggono lo stesso `count` e producono
entrambe `MAN:<commessa>:<n>`. La riga passa poi da
`fn_upsert_commessa_attivita`, che fa **upsert sulla chiave naturale**
`(commessa_id, segment_key)`: la seconda chiamata **aggiorna la riga della
prima invece di crearne una nuova**.

**Effetto**: un onere sparisce in silenzio — entrambe le chiamate tornano
200 con lo **stesso** `attivita_id`, e `commesse_attivita_log` registra due
`ONERE_AGGIUNTO` sulla stessa riga. Nessun errore da nessuna parte.

La porta manuale è il **primo scrittore concorrente reale** di questa fn: i
push sorgente serializzano per costruzione (worker singolo), gli operatori no.

## 2. Richiesta

Rendere il progressivo sicuro sotto concorrenza. Due opzioni, in ordine di
preferenza:

1. **Advisory lock transazionale per commessa** prima del conteggio:

   ```sql
   PERFORM pg_advisory_xact_lock(hashtextextended('onere:' || p_commessa_id, 0));
   ```

   Serializza solo gli oneri della **stessa** commessa (commesse diverse non
   si bloccano tra loro), si rilascia da solo a fine transazione, zero oggetti
   nuovi. Il `count(*)+1` sotto lock diventa corretto.

2. In alternativa, progressivo da **sequence** dedicata (o `max(...)+1` con
   lock) — più invasivo (oggetto nuovo, buchi nei progressivi ammessi da
   dichiarare) e non necessario se l'opzione 1 basta.

Da valutare del team: se la collisione debba anche essere **impedita a valle**
(la fn upsert accetta l'update di una riga `MAN:%` esistente — per la porta
manuale un "update" non è mai legittimo: ogni chiamata è un onere NUOVO).
Un guard `E_ONERE_SEGMENT_DUPLICATO` sull'esito `updated` della upsert
trasformerebbe qualunque futura regressione da perdita silenziosa a errore
parlante (difesa in profondità, coerente con [[feedback_concentrico_no_yagni]]).

## 3. Accettazione

- pgTAP: due insert nella stessa transazione/commessa producono **due** righe
  con progressivi distinti (`MAN:x:1`, `MAN:x:2`).
- Test di concorrenza (anche solo manuale, due sessioni psql con
  `BEGIN`/sleep): la seconda sessione attende il lock e produce il
  progressivo successivo, non lo stesso.
- Gli smoke/test BE esistenti della porta oneri restano verdi senza modifiche
  (il contratto della fn non cambia: stessi parametri, stesso risultato).

## 4. Riferimenti

- Doc fn viva: `docs/it/dbzero/vendite/funzioni/fn_aggiungi_onere_commessa.md`
  (righe 87–96) — per il `CREATE OR REPLACE` partire da QUESTA, non dagli YAML
  ([[feedback_db_doc_first]]).
- Wrapper BE: `backend/apps/vendite/db/commesse_repository.py::aggiungi_onere`;
  service `backend/apps/vendite/services/commesse_service.py::aggiungi_onere_commessa`.
- Endpoint esposto: `POST /api/v1/vendite/commesse/<id>/oneri/` (azione
  `carica_voce_manuale`).
