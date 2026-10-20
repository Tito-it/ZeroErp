{% include-markdown "it/dbzero/script/manual/fn_notify_permessi_catalogo.md" %}
# ⚙️ Funzione `fn_notify_permessi_catalogo`

```sql
CREATE FUNCTION fn_notify_permessi_catalogo(p_tabella text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_notify_permessi_catalogo(p_tabella text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: avvisare il backend che il catalogo o i profili dei permessi sono
--   cambiati, perche' svuoti la cache permessi di tutti (invalidate_all).
--   Canale 'permessi_catalogo', payload {"tabella": p_tabella}. Parte al
--   commit; su rollback no (brief-db-permessi-catalogo-notify-cache).
BEGIN
    IF p_tabella IS NULL OR btrim(p_tabella) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_notify_permessi_catalogo',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tabella', 'valore', p_tabella),
            NULL::uuid,
            'p_tabella deve essere NOT NULL e non vuoto'
        );
    END IF;

    PERFORM pg_notify(
        'permessi_catalogo',
        jsonb_build_object('tabella', p_tabella)::text
    );
END;
$function$

COMMENT ON FUNCTION script.fn_notify_permessi_catalogo(p_tabella text)
IS 'Emette NOTIFY sul canale permessi_catalogo con payload JSON {"tabella": p_tabella}: il listener del backend (processo listen_permessi) svuota la cache permessi di tutti (invalidate_all). Transazionale: parte al commit, non su rollback, payload identici della stessa transazione fusi in uno. Sede unica del nome del canale lato DB. Due consumatori: script.trgfn_notify_permessi_catalogo (trigger z90 per istruzione sulle sette tabelle del catalogo permessi) e la LEVA MANUALE SELECT script.fn_notify_permessi_catalogo(''manuale'') dopo una correzione fuori dall''app su una tabella che il trigger non copre (es. anagrafiche.identita_digitali, user_override_*). p_tabella NULL o vuoto -> E_PARAMETRO_INVALIDO. VOLATILE, INVOKER. Brief: brief-db-permessi-catalogo-notify-cache R1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
