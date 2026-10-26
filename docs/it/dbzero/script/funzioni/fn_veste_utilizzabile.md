{% include-markdown "it/dbzero/script/manual/fn_veste_utilizzabile.md" %}
# ⚙️ Funzione `fn_veste_utilizzabile`

```sql
CREATE FUNCTION fn_veste_utilizzabile(p_identita_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_veste_utilizzabile(p_identita_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT (EXISTS ( SELECT 1
            FROM ((anagrafiche.identita_digitali idg
              JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = idg.soggetto_ruolo_id)))
              JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
           WHERE ((idg.id = fn_veste_utilizzabile.p_identita_id) AND idg.attivo AND (idg.valido_dal <= ( SELECT script.fn_data_operativa() AS fn_data_operativa)) AND ((idg.valido_al IS NULL) OR (idg.valido_al >= ( SELECT script.fn_data_operativa() AS fn_data_operativa))) AND s.attivo AND ((idg.ruolo_applicativo <> 'OPERATORE'::config.ruolo_applicativo) OR idg.tecnica OR (EXISTS ( SELECT 1
                    FROM anagrafiche.risorse_umane ru
                   WHERE ((ru.soggetto_ruolo_id = idg.soggetto_ruolo_id) AND ru.attivo AND (ru.valido_dal <= ( SELECT script.fn_data_operativa() AS fn_data_operativa)) AND ((ru.valido_al IS NULL) OR (ru.valido_al >= ( SELECT script.fn_data_operativa() AS fn_data_operativa)))))))))) AS "exists";
END

COMMENT ON FUNCTION script.fn_veste_utilizzabile(p_identita_id bigint)
IS 'Una veste vale oggi? true se e'' accesa, CURRENT_DATE sta nella sua finestra (estremi compresi) e il suo soggetto e'' attivo; per l''operatore UMANO (OPERATORE, tecnica = false) anche il rapporto, cioe'' la risorsa umana dello stesso soggetto_ruolo, e'' attivo e nella sua finestra (senza risorsa umana: false). L''identita'' tecnica di un processo non ha risorsa umana e non la pretende. false per un id assente o NULL. Building block unico della regola (regola del 2): la leggono fn_has_identita_attiva, fn_is_super_admin_account, fn_check_ultimo_super_admin_attivo, fn_check_almeno_un_super_admin_attivo, fn_get_profili_accesso_applicabili, fn_get_setup_status, fn_get_user_profile, le fn_scope_* sulle vesti, anagrafiche.fn_sync_auth_user_is_active e fn_sync_auth_user_expired; il backend al login, a ogni richiesta, al refresh, al secondo passo e al cambio password. L''appartenenza della veste alla credenziale resta al chiamante. Brief: brief-db-veste-utilizzabile.';
```

</div>

---
{% include-markdown "signature-core.md" %}
