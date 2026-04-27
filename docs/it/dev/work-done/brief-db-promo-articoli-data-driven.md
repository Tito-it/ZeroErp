# Brief DB — Guard data-driven `vendite.promo_articoli` (no-retroattivita' + immutabilita' iniziata/scaduta) [LANDED 2026-04-26]

> **Status**: ✅ **LANDED** — Team DB ha applicato il trigger guard (singolo, INS+UPD) con miglioramenti rispetto al brief originale. Il backend agent NON deve modificare lato Python: i 3 codici errore (`E_PROMO_RETROATTIVA`, `E_PROMO_INIZIATA_CAMPI_RISTRETTI`, `E_PROMO_SCADUTA_IMMUTABILE`) sono identici a quelli usati dal service `PromoArticoliService` — la mappatura `error_policies.py` resta valida.
>
> **Modifiche applicate dal team DB rispetto al brief**:
>
> - **Naming corretto**: `trgfn_promo_articoli_guard_data_driven` (nessuna fase / nessun evento nel nome funzione) + `trg_promo_articoli_a10_guard_data_driven_ins_upd` (uso `_a10_` non `_a05_` come da convenzione esistente nello schema).
> - **Trigger unico anziche' due**: l'INSERT e' caso degenere di UPDATE FUTURA (riusa la stessa logica). Piu' manutenibile, single source of truth.
> - **Confronto SCADUTA esteso** a `codice`, `articolo_id`, `uom_id` oltre alle 7 colonne dominio del brief (defense-in-depth completa anche su rinomina codice / cambio FK in scaduta).
> - **CSV codici errore solo IT** (coerente con convenzione esistente: il fallback `it` e' gestito da `fn_get_messaggio` come da brief `brief-db-fallback-lingua-errori.md` chiuso 2026-04-23).
> - **Check `valido_al < CURRENT_DATE` su INSERT rimosso**: ridondante. `chk_promo_articoli_date` (CHECK constraint esistente) + nuovo `valido_dal > CURRENT_DATE` lo coprono per costruzione (se `valido_dal > today` e `valido_al >= valido_dal`, allora `valido_al >= today + 1 > today`).
>
> ---
>
> **Target team**: DB (`dev/db-tid`)
> **Origine**: backend agent (`dev/backend-tid`), sessione 2026-04-26 (validazione UI v5 §1.5 promo articoli)
> **Impatto**: `vendite.promo_articoli` (INSERT + UPDATE)
> **Pattern di riferimento**: simmetrico ai brief gia' chiusi `brief-db-listini-stato-chiusa-sync.md` (listini-versioni 24-04) e `brief-db-contratti-cessazione-data-driven.md` (contratti 26-04). Stesso paradigma fail-safe data-driven applicato a un'altra entita' v5 — terza occorrenza del pattern.

## 1. Contesto

Le promo articoli (STADIO 0 del resolver pricing v5) sono un **overlay temporale**: chiavi `(articolo, uom, validita)`, finestra `[valido_dal, valido_al]`, niente colonna stato esplicita — lo stato e' **derivato dalle date**.

Il backend ha appena introdotto le seguenti regole applicative in `PromoArticoliService` (commit `dev/backend-tid` in arrivo, vedi `apps/vendite/services/promo_articoli_service.py`):

| Stato derivato (oggi) | Operazione | Regola |
|---|---|---|
| — | INSERT | `valido_dal > CURRENT_DATE` (no retroattiva), `valido_al >= CURRENT_DATE` |
| FUTURA (`CURRENT_DATE < valido_dal`) | UPDATE | tutti i campi mutabili, ma `valido_dal` solo `> CURRENT_DATE`, `valido_al` solo `>= CURRENT_DATE` |
| INIZIATA (`valido_dal <= CURRENT_DATE <= valido_al`) | UPDATE | **solo** `descrizione`, `valido_al` (se `>= CURRENT_DATE`), `meta`. `tipo_variazione`/`valore_variazione`/`valido_dal`/`attivo` rifiutati. |
| SCADUTA (`CURRENT_DATE > valido_al`) | UPDATE | **rifiutato** (immutabile) |
| qualunque | DELETE | non in scope di questo brief (resta ammesso da DB; il service non espone delete) |

Codici errore applicativi gia' registrati in [`error_policies.py`](../../../../backend/apps/core/services/error_policies.py):

- `E_PROMO_RETROATTIVA` (HTTP 400, `highlight_form_fields`)
- `E_PROMO_INIZIATA_CAMPI_RISTRETTI` (HTTP 409, `show_toast_error`)
- `E_PROMO_SCADUTA_IMMUTABILE` (HTTP 409, `show_toast_error`)

**Manca lato DB**: trigger guard defense-in-depth che applichi le stesse regole su bypass del service (UPDATE diretto via psql, script di manutenzione, integrazione esterna). Senza guard DB un'incoerenza retroattiva su una promo gia' iniziata altererebbe i prossimi calcoli `fn_resolve_prezzo_listino_v2` e i `riallinea-prezzo` su righe `commesse_attivita`, inquinando lo snapshot pricing v5 (`promo_id` FK + `prezzo_base_snapshot` etc.).

## 2. Decisione di design

> **Fonte di verita' operativa = `valido_dal` / `valido_al`. Lo "stato" della promo e' un flag derivato, mai persistito. Il resolver legge le date, le date governano.**

I trigger DB applicano le stesse regole del service. Niente colonna `stato` da aggiungere.

## 3. Richieste al team DB

### 3.1 Trigger guard INSERT (no-retroattivita')

Nome proposto: `trgfn_promo_articoli_a05_guard_no_retroattiva_ins`

Logica (BEFORE INSERT):

```sql
IF NEW.valido_dal <= CURRENT_DATE THEN
  PERFORM script.fn_log_and_raise_error(
    'E_PROMO_RETROATTIVA',
    p_table_name => 'vendite.promo_articoli',
    p_detail => format(
      'valido_dal=%s deve essere > CURRENT_DATE=%s.',
      NEW.valido_dal, CURRENT_DATE
    )
  );
END IF;

IF NEW.valido_al < CURRENT_DATE THEN
  PERFORM script.fn_log_and_raise_error(
    'E_PROMO_RETROATTIVA',
    p_table_name => 'vendite.promo_articoli',
    p_detail => format(
      'valido_al=%s antecedente a CURRENT_DATE=%s.',
      NEW.valido_al, CURRENT_DATE
    )
  );
END IF;

RETURN NEW;
```

> **Nota**: il check `valido_al >= valido_dal` e' gia' coperto dal `daterange validita` (trigger `trg_promo_articoli_a20_set_validita_ins_upd` esistente — `daterange(dal, al, '[]')` lancera' su al < dal).

### 3.2 Trigger guard UPDATE (whitelist data-driven)

Nome proposto: `trgfn_promo_articoli_a10_guard_data_driven_upd`

Logica (BEFORE UPDATE):

```sql
DECLARE
  v_today CONSTANT date := CURRENT_DATE;
  v_old_dal date := OLD.valido_dal;
  v_old_al  date := OLD.valido_al;
BEGIN
  -- SCADUTA: nessun UPDATE ammesso (idempotenza colonne audit + tx_id esclusa
  -- dai trigger esistenti, qui parliamo di UPDATE applicativi).
  IF v_today > v_old_al THEN
    -- Ammetti solo cambi che NON toccano nessuna colonna dominio:
    -- audit/tx_id sono gestiti dai trigger di sistema. Se il trigger
    -- system tocca solo data_update/user_update/tx_id, non passa di qui
    -- come UPDATE applicativo (NEW.* identici a OLD.*). In ogni caso,
    -- per sicurezza confrontiamo le colonne di dominio:
    IF (NEW.descrizione, NEW.tipo_variazione, NEW.valore_variazione,
        NEW.valido_dal, NEW.valido_al, NEW.attivo, NEW.meta)
       IS DISTINCT FROM
       (OLD.descrizione, OLD.tipo_variazione, OLD.valore_variazione,
        OLD.valido_dal, OLD.valido_al, OLD.attivo, OLD.meta) THEN
      PERFORM script.fn_log_and_raise_error(
        'E_PROMO_SCADUTA_IMMUTABILE',
        p_table_name => 'vendite.promo_articoli',
        p_detail => format(
          'Promo id=%s scaduta (valido_al=%s < %s): immutabile.',
          OLD.id, v_old_al, v_today
        )
      );
    END IF;
    RETURN NEW;
  END IF;

  -- INIZIATA: whitelist ristretta. Solo descrizione, valido_al (>= today), meta.
  IF v_old_dal <= v_today AND v_today <= v_old_al THEN
    IF NEW.tipo_variazione   IS DISTINCT FROM OLD.tipo_variazione
       OR NEW.valore_variazione IS DISTINCT FROM OLD.valore_variazione
       OR NEW.valido_dal     IS DISTINCT FROM OLD.valido_dal
       OR NEW.attivo         IS DISTINCT FROM OLD.attivo THEN
      PERFORM script.fn_log_and_raise_error(
        'E_PROMO_INIZIATA_CAMPI_RISTRETTI',
        p_table_name => 'vendite.promo_articoli',
        p_detail => format(
          'Promo id=%s gia'' iniziata (valido_dal=%s <= %s): solo descrizione, '
          'valido_al e meta sono modificabili.',
          OLD.id, v_old_dal, v_today
        )
      );
    END IF;
    -- valido_al non puo' tornare al passato in iniziata.
    IF NEW.valido_al < v_today THEN
      PERFORM script.fn_log_and_raise_error(
        'E_PROMO_RETROATTIVA',
        p_table_name => 'vendite.promo_articoli',
        p_detail => format(
          'valido_al=%s antecedente a %s su promo iniziata.',
          NEW.valido_al, v_today
        )
      );
    END IF;
    RETURN NEW;
  END IF;

  -- FUTURA (v_today < v_old_dal): tutti i campi mutabili, ma date solo
  -- verso il futuro (no spostamento al passato).
  IF NEW.valido_dal IS DISTINCT FROM OLD.valido_dal
     AND NEW.valido_dal <= v_today THEN
    PERFORM script.fn_log_and_raise_error(
      'E_PROMO_RETROATTIVA',
      p_table_name => 'vendite.promo_articoli',
      p_detail => format(
        'valido_dal=%s deve essere > %s.', NEW.valido_dal, v_today
      )
    );
  END IF;
  IF NEW.valido_al IS DISTINCT FROM OLD.valido_al
     AND NEW.valido_al < v_today THEN
    PERFORM script.fn_log_and_raise_error(
      'E_PROMO_RETROATTIVA',
      p_table_name => 'vendite.promo_articoli',
      p_detail => format(
        'valido_al=%s antecedente a %s.', NEW.valido_al, v_today
      )
    );
  END IF;

  RETURN NEW;
END;
```

**Importante**: `IS DISTINCT FROM` gestisce correttamente NULL su `meta`/`attivo` senza falsi positivi. La transizione `valido_dal` su promo FUTURA puo' anche restare uguale (no-op): in quel caso `IS DISTINCT FROM OLD.valido_dal` e' false, niente check.

### 3.3 Codici errore da seedare

In `config.messaggi_errore` (con tutte le lingue del seed: `it` obbligatorio, `en` consigliato — vedi anche brief gia' chiuso `brief-db-fallback-lingua-errori.md` per il fallback IT):

| codice | lingua | messaggio | causa | soluzione |
|---|---|---|---|---|
| `E_PROMO_RETROATTIVA` | `it` | "Date promo non valide: non sono ammessi valori retroattivi." | "valido_dal deve essere > oggi e valido_al >= oggi." | "Correggere le date selezionando un periodo a partire da domani." |
| `E_PROMO_RETROATTIVA` | `en` | "Promo dates not valid: retroactive values not allowed." | "valid_from must be > today and valid_to >= today." | "Pick dates starting from tomorrow." |
| `E_PROMO_INIZIATA_CAMPI_RISTRETTI` | `it` | "Promo gia' iniziata: campi modificabili limitati." | "Solo descrizione, valido_al (>= oggi) e meta sono modificabili in stato INIZIATA." | "Per cambiare prezzo o periodo chiudere la promo (valido_al = oggi) e crearne una nuova." |
| `E_PROMO_INIZIATA_CAMPI_RISTRETTI` | `en` | "Promo already started: editable fields restricted." | "Only description, valid_to (>= today) and meta are mutable in INIZIATA state." | "To change price or period, close the promo (valid_to = today) and create a new one." |
| `E_PROMO_SCADUTA_IMMUTABILE` | `it` | "Promo scaduta: non modificabile." | "valido_al e' antecedente a oggi." | "Per riproporre la promo, crearne una nuova." |
| `E_PROMO_SCADUTA_IMMUTABILE` | `en` | "Expired promo: not editable." | "valid_to is before today." | "To re-offer the promo, create a new one." |

Tutti e 3 con `http_status=NULL` (gestito lato applicativo via `error_policies.py`) e senza `retryable=true`.

## 4. Test pgTAP

File da creare: `db/pgtap/vendite/test_promo_articoli_data_driven_guard.sql`.

Casi proposti:

### 4.1 INSERT no-retroattiva

1. INSERT con `valido_dal = CURRENT_DATE` → `E_PROMO_RETROATTIVA`
2. INSERT con `valido_dal = CURRENT_DATE - 1` → `E_PROMO_RETROATTIVA`
3. INSERT con `valido_dal = CURRENT_DATE + 1`, `valido_al = CURRENT_DATE - 1` → fallisce su daterange (al < dal)
4. INSERT con `valido_dal = CURRENT_DATE + 1`, `valido_al = CURRENT_DATE + 30` → OK

### 4.2 UPDATE su promo SCADUTA

Setup: insert promo con `valido_dal = CURRENT_DATE - 60`, `valido_al = CURRENT_DATE - 10` (per bypassare la guard INSERT in setup pgTAP, usare direttamente INSERT come superuser disabilitando il trigger del 3.1; oppure inserire promo futura e poi `UPDATE` dei campi date in stato corrente per portarla nel passato — questa pero' richiede un workaround simile.).

Suggerimento: il setup pgTAP dovrebbe disabilitare temporaneamente il trigger 3.1 con `ALTER TABLE ... DISABLE TRIGGER trgfn_promo_articoli_a05_guard_no_retroattiva_ins`, fare l'INSERT dei dati di test "nel passato", e poi riabilitare per testare la guard 3.2.

5. UPDATE descrizione → `E_PROMO_SCADUTA_IMMUTABILE`
6. UPDATE valido_al → `E_PROMO_SCADUTA_IMMUTABILE`
7. UPDATE meta → `E_PROMO_SCADUTA_IMMUTABILE`

### 4.3 UPDATE su promo INIZIATA

Setup analogo (valido_dal nel passato, valido_al nel futuro).

8. UPDATE descrizione → OK
9. UPDATE valido_al = CURRENT_DATE + 30 → OK
10. UPDATE valido_al = CURRENT_DATE - 1 → `E_PROMO_RETROATTIVA`
11. UPDATE tipo_variazione → `E_PROMO_INIZIATA_CAMPI_RISTRETTI`
12. UPDATE valore_variazione → `E_PROMO_INIZIATA_CAMPI_RISTRETTI`
13. UPDATE valido_dal → `E_PROMO_INIZIATA_CAMPI_RISTRETTI`
14. UPDATE attivo = false → `E_PROMO_INIZIATA_CAMPI_RISTRETTI`
15. UPDATE meta → OK

### 4.4 UPDATE su promo FUTURA

Setup standard (entrambe le date nel futuro).

16. UPDATE tutti i campi → OK
17. UPDATE valido_dal = CURRENT_DATE → `E_PROMO_RETROATTIVA`
18. UPDATE valido_al = CURRENT_DATE - 1 → `E_PROMO_RETROATTIVA`
19. UPDATE valido_dal stesso valore (no-op) → OK (non triggera guard)

## 5. File coinvolti / dipendenze

- **Tabella**: `vendite.promo_articoli` (vedi `docs/it/dbzero/vendite/tabelle/promo_articoli.md`)
- **Funzione errore**: `script.fn_log_and_raise_error` (gia' in uso da altri trigger)
- **Codici errore**: `config.messaggi_errore` (insert con id auto-seedati; sempre IT + EN)
- **Changelog v2**: nuovo file `db/changelog/migrations_v2/20_code/vendite/YYYYMMDD-NN-create-trgfn-promo-articoli-data-driven-mctit.yaml` con sub-changeset:
  - `-NN-01-seed-codici-errore`
  - `-NN-02-create-trgfn-guard-no-retroattiva-ins`
  - `-NN-03-create-trgfn-guard-data-driven-upd`
- **pgTAP**: `db/pgtap/vendite/test_promo_articoli_data_driven_guard.sql`
- **Doc autogenerata**: rigenerare `docs/it/dbzero/vendite/tabelle/promo_articoli.md` e (se presenti) i manual associati post-merge

## 6. Conferma di land

Il backend agent attende conferma di land su `dev/db-tid` per:

- chiudere il task corrispondente nel WIP `sviluppo-listini-v5-test-ui.md` §1.5 (test scenario UI promo)
- aggiornare l'index memory `MEMORY.md` aggiungendo questo brief al pattern `feedback_stato_terminale_con_data.md` come terza occorrenza (dopo listini-versioni 2026-04-24 e contratti 2026-04-26)
- spostare il brief in `docs/it/dev/work-done/` con header LANDED (incluso elenco modifiche eventuali rispetto al brief, come gia' fatto per i due precedenti)

Eventuali variazioni di design (es. semplificazione "scaduta" e "iniziata" in un unico trigger, fix opportunistici) sono benvenute — il backend agent allinea il service in seguito.
