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
--   DELETE). Vedi l'intestazione dei changeSet 20261028-09, -37
--   e 20261029-07.
DECLARE
    v_stato  config.stati_doc_listino_versioni.codice_interno%TYPE;
    v_iniziale config.stati_doc_listino_versioni.iniziale%TYPE;
    -- Nomi di colonna della tabella: nessuna colonna di cui
    -- siano il riflesso.
    v_libere text[] := ARRAY['data_update', 'user_update', 'tx_id', 'validita',
                             'stato_doc_listino_versione_id'];
    v_campo  text;
BEGIN
    SELECT s.codice_interno, s.iniziale INTO v_stato, v_iniziale
      FROM config.stati_doc_listino_versioni s
     WHERE s.id = OLD.stato_doc_listino_versione_id;

    -- Se si cancella lo dice script.fn_check_versione_listino_eliminabile
    -- (20261028-36): la stessa regola del verbo e del pulsante.
    IF TG_OP = 'DELETE' THEN
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'vendite', TG_NAME::text,
            script.fn_check_versione_listino_eliminabile(OLD.id),
            NULL,
            OLD.tx_id,
            jsonb_build_object('versione_id', OLD.id, 'listino_id', OLD.listino_id,
                               'stato', v_stato));
        RETURN OLD;
    END IF;

    -- In bozza (lo stato iniziale del vocabolario) tutto si cambia.
    IF v_iniziale THEN
        RETURN NEW;
    END IF;

    -- ATTIVA: in piu' si cambia valido_al (dai verbi, sotto).
    -- CHIUSA: niente.
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

    -- La fine di una ATTIVA: solo dalla porta dei verbi («Chiudi»,
    -- l'attivazione), per QUESTA versione, dal proprietario della
    -- tabella.
    IF v_stato = 'ATTIVA'
       AND NEW.valido_al IS DISTINCT FROM OLD.valido_al
       AND NOT (COALESCE(current_setting('zeroerp.listino_versione_fine', true), '') = OLD.id::text
                AND script.fn_is_proprietario_tabella(TG_RELID)) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, 'E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO',
            jsonb_build_object('versione_id', OLD.id, 'listino_id', OLD.listino_id,
                               'valido_al_prima', OLD.valido_al,
                               'valido_al', NEW.valido_al),
            NEW.tx_id,
            OLD.codice_versione::text);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_versioni_guard_per_stato()
IS 'Guard di una versione di listino, stato per stato (BEFORE UPDATE e BEFORE DELETE): in bozza, lo stato iniziale del vocabolario config.stati_doc_listino_versioni, tutto si cambia e si cancella; ATTIVA si cambia solo valido_al (la chiusura programmata, e quella delle precedenti all''attivazione di una nuova), e solo dalla porta dei verbi vendite.fn_programma_chiusura_versione_listino e vendite.fn_attiva_versione_listino (GUC transazionale zeroerp.listino_versione_fine = id della versione, e il proprietario della tabella, script.fn_is_proprietario_tabella; senza: E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO); CHIUSA niente. Se si cancella lo dice script.fn_check_versione_listino_eliminabile, la stessa regola del verbo vendite.fn_elimina_versione_listino e del pulsante (vendite.vw_listini_versioni_azioni), e il ramo DELETE ne solleva il primo motivo (fuori dalla bozza E_LISTINO_VERSIONE_NON_ELIMINABILE; una bozza citata da un documento E_LISTINO_VERSIONE_CITATA); un altro campo cambiato fuori dalla bozza: E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE, col primo campo nell''ordine delle colonne. Lo stato non e'' un campo di questa regola (guard di transizione, porta); le colonne d''audit e la generata validita non contano.';
```

</div>

---
{% include-markdown "signature-core.md" %}
