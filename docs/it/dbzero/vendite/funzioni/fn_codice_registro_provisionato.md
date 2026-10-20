# ⚙️ Funzione `fn_codice_registro_provisionato`

```sql
CREATE FUNCTION fn_codice_registro_provisionato(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_codice_registro_provisionato(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint)
 RETURNS character varying
 LANGUAGE sql
 IMMUTABLE
AS $function$
-- rev 2026-10-20 (20261020-64, brief-db-grammatica-unica-documenti L2c-1):
--   il codice intero della famiglia, non le prime tre lettere; firma ancorata.
    -- ⚠️ Il codice INTERO della famiglia + id dell'emittente:
    --   deterministico e unico per costruzione (il codice della
    --   famiglia e' unico, l'emittente pure). Rev 2026-10-20
    --   (L2c-1): erano le prime tre lettere, che collidono fra
    --   ORDINE_VENDITA e ORDINE_ACQUISTO. ⛔ NON la sigla
    --   dell'emittente: troncarla su una UNIQUE trasformerebbe
    --   due sigle simili in una collisione. La parte parlante sta
    --   nella descrizione.
    SELECT p_famiglia_documento || '-' || p_emittente_soggetto_ruolo_id::text;
$function$

COMMENT ON FUNCTION vendite.fn_codice_registro_provisionato(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint)
IS 'La regola del CODICE di un registro nato dal provisioning: prime tre lettere della famiglia, un trattino, l''id del soggetto_ruolo dell''emittente (es. DDT-123, FAT-123). Deterministica e unica per costruzione, dentro i 16 caratteri della colonna; mai la sigla dell''emittente (varchar(32), troncata su una UNIQUE farebbe collidere due sigle simili). ⭐ Esce dalla primitiva vendite.fn_provision_registri il 2026-10-18 (20261019-08) perche'' serve tre volte: i registri delle famiglie, il registro standard delle fatture, e il RITROVARLO per collegargli le coppie (tipo documento, natura). R-BE-14, brief-db-processi-accensione-per-ambiente §6.14. Rev 2026-10-20 (20261020-64, brief-db-grammatica-unica-documenti L2c-1): <codice della famiglia>-<id dell''emittente> (ORDINE_ACQUISTO-31848), non piu'' le prime tre lettere, che collidevano fra famiglie con le stesse iniziali.';
```

</div>

---
{% include-markdown "signature-core.md" %}
