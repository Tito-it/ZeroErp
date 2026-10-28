{% include-markdown "it/dbzero/script/manual/fn_get_credenziale_per_email.md" %}
# ⚙️ Funzione `fn_get_credenziale_per_email`

```sql
CREATE FUNCTION fn_get_credenziale_per_email(p_email text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_credenziale_per_email(p_email text)
 RETURNS TABLE(auth_user_id integer, username text, vesti jsonb)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la credenziale che porta questa email, con il suo username e
--   le sue vesti, per chi deve decidere se riusarla.
-- Uso: SELECT * FROM script.fn_get_credenziale_per_email(p_email);
DECLARE
    -- integer esplicito: e' django.auth_user.id (niente %TYPE su Django).
    v_id integer;
BEGIN
    -- La regola «quale credenziale ha questa email» sta in un posto solo:
    --   senza maiuscole, email vuota = nessuna, due = errore.
    v_id := script.fn_get_auth_user_id_for_email(p_email);

    IF v_id IS NULL THEN
        RETURN;
    END IF;

    -- ⭐ Una riga anche senza vesti: la credenziale c'e', ed e' proprio
    --   cio' che l'admin deve vedere prima di riusarla.
    RETURN QUERY
    SELECT au.id,
           au.username::text,
           COALESCE((
               SELECT jsonb_agg(jsonb_build_object(
                          'ruolo_applicativo', idg.ruolo_applicativo,
                          'attivo',            idg.attivo,
                          'soggetto',          s.ragione_sociale_completa)
                        ORDER BY idg.id)
                 FROM anagrafiche.identita_digitali idg
                 JOIN anagrafiche.soggetti_ruoli sr ON sr.id = idg.soggetto_ruolo_id
                 JOIN anagrafiche.soggetti s        ON s.id  = sr.soggetto_id
                WHERE idg.auth_user_id = au.id), '[]'::jsonb)
      FROM django.auth_user au
     WHERE au.id = v_id;
END;
$function$

COMMENT ON FUNCTION script.fn_get_credenziale_per_email(p_email text)
IS 'Building block: la credenziale che porta questa email (la trova script.fn_get_auth_user_id_for_email: senza maiuscole, email vuota = nessuna, due credenziali = E_CREDENZIALE_EMAIL_AMBIGUA), con username e vesti. Ritorna TABLE(auth_user_id, username, vesti jsonb): zero righe se l''email non ha credenziale; una riga anche senza vesti (vesti = []). vesti = array di {ruolo_applicativo, attivo, soggetto (ragione_sociale_completa)} in ordine di id. Regola del 2 (brief-db-blocco-login-per-credenziale §17): la leggono la madre anagrafiche.fn_crea_operatore_v2 per il rifiuto E_CREDENZIALE_DA_CONFERMARE e il backend per il dialog di conferma, che cosi'' mostrano la stessa cosa. Nessun guard di permesso (Tid, 2026-09-27): il cancello e'' la porta AdminAPIView, e un guard qui cambierebbe il rifiuto della madre in E_PERMESSO_NEGATO. plpgsql e tipi espliciti perche'' nomina django.*. INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
