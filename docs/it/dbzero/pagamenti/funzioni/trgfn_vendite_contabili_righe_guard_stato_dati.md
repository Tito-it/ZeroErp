{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_contabili_righe_guard_stato_dati.md" %}
# ⚙️ Funzione `trgfn_vendite_contabili_righe_guard_stato_dati`

```sql
CREATE FUNCTION trgfn_vendite_contabili_righe_guard_stato_dati()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_stato_dati()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_richiede  pagamenti.vendite_contabili_righe_stati.richiede_abbinamento%TYPE;
    v_codice    pagamenti.vendite_contabili_righe_stati.codice_interno%TYPE;
    v_mancanti  text;
    v_campo     text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Una riga contabile in uno stato che PRETENDE l'abbinamento
    --   deve dire a quale fattura e a quale cliente appartiene.
    --   Sono i due dati da cui nasce il movimento contabile.
    --
    -- ⭐ Quali stati lo pretendano NON e' scritto qui: e' la
    --    bandiera richiede_abbinamento del catalogo (D14-a).
    --
    -- ⚠️ La RATA resta FACOLTATIVA anche sugli stati abbinati: la
    --    riga del fondo fattura ha fattura si' e rata no, perche'
    --    e' un saldo per trasferimento. Quando arrivera'
    --    scadenza_id (slice 2) questa funzione NON va toccata.
    -- =========================================================

    SELECT s.richiede_abbinamento, s.codice_interno
      INTO v_richiede, v_codice
      FROM pagamenti.vendite_contabili_righe_stati s
     WHERE s.id = NEW.stato_id;

    -- Stato sconosciuto: non e' compito di questo guard: la FK
    -- fk_vendite_contabili_righe_stato lo impedisce gia'.
    IF COALESCE(v_richiede, false) IS FALSE THEN
        RETURN NEW;
    END IF;

    IF NEW.fattura_id IS NOT NULL AND NEW.billing_account_id IS NOT NULL THEN
        RETURN NEW;
    END IF;

    -- Che cosa manca, detto all'operatore e non al programma. Il
    -- campo da accendere e' UNO: se mancano entrambi si indica il
    -- primo del percorso, perche' scegliendo la fattura il cliente
    -- viene con lei.
    v_mancanti := CASE
        WHEN NEW.fattura_id IS NULL AND NEW.billing_account_id IS NULL
            THEN 'la fattura e il cliente'
        WHEN NEW.fattura_id IS NULL THEN 'la fattura'
        ELSE 'il cliente'
    END;
    v_campo := CASE
        WHEN NEW.fattura_id IS NULL THEN 'fattura_id'
        ELSE 'billing_account_id'
    END;

    PERFORM script.fn_log_and_raise_error(
        'database',
        'pagamenti.trgfn_vendite_contabili_righe_guard_stato_dati',
        'E_RIGA_CONTABILE_ABBINAMENTO_INCOMPLETO',
        jsonb_build_object(
            'campo',              v_campo,
            'contabile_riga_id',  NEW.id,
            'contabile_id',       NEW.contabile_id,
            'stato_id',           NEW.stato_id,
            'stato',              v_codice,
            'fattura_id',         NEW.fattura_id,
            'billing_account_id', NEW.billing_account_id
        ),
        NEW.tx_id,
        COALESCE(v_codice, 'NULL'),
        v_mancanti
    );

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_stato_dati()
IS 'Guard stato <-> dati della riga contabile: uno stato con richiede_abbinamento pretende fattura_id e billing_account_id. Meta'' «bagaglio» di D14-a, di cui pagamenti.trgfn_vendite_contabili_righe_guard_transizione e'' la meta'' «percorso». ⚠️ La RATA resta facoltativa di proposito (la riga del fondo fattura non ne ha una): quando arrivera'' scadenza_id questa funzione NON va toccata. La lista degli stati che pretendono l''abbinamento sta nel CATALOGO, non qui.';
```

</div>

---
{% include-markdown "signature-core.md" %}
