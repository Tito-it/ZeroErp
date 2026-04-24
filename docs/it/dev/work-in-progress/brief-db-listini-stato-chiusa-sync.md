# Brief DB — Sincronizzazione `stato = CHIUSA` con `valido_al` su `listini_versioni`

> **Target team**: DB (`dev/db-tid`)
> **Origine**: bug logico individuato 2026-04-24 durante smoke UI v5 §1.2
> **Impatto**: `vendite.listini_versioni` (ATTIVA/CHIUSA)
> **Autore memo**: backend agent (`dev/backend-tid`)

## 1. Contesto

Il modello listini ha due azioni UI separate sulla versione ATTIVA:

- `Programma chiusura` → `PATCH { valido_al }` (resta ATTIVA, programma data fine)
- `Chiudi` → `POST cambia-stato { stato: 'CHIUSA' }` (cambia solo stato, NON tocca `valido_al`)

Il resolver `vendite.fn_resolve_prezzo_listino_v2` filtra per `lv.validita @> p_data_riferimento AND lv.attivo = TRUE` e **NON** filtra per `lv.stato`. Quindi:

- Se clicco "Chiudi" senza aver prima programmato la chiusura:
  - `stato = 'CHIUSA'`
  - `valido_al = NULL`
  - `validita = [valido_dal, infinity)` — ancora aperta
  - Il resolver continua a pescare la versione come fosse ATTIVA
- Lo stato è contabilmente CHIUSA, operativamente aperta → **incoerente**

## 2. Decisione di design (allineata BE+FE)

Unificare le due azioni in **una sola**: "Chiudi" = `PATCH { valido_al }` con default `valido_al = CURRENT_DATE` (oggi) o data futura a scelta utente. La transizione di stato **non è più manuale** dal FE; diventa **derivata** da `valido_al < CURRENT_DATE` e sincronizzata dal DB.

### Principio di design fail-safe (non negoziabile)

**Fonte di verità operativa = `validita` / `valido_al`. Lo `stato` è flag informativo.**

Ogni processo che determina se una versione è "aperta/chiusa" in senso operativo — resolver prezzi, filtri commesse, lookup listini in pipeline, view di reportistica, ecc. — **deve** basarsi sul daterange `validita` (o su `valido_al`), **mai** sullo `stato`. Motivazione:

- La data è immutabile e non richiede manutenzione
- Lo stato dipende da trigger/job/service: se uno di questi salta o ha bug, lo stato diverge dalla realtà. Componenti che dipendono dallo stato "stantio" producono risposte errate in silenzio
- Basare tutto sulla data garantisce fail-safe automatico: anche se il sync stato → data si rompe, il resolver continua a escludere le versioni scadute

Lo `stato = 'CHIUSA'` resta come flag di comodità per audit/reportistica/badge UI, ma **nessuna decisione operativa** può dipendere da esso.

### Verifica al team DB

Prima di landare 3.1/3.2/3.3 chiedo al team DB di grep su `db/changelog/migrations_v2/20_code/`:

```bash
grep -rn "lv.stato\s*=\|listini_versioni.*stato\s*=\|stato\s*=\s*'CHIUSA'\|stato\s*=\s*'ATTIVA'" db/changelog/migrations_v2/20_code/
```

Per ogni risultato che non sia una guard di tipo `check stato per CRUD utente`, confermare se la logica può migrare a condizione su `validita @> ...` o `valido_al`. Casi tipici da cercare:

- Funzioni di lookup listino che filtrano `WHERE lv.stato = 'ATTIVA'` — devono usare `validita @> data_riferimento`
- View di reportistica operativa (non audit)
- Trigger che bloccano/permettono scritture su tabelle collegate

## 3. Richieste al team DB

### 3.1 Trigger sync automatico `stato` ⇔ `valido_al`

**Obiettivo**: quando `valido_al` è settato a una data passata (`<= CURRENT_DATE - 1`), allineare `stato = 'CHIUSA'` nella stessa riga.

Nome proposto: `trg_vendite_listini_versioni_z90_sync_stato_chiusa_upd`

Logica (AFTER UPDATE OF `valido_al`):

```sql
IF NEW.valido_al IS NOT NULL
   AND NEW.valido_al <= CURRENT_DATE
   AND NEW.stato = 'ATTIVA' THEN
    UPDATE vendite.listini_versioni
       SET stato = 'CHIUSA'
     WHERE id = NEW.id;
END IF;
```

Alternativa 1 (preferita per evitare ricorsione): trigger `BEFORE UPDATE` che normalizza lo stato in NEW prima dell'UPDATE.

Alternativa 2: funzione `vendite.fn_sync_listini_versioni_stato_chiusa(p_versione_id bigint)` richiamata esplicitamente dal service dopo PATCH.

### 3.2 Job notturno pgAgent (complementare)

Per versioni con `valido_al` programmato in futuro che "scade" col tempo (trigger in 3.1 non scatta perché nessun UPDATE ulteriore):

- Job daily `vendite.job_listini_versioni_close_scadute` (eseguire a 00:05)
- Query:

