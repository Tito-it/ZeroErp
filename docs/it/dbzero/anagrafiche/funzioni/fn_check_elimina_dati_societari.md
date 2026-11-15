# ⚙️ Funzione `fn_check_elimina_dati_societari`

```sql
CREATE FUNCTION fn_check_elimina_dati_societari(p_soggetto_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_check_elimina_dati_societari(p_soggetto_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_motivi jsonb := '[]'::jsonb;
    v_natura record;
BEGIN
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_check_elimina_dati_societari', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_soggetto_id', 'valore', NULL),
            NULL::uuid,
            'il soggetto e'' obbligatorio');
    END IF;

    SELECT tsd.dati_societari_policy,
           COALESCE(tsd.descrizione, tsd.codice_interno) AS nome
      INTO v_natura
      FROM anagrafiche.soggetti s
      JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
     WHERE s.id = p_soggetto_id;

    IF FOUND AND v_natura.dati_societari_policy = 'REQUIRED'
       AND EXISTS (SELECT 1 FROM anagrafiche.dati_societari d
                    WHERE d.soggetto_id = p_soggetto_id) THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_DATI_SOCIETARI_NON_ELIMINABILI',
            'reason',     'NATURA_LI_RICHIEDE',
            'reason_key', 'anagrafiche.soggetti.dati_societari_elimina_blocco.natura_li_richiede',
            'dettaglio',  jsonb_build_object('campo', 'tipo_soggetto_dettaglio_id',
                                             'soggetto_id', p_soggetto_id),
            'valori',     jsonb_build_array(v_natura.nome));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_check_elimina_dati_societari(p_soggetto_id uuid)
IS 'I motivi per cui i dati societari del soggetto non si possono eliminare: check pura, array di {codice, reason, reason_key, dettaglio, valori}, [] se si puo'' o se non c''e'' niente da eliminare. Un motivo solo: la natura attuale li pretende (dati_societari_policy REQUIRED), E_DATI_SOCIETARI_NON_ELIMINABILI. Natura NULL: nessuna pretesa. Soggetto NULL: E_PARAMETRO_INVALIDO. La legge anagrafiche.fn_elimina_dati_societari, che solleva il primo motivo, e chi spegne l''azione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
