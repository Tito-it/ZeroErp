{% include-markdown "it/dbzero/catalogo/manual/fn_articoli_ammessi.md" %}
# ⚙️ Funzione `fn_articoli_ammessi`

```sql
CREATE FUNCTION fn_articoli_ammessi(p_documento text, p_documento_id bigint, p_search text, p_limit integer, p_tipo_eccezione vendite.tipo_eccezione_contratto, p_articolo_padre_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_articoli_ammessi(p_documento text, p_documento_id bigint, p_search text DEFAULT NULL::text, p_limit integer DEFAULT 50, p_tipo_eccezione vendite.tipo_eccezione_contratto DEFAULT NULL::vendite.tipo_eccezione_contratto, p_articolo_padre_id uuid DEFAULT NULL::uuid)
 RETURNS TABLE(articolo_id uuid, codice character varying, descrizione character varying, motivo jsonb, ordine integer)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_contesto jsonb;
    v_termine  text := lower(btrim(COALESCE(p_search, '')));
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il picker degli articoli di una riga: i candidati della
    --   ricerca col primo motivo per cui il documento non li
    --   ammette (NULL = ammesso), prima gli ammessi. Il motivo
    --   viene dalla check dei guard (A-2): picker e guard non
    --   possono dissentire.
    -- =========================================================

    -- L'id del documento (A-1): ogni documento con testata.
    IF p_documento_id IS NULL
       AND p_documento IN ('PREVENTIVO', 'ORDINE_VENDITA', 'DDT_VENDITA',
                           'OFFERTA_COMMERCIALE', 'CONTRATTO',
                           'LISTINO_VERSIONE') THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo',
            'catalogo.fn_articoli_ammessi',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_documento_id', 'documento', p_documento),
            NULL::uuid,
            'p_documento_id obbligatorio per ' || p_documento);
    END IF;

    IF p_limit IS NOT NULL AND p_limit < 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo',
            'catalogo.fn_articoli_ammessi',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_limit', 'valore', p_limit),
            NULL::uuid,
            'p_limit deve essere almeno 1 (NULL = nessun tetto)');
    END IF;

    -- Il lato documento, una volta; valida anche p_documento,
    -- p_tipo_eccezione e p_articolo_padre_id.
    v_contesto := script.fn_articolo_riga_contesto(
        p_documento, p_documento_id, p_tipo_eccezione, p_articolo_padre_id);

    RETURN QUERY
    SELECT g.id,
           g.codice,
           g.descrizione,
           g.motivi -> 0,
           (row_number() OVER (ORDER BY (g.motivi -> 0) IS NOT NULL, g.codice, g.id))::integer
      FROM (
            -- p_scelta_nuova = true: il picker propone una scelta nuova, quindi
            -- l'articolo ritirato esce fra gli esclusi col motivo OBSOLETO, lo
            -- stesso che il guard di riga solleva (brief-db-articoli-obsoleto-dal).
            SELECT a.id, a.codice, a.descrizione,
                   script.fn_check_articolo_riga_su_contesto(v_contesto, a.id, NULL, true) AS motivi
              FROM catalogo.articoli a
             WHERE a.attivo
               AND (v_termine = ''
                    OR strpos(lower(a.codice), v_termine) > 0
                    OR strpos(lower(a.descrizione), v_termine) > 0)
           ) g
     ORDER BY (g.motivi -> 0) IS NOT NULL, g.codice, g.id
     LIMIT p_limit;
END;
$function$

COMMENT ON FUNCTION catalogo.fn_articoli_ammessi(p_documento text, p_documento_id bigint, p_search text, p_limit integer, p_tipo_eccezione vendite.tipo_eccezione_contratto, p_articolo_padre_id uuid)
IS 'Sede unica del picker degli articoli di una riga (R-2, A-7): dato il documento (codice di config.tipi_entita: PREVENTIVO | ORDINE_VENDITA | DDT_VENDITA | OFFERTA_COMMERCIALE | CONTRATTO | LISTINO_VERSIONE | ARTICOLO | PROMO_ARTICOLO) e il suo id (A-1: obbligatorio, E_PARAMETRO_INVALIDO, tranne ARTICOLO, che vuole p_articolo_padre_id, e PROMO_ARTICOLO), gli articoli ATTIVI che la ricerca trova (p_search: «contiene», senza maiuscole, su codice o descrizione, letterale; vuoto = tutti), {articolo_id, codice, descrizione, motivo, ordine}: motivo = il PRIMO motivo della check per tipo di riga ({codice, reason, reason_key, dettaglio, valori}; NULL = ammesso), cioe'' quello che il guard di tabella solleverebbe scrivendo la riga; prima gli ammessi, poi per codice; ordine = la posizione. p_tipo_eccezione per offerta e contratto (AGGIUNTA | OVERRIDE | ESCLUSIONE), obbligatorio. Il tetto (p_limit, NULL = nessuno, almeno 1) lo sceglie il chiamante; la check gira su ogni articolo trovato, prima del tetto. Il composito della versione di listino esce con COMPOSITO_COME_BUNDLE: nella versione entra come bundle, coi componenti. Due meta'' della stessa check dei guard (A-2): script.fn_articolo_riga_contesto (il documento, letto una volta: R-5) e script.fn_check_articolo_riga_su_contesto (i motivi). Sotto RLS (SECURITY INVOKER). Nasce il 2026-10-14, brief-db-articoli-ammessi-per-documento (Lotto 4, §9.4); prende il posto dei filtri liberi di catalogo_repository.lookup_articoli per le righe di documento (giro BE/FE). ⭐ rev 2026-11-05 (20261105-12, brief-db-articoli-obsoleto-dal §4): il picker giudica come SCELTA NUOVA (p_scelta_nuova = true della check): un articolo ritirato (catalogo.articoli.obsoleto_dal raggiunta, script.fn_e_obsoleto) resta nell''elenco fra gli esclusi col motivo OBSOLETO (E_ARTICOLO_OBSOLETO, il primo), lo stesso che il guard di riga solleva.';
```

</div>

---
{% include-markdown "signature-core.md" %}
