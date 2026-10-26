{% include-markdown "it/dbzero/script/manual/fn_identita_super_admin_senza_scadenza.md" %}
# ⚙️ Funzione `fn_identita_super_admin_senza_scadenza`

```sql
CREATE FUNCTION fn_identita_super_admin_senza_scadenza(p_identita_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_identita_super_admin_senza_scadenza(p_identita_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT (EXISTS ( SELECT 1
            FROM ((anagrafiche.identita_digitali idg
              JOIN config.profili_accesso_bindings pab ON (((pab.identita_digitale_id = idg.id) AND pab.attivo)))
              JOIN config.profili_accesso pa ON (((pa.id = pab.profilo_accesso_id) AND pa.attivo AND (pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso))))
           WHERE ((idg.id = fn_identita_super_admin_senza_scadenza.p_identita_id) AND (idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo) AND script.fn_veste_utilizzabile(idg.id) AND (idg.valido_al IS NULL) AND (NOT (EXISTS ( SELECT 1
                    FROM anagrafiche.risorse_umane ru
                   WHERE ((ru.soggetto_ruolo_id = idg.soggetto_ruolo_id) AND (ru.valido_al IS NOT NULL))))) AND (NOT (EXISTS ( SELECT 1
                    FROM config.credenziali c
                   WHERE ((c.auth_user_id = idg.auth_user_id) AND (c.bloccata_at IS NOT NULL)))))))) AS "exists";
END

COMMENT ON FUNCTION script.fn_identita_super_admin_senza_scadenza(p_identita_id bigint)
IS 'L''identita'' e'' un SUPER_ADMIN che non scade? true se ha un binding SUPER_ADMIN attivo verso un profilo attivo, e'' OPERATORE e utilizzabile oggi (script.fn_veste_utilizzabile), non ha data di fine ne'' sulla veste ne'' sul rapporto (risorsa umana dello stesso soggetto_ruolo), e la sua credenziale non e'' bloccata dall''amministratore. Building block dell''anti-lockout (decisione di Tid del 2026-10-07: resta sempre almeno un amministratore senza scadenza, perche'' il calendario non scrive e nessun guard lo ferma): lo leggono fn_check_almeno_un_super_admin_attivo e fn_check_ultimo_super_admin_attivo. Brief: brief-db-veste-utilizzabile.';
```

</div>

---
{% include-markdown "signature-core.md" %}
