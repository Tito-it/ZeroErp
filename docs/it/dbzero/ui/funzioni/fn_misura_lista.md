{% include-markdown "it/dbzero/ui/manual/fn_misura_lista.md" %}
# ⚙️ Funzione `fn_misura_lista`

```sql
CREATE FUNCTION fn_misura_lista(p_lista_codice character varying, p_auth_user_id integer, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_misura_lista(p_lista_codice character varying, p_auth_user_id integer, p_emittente_fiscale_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: le righe per pagina di una lista per un utente, con la cascata della
--   lista (preferenza, preset di base, default dell'uso), senza risolvere
--   colonne e permessi.
DECLARE
    v_lista   ui.lista_definizione%ROWTYPE;
    -- La veste corrente dalla GUC: senza veste il preset di ruolo non concorre.
    v_ruolo   config.ruolo_applicativo := ui.fn_veste_corrente();
    v_base_id ui.lista_preset.id%TYPE;
    v_pref    ui.misure_pagina.misura%TYPE;
    v_preset  ui.lista_preset.pagina_dimensione%TYPE;
BEGIN
    -- Lista assente o spenta: E_UI_LISTA_NON_TROVATA, dal BB.
    v_lista := ui.fn_lista_da_codice(p_lista_codice);

    -- La misura della preferenza; un valore che intero non e' vale «nessuna
    -- scelta», come nel resolver.
    SELECT ui.fn_intero_da_jsonb(pu.configurazione -> 'pagina_dimensione')
      INTO v_pref
      FROM ui.lista_preferenza_utente pu
     WHERE pu.auth_user_id = p_auth_user_id
       AND pu.lista_id     = v_lista.id;

    SELECT b.preset_id INTO v_base_id
      FROM ui.fn_preset_di_base('lista', v_lista.id, p_auth_user_id, v_ruolo,
                                p_emittente_fiscale_id) b;
    IF v_base_id IS NOT NULL THEN
        SELECT lp.pagina_dimensione INTO v_preset
          FROM ui.lista_preset lp
         WHERE lp.id = v_base_id;
    END IF;

    RETURN (SELECT r.misura
              FROM ui.fn_misura_pagina_risolta(v_pref, v_preset, v_lista.uso_misura) r);
END;
$function$

COMMENT ON FUNCTION ui.fn_misura_lista(p_lista_codice character varying, p_auth_user_id integer, p_emittente_fiscale_id bigint)
IS 'Le righe per pagina di una lista per un utente: la misura che ui.fn_resolve_lista_config risponde in pagina_dimensione, senza risolvere colonne e permessi. La cascata è ui.fn_misura_pagina_risolta: la misura della preferenza se è nel catalogo ui.misure_pagina, altrimenti quella del preset di base (ui.fn_preset_di_base, la stessa scelta del resolver) se è nel catalogo, altrimenti il default dell''uso della lista (ui.lista_definizione.uso_misura). Mai NULL. Gemella di ui.fn_ordinamento_lista: la legge il backend per una lista configurabile chiamata senza limit. Lista assente o spenta: E_UI_LISTA_NON_TROVATA (ui.fn_lista_da_codice); catalogo senza il default dell''uso: E_UI_MISURA_PAGINA_DEFAULT_MANCANTE. La veste la legge ui.fn_veste_corrente. STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
