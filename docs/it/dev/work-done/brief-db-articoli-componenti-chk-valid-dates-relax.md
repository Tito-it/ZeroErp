# Brief DB — Relax `chk_articoli_componenti_valid_dates` da `>` a `>=` (chiusura same-day BoM) [LANDED 2026-04-27]

> **Status**: ✅ **LANDED** — Team DB ha applicato la richiesta con scelta migliore: invece di relax `>` -> `>=`, **drop completo** del CHECK su 4 tabelle outlier (perimetro esteso). Il backend agent ha allineato `listini_service.py` rimuovendo il guard "gap >= 2 giorni" diventato codice morto post-drop, il mapping `chk_listini_versioni_date` e il test `test_change_state_attiva_blocked_when_autoclose_violates_chk`.
>
> **Modifiche applicate dal team DB rispetto al brief originario**:
>
> - **Drop completo invece di relax `>=`**: `chk_articoli_componenti_valid_dates` è stato droppato (non rilassato). Motivazione tecnica: `script.trgfn_set_validita()` costruisce il `daterange(valido_dal, COALESCE(valido_al, infinity), '[]')` BEFORE INSERT/UPDATE e Postgres rifiuta `valido_al < valido_dal` con SQLSTATE 22000 *prima* che il CHECK scatti — il CHECK era codice morto + bloccava `valido_al = valido_dal` (range degenere `[X, X+1)` di 1 giorno) impedendo il pattern stato-terminale-data-driven.
> - **Perimetro esteso a 4 tabelle outlier** (oltre `articoli_componenti` del brief): droppati anche `chk_uom_conv_valid_dates` (catalogo.unita_misura_conversioni), `chk_listini_versioni_date` (vendite.listini_versioni), `chk_listini_associazioni_date` (vendite.listini_associazioni). Pattern allineato al precedente `20260414-22-drop-check-date-redundant` che aveva già droppato i CHECK su `categorie_clienti_listini` e `promo_articoli`.
> - **Test pgTAP**: estesi i casi 17-18 in `test-articoli-componenti-immutabilita.sql` con regressione esplicita per chiusura same-day (ora ammessa).
> - **Aggiornamento commento trigger `block_modifica_struttura`**: il blocco "Il caso valido_al = valido_dal resta a carico del CHECK (errore tecnico)" è stato rimosso/aggiornato a "ammesso" coerentemente al drop.
>
> **Impatto BE allineato in stessa sessione (commit pendente su `dev/backend-tid`)**:
>
> - [`apps/vendite/services/listini_service.py`](../../../backend/apps/vendite/services/listini_service.py): rimosso il blocco `for row in candidates: ErrorManager.require(nuova_valido_al > prec_valido_dal, ...)` (era righe 1474-1496) — guard tarato sul CHECK strict, ora codice morto. La query `find_versioni_per_autoclose` filtra `valido_dal < nuova_valido_dal` strict, quindi gap=0 non arriva mai al guard (gestito da `ex_listini_versioni_no_overlap` con messaggio user-friendly già esistente). Aggiornato commento `_plan_versione_state_change` per chiarire la nuova invariante.
> - [`apps/vendite/services/listini_service.py`](../../../backend/apps/vendite/services/listini_service.py) `constraint_map`: rimosso il mapping di `chk_listini_versioni_date` (codice morto: il constraint non esiste più).
> - [`apps/vendite/services/listini_service.py`](../../../backend/apps/vendite/services/listini_service.py): aggiornato il detail di `ex_listini_versioni_no_overlap` da "decorrenza minima 2 giorni dopo" a "almeno 1 giorno dopo" (la nuova soglia post-drop).
> - [`apps/vendite/tests/services/test_listini_service.py`](../../../backend/apps/vendite/tests/services/test_listini_service.py): rimosso `test_change_state_attiva_blocked_when_autoclose_violates_chk` (logicamente obsoleto: l'invariante non esiste più). 55 test verdi.
>
> **Lezione operativa per future sessioni**: prima di proporre allentamenti su CHECK constraint che si sovrappongono semanticamente al `daterange validita`, verificare quale dei due lavora *prima* nel BEFORE INS/UPD. Il trigger `trgfn_set_validita()` rifiuta range invalidi via SQLSTATE 22000 e questo rende ridondanti i CHECK strict `valid_to > valid_from` dovunque `valido_al = valido_dal` debba essere ammesso semanticamente.
>
> **FE BoM drawer in stessa sessione**: paginazione 10 + ReloadButton + F5 + filtro client-side + dialog chiusura simmetrico a `ChiudiVersioneDialog` (DatePicker, no più `confirmAction`). Indipendente dal land DB, già allineato al pattern data-driven.
>
> ---
>
> **Target team**: DB (`dev/db-tid`)
> **Origine**: backend agent (`dev/backend-tid`), sessione 2026-04-27 (validazione UI v5 §3 BoM versionata, smoke "Chiudi riga")
> **Impatto**: `catalogo.articoli_componenti` (CHECK constraint + trigger commento)
> **Priorita'**: alta — bug logico modello che intercetta un caso d'uso reale ("admin chiude oggi una BoM creata oggi") in un errore tecnico non UI-friendly. Pattern incoerente con `feedback_stato_terminale_con_data.md`.

## 1. Bug logico individuato

Il CHECK attuale e' definito strict `>`:

```sql
ALTER TABLE catalogo.articoli_componenti
  ADD CONSTRAINT chk_articoli_componenti_valid_dates
  CHECK (valid_to IS NULL OR valid_to > valid_from);
```

(seedato in [`20250819-50-create-catalogo-articoli-componenti-mctit.yaml`](../../../../db/changelog/migrations/00_bootstrap/20250819-50-create-catalogo-articoli-componenti-mctit.yaml) riga 176-177; commento riga 238 — **"valid_to deve essere NULL o successivo a valid_from"**).

Il trigger `trg_articoli_componenti_a10_block_modifica_struttura_upd_dlt` ([20260422-01-create-trgfn-articoli-componenti-block-modifica-struttura-mctit.yaml](../../../../db/changelog/migrations_v2/20_code/catalogo/20260422-01-create-trgfn-articoli-componenti-block-modifica-struttura-mctit.yaml) riga 137-145) esplicita la conseguenza intenzionale del modello attuale:

```sql
-- Check coerenza range su UPDATE valido_al.
-- chk_articoli_componenti_valid_dates copre
-- "valido_al > valido_dal"; qui intercettiamo
-- valido_al < valido_dal con error code custom
-- UI-friendly. Il caso valido_al = valido_dal
-- resta a carico del CHECK (errore tecnico).
```

> *"Il caso valido_al = valido_dal resta a carico del CHECK (errore tecnico)."*

Cioe': `valido_al = valido_dal` cade in errore tecnico Postgres senza messaggio business. La FE riceve il payload grezzo del `chk_articoli_componenti_valid_dates`. **Esempio reale (smoke 2026-04-27)**:

```
{
  code: "E_CATALOGO_VALIDATION",
  message: "Violazione vincoli componente.",
  detail: "la nuova riga per la relazione \"articoli_componenti\" viola il
           vincolo di controllo \"chk_articoli_componenti_valid_dates\"
           DETAIL: La riga in errore contiene (...,
           2026-04-27, 2026-04-27, ...)."
}
```

## 2. Scenario d'uso bloccato

L'admin crea una nuova riga BoM oggi, si accorge subito di aver inserito un componente sbagliato (errore di selezione articolo, errore quantita', etc.) e clicca **"Chiudi riga"** per terminarla immediatamente.

