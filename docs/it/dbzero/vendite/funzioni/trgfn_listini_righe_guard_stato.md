{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_righe_guard_stato.md" %}
# ⚙️ Funzione `trgfn_listini_righe_guard_stato`

```sql
CREATE FUNCTION trgfn_listini_righe_guard_stato()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_righe_guard_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: protezione righe listino in base allo stato della versione padre.
--   BOZZA  → passa sempre
--   ATTIVA → ammessa solo se la riga non e` propagata a valle
--   CHIUSA → blocca sempre
-- Perimetro: solo UPDATE e DELETE (INSERT su ATTIVA e` ammesso come rettifica).
DECLARE
    v_stato vendite.listini_versioni.stato%TYPE;
    v_propagata boolean;
BEGIN
    -- Recupera stato della versione padre
    SELECT lv.stato
      INTO v_stato
      FROM vendite.listini_versioni lv
     WHERE lv.id = OLD.listino_versione_id;

    -- BOZZA: modifica libera
    IF v_stato = 'BOZZA' THEN
        RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END IF;

    -- CHIUSA: blocca sempre
    IF v_stato = 'CHIUSA' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'vendite.trgfn_listini_righe_guard_stato',
            'E_RIGA_LISTINO_VERSIONE_CHIUSA',
            jsonb_build_object(
                'listino_riga_id', OLD.id,
                'listino_versione_id', OLD.listino_versione_id,
                'stato', v_stato,
                'operazione', TG_OP
            ),
            OLD.tx_id,
            -- ⚠️ ARITA' (2026-08-18): il messaggio comincia con «Operazione %s
            --   non ammessa: ...» e di segnaposto ne ha TRE; qui ne arrivavano
            --   due. Mancava proprio il primo, l'operazione — che il trigger
            --   aveva gia' in mano (TG_OP) e metteva perfino nel context.
            TG_OP, OLD.id::text, v_stato
        );
    END IF;

    -- ATTIVA: verifica propagazione
    -- Tabelle controllate per propagazione riga:
    -- 1. vendite.commesse_attivita (listino_riga_id)
    -- 2. vendite.attivita_fatturabili (listino_riga_id)
    -- Per aggiungere nuove tabelle: UNION ALL qui sotto
    SELECT EXISTS(
        SELECT 1 FROM vendite.commesse_attivita
         WHERE listino_riga_id = OLD.id
        UNION ALL
        SELECT 1 FROM vendite.attivita_fatturabili
         WHERE listino_riga_id = OLD.id
    )
    INTO v_propagata;

    IF v_propagata THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'vendite.trgfn_listini_righe_guard_stato',
            'E_RIGA_LISTINO_PROPAGATA',
            jsonb_build_object(
                'listino_riga_id', OLD.id,
                'listino_versione_id', OLD.listino_versione_id,
                'stato', v_stato,
                'operazione', TG_OP
            ),
            OLD.tx_id,
            OLD.id::text
        );
    END IF;

    -- ATTIVA e non propagata: rettifica controllata ammessa
    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_righe_guard_stato()
IS 'Guard N6: protegge righe listino in base a stato versione. BOZZA=passa, ATTIVA=solo se non propagata, CHIUSA=blocca. Solo UPDATE/DELETE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
