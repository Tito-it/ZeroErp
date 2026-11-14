{% include-markdown "it/dbzero/documenti/manual/trgfn_template_documenti_versioni_protect_pubblicata.md" %}
# ⚙️ Funzione `trgfn_template_documenti_versioni_protect_pubblicata`

```sql
CREATE FUNCTION trgfn_template_documenti_versioni_protect_pubblicata()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_template_documenti_versioni_protect_pubblicata()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Una versione template fuori bozza (PUBBLICATA o OBSOLETA) non si
--   modifica: HTML, CSS, render engine, pagina, validita', forma dei
--   dati, template_documento_id, versione e stato restano quelli della
--   pubblicazione. Per ogni cambio si crea una nuova BOZZA.
--
-- Eccezione (una sola):
--   la chiusura che fa documenti.fn_pubblica_template_documento_versione
--   quando pubblica la versione successiva: PUBBLICATA -> OBSOLETA con
--   valido_al che si accorcia, ogni altra colonna protetta invariata, e
--   solo a porta aperta (zeroerp.allow_template_versione_chiusura_override
--   = 'on', che la funzione apre e richiude).
--
-- Errore:
--   E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE
BEGIN
  IF OLD.stato IN ('PUBBLICATA', 'OBSOLETA') THEN
    IF OLD.stato = 'PUBBLICATA'
       AND NEW.stato = 'OBSOLETA'
       AND current_setting('zeroerp.allow_template_versione_chiusura_override', true) = 'on'
       AND NEW.valido_al IS NOT NULL
       AND (OLD.valido_al IS NULL OR NEW.valido_al <= OLD.valido_al)
       AND (NEW.html_template, NEW.css_template, NEW.markdown_template,
            NEW.render_engine_id, NEW.formato_template, NEW.page_format,
            NEW.page_orientation, NEW.margin_top_mm, NEW.margin_right_mm,
            NEW.margin_bottom_mm, NEW.margin_left_mm, NEW.valido_dal,
            NEW.context_schema, NEW.versione_contesto,
            NEW.template_documento_id, NEW.versione)
           IS NOT DISTINCT FROM
           (OLD.html_template, OLD.css_template, OLD.markdown_template,
            OLD.render_engine_id, OLD.formato_template, OLD.page_format,
            OLD.page_orientation, OLD.margin_top_mm, OLD.margin_right_mm,
            OLD.margin_bottom_mm, OLD.margin_left_mm, OLD.valido_dal,
            OLD.context_schema, OLD.versione_contesto,
            OLD.template_documento_id, OLD.versione)
    THEN
      RETURN NEW;
    END IF;

    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_template_documenti_versioni_protect_pubblicata',
      'E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE',
      jsonb_build_object(
        'template_documento_id', OLD.template_documento_id,
        'versione', OLD.versione,
        'stato', OLD.stato,
        'stato_nuovo', NEW.stato
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_template_documenti_versioni_protect_pubblicata()
IS 'Guard A1: una versione template PUBBLICATA o OBSOLETA non si modifica, e il suo stato non torna indietro (E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE). Unica eccezione: la chiusura di documenti.fn_pubblica_template_documento_versione, da PUBBLICATA a OBSOLETA con valido_al accorciato e nient''altro cambiato, a porta zeroerp.allow_template_versione_chiusura_override aperta.';
```

</div>

---
{% include-markdown "signature-core.md" %}
