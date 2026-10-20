{% include-markdown "it/dbzero/script/manual/fn_stato_veste.md" %}
# ⚙️ Funzione `fn_stato_veste`

```sql
CREATE FUNCTION fn_stato_veste(p_identita_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_stato_veste(p_identita_id bigint)
 RETURNS TABLE(stato text, token_scade_at timestamp with time zone)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT
         CASE
             WHEN idg.attivo THEN 'ATTIVO'::text
             WHEN (tk.scade_at IS NULL) THEN 'DISATTIVO'::text
             WHEN ((idg.invito_inviato_at IS NOT NULL) AND (idg.invito_inviato_at >= tk.emesso_at)) THEN 'PENDING'::text
             ELSE 'NON_SPEDITO'::text
         END AS "case",
     tk.scade_at
    FROM (anagrafiche.identita_digitali idg
      LEFT JOIN LATERAL ( SELECT max(t.scadenza) AS scade_at,
             max(t.data_insert) AS emesso_at
            FROM config.token_monouso t
           WHERE ((t.auth_user_id = idg.auth_user_id) AND ((t.meta ->> 'identita_id'::text) = (idg.id)::text) AND (NOT t.utilizzato) AND (t.scadenza > now()))) tk ON (true))
   WHERE (idg.id = fn_stato_veste.p_identita_id);
END

COMMENT ON FUNCTION script.fn_stato_veste(p_identita_id bigint)
IS 'Lo stato di UNA veste, calcolato solo a DB (A-7): ATTIVO (accesa), PENDING (spenta, invito pendente e la sua email partita: invito_inviato_at >= emissione del token), NON_SPEDITO (spenta, invito pendente, email di quel token non partita), DISATTIVO (spenta, nessun invito pendente). Invito pendente = token di config.token_monouso non usato e non scaduto con l''identita_id della veste nel meta (lo scrive solo l''emissione di un invito); con piu'' token vale il MAX di scadenza ed emissione. token_scade_at = scadenza del token pendente piu'' lontano. Zero righe per un id assente. La regola e'' quella che il backend calcolava in portale_repository.stato_veste, portata com''era; NESSUNO (nessuna veste) resta a chi cerca la veste. La leggono anagrafiche.vw_accessi_altri e lo stato accessi della scheda di cliente e fornitore. Brief: brief-db-be-fe-area-accessi (A-7, R-DB-A2).';
```

</div>

---
{% include-markdown "signature-core.md" %}