```sql
UPDATE vendite.listini_versioni
   SET stato = 'CHIUSA'
 WHERE stato = 'ATTIVA'
   AND valido_al IS NOT NULL
   AND valido_al < CURRENT_DATE;
```

### 3.3 Guard defense-in-depth: rifiuto stato incoerente

**Obiettivo**: impedire il permanere di righe con `stato = 'CHIUSA' AND valido_al IS NULL` (lo stato di inconsistenza di oggi).

Opzione A — trigger fail-fast (`_a10_` fase guard):

Nome proposto: `trgfn_vendite_listini_versioni_a10_guard_chiusa_senza_data_ins_upd`

```sql
IF NEW.stato = 'CHIUSA' AND NEW.valido_al IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
        'vendite', 'trgfn_listini_versioni_guard_chiusa_senza_data',
        'E_VERSIONE_CHIUSA_SENZA_DATA',
        jsonb_build_object('versione_id', NEW.id),
        NEW.tx_id::uuid, NEW.id::text
    );
END IF;
```

Messaggio errore da seedare in `config.messaggi_errore` con codice `E_VERSIONE_CHIUSA_SENZA_DATA`, testo:
"Versione CHIUSA senza data di fine validità. Impostare `valido_al` prima o contestualmente al passaggio in CHIUSA."

### 3.4 Back-fill versioni storiche incoerenti

Se in DB esistono versioni `stato = 'CHIUSA' AND valido_al IS NULL` create prima di questo fix, fare back-fill:

```sql
-- Prima eseguire check conta:
SELECT count(*)
  FROM vendite.listini_versioni
 WHERE stato = 'CHIUSA' AND valido_al IS NULL;

-- Se > 0, back-fill con data_update (ultima modifica, approssima data chiusura):
UPDATE vendite.listini_versioni
   SET valido_al = data_update::date
 WHERE stato = 'CHIUSA'
   AND valido_al IS NULL;
```

Eseguire **prima** di landare il trigger guard 3.3 (altrimenti l'UPDATE di back-fill stesso fallisce).

### 3.5 (Opzionale) filtro stato nel resolver

Lasciando il resolver com'è (`validita @> oggi`), il sync trigger 3.1 è sufficiente a garantire coerenza. Non serve modificare `fn_resolve_prezzo_listino_v2`.

Se per ragioni di audit si vuole difesa extra, si può aggiungere `AND lv.stato = 'ATTIVA'` ma è ridondante dopo 3.1.

## 4. Impatto BE (già pianificato su `dev/backend-tid`)

Contestualmente al merge del trigger 3.1:

- `apps/vendite/services/listini_service.py::_validate_versione_state_transition`: rimuovere `ATTIVA → CHIUSA` dalle transizioni manuali ammesse. Motivazione in errore: "Usa PATCH `valido_al` per chiudere."
- Test `apps/vendite/tests/services/test_listini_service.py`: aggiornare i test che esercitavano ATTIVA→CHIUSA manuale.

## 5. Impatto FE (già pianificato su `dev/backend-tid`)

- Rimuovere azione kebab "Chiudi" (che oggi fa POST cambia-stato)
- Rinominare azione "Programma chiusura" → "Chiudi", default DatePicker = oggi
- i18n: riutilizzare `listini.chiudi` esistente, dismettere `listini.programma_chiusura` (→ alias temporaneo o rimozione)

## 6. Ordine di landing consigliato

1. 3.4 back-fill (se necessario, su base dati sviluppo)
2. 3.1 trigger sync + 3.3 trigger guard (stessa migration, in `20_code/vendite/`)
3. 3.2 job pgAgent (in `85_pgagent/`)
4. Merge BE+FE su `dev/backend-tid`
5. Smoke test: creare V001 ATTIVA → PATCH `valido_al = CURRENT_DATE` → verificare che in DB risulti `stato = 'CHIUSA'` automaticamente
6. Smoke test: tentare INSERT/UPDATE con `stato = 'CHIUSA' AND valido_al IS NULL` → atteso errore `E_VERSIONE_CHIUSA_SENZA_DATA`

## 7. Riferimenti codice attuali

- Resolver DB: [db/changelog/migrations_v2/20_code/vendite/20260415-14-update-fn-resolve-prezzo-listino-v2-classe-da-contratto-mctit.yaml](../../../db/changelog/migrations_v2/20_code/vendite/20260415-14-update-fn-resolve-prezzo-listino-v2-classe-da-contratto-mctit.yaml) righe 241, 350
- Service BE `fn_change_versione_state`: [backend/apps/vendite/services/listini_service.py:1491-1577](../../../backend/apps/vendite/services/listini_service.py#L1491)
- Dialog FE `ProgrammaChiusuraDialog`: [frontend/src/vendite/components/ProgrammaChiusuraDialog.vue](../../../frontend/src/vendite/components/ProgrammaChiusuraDialog.vue)
- Azioni kebab versione: [frontend/src/vendite/components/ListiniSearchTable.vue:229-244](../../../frontend/src/vendite/components/ListiniSearchTable.vue#L229)

---

*Brief redatto 2026-04-24. Aggiornare in coda con esito landing + eventuali adjust.*
