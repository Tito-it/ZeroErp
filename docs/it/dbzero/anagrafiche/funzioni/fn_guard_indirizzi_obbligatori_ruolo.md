# ⚙️ Funzione `fn_guard_indirizzi_obbligatori_ruolo`

```sql
CREATE FUNCTION fn_guard_indirizzi_obbligatori_ruolo(p_soggetto_ruolo_id bigint, p_tx_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_indirizzi_obbligatori_ruolo(p_soggetto_ruolo_id bigint, p_tx_id uuid)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    c_chi           CONSTANT text := 'anagrafiche.fn_guard_indirizzi_obbligatori_ruolo';
    v_tipo_ruolo_id anagrafiche.soggetti_ruoli.tipo_ruolo_id%TYPE;
    v_natura_id     anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE;
    v_tipo_id       config.tipi_ruolo_tipi_indirizzo.tipo_indirizzo_id%TYPE;
    v_ripiego_id    config.tipi_ruolo_tipi_indirizzo.fallback_tipo_indirizzo_id%TYPE;
    v_ruolo_nome    config.tipi_ruoli.descrizione%TYPE;
BEGIN
    IF p_soggetto_ruolo_id IS NULL OR p_soggetto_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('soggetto_ruolo_id', p_soggetto_ruolo_id),
            p_tx_id,
            c_chi,
            'il ruolo da controllare non e'' indicato');
    END IF;

    SELECT sr.tipo_ruolo_id, s.tipo_soggetto_dettaglio_id
      INTO v_tipo_ruolo_id, v_natura_id
      FROM anagrafiche.soggetti_ruoli sr
      JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
     WHERE sr.id = p_soggetto_ruolo_id;

    -- Il ruolo non c'e' piu': cancellato nella stessa transazione,
    -- insieme ai suoi indirizzi. Niente da completare.
    IF NOT FOUND THEN
        RETURN;
    END IF;

    SELECT o.tipo_indirizzo_id, o.ripiego_tipo_indirizzo_id
      INTO v_tipo_id, v_ripiego_id
      FROM anagrafiche.fn_indirizzi_obbligatori_ruolo(
               v_tipo_ruolo_id, v_natura_id, script.fn_data_operativa()) o
     WHERE NOT EXISTS (
             SELECT 1
               FROM anagrafiche.indirizzi i
              WHERE i.soggetto_ruolo_id = p_soggetto_ruolo_id
                AND (i.tipo_indirizzo_id = o.tipo_indirizzo_id
                     OR i.tipo_indirizzo_id = o.ripiego_tipo_indirizzo_id))
     ORDER BY o.tipo_indirizzo_id
     LIMIT 1;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    SELECT tr.descrizione INTO v_ruolo_nome
      FROM config.tipi_ruoli tr
     WHERE tr.id = v_tipo_ruolo_id;

    -- Valori per descrizione, nell'ordine della frase: il ruolo,
    -- poi il tipo richiesto col suo ripiego. Gli id nel contesto.
    PERFORM script.fn_log_and_raise_error(
        'anagrafiche', c_chi, 'E_INDIRIZZO_OBBLIGATORIO_MANCANTE',
        jsonb_build_object(
            'soggetto_ruolo_id',          p_soggetto_ruolo_id,
            'tipo_ruolo_id',              v_tipo_ruolo_id,
            'tipo_soggetto_dettaglio_id', v_natura_id,
            'tipo_indirizzo_id_required', v_tipo_id,
            'fallback_tipo_indirizzo_id', v_ripiego_id),
        p_tx_id,
        COALESCE(v_ruolo_nome, v_tipo_ruolo_id::text),
        COALESCE(anagrafiche.fn_nomi_tipo_indirizzo_richiesto(v_tipo_id, v_ripiego_id),
                 v_tipo_id::text));
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_indirizzi_obbligatori_ruolo(p_soggetto_ruolo_id bigint, p_tx_id uuid)
IS 'Guard: il ruolo deve avere, fra i suoi indirizzi (anagrafiche.indirizzi, istanze comprese), ogni tipo che il requisito del ruolo chiede (anagrafiche.fn_indirizzi_obbligatori_ruolo, sul tipo di ruolo e sulla natura del soggetto, il giorno di script.fn_data_operativa()), oppure il suo ripiego. Al primo mancante, per tipo richiesto, E_INDIRIZZO_OBBLIGATORIO_MANCANTE coi valori della frase nell''ordine tipo di ruolo e tipo richiesto col ripiego, per descrizione (anagrafiche.fn_nomi_tipo_indirizzo_richiesto); gli id nel contesto. Ruolo che non esiste (cancellato nella stessa transazione): tace. Id NULL o non positivo: E_SCRIPT_CHIAMATA_NON_VALIDA. Il tx_id va al log dell''errore. Sede unica del controllo del layer RUOLO: la chiamano i constraint trigger differiti di anagrafiche.soggetti_ruoli (anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required), di anagrafiche.indirizzi (anagrafiche.trgfn_indirizzi_guard_obbligatori_ruolo) e di anagrafiche.soggetti al cambio di natura (anagrafiche.trgfn_soggetti_guard_obbligatori_ruoli). Gemello di anagrafiche.fn_guard_indirizzi_obbligatori_soggetto, il layer SOGGETTO. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
