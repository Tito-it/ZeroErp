{% include-markdown "it/dbzero/magazzino/manual/fn_aggiungi_riga_inventario.md" %}
# ⚙️ Funzione `fn_aggiungi_riga_inventario`

```sql
CREATE FUNCTION fn_aggiungi_riga_inventario(p_inventario_id bigint, p_articolo_id uuid, p_qta_contata numeric, p_campi jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_aggiungi_riga_inventario(p_inventario_id bigint, p_articolo_id uuid, p_qta_contata numeric, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente    config.user_override_oggetti.auth_user_id%TYPE;
    v_campi     jsonb := COALESCE(p_campi, '{}'::jsonb);
    c_argomenti CONSTANT text[] := ARRAY['articolo_id', 'qta_contata'];
BEGIN
    -- Scopo: il gesto «aggiungi una riga contata» all'inventario
    --   p_inventario_id. Ritorna l'id della riga.
    v_utente := script.fn_utente_di_sessione('magazzino.fn_aggiungi_riga_inventario');
    PERFORM script.fn_guard_livello(v_utente, 'magazzino', 'inventari', 'TUTTO');
    PERFORM magazzino.fn_documento_interno_blocca(
        'INVENTARIO', p_inventario_id, v_utente, 'magazzino.fn_aggiungi_riga_inventario');
    PERFORM script.fn_guard_campi_ammessi(
        v_campi,
        ARRAY(SELECT c
                FROM unnest(magazzino.fn_documento_interno_colonne_ammesse(
                                'INVENTARIO', 'riga', 'crea')) AS c
               WHERE c <> ALL (c_argomenti)),
        'magazzino', 'magazzino.fn_aggiungi_riga_inventario',
        jsonb_build_object('inventario_id', p_inventario_id));

    RETURN (script.fn_scrivi_riga_da_jsonb(
                'magazzino.inventari_righe'::regclass,
                jsonb_strip_nulls(v_campi || jsonb_build_object(
                                     'inventario_id', p_inventario_id,
                                     'articolo_id',   p_articolo_id,
                                     'qta_contata',   p_qta_contata)))
            ->> 'id')::bigint;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_aggiungi_riga_inventario(p_inventario_id bigint, p_articolo_id uuid, p_qta_contata numeric, p_campi jsonb)
IS 'VERBO: il gesto «aggiungi una riga contata» all''inventario p_inventario_id: articolo e quantita'' contata sono argomenti. Prima riga script.fn_guard_livello(utente, magazzino, inventari, TUTTO): sotto il livello, o senza utente, E_PERMESSO_NEGATO. La testata nel perimetro, presa FOR UPDATE (magazzino.fn_documento_interno_blocca), altrimenti E_MAG_DOCUMENTO_NON_TROVATO. In p_campi le colonne della lista crea di magazzino.fn_documento_interno_colonne_ammesse(INVENTARIO, riga, crea) tolti gli argomenti: ubicazione, lotto, seriale, costo unitario; le assenti e le null al DEFAULT; una chiave fuori lista: E_CAMPO_NON_AMMESSO col suo nome. La testata in DRAFT, la posizione, le quantita'' e la coerenza dell''azienda li dicono i guard e i vincoli della riga. qta_sistema non e'' un campo: la scrive la registrazione. SECURITY DEFINER del proprietario, search_path bloccato. Ritorna l''id della riga.';
```

</div>

---
{% include-markdown "signature-core.md" %}
