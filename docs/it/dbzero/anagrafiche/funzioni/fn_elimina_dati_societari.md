{% include-markdown "it/dbzero/anagrafiche/manual/fn_elimina_dati_societari.md" %}
# ⚙️ Funzione `fn_elimina_dati_societari`

```sql
CREATE FUNCTION fn_elimina_dati_societari(p_soggetto_id uuid)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_elimina_dati_societari(p_soggetto_id uuid)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_eliminati integer;  -- righe cancellate: un conteggio, nessuna colonna dietro
BEGIN
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_elimina_dati_societari', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_soggetto_id', 'valore', NULL),
            NULL::uuid,
            'il soggetto e'' obbligatorio');
    END IF;

    -- La riga del soggetto si blocca: un cambio di natura concorrente aspetta,
    -- e la natura che la check giudica e' quella che resta.
    PERFORM 1 FROM anagrafiche.soggetti s WHERE s.id = p_soggetto_id FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_elimina_dati_societari',
            'E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO',
            jsonb_build_object('soggetto_id', p_soggetto_id),
            NULL::uuid,
            p_soggetto_id::text);
    END IF;

    PERFORM script.fn_raise_primo_motivo_se_presente(
        'database', 'anagrafiche.fn_elimina_dati_societari',
        anagrafiche.fn_check_elimina_dati_societari(p_soggetto_id));

    DELETE FROM anagrafiche.dati_societari d WHERE d.soggetto_id = p_soggetto_id;
    GET DIAGNOSTICS v_eliminati = ROW_COUNT;

    RETURN v_eliminati > 0;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_elimina_dati_societari(p_soggetto_id uuid)
IS 'Il verbo che elimina a mano la riga di anagrafiche.dati_societari del soggetto: blocca la riga del soggetto, solleva il primo motivo di anagrafiche.fn_check_elimina_dati_societari (la natura attuale li pretende: E_DATI_SOCIETARI_NON_ELIMINABILI), cancella. Vero se ha cancellato, falso se non c''era niente da eliminare. Lo storico conserva la riga. E'' un''azione separata dal cambio di natura, che non la chiama: chi cambia una ditta in privato elimina prima i dati societari. SECURITY DEFINER: l''applicazione non scrive anagrafiche.dati_societari direttamente, e questa e'' la porta della cancellazione, come anagrafiche.fn_scrivi_dati_societari lo e'' della scrittura; nessun guard di livello, il permesso resta al backend. Soggetto NULL: E_PARAMETRO_INVALIDO; inesistente: E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
