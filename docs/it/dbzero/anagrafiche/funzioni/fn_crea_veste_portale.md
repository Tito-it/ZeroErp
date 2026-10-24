{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_veste_portale.md" %}
# ⚙️ Funzione `fn_crea_veste_portale`

```sql
CREATE FUNCTION fn_crea_veste_portale(p_auth_user_id integer, p_soggetto_ruolo_id bigint, p_ruolo_applicativo config.ruolo_applicativo, p_attivo boolean)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_veste_portale(p_auth_user_id integer, p_soggetto_ruolo_id bigint, p_ruolo_applicativo config.ruolo_applicativo, p_attivo boolean)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Creare la veste esterna di una credenziale su un ruolo
    --   (portale clienti, portale fornitori, shop), spenta o
    --   accesa. Ritorna l'id della riga di identita_digitali.
    --
    -- Regole:
    --   - una veste fuori dalle tre esterne, o un argomento
    --     NULL: E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - coerenza veste/ruolo, natura della credenziale,
    --     unicita': i guard della tabella.
    -- =========================================================
    IF p_auth_user_id IS NULL OR p_soggetto_ruolo_id IS NULL OR p_attivo IS NULL
       OR p_ruolo_applicativo IS NULL
       OR p_ruolo_applicativo NOT IN ('CLIENTE_PORTALE', 'FORNITORE_PORTALE', 'SHOP_CUSTOMER') THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_crea_veste_portale', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('auth_user_id',      p_auth_user_id,
                               'soggetto_ruolo_id', p_soggetto_ruolo_id,
                               'ruolo_applicativo', p_ruolo_applicativo,
                               'attivo',            p_attivo),
            NULL::uuid,
            'anagrafiche.fn_crea_veste_portale',
            'argomento mancante o veste che non e'' dei portali');
    END IF;

    RETURN (script.fn_scrivi_riga_da_jsonb(
                'anagrafiche.identita_digitali'::regclass,
                jsonb_build_object('auth_user_id',      p_auth_user_id,
                                   'soggetto_ruolo_id', p_soggetto_ruolo_id,
                                   'ruolo_applicativo', p_ruolo_applicativo,
                                   'attivo',            p_attivo))
            ->> 'id')::bigint;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_veste_portale(p_auth_user_id integer, p_soggetto_ruolo_id bigint, p_ruolo_applicativo config.ruolo_applicativo, p_attivo boolean)
IS 'BB (2026-10-18): crea la veste esterna di una credenziale su un ruolo, cioe'' la riga di anagrafiche.identita_digitali con ruolo_applicativo CLIENTE_PORTALE, FORNITORE_PORTALE o SHOP_CUSTOMER, spenta o accesa (p_attivo obbligatorio: l''invito la crea spenta, lo shop accesa). Ritorna l''id. Un argomento NULL o un''altra veste: E_SCRIPT_CHIAMATA_NON_VALIDA (la veste OPERATORE nasce dalle sue madri, anagrafiche.fn_crea_operatore_v2 e script.fn_crea_utente_tecnico, che portano perimetro e risorsa umana). Coerenza veste/ruolo, natura della credenziale e unicita'' le dicono i guard della tabella. Scrive con script.fn_scrivi_riga_da_jsonb. Non controlla il permesso ne'' il flusso dell''invito (backend). INVOKER. Prende il posto di PortaleRepository.create_identita_portale (2b-2) e degli INSERT delle vesti esterne nei pgTAP. Brief: brief-db-processi-accensione-per-ambiente (2b-1, lotto 6).';
```

</div>

---
{% include-markdown "signature-core.md" %}
