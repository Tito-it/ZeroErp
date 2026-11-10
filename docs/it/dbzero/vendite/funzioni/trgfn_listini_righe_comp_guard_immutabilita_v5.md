{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_righe_comp_guard_immutabilita_v5.md" %}
# ⚙️ Funzione `trgfn_listini_righe_comp_guard_immutabilita_v5`

```sql
CREATE FUNCTION trgfn_listini_righe_comp_guard_immutabilita_v5()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_righe_comp_guard_immutabilita_v5()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: BEFORE INS/UPD/DEL su listini_righe_componenti — immutabilita'.
--   INSERT e DELETE solo in versione BOZZA; fuori dalla bozza i campi
--   core (prezzo, iva_id, valido_dal, valido_al) non cambiano.
--   Eccezione: la porta della chiusura del legame (GUC
--   zeroerp.legame_distinta_chiudi = id del legame, col proprietario
--   della tabella) accorcia la sola valido_al.
--   Il periodo si legge da valido_dal/valido_al: validita e' STORED
--   generated, non visibile nei BEFORE trigger.
DECLARE
    v_stato   config.stati_doc_listino_versioni.codice_interno%TYPE;
    v_riga_id vendite.listini_righe_componenti.id%TYPE;
    v_versione_id vendite.listini_righe_componenti.listino_versione_id%TYPE;
    v_porta   text := COALESCE(current_setting('zeroerp.legame_distinta_chiudi', true), '');
BEGIN
    v_riga_id     := CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END;
    v_versione_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.listino_versione_id
                          ELSE NEW.listino_versione_id END;

    -- Legge stato versione
    SELECT s.codice_interno INTO v_stato
      FROM vendite.listini_versioni lv
      JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
     WHERE lv.id = v_versione_id;

    -- DELETE: solo in versione BOZZA, come le righe (fuori dalla bozza:
    -- attivo = FALSE). Una versione che non si legge non e' una bozza.
    IF TG_OP = 'DELETE' THEN
        IF v_stato IS DISTINCT FROM 'BOZZA' THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', TG_NAME, 'E_RIGA_LISTINO_VERSIONE_CHIUSA',
                jsonb_build_object(
                    'operazione',          'DELETE',
                    'hint',                'Usare attivo=FALSE per disattivare la riga.',
                    'stato_versione',      v_stato,
                    'listino_versione_id', v_versione_id,
                    'riga_id',             v_riga_id
                ),
                NULL::uuid,
                'DELETE', v_riga_id::text, COALESCE(v_stato, 'NULL')
            );
        END IF;
        RETURN OLD;
    END IF;

    -- INSERT: solo in versione BOZZA
    IF TG_OP = 'INSERT' AND COALESCE(v_stato, 'BOZZA') <> 'BOZZA' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME, 'E_RIGA_LISTINO_VERSIONE_CHIUSA',
            jsonb_build_object(
                'operazione',         'INSERT',
                'stato_versione',     v_stato,
                'listino_versione_id', NEW.listino_versione_id
            ),
            NULL::uuid,
            'INSERT', v_riga_id::text, v_stato
        );
    END IF;

    -- UPDATE campi core: bloccato se versione non BOZZA.
    IF TG_OP = 'UPDATE' AND COALESCE(v_stato, 'BOZZA') <> 'BOZZA' THEN
        IF NEW.prezzo    IS DISTINCT FROM OLD.prezzo
           OR NEW.iva_id    IS DISTINCT FROM OLD.iva_id
           OR NEW.valido_dal IS DISTINCT FROM OLD.valido_dal
           OR NEW.valido_al  IS DISTINCT FROM OLD.valido_al
        THEN
            -- La porta della chiusura del legame: solo la fine, solo
            -- piu' corta, solo per il legame della riga, solo dal verbo.
            IF v_porta = OLD.articolo_componente_id::text
               AND script.fn_is_proprietario_tabella('vendite.listini_righe_componenti'::regclass)
               AND NEW.prezzo     IS NOT DISTINCT FROM OLD.prezzo
               AND NEW.iva_id     IS NOT DISTINCT FROM OLD.iva_id
               AND NEW.valido_dal IS NOT DISTINCT FROM OLD.valido_dal
               AND NEW.valido_al IS NOT NULL
               AND NEW.valido_al < COALESCE(OLD.valido_al, 'infinity'::date)
            THEN
                RETURN NEW;
            END IF;

            PERFORM script.fn_log_and_raise_error(
                'vendite', TG_NAME, 'E_RIGA_LISTINO_VERSIONE_CHIUSA',
                jsonb_build_object(
                    'operazione',         'UPDATE_CAMPI_CORE',
                    'stato_versione',     v_stato,
                    'listino_versione_id', NEW.listino_versione_id,
                    'riga_id',            NEW.id
                ),
                NULL::uuid,
                'UPDATE', NEW.id::text, v_stato
            );
        END IF;
    END IF;

    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_righe_comp_guard_immutabilita_v5()
IS 'Trigger BEFORE INS/UPD/DEL su vendite.listini_righe_componenti: l''immutabilita'' dei prezzi bundle fuori dalla bozza. INSERT e DELETE solo in versione BOZZA (fuori dalla bozza: attivo = FALSE; una bozza si elimina con le sue righe da vendite.fn_elimina_versione_listino). Fuori dalla bozza prezzo, iva_id, valido_dal e valido_al non cambiano. Una sola eccezione, la chiusura del legame di distinta: con la GUC transazionale zeroerp.legame_distinta_chiudi = id del legame della riga (articolo_componente_id) e il proprietario della tabella (script.fn_is_proprietario_tabella), la riga accorcia la sola valido_al (non NULL, prima della fine di adesso) e il resto resta fermo. La porta l''apre solo il verbo catalogo.fn_chiudi_legame_distinta (SECURITY DEFINER), che chiede il permesso e la conferma: il prezzo sta dentro il periodo del legame (FK temporale fk_listrighe_comp_articoli_comp_temporal) e chiudendo il legame si chiude anche lui. Lo stato della versione si legge dal vocabolario config.stati_doc_listino_versioni (codice_interno). Raise E_RIGA_LISTINO_VERSIONE_CHIUSA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
