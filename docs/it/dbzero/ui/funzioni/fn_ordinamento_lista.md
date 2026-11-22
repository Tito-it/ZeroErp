{% include-markdown "it/dbzero/ui/manual/fn_ordinamento_lista.md" %}
# ⚙️ Funzione `fn_ordinamento_lista`

```sql
CREATE FUNCTION fn_ordinamento_lista(p_lista_codice character varying, p_auth_user_id integer, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_ordinamento_lista(p_lista_codice character varying, p_auth_user_id integer, p_emittente_fiscale_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: l'ordinamento di partenza di una lista per un utente: quello del
--   preset di base, senza le voci delle colonne che l'utente non puo'
--   ordinare, con il campo sorgente di ogni voce.
DECLARE
    v_lista   ui.lista_definizione%ROWTYPE;
    -- La veste corrente dalla GUC: senza veste il preset di ruolo non concorre.
    v_ruolo   config.ruolo_applicativo := ui.fn_veste_corrente();
    v_base_id ui.lista_preset.id%TYPE;
    v_ord     ui.lista_preset.ordinamento_default%TYPE;
BEGIN
    -- Lista assente o spenta: E_UI_LISTA_NON_TROVATA, dal BB.
    v_lista := ui.fn_lista_da_codice(p_lista_codice);

    SELECT b.preset_id INTO v_base_id
      FROM ui.fn_preset_di_base('lista', v_lista.id, p_auth_user_id, v_ruolo,
                                p_emittente_fiscale_id) b;
    IF v_base_id IS NULL THEN
        RETURN '[]'::jsonb;
    END IF;

    SELECT lp.ordinamento_default INTO v_ord
      FROM ui.lista_preset lp
     WHERE lp.id = v_base_id;
    IF v_ord IS NULL OR jsonb_typeof(v_ord) <> 'array' THEN
        RETURN '[]'::jsonb;
    END IF;

    RETURN COALESCE(
        (SELECT jsonb_agg(jsonb_build_object('col',            lc.codice,
                                             'dir',            e.value ->> 'dir',
                                             'campo_sorgente', lc.campo_sorgente)
                          ORDER BY e.ord)
           FROM jsonb_array_elements(v_ord) WITH ORDINALITY AS e(value, ord)
           JOIN ui.lista_colonna lc
             ON lc.lista_id = v_lista.id
            AND lc.codice   = e.value ->> 'col'
            AND lc.attivo
            AND lc.ordinabile
            AND lc.campo_sorgente IS NOT NULL
           JOIN ui.fn_lista_colonne_livello(v_lista.id, p_auth_user_id, v_ruolo) lv
             ON lv.colonna_id = lc.id
          WHERE lv.livello_accesso <> 'BLOCCATO'
            AND e.value ->> 'dir' IN ('asc', 'desc')),
        '[]'::jsonb);
END;
$function$

COMMENT ON FUNCTION ui.fn_ordinamento_lista(p_lista_codice character varying, p_auth_user_id integer, p_emittente_fiscale_id bigint)
IS 'L''ordinamento di partenza di una lista per un utente: un elenco di {col, dir, campo_sorgente}, nell''ordine dell''ordinamento_default del preset di base (lo sceglie ui.fn_preset_di_base, come per ui.fn_resolve_lista_config). col è il codice della colonna, campo_sorgente il campo con cui il backend ordina, dir asc o desc. Escono le voci di una colonna spenta, non ordinabile, senza campo sorgente o BLOCCATO per l''utente (ui.fn_lista_colonne_livello, lo stesso calcolo della lista e della ricerca). Nessun preset di base, o un preset senza ordinamento: []. La preferenza non porta l''ordinamento: il clic sull''intestazione vale per la sessione. Lista assente o spenta: E_UI_LISTA_NON_TROVATA (ui.fn_lista_da_codice). La veste la legge ui.fn_veste_corrente. STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