Il pattern v5 [`feedback_stato_terminale_con_data.md`](../../../../.claude/projects/-home-tid-apps-ZeroErp/memory/feedback_stato_terminale_con_data.md) prevede esattamente:

> Chiusura immediata = `valido_al = oggi` (PATCH atomica). La regola fail-safe data-driven per le entita' v5 con storico.

Pero' su `articoli_componenti` con `valido_dal = oggi` la chiusura `valido_al = oggi` viola il CHECK strict, ricadendo in errore tecnico.

L'unico workaround attuale e':
- chiudere il giorno successivo (`valido_al = oggi + 1`) — viola la semantica UX "chiusura immediata"
- DELETE diretto — bloccato dal trigger `block_modifica_struttura` (E_BOM_MODIFICA_VIETATA, by design)

Il modello e' quindi **fuori coerenza** col pattern: per BoM l'admin non puo' "chiudere subito" un errore appena commesso.

## 3. Decisione di design proposta

> **Allentare il CHECK da `>` a `>=`**: una BoM con finestra `[X, X]` e' valida e significa "componente attivo solo per il giorno X". Coerente con il pattern stato-terminale data-driven gia' usato su listini-versioni / contratti / promo articoli.

Il `daterange validita` (impostato da `script.trgfn_set_validita`) per `[2026-04-27, 2026-04-27]` produce `[2026-04-27, 2026-04-28)` (upper exclusive +1) — finestra di **1 giorno** — gia' verificato in produzione su altre tabelle simili. Nessun problema di range degenere.

**Nessun rischio di overlap** con il relax: `ex_articoli_componenti_no_overlap` (gist su `prodotto_id, componente_id, validita`) e `uq_articoli_componenti_prodotto_componente_from` (UNIQUE su `prodotto_id, componente_id, valido_dal`) coprono entrambi gia' qualunque sovrapposizione, anche di 1 giorno.

## 4. Richieste al team DB

### 4.1 Relax CHECK constraint

DROP + recreate del CHECK in single changeset:

```sql
ALTER TABLE catalogo.articoli_componenti
  DROP CONSTRAINT chk_articoli_componenti_valid_dates;

ALTER TABLE catalogo.articoli_componenti
  ADD CONSTRAINT chk_articoli_componenti_valid_dates
  CHECK (valid_to IS NULL OR valid_to >= valid_from);

COMMENT ON CONSTRAINT chk_articoli_componenti_valid_dates ON catalogo.articoli_componenti
  IS 'valid_to deve essere NULL o >= valid_from (ammette chiusura same-day per il pattern stato-terminale-data-driven)';
```

### 4.2 Aggiornare trigger commento (no logica)

