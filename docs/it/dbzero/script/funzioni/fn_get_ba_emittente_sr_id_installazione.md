{% include-markdown "it/dbzero/script/manual/fn_get_ba_emittente_sr_id_installazione.md" %}
# ⚙️ Funzione `fn_get_ba_emittente_sr_id_installazione`

```sql
CREATE FUNCTION fn_get_ba_emittente_sr_id_installazione(p_billing_account_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_ba_emittente_sr_id_installazione(p_billing_account_id bigint)
 RETURNS bigint
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: «di quale azienda e' questo BA per l'installazione»:
    --   collegamento specifico, altrimenti la predefinita. Senza
    --   il livello «chi agisce» di script.fn_get_ba_emittente_sr_id.
    -- ⚠️ Il CASE esterno: un BA NULL non e' un BA non collegato,
    --   e non deve ricevere la predefinita.
    SELECT CASE
             WHEN p_billing_account_id IS NULL THEN NULL
             ELSE COALESCE(
                    -- 1) Collegamento specifico (al massimo uno:
                    --    uq_emittenti_fiscali_ba).
                    (SELECT efba.emittente_soggetto_ruolo_id
                       FROM anagrafiche.emittenti_fiscali_billing_account efba
                      WHERE efba.billing_account_id = p_billing_account_id),
                    -- 2) La predefinita dell'installazione (al
                    --    massimo una: uq_emittenti_fiscali_ba_default).
                    (SELECT d.emittente_soggetto_ruolo_id
                       FROM anagrafiche.emittenti_fiscali_billing_account d
                      WHERE d.is_default)
                  )
           END;
$function$

COMMENT ON FUNCTION script.fn_get_ba_emittente_sr_id_installazione(p_billing_account_id bigint)
IS 'L''azienda emittente (soggetto_ruolo_id) di un billing account per l''INSTALLAZIONE: il collegamento specifico in emittenti_fiscali_billing_account, altrimenti la predefinita (is_default). A differenza di script.fn_get_ba_emittente_sr_id non guarda chi agisce: e'' la risposta che vale anche fuori sessione (job, altri utenti). Serve ai guard dello spostamento della predefinita (fn_guard_istanza_ba_gestore_globale, fn_guard_albero_ba_gestore_globale), che con il risolutore di sessione lasciavano passare una coppia mista se a spostarla era un utente con un''azienda. Input NULL -> NULL; BA scollegato senza predefinita -> NULL (chi confronta lo tratta come diverso). Brief: brief-db-istanza-nasce-col-ba-residui (D-5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
