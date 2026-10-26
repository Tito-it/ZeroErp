{% include-markdown "it/dbzero/script/manual/fn_get_ba_id_da_coppia.md" %}
# ⚙️ Funzione `fn_get_ba_id_da_coppia`

```sql
CREATE FUNCTION fn_get_ba_id_da_coppia(p_istanza_utility_id bigint, p_utility_id integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_ba_id_da_coppia(p_istanza_utility_id bigint, p_utility_id integer)
 RETURNS bigint
 LANGUAGE sql
 STABLE SECURITY DEFINER COST 5000
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
    -- Scopo: dire QUALE billing account e' la coppia (istanza, utility),
    --   e nient'altro. NULL se la coppia non porta a nessun BA.
    -- ⭐ Perche' SECURITY DEFINER: anagrafiche.billing_account ha la RLS
    --   accesa. Letta dall'operatore, ogni lettura rieseguirebbe la policy
    --   del BA, e chiamata da una policy lo farebbe per ogni riga. La
    --   domanda di FATTO («quale BA») e quella di PERMESSO («lo vedo»)
    --   restano separate: la seconda e' della policy che chiama, come per
    --   script.fn_resolve_emittente_fiscale_id.
    -- ⚠️ Dipende dalla RLS ABILITATA ma NON FORZATA: il proprietario la
    --   salta (linee-guida-sql §10.5). Con FORCE andrebbe rivista.
    -- ⚠️ Una riga al massimo: uq_billing_instance_utility.
    SELECT ba.id
      FROM anagrafiche.billing_account ba
     WHERE ba.istanza_utility_id = p_istanza_utility_id
       AND ba.utility_id         = p_utility_id
$function$

COMMENT ON FUNCTION script.fn_get_ba_id_da_coppia(p_istanza_utility_id bigint, p_utility_id integer)
IS 'Il billing account della coppia (istanza_utility_id, utility_id): al massimo uno (uq_billing_instance_utility), NULL se la coppia non porta a nessun BA. Domanda di FATTO, non di permesso: SECURITY DEFINER del PROPRIETARIO, non di un superuser, perche'' billing_account e'' sotto RLS e una lettura dalla policy di un figlio rieseguirebbe per ogni riga la policy del BA. Il permesso resta a chi chiama: la policy rls_istanze_dati_precontrattuali_ef_whitelist lo chiede a script.fn_scope_ef_perimetro col perimetro calcolato una volta per istruzione (linee-guida-sql §10.3). Dipende dalla RLS non forzata. search_path bloccato. Rev 2026-10-21 (20261021-24, P-3 di brief-db-perimetro-una-volta-famiglie-residue).';
```

</div>

---
{% include-markdown "signature-core.md" %}
