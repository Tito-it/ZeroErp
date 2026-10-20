{% include-markdown "it/dbzero/script/manual/fn_scope_identita_processo.md" %}
# ⚙️ Funzione `fn_scope_identita_processo`

```sql
CREATE FUNCTION fn_scope_identita_processo(p_auth_user_id integer, p_processo_codice text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_identita_processo(p_auth_user_id integer, p_processo_codice text)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- =====================================================
    -- Scopo:
    --   «Questa sessione e' l'identita' tecnica VIVA del
    --   processo indicato?» Una domanda sola, scritta una
    --   volta sola, usata da chi deve decidere se una
    --   macchina puo' leggere.
    --
    -- ⭐ Cinque livelli, non uno. Il legame attivo da solo
    --   lascerebbe leggere un'identita' REVOCATA: basta che
    --   nessuno abbia toccato anche `processi_identita`.
    -- ⚠️ L'emittente NON entra: qui si chiede «chi sei», non
    --   «su quale azienda lavori» — quello lo dice
    --   dbops.vw_processi_roster.
    -- =====================================================
    SELECT EXISTS (
        SELECT 1
          FROM dbops.processi_identita pi
          JOIN dbops.processi pr
            ON pr.id = pi.processo_id
           AND pr.attivo
           AND pr.obsoleto_dal IS NULL
          JOIN anagrafiche.identita_digitali idg
            ON idg.auth_user_id = pi.auth_user_id
           -- Rev 2026-10-07: utilizzabile oggi (accesa, nelle sue
           --   date, soggetto attivo), non solo accesa.
           AND script.fn_veste_utilizzabile(idg.id)
           AND idg.ruolo_applicativo
               = 'OPERATORE'::config.ruolo_applicativo
          -- ⚠️ django.* si attraversa da una funzione, mai da
          --   una vista: zero righe se l'utente non c'e' piu',
          --   che in un join fa sparire la riga (fail-closed).
          JOIN LATERAL script.fn_get_auth_user_stato(pi.auth_user_id) au
            ON au.is_active
         WHERE pi.attivo
           AND pi.auth_user_id    = p_auth_user_id
           AND pr.codice          = p_processo_codice
    );
$function$

COMMENT ON FUNCTION script.fn_scope_identita_processo(p_auth_user_id integer, p_processo_codice text)
IS 'Dice se p_auth_user_id e'' l''identita'' tecnica VIVA del processo p_processo_codice. ⭐ Nasce il 2026-09-05 per togliere due copie dello stesso EXISTS dalla policy rls_email_outbox_ambito (USING e WITH CHECK): la famiglia duplica anche altrove, ma li'' e'' UNA CHIAMATA, e due chiamate identiche non possono divergere — dieci righe si''. ⭐ E la regola e'' piu'' stretta di quella che sostituisce: guarda CINQUE livelli (legame attivo, processo vivo, identita'' attiva, ruolo OPERATORE, utente Django attivo) invece del solo legame, perche'' un''identita'' revocata a un livello solo avrebbe continuato a leggere. ⚠️ L''emittente non entra: qui si chiede «chi sei», non «su quale azienda lavori» — quello e'' dbops.vw_processi_roster, e legarli toglierebbe la lettura delle email di SISTEMA, che di azienda non ne hanno. ⚠️ LANGUAGE sql STABLE perche'' una policy si valuta per riga e il pianificatore la puo'' incorporare. ⛔ Niente STRICT: con un parametro NULL l''EXISTS non trova niente e la funzione torna false — fail-closed per costruzione, non per coincidenza. ⚠️ django.* si attraversa da script.fn_get_auth_user_stato (plpgsql, late-bound), mai da una vista: regola presa col changeSet 20260905-30. Rev 2026-10-07 (brief-db-veste-utilizzabile): il livello «identita'' attiva» e'' diventato «identita'' utilizzabile oggi» (script.fn_veste_utilizzabile: accesa, nelle sue date, soggetto attivo; l''identita'' tecnica non pretende un rapporto).';
```

</div>

---
{% include-markdown "signature-core.md" %}
