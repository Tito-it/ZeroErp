{% include-markdown "it/dbzero/anagrafiche/manual/fn_clienti_stessa_chiave.md" %}
# ⚙️ Funzione `fn_clienti_stessa_chiave`

```sql
CREATE FUNCTION fn_clienti_stessa_chiave(p_soggetto_ruolo_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_clienti_stessa_chiave(p_soggetto_ruolo_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
 RETURNS TABLE(cliente_id bigint, billing_account_id bigint, billing_account_codice character varying, istanza_utility_id bigint, stato_codice_interno character varying, data_attivazione date, data_chiusura date, periodo daterange)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    -- Scopo: chi occupa la chiave soggetto + utility + azienda
    --   fra le istanze fittizie (C-1). Lo leggono il guard del
    --   doppione, l'avviso del pre-contrattuale e la catena.
    -- ⚠️ SECURITY DEFINER: clienti e billing_account sono in
    --   RLS, e un cliente fuori perimetro sarebbe invisibile.
    SELECT c.id,
           c.billing_account_id,
           ba.codice,
           c.istanza_utility_id,
           sc.codice_interno,
           c.data_attivazione,
           c.data_chiusura,
           c.periodo
      FROM anagrafiche.clienti c
      JOIN anagrafiche.istanze_utilities iu
        ON iu.id = c.istanza_utility_id
      JOIN anagrafiche.billing_account ba
        ON ba.id = c.billing_account_id
      JOIN config.stati_cliente sc
        ON sc.id = c.stato_cliente_id
     WHERE c.soggetto_ruolo_id = p_soggetto_ruolo_id
       AND c.utility_id = p_utility_id
       AND iu.fittizia
       AND c.periodo IS NOT NULL
       -- Gli stati di fornitura, per elenco (C-2, C-6, C-7).
       AND sc.codice_interno IN ('AT', 'RS', 'SF', 'SC',
                                 'CH', 'CM', 'CW', 'CF')
       AND script.fn_get_ba_emittente_sr_id_installazione(c.billing_account_id)
           = p_emittente_soggetto_ruolo_id
     ORDER BY c.data_attivazione DESC, c.id DESC;
$function$

COMMENT ON FUNCTION anagrafiche.fn_clienti_stessa_chiave(p_soggetto_ruolo_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
IS 'I clienti delle istanze fittizie che occupano la chiave soggetto (ruolo CL) + utility + azienda emittente (C-1 di Tid del 2026-10-13): con un periodo e in uno stato di fornitura per elenco (AT, RS, SF, SC, CH, CM, CW, CF; fuori AN, PR, AG). L''azienda si legge per l''installazione (script.fn_get_ba_emittente_sr_id_installazione), mai per chi agisce. Restituisce anche il periodo: la sovrapposizione la decide chi legge. Predicato unico (C-4) di tre lettori: il guard anagrafiche.fn_guard_cliente_chiave_unica (E_CLIENTE_STESSA_CHIAVE), l''avviso del pre-contrattuale (BE) e la catena delle fittizie (anagrafiche.trgfn_clienti_set_parent_istanza, C-9). SECURITY DEFINER: clienti e billing_account sono in RLS. Ordine: data_attivazione e id decrescenti. Brief: brief-db-cliente-manuale-uno-per-soggetto-e-utility.';
```

</div>

---
{% include-markdown "signature-core.md" %}
