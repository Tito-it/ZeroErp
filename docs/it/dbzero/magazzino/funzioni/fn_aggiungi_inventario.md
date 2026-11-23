{% include-markdown "it/dbzero/magazzino/manual/fn_aggiungi_inventario.md" %}
# ⚙️ Funzione `fn_aggiungi_inventario`

```sql
CREATE FUNCTION fn_aggiungi_inventario(p_magazzino_id bigint, p_campi jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_aggiungi_inventario(p_magazzino_id bigint, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente config.user_override_oggetti.auth_user_id%TYPE;
    v_campi  jsonb := COALESCE(p_campi, '{}'::jsonb);
BEGIN
    -- Scopo: il gesto «nuovo inventario» dell'operatore nel
    --   magazzino p_magazzino_id. Ritorna l'id.
    v_utente := script.fn_utente_di_sessione('magazzino.fn_aggiungi_inventario');
    PERFORM script.fn_guard_livello(v_utente, 'magazzino', 'inventari', 'TUTTO');
    PERFORM magazzino.fn_guard_magazzino_nel_perimetro(
        p_magazzino_id, v_utente, 'magazzino.fn_aggiungi_inventario');
    PERFORM script.fn_guard_campi_ammessi(
        v_campi, magazzino.fn_documento_interno_colonne_ammesse('INVENTARIO', 'testata', 'crea'),
        'magazzino', 'magazzino.fn_aggiungi_inventario',
        jsonb_build_object('magazzino_id', p_magazzino_id));

    RETURN (script.fn_scrivi_riga_da_jsonb(
                'magazzino.inventari'::regclass,
                jsonb_strip_nulls(v_campi || jsonb_build_object('magazzino_id', p_magazzino_id)))
            ->> 'id')::bigint;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_aggiungi_inventario(p_magazzino_id bigint, p_campi jsonb)
IS 'VERBO: il gesto «nuovo inventario» dell''operatore nel magazzino p_magazzino_id. Prima riga script.fn_guard_livello(utente, magazzino, inventari, TUTTO): sotto il livello, o senza utente, E_PERMESSO_NEGATO. Il magazzino nel perimetro, altrimenti E_MAG_MAGAZZINO_NON_TROVATO (magazzino.fn_guard_magazzino_nel_perimetro). In p_campi le colonne della lista crea di magazzino.fn_documento_interno_colonne_ammesse(INVENTARIO, testata, crea): data, descrizione e la provenienza (sorgente_*); le assenti e le null al DEFAULT; una chiave fuori lista: E_CAMPO_NON_AMMESSO col suo nome (script.fn_guard_campi_ammessi). Nasce in DRAFT. Provenienza, perimetro e magazzino attivo li dicono i guard della tabella. SECURITY DEFINER del proprietario, search_path bloccato. Ritorna l''id.';
```

</div>

---
{% include-markdown "signature-core.md" %}
