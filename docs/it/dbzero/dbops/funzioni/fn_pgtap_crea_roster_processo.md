# ⚙️ Funzione `fn_pgtap_crea_roster_processo`

```sql
CREATE FUNCTION fn_pgtap_crea_roster_processo(p_processo_codice text, p_sigla character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_roster_processo(p_processo_codice text, p_sigla character varying DEFAULT NULL::character varying)
 RETURNS TABLE(emittente_fiscale_id bigint, emittente_codice character varying, emittente_soggetto_ruolo_id bigint, auth_user_id integer, identita_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP una coppia (processo, azienda)
--   che compaia davvero in dbops.vw_processi_roster.
-- ⭐ Rev 2026-09-09: il corpo era identico a
--   fn_pgtap_crea_emittente_operatore tranne il nome del processo.
--   Ora la chiama: resta qui solo il guard sul parametro, che e'
--   l'unica cosa che questa funzione ha in piu' — li' il processo
--   e' il SOGGETTO del test, non un dettaglio con un default.
DECLARE
    v_r record;
BEGIN
    IF p_processo_codice IS NULL OR btrim(p_processo_codice) = '' THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_roster_processo: p_processo_codice e'' obbligatorio';
    END IF;

    SELECT * INTO v_r
      FROM dbops.fn_pgtap_crea_emittente_operatore(
               p_sigla           := p_sigla,
               p_processo_codice := p_processo_codice);

    RETURN QUERY
    SELECT v_r.emittente_fiscale_id, v_r.emittente_codice,
           v_r.soggetto_ruolo_id, v_r.auth_user_id, v_r.identita_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_roster_processo(p_processo_codice text, p_sigla character varying)
IS 'Helper di fixture pgTAP: crea un''azienda e le aggancia l''utente tecnico di un processo automatico, cosi'' la coppia (processo, azienda) compare in dbops.vw_processi_roster. ⭐ Rev 2026-09-09: il corpo e'' passato a dbops.fn_pgtap_crea_emittente_operatore, di cui questa e'' il caso in cui il processo e'' il SOGGETTO del test e quindi non ha un default. ⚠️ Pretende django.auth_user, che costruisce manage.py migrate e non Liquibase.';
```

</div>

---
{% include-markdown "signature-core.md" %}
