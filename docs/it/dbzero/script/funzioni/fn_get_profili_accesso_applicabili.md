{% include-markdown "it/dbzero/script/manual/fn_get_profili_accesso_applicabili.md" %}
# ⚙️ Funzione `fn_get_profili_accesso_applicabili`

```sql
CREATE FUNCTION fn_get_profili_accesso_applicabili(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_profili_accesso_applicabili(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo DEFAULT NULL::config.ruolo_applicativo)
 RETURNS TABLE(profilo_accesso_id integer, priorita smallint)
 LANGUAGE sql
 STABLE
AS $function$
    -- =========================================================
    -- Risolve i profili di accesso applicabili a un utente
    -- via bindings, dal piu' specifico al piu' generale:
    --   AD_HOC  prio 1 (sull'identita')
    --   REPARTO prio 2 (sull'unita' organizzativa)
    --   PORTALE prio 3 (sulla veste, cioe' tutti)
    -- Rev 20260925-80 (D-3): PORTALE era 2, a pari merito col
    -- REPARTO; sotto la veste OPERATORE i due coesistono e
    -- LIMIT 1 sceglieva a caso.
    --
    -- p_ruolo_applicativo:
    --   NULL -> tutti i profili applicabili all'user
    --           (comportamento legacy, tutte le vesti)
    --   non NULL -> solo le identita dell'user con quel
    --               ruolo_applicativo (veste corrente)
    -- ⚠️ Con una veste sola ogni priorita' ha al massimo UN
    --   profilo (indici unici dei binding e di risorse_umane):
    --   chi ordina per priorita' ha uno spareggio determinato.
    --   Con NULL no: due vesti di portale danno due PORTALE.
    -- ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile): in tutti e
    --   tre i rami la veste conta se e' UTILIZZABILE oggi, cioe'
    --   script.fn_veste_utilizzabile, non piu' attivo + finestra
    --   ricopiati tre volte. Nel ramo REPARTO cade `ru.attivo`: il
    --   rapporto dell'operatore umano lo guarda il building block
    --   (attivo E nelle sue date), e la risorsa umana e' una sola
    --   per soggetto_ruolo.
    -- =========================================================

    -- 1) AD_HOC: binding diretto sull'identita
    SELECT DISTINCT
           pab.profilo_accesso_id,
           1::smallint AS priorita
      FROM anagrafiche.identita_digitali id
      JOIN config.profili_accesso_bindings pab
        ON pab.identita_digitale_id = id.id
      JOIN config.profili_accesso pa
        ON pa.id = pab.profilo_accesso_id
     WHERE id.auth_user_id      = p_auth_user_id
       AND (p_ruolo_applicativo IS NULL
            OR id.ruolo_applicativo = p_ruolo_applicativo)
       AND script.fn_veste_utilizzabile(id.id)
       AND pab.attivo = true
       AND pa.attivo  = true
       AND pa.tipo    = 'AD_HOC'::config.tipo_profilo_accesso

    UNION ALL

    -- 2) REPARTO: binding per UO (solo identita OPERATORE)
    SELECT DISTINCT
           pab.profilo_accesso_id,
           2::smallint AS priorita
      FROM anagrafiche.identita_digitali id
      JOIN anagrafiche.risorse_umane ru
        ON ru.soggetto_ruolo_id = id.soggetto_ruolo_id
      JOIN config.profili_accesso_bindings pab
        ON pab.unita_organizzativa_id = ru.unita_organizzativa_id
      JOIN config.profili_accesso pa
        ON pa.id = pab.profilo_accesso_id
     WHERE id.auth_user_id      = p_auth_user_id
       AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
       AND (p_ruolo_applicativo IS NULL
            OR p_ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo)
       AND script.fn_veste_utilizzabile(id.id)
       AND pab.attivo = true
       AND pa.attivo  = true
       AND pa.tipo    = 'REPARTO'::config.tipo_profilo_accesso

    UNION ALL

    -- 3) PORTALE: binding per ruolo_applicativo dell'identita
    SELECT DISTINCT
           pab.profilo_accesso_id,
           3::smallint AS priorita
      FROM anagrafiche.identita_digitali id
      JOIN config.profili_accesso_bindings pab
        ON pab.ruolo_applicativo = id.ruolo_applicativo
      JOIN config.profili_accesso pa
        ON pa.id = pab.profilo_accesso_id
     WHERE id.auth_user_id      = p_auth_user_id
       AND (p_ruolo_applicativo IS NULL
            OR id.ruolo_applicativo = p_ruolo_applicativo)
       AND script.fn_veste_utilizzabile(id.id)
       AND pab.attivo = true
       AND pa.attivo  = true
       AND pa.tipo    = 'PORTALE'::config.tipo_profilo_accesso;
$function$

COMMENT ON FUNCTION script.fn_get_profili_accesso_applicabili(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
IS 'Profili applicabili a un auth_user, dal piu'' specifico al piu'' generale: AD_HOC priorita'' 1 (sull''identita''), REPARTO 2 (sull''unita'' organizzativa), PORTALE 3 (sulla veste). Rev 20260925-80 (D-3 di brief-db-pgtap-permessi-ereditati): PORTALE era 2, a pari merito col REPARTO, e sotto la veste OPERATORE lo spareggio per priorita'' sceglieva a caso. p_ruolo_applicativo NULL = tutte le vesti (legacy), valorizzato = solo quella veste; con una veste sola ogni priorita'' ha al massimo un profilo (indici unici dei binding e di risorse_umane). I resolver dei permessi da operatore passano ''OPERATORE'' tramite script.fn_get_permessi_ereditati_aree / _azioni (D-1). Rev 2026-10-02 (brief-db-be-fe-area-accessi R-DB-1): una veste spenta si riconosce solo da attivo; il controllo su DISABILITATO (rami AD_HOC e PORTALE) e'' caduto con il tipo. Rev 2026-10-07 (brief-db-veste-utilizzabile): la veste conta se e'' utilizzabile oggi (script.fn_veste_utilizzabile) in tutti e tre i rami; nel ramo REPARTO il controllo del rapporto (prima solo ru.attivo) e'' quello del building block, con le date.';
```

</div>

---
{% include-markdown "signature-core.md" %}
