{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_fixture_crea_utente_tecnico.md" %}
# ⚙️ Funzione `fn_pgtap_fixture_crea_utente_tecnico`

```sql
CREATE FUNCTION fn_pgtap_fixture_crea_utente_tecnico(p_processo_codice text, p_emittente_codice character varying, p_profilo_codice character varying)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_fixture_crea_utente_tecnico(p_processo_codice text, p_emittente_codice character varying, p_profilo_codice character varying DEFAULT NULL::character varying)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo:
--   Fixture dei pgTAP: creare l'utente tecnico di un processo per un
--   emittente senza chiedere permessi, solo dove sono ammessi i dati di
--   sviluppo.
--
-- Regole:
--   - in PRODUZIONE: E_DATI_DI_SVILUPPO_IN_PRODUZIONE, prima di ogni scrittura;
--   - argomenti, regole e risultato: quelli di script.fn_crea_utente_tecnico,
--     tramite la sua primitiva script.fn_applica_crea_utente_tecnico.
DECLARE
    v_ambiente dbops.installazione.ambiente%TYPE;
BEGIN
    -- Il cancello: solo dove sono ammessi i dati di sviluppo.
    v_ambiente := script.fn_ambiente_installazione();
    IF NOT dbops.fn_dati_di_sviluppo_ammessi_su_valori(v_ambiente) THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_pgtap_fixture_crea_utente_tecnico',
            'E_DATI_DI_SVILUPPO_IN_PRODUZIONE',
            jsonb_build_object('ambiente', v_ambiente),
            NULL::uuid,
            v_ambiente);
    END IF;

    RETURN script.fn_applica_crea_utente_tecnico(p_processo_codice, p_emittente_codice, p_profilo_codice);
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_fixture_crea_utente_tecnico(p_processo_codice text, p_emittente_codice character varying, p_profilo_codice character varying)
IS 'Fixture dei pgTAP: crea l''utente tecnico di un processo per un emittente con la primitiva script.fn_applica_crea_utente_tecnico, senza chiedere permessi; argomenti, regole e risultato sono quelli del verbo script.fn_crea_utente_tecnico. SECURITY DEFINER ed eseguibile dall''applicazione: parte solo dove sono ammessi i dati di sviluppo (dbops.fn_dati_di_sviluppo_ammessi_su_valori sull''ambiente dell''installazione), e in PRODUZIONE solleva E_DATI_DI_SVILUPPO_IN_PRODUZIONE. La usa dbops.fn_pgtap_crea_emittente_operatore; un test non la chiama da sé.';
```

</div>

---
{% include-markdown "signature-core.md" %}
