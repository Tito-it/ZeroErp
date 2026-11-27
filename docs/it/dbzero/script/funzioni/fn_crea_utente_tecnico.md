{% include-markdown "it/dbzero/script/manual/fn_crea_utente_tecnico.md" %}
# ⚙️ Funzione `fn_crea_utente_tecnico`

```sql
CREATE FUNCTION fn_crea_utente_tecnico(p_processo_codice text, p_emittente_codice character varying, p_profilo_codice character varying)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_crea_utente_tecnico(p_processo_codice text, p_emittente_codice character varying, p_profilo_codice character varying DEFAULT NULL::character varying)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo:
--   Il verbo con cui il SUPER_ADMIN crea l'utente tecnico di un processo
--   automatico per un emittente. E' la strada dell'endpoint dei processi.
--
-- Regole:
--   - SECURITY DEFINER: il permesso e' qui, in prima riga, e chiede lo stesso
--     controllo dell'endpoint, il SUPER_ADMIN (script.fn_guard_super_admin:
--     E_PERMESSO_NEGATO, anche senza utente);
--   - la sessione del migratore (dbops.fn_sessione_del_migratore) crea gli
--     utenti tecnici di seed senza utente e non passa dal guard: e' il software;
--   - la creazione la fa la primitiva script.fn_applica_crea_utente_tecnico,
--     che l'app non esegue.
DECLARE
    v_utente config.user_emittenti_fiscali.auth_user_id%TYPE;
BEGIN
    -- Il permesso, prima di ogni altra cosa.
    IF NOT dbops.fn_sessione_del_migratore() THEN
        v_utente := script.fn_utente_di_sessione('script.fn_crea_utente_tecnico');
        PERFORM script.fn_guard_super_admin(v_utente);
    END IF;

    RETURN script.fn_applica_crea_utente_tecnico(p_processo_codice, p_emittente_codice, p_profilo_codice);
END;
$function$

COMMENT ON FUNCTION script.fn_crea_utente_tecnico(p_processo_codice text, p_emittente_codice character varying, p_profilo_codice character varying)
IS 'Il verbo con cui il SUPER_ADMIN crea l''utente tecnico di un processo automatico per un emittente: utente Django con password inutilizzabile e username processo@emittente, soggetto dedicato col suo contatto, ruolo PROC_AUTO, identità OPERATORE col flag tecnica, la riga di perimetro in config.user_emittenti_fiscali e il legame in dbops.processi_identita; ritorna l''auth_user_id. SECURITY DEFINER: in prima riga chiede il SUPER_ADMIN all''utente di sessione (script.fn_guard_super_admin: E_PERMESSO_NEGATO, anche senza utente), lo stesso controllo dell''endpoint; la sessione del migratore (dbops.fn_sessione_del_migratore) crea gli utenti tecnici di seed senza utente e non passa dal guard. La creazione la fa la primitiva script.fn_applica_crea_utente_tecnico, che l''applicazione non esegue: l''emittente è obbligatorio e costitutivo (un processo che serve N emittenti ha N utenti tecnici), il profilo è facoltativo e solo AD_HOC, mai SUPER_ADMIN; processo inesistente E_PROCESSO_NON_TROVATO, non eleggibile E_PROCESSO_NON_ELEGGIBILE_UTENTE_TECNICO, già presente E_UTENTE_TECNICO_GIA_ESISTE, username già usato E_UTENTE_TECNICO_DA_RIATTIVARE (il verbo giusto è script.fn_riattiva_utente_tecnico).';
```

</div>

---
{% include-markdown "signature-core.md" %}
