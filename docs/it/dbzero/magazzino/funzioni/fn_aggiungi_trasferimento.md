{% include-markdown "it/dbzero/magazzino/manual/fn_aggiungi_trasferimento.md" %}
# ⚙️ Funzione `fn_aggiungi_trasferimento`

```sql
CREATE FUNCTION fn_aggiungi_trasferimento(p_magazzino_id_from bigint, p_magazzino_id_to bigint, p_campi jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_aggiungi_trasferimento(p_magazzino_id_from bigint, p_magazzino_id_to bigint, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente    config.user_override_oggetti.auth_user_id%TYPE;
    v_campi     jsonb := COALESCE(p_campi, '{}'::jsonb);
    -- Le colonne che il verbo riceve come argomenti: non stanno in p_campi.
    c_argomenti CONSTANT text[] := ARRAY['magazzino_id_to'];
BEGIN
    -- Scopo: il gesto «nuovo trasferimento» dell'operatore dal
    --   magazzino p_magazzino_id_from a p_magazzino_id_to. Ritorna l'id.
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    PERFORM script.fn_guard_livello(v_utente, 'magazzino', 'trasferimenti', 'TUTTO');
    -- Tutti e due nel perimetro: un arrivo fuori perimetro e' «non
    -- trovato» come la partenza, non un emittente diverso.
    PERFORM magazzino.fn_guard_magazzino_nel_perimetro(
        p_magazzino_id_from, v_utente, 'magazzino.fn_aggiungi_trasferimento');
    PERFORM magazzino.fn_guard_magazzino_nel_perimetro(
        p_magazzino_id_to, v_utente, 'magazzino.fn_aggiungi_trasferimento');
    PERFORM script.fn_guard_campi_ammessi(
        v_campi,
        ARRAY(SELECT c
                FROM unnest(magazzino.fn_documento_interno_colonne_ammesse(
                                'TRASFERIMENTO', 'testata', 'crea')) AS c
               WHERE c <> ALL (c_argomenti)),
        'magazzino', 'magazzino.fn_aggiungi_trasferimento',
        jsonb_build_object('magazzino_id_from', p_magazzino_id_from,
                           'magazzino_id_to',   p_magazzino_id_to));

    RETURN (script.fn_scrivi_riga_da_jsonb(
                'magazzino.trasferimenti'::regclass,
                jsonb_strip_nulls(v_campi || jsonb_build_object(
                                     'magazzino_id_from', p_magazzino_id_from,
                                     'magazzino_id_to',   p_magazzino_id_to)))
            ->> 'id')::bigint;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_aggiungi_trasferimento(p_magazzino_id_from bigint, p_magazzino_id_to bigint, p_campi jsonb)
IS 'VERBO: il gesto «nuovo trasferimento» dell''operatore, dal magazzino p_magazzino_id_from a p_magazzino_id_to. Prima riga script.fn_guard_livello(utente, magazzino, trasferimenti, TUTTO): sotto il livello, o senza utente, E_PERMESSO_NEGATO. Partenza e arrivo nel perimetro, altrimenti E_MAG_MAGAZZINO_NON_TROVATO (magazzino.fn_guard_magazzino_nel_perimetro), senza dire se non esiste o non e'' suo. In p_campi le colonne della lista crea di magazzino.fn_documento_interno_colonne_ammesse(TRASFERIMENTO, testata, crea) tolto l''arrivo, che e'' un argomento: la data e la provenienza (sorgente_*); le assenti e le null al DEFAULT; una chiave fuori lista: E_CAMPO_NON_AMMESSO col suo nome (script.fn_guard_campi_ammessi). Nasce in DRAFT. Stesso emittente per partenza e arrivo, magazzini attivi, provenienza e perimetro li dicono i guard della tabella. Partenza e arrivo non cambiano dopo la nascita. SECURITY DEFINER del proprietario, search_path bloccato. Ritorna l''id.';
```

</div>

---
{% include-markdown "signature-core.md" %}
