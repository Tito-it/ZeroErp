{% include-markdown "it/dbzero/script/manual/fn_check_almeno_un_super_admin_attivo.md" %}
# ⚙️ Funzione `fn_check_almeno_un_super_admin_attivo`

```sql
CREATE FUNCTION fn_check_almeno_un_super_admin_attivo()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_almeno_un_super_admin_attivo()
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Condizione di sicurezza: il sistema mantiene almeno un
    -- amministratore raggiungibile OGGI E DOMANI.
    -- ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile, decisione di Tid):
    --   la condizione e' «esiste almeno un SUPER_ADMIN SENZA SCADENZA»,
    --   letta da script.fn_identita_super_admin_senza_scadenza
    --   (utilizzabile oggi, nessuna data di fine su veste e rapporto,
    --   credenziale non bloccata).
    --   Perche' «senza scadenza» e non «attivo»: una data che passa non
    --   scrive niente, e nessun guard puo' fermare il calendario. La
    --   garanzia si chiede quindi sulla SCRITTURA che mette la data di
    --   fine (guard su veste e rapporto), finche' resta almeno un
    --   amministratore che non scade.
    --   Prima qui bastava identita_digitali.attivo: un amministratore
    --   gia' scaduto contava come raggiungibile.
    -- Il prefiltro sui binding con identita (AD_HOC) e' solo una scorciatoia:
    -- la regola intera e' nel building block.
    SELECT EXISTS (
        SELECT 1
          FROM config.profili_accesso_bindings pab
         WHERE pab.identita_digitale_id IS NOT NULL
           AND script.fn_identita_super_admin_senza_scadenza(pab.identita_digitale_id)
    );
$function$

COMMENT ON FUNCTION script.fn_check_almeno_un_super_admin_attivo()
IS 'Ritorna true se esiste almeno un SUPER_ADMIN SENZA SCADENZA (script.fn_identita_super_admin_senza_scadenza: identita'' utilizzabile oggi, nessuna data di fine su veste e rapporto, binding e profilo SUPER_ADMIN attivi, credenziale non bloccata). E'' la sede unica della condizione «il sistema ha un amministratore che non scade», usata dai guard anti-lockout su profili_accesso_bindings, identita_digitali (attivo e date), risorse_umane (attivo e date) e credenziali. LANGUAGE sql, STABLE, fail-closed, nessun raise. Rev 2026-10-07 (brief-db-veste-utilizzabile, decisione di Tid): prima bastava identita_digitali.attivo; un amministratore scaduto contava come raggiungibile, e una data di fine non era fermata da nessun guard, perche'' il calendario non scrive.';
```

</div>

---
{% include-markdown "signature-core.md" %}
