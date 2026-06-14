# Brief DB — `data_apertura` valorizzata anche all'INSERT (pratica creata già APERTA)

**Area:** `pratiche` · **Tipo:** modifica trigger function + trigger
**Branch destinazione:** `dev/db-tid`
**Richiesto da:** backend agent (per conto di Tid) · **Data:** 2026-06-13

---

## 1. Contesto e decisione

Decisione di modello presa con Tid: **una nuova pratica nasce direttamente in stato
`APERTA`**, saltando il default `BOZZA`. Motivazione: lo stato `BOZZA` non porta
alcun privilegio reale (verificato: nessun editing/visibilità/cancellazione
esclusivi; transizioni `BOZZA→APERTA`, `BOZZA→ANNULLATA`, ma anche
`APERTA→ANNULLATA` esiste). Il passaggio per la bozza aggiungeva solo attrito:
l'operatore creava la pratica, vedeva la roadmap percorso ma doveva riaprire la
scheda per "Apri pratica" prima di poter operare.

Lo stato `BOZZA` **resta nel modello** (transizioni e codice invariati) per un
eventuale "salva bozza" esplicito futuro — non va rimosso. Cambia solo lo stato
**di default alla creazione** (lato BE, vedi §4).

## 2. Problema da risolvere a DB

`data_apertura` è valorizzata da `pratiche.trgfn_pratiche_set_data_apertura`, oggi
attivo **solo su UPDATE**:

```
trg_pratiche_m50_set_data_apertura_upd  BEFORE UPDATE OF stato_id
```

Regola attuale: alla transizione `BOZZA → APERTA` setta `data_apertura := CURRENT_DATE`,
poi immutabile.

Se la pratica nasce **direttamente APERTA via INSERT**, il trigger non scatta e
`data_apertura` resta `NULL`. Va quindi esteso il trigger anche all'INSERT.

Nota: il guard transizioni (`trg_pratiche_a10_guard_transizione_upd`) è **UPDATE
only**, quindi l'INSERT-as-APERTA non viola alcun guard di transizione. La roadmap
percorso è template-driven (`get_percorso_pratica`), non dipende dalla transizione,
quindi non serve altro.

## 3. Modifica richiesta

Estendere `pratiche.trgfn_pratiche_set_data_apertura` a gestire `TG_OP = 'INSERT'`
oltre all'`UPDATE` esistente, e aggiungere un trigger `BEFORE INSERT` (stessa fase
`m50`). Mantenere invariata la logica UPDATE (transizione `BOZZA→APERTA` +
immutabilità). Id stati sempre risolti da `config.stati_pratiche.codice_interno`,
mai hardcodati.

### SQL proposto (function)

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_set_data_apertura()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
-- Scopo: valorizzare data_apertura quando la pratica entra in APERTA, sia per
--   creazione diretta (INSERT con stato APERTA) sia per transizione BOZZA→APERTA.
-- Regole:
--   1. INSERT con stato APERTA e data_apertura non fornita -> CURRENT_DATE
--   2. UPDATE: solo alla transizione BOZZA -> APERTA
--   3. Immutabile: se data_apertura e' gia' valorizzata, preserva il valore
--   4. Gli id degli stati vengono risolti da config.stati_pratiche tramite
--      codice_interno, mai hardcodati
DECLARE
    v_bozza_id  config.stati_pratiche.id%TYPE;
    v_aperta_id config.stati_pratiche.id%TYPE;
BEGIN
    SELECT id INTO v_aperta_id
      FROM config.stati_pratiche
     WHERE codice_interno = 'APERTA';

    -- Creazione diretta in APERTA: valorizza se non gia' fornita dal chiamante
    IF TG_OP = 'INSERT' THEN
        IF NEW.data_apertura IS NULL AND NEW.stato_id = v_aperta_id THEN
            NEW.data_apertura := CURRENT_DATE;
        END IF;
        RETURN NEW;
    END IF;

    -- UPDATE: logica preesistente invariata
    -- Nessuna transizione: niente da fare
    IF OLD.stato_id = NEW.stato_id THEN
        RETURN NEW;
    END IF;

    -- Immutabilita': se gia' valorizzata, preserva
    IF OLD.data_apertura IS NOT NULL THEN
        NEW.data_apertura := OLD.data_apertura;
        RETURN NEW;
    END IF;

    SELECT id INTO v_bozza_id
      FROM config.stati_pratiche
     WHERE codice_interno = 'BOZZA';

    -- Transizione BOZZA -> APERTA: valorizza data_apertura
    IF OLD.stato_id = v_bozza_id AND NEW.stato_id = v_aperta_id THEN
        NEW.data_apertura := CURRENT_DATE;
    END IF;

    RETURN NEW;
END;
$function$;

COMMENT ON FUNCTION pratiche.trgfn_pratiche_set_data_apertura()
  IS 'BEFORE INSERT/UPDATE: valorizza data_apertura quando la pratica entra in APERTA (creazione diretta o transizione BOZZA->APERTA). Immutabile dopo prima valorizzazione.';
```

### SQL proposto (trigger INSERT, oltre a quello UPDATE esistente)

```sql
DROP TRIGGER IF EXISTS trg_pratiche_m50_set_data_apertura_ins ON pratiche.pratiche;

CREATE TRIGGER trg_pratiche_m50_set_data_apertura_ins
BEFORE INSERT
ON pratiche.pratiche
FOR EACH ROW
EXECUTE FUNCTION pratiche.trgfn_pratiche_set_data_apertura();

COMMENT ON TRIGGER trg_pratiche_m50_set_data_apertura_ins
ON pratiche.pratiche
IS 'Valorizza data_apertura alla creazione diretta in APERTA.';
```

Il trigger UPDATE esistente (`trg_pratiche_m50_set_data_apertura_upd`) **resta
invariato**.

### Rollback

Ripristinare la function alla versione UPDATE-only e fare
`DROP TRIGGER IF EXISTS trg_pratiche_m50_set_data_apertura_ins`.

## 4. Downstream lato BE (NON eseguito ora — attende consegna DB)

In [pratiche_service.py:144](../../../backend/apps/pratiche/services/pratiche_service.py)
`crea_pratica` risolve lo stato iniziale con `resolve_stato_pratica("BOZZA")`.
Dopo la consegna del trigger, va cambiato in `resolve_stato_pratica("APERTA")`
(una riga + aggiornamento commento di scopo della funzione).

**Coupling:** la riga BE NON va applicata prima del trigger, altrimenti le nuove
pratiche sarebbero APERTA con `data_apertura = NULL`. FE: nessuna modifica (le
azioni del drawer sono data-driven: "Apri pratica" semplicemente non comparirà più
per le pratiche nuove, già APERTA; "Sospendi/Chiudi/Annulla" restano).

## 5. Test pgTAP richiesti

1. INSERT pratica con stato `APERTA` (senza passare `data_apertura`) → `data_apertura = CURRENT_DATE`.
2. INSERT pratica con stato `APERTA` passando `data_apertura` esplicita → valore del chiamante preservato (immutabilità all'INSERT).
3. INSERT pratica con stato `BOZZA` → `data_apertura IS NULL` (comportamento bozza invariato).
4. UPDATE `BOZZA → APERTA` → `data_apertura = CURRENT_DATE` (regressione: path esistente intatto).
5. UPDATE successivo su pratica già APERTA → `data_apertura` invariata (immutabilità).
