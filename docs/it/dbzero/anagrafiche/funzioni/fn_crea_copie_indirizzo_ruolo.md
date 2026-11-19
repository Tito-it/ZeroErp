# ⚙️ Funzione `fn_crea_copie_indirizzo_ruolo`

```sql
CREATE FUNCTION fn_crea_copie_indirizzo_ruolo(p_soggetto_ruolo_id bigint, p_elemento jsonb, p_istanza_utility_id bigint, p_tipi_indirizzo_codice_interno text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_copie_indirizzo_ruolo(p_soggetto_ruolo_id bigint, p_elemento jsonb, p_istanza_utility_id bigint, p_tipi_indirizzo_codice_interno text[])
 RETURNS bigint[]
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_el     jsonb;  -- l'elemento con l'istanza: nessuna colonna
    v_codice config.tipi_indirizzi.codice_interno%TYPE;
    v_ids    bigint[] := '{}';  -- vedi RETURNS
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scrivere l'elemento in uno o piu' tipi sulla chiave
    --   (ruolo, istanza) data. Ritorna gli id nuovi,
    --   nell'ordine dei tipi. Tutto o niente.
    --
    -- Regole:
    --   - istanza NULL = il ruolo: la chiave non si scrive;
    --   - ogni giudizio e' della singolare e dei guard.
    -- =========================================================
    v_el := p_elemento
            || jsonb_strip_nulls(jsonb_build_object(
                   'istanza_utility_id', p_istanza_utility_id));

    FOREACH v_codice IN ARRAY p_tipi_indirizzo_codice_interno LOOP
        v_ids := v_ids || anagrafiche.fn_crea_indirizzo_ruolo(
                     p_soggetto_ruolo_id,
                     v_el || jsonb_build_object('tipo_indirizzo_codice_interno', v_codice));
    END LOOP;

    RETURN v_ids;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_copie_indirizzo_ruolo(p_soggetto_ruolo_id bigint, p_elemento jsonb, p_istanza_utility_id bigint, p_tipi_indirizzo_codice_interno text[])
IS 'Building block dei verbi della copia verso il ruolo (anagrafiche.fn_copia_indirizzo_ruolo e anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo): scrive un elemento di indirizzo, senza tipo e senza istanza (quello di anagrafiche.fn_indirizzo_elemento_da_riga), in uno o piu'' tipi (codici interni, nell''ordine dato) sulla chiave di destinazione: il ruolo (istanza NULL) o una sua istanza. Tutto o niente; ritorna gli id delle righe nuove nello stesso ordine. Ogni riga la scrive la singolare anagrafiche.fn_crea_indirizzo_ruolo, che giudica il tipo sulla chiave di destinazione: tipo inesistente E_TIPO_INDIRIZZO_NON_TROVATO, gia'' presente (anche ripetuto nell''elenco) E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE, non ammesso dal tipo di ruolo E_TIPO_INDIRIZZO_NON_PERMESSO o dalla natura E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO. L''istanza di un altro soggetto la rifiuta il guard della tabella (E_ISTANZA_ALTRO_SOGGETTO). Non valida i parametri: lo fanno i verbi. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