Nel trigger `catalogo.trgfn_articoli_componenti_block_modifica_struttura()` ([20260422-01-create-trgfn-articoli-componenti-block-modifica-struttura-mctit.yaml](../../../../db/changelog/migrations_v2/20_code/catalogo/20260422-01-create-trgfn-articoli-componenti-block-modifica-struttura-mctit.yaml)), aggiornare il commento riga 137-145:

```sql
-- Check coerenza range su UPDATE valido_al.
-- chk_articoli_componenti_valid_dates copre
-- "valido_al >= valido_dal"; qui intercettiamo
-- valido_al < valido_dal con error code custom
-- UI-friendly E_BOM_VALIDO_AL_INVALIDO.
-- Il caso valido_al = valido_dal e' AMMESSO (chiusura same-day,
-- pattern feedback_stato_terminale_con_data, allineato relax CHECK
-- 2026-04-NN).
```

La logica del trigger NON cambia: il check `NEW.valido_al < OLD.valido_dal` resta strict `<`, perche' al = dal e' ora ammesso anche dal CHECK constraint sottostante.

### 4.3 Test pgTAP

File da estendere: `db/pgtap/catalogo/test_articoli_componenti_block_modifica_struttura.sql` (se esiste; altrimenti nuovo `test_articoli_componenti_chk_valid_dates_relax.sql`).

Casi:

1. INSERT con `valido_dal = '2026-05-01'`, `valido_al = '2026-05-01'` → OK (chiusura same-day in create — caso teorico, in pratica la FE non lo permette ma DB deve ammetterlo)
2. INSERT con `valido_dal = '2026-05-01'`, `valido_al = '2026-04-30'` → fallisce CHECK (al < dal)
3. INSERT con `valido_dal = '2026-05-01'`, `valido_al = '2026-05-02'` → OK (caso normale)
4. INSERT con `valido_al = NULL` → OK (riga aperta)
5. **UPDATE su riga creata oggi: `valido_al = valido_dal` → OK** (regressione esplicita per bug 2026-04-27)
6. UPDATE con `valido_al < valido_dal` → fallisce trigger `E_BOM_VALIDO_AL_INVALIDO`
7. Verifica `daterange(valido_dal, valido_al, '[]')` su `[X, X]` → `[X, X+1)` (range 1 giorno)
8. Verifica overlap exclusion: due righe con stesso `prodotto_id`+`componente_id` su `[X, X]` → seconda fallisce su `ex_articoli_componenti_no_overlap`

## 5. File coinvolti / dipendenze

- **Tabella**: `catalogo.articoli_componenti` (vedi [docs/it/dbzero/catalogo/tabelle/articoli_componenti.md](../../dbzero/catalogo/tabelle/articoli_componenti.md))
- **Constraint**: `chk_articoli_componenti_valid_dates`
- **Trigger commento**: `catalogo.trgfn_articoli_componenti_block_modifica_struttura()` (no cambio logica)
- **Changelog v2**: nuovo file `db/changelog/migrations_v2/20_code/catalogo/YYYYMMDD-NN-relax-chk-articoli-componenti-valid-dates-mctit.yaml` con sub-changeset:
  - `-NN-01-relax-chk-valid-dates` (DROP + ADD constraint)
  - `-NN-02-update-trgfn-comment` (no DDL — solo refresh commento se serve riemissione fn)
- **pgTAP**: `db/pgtap/catalogo/test_articoli_componenti_chk_valid_dates_relax.sql`
- **Doc autogenerata**: rigenerare [docs/it/dbzero/catalogo/tabelle/articoli_componenti.md](../../dbzero/catalogo/tabelle/articoli_componenti.md) post-merge

## 6. Conferma di land

Il backend agent attende conferma di land su `dev/db-tid` per:

- abilitare smoke UI §3 BoM versionata in `sviluppo-listini-v5-test-ui.md` (test "Chiudi riga" oggi sblocca completamente)
- aggiornare il commento sviluppo backend nel `ArticoloBomDrawer.vue` (FE gia' allineato al pattern data-driven; nessuna modifica struttura, solo dialog di chiusura aggiornato in stessa sessione)
- spostare il brief in `docs/it/dev/work-done/` con header LANDED

**Nota lato FE in stessa sessione (non dipende da land DB)**: in parallelo a questo brief, il backend agent ha allineato `ArticoloBomDrawer.vue` al pattern dei sub-drawer paginati (paginazione 10 righe / ReloadButton / F5 / filtro articolo client-side / sort) e sostituito il `confirmAction` semplice della "Chiudi riga" con un dialog dedicato simmetrico a `ChiudiVersioneDialog.vue` (DatePicker default oggi, min-date = `valido_dal` riga, ammette chiusura programmata se data futura). Una volta landed il relax DB, lo smoke same-day tornera' verde end-to-end.

Eventuali variazioni di design sono benvenute — il backend agent allinea il service in seguito (al momento il service `ArticoliComponentiService` non ha guard applicativa data-driven simmetrica perche' la BoM e' immutabile per design via trigger; con questo relax il pattern resta consistente, niente refactor service).
