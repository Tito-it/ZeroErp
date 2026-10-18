# ⚙️ Funzione `fn_codice_registro_provisionato`

```sql
CREATE FUNCTION fn_codice_registro_provisionato(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_codice_registro_provisionato(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint)
 RETURNS character varying
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- ⚠️ Prime tre lettere della famiglia + id dell'emittente:
    --   deterministico, unico per costruzione, e dentro i 16
    --   caratteri della colonna. ⛔ NON la sigla
    --   dell'emittente: e' varchar(32) contro 16, e troncarla
    --   su una UNIQUE trasformerebbe due sigle simili in una
    --   collisione. La parte parlante sta nella descrizione.
    SELECT left(p_famiglia_documento, 3) || '-' || p_emittente_soggetto_ruolo_id::text;
$function$

COMMENT ON FUNCTION vendite.fn_codice_registro_provisionato(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint)
IS 'La regola del CODICE di un registro nato dal provisioning: prime tre lettere della famiglia, un trattino, l''id del soggetto_ruolo dell''emittente (es. DDT-123, FAT-123). Deterministica e unica per costruzione, dentro i 16 caratteri della colonna; mai la sigla dell''emittente (varchar(32), troncata su una UNIQUE farebbe collidere due sigle simili). ⭐ Esce dalla primitiva vendite.fn_provision_registri il 2026-10-18 (20261019-08) perche'' serve tre volte: i registri delle famiglie, il registro standard delle fatture, e il RITROVARLO per collegargli le coppie (tipo documento, natura). R-BE-14, brief-db-processi-accensione-per-ambiente §6.14.';
```

---
{% include-markdown "signature-core.md" %}
