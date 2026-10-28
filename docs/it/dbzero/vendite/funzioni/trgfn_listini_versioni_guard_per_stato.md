{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_versioni_guard_per_stato.md" %}
# ⚙️ Funzione `trgfn_listini_versioni_guard_per_stato`

```sql
CREATE FUNCTION trgfn_listini_versioni_guard_per_stato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_versioni_guard_per_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: che cosa si cambia di una versione di listino nello
--   stato in cui e' (BEFORE UPDATE), e se si cancella (BEFORE
--   DELETE). Vedi l'intestazione del changeSet 20261028-09.
DECLARE
    v_stato  config.stati_doc_listino_versioni.codice_interno%TYPE;
    -- Nomi di colonna della tabella: nessuna colonna di cui
    -- siano il riflesso.
    v_libere text[] := ARRAY['data_update', 'user_update', 'tx_id', 'validita',
                             'stato_doc_listino_versione_id'];
    v_campo  text;
BEGIN
    SELECT s.codice_interno INTO v_stato
      FROM config.stati_doc_listino_versioni s
     WHERE s.id = OLD.stato_doc_listino_versione_id;

    IF TG_OP = 'DELETE' THEN
        IF v_stato IS DISTINCT FROM 'BOZZA' THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', TG_NAME::text, 'E_LISTINO_VERSIONE_NON_ELIMINABILE',
                jsonb_build_object('versione_id', OLD.id, 'listino_id', OLD.listino_id,
                                   'stato', v_stato),
                OLD.tx_id,
                OLD.codice_versione::text,
                COALESCE(v_stato, 'NULL'));
        END IF;
        RETURN OLD;
    END IF;

    IF v_stato = 'BOZZA' THEN
        RETURN NEW;
    END IF;

    -- ATTIVA: in piu' si cambia valido_al. CHIUSA: niente.
    IF v_stato = 'ATTIVA' THEN
        v_libere := array_append(v_libere, 'valido_al');
    END IF;

    -- Il primo campo cambiato fuori da quelli liberi, nell'ordine
    -- delle colonne della tabella.
    SELECT a.attname INTO v_campo
      FROM pg_catalog.pg_attribute a
     WHERE a.attrelid = TG_RELID
       AND a.attnum > 0
       AND NOT a.attisdropped
       AND a.attname <> ALL (v_libere)
       AND (to_jsonb(NEW) -> a.attname) IS DISTINCT FROM (to_jsonb(OLD) -> a.attname)
     ORDER BY a.attnum
     LIMIT 1;

    IF FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, 'E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE',
            jsonb_build_object('versione_id', OLD.id, 'listino_id', OLD.listino_id,
                               'stato', v_stato, 'campo', v_campo),
            NEW.tx_id,
            OLD.codice_versione::text,
            COALESCE(v_stato, 'NULL'),
            v_campo);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_versioni_guard_per_stato()
IS 'Guard di una versione di listino, stato per stato (BEFORE UPDATE e BEFORE DELETE): BOZZA tutto si cambia e si cancella; ATTIVA si cambia solo valido_al (la chiusura programmata, e quella delle precedenti all''attivazione di una nuova); CHIUSA niente. Si cancella solo una BOZZA (E_LISTINO_VERSIONE_NON_ELIMINABILE); un altro campo cambiato fuori dalla BOZZA: E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE, col primo campo nell''ordine delle colonne. Lo stato non e'' un campo di questa regola (guard di transizione, porta); le colonne d''audit e la generata validita non contano. Prima la regola stava nel backend (listini_service._VERSIONE_PATCH_ALLOWED_BY_STATE, fn_delete_versione), e il database ne aveva solo le date della CHIUSA (vendite.trgfn_listini_versioni_guard_date_chiusa, ritirata qui). Brief: brief-modello-documento-vendita §16 (L-5, Tid 2026-10-28).';
```

</div>

---
{% include-markdown "signature-core.md" %}
