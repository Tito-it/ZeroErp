# ⚙️ Funzione `fn_get_ba_emittente_sr_id`

```sql
CREATE FUNCTION fn_get_ba_emittente_sr_id(p_billing_account_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_ba_emittente_sr_id(p_billing_account_id bigint)
 RETURNS bigint
 LANGUAGE sql
 STABLE PARALLEL SAFE
AS $function$
    -- ⚠️ Il CASE esterno non e' ridondante. Senza, un BA NULL
    --   cadrebbe nel ramo 2 e si vedrebbe rispondere l'emittente
    --   di default — cioe' «nessun billing account» verrebbe
    --   letto come «billing account non ancora mappato», che e'
    --   una cosa diversa e apre invece di chiudere.
    SELECT CASE
             WHEN p_billing_account_id IS NULL THEN NULL
             ELSE COALESCE(
                    -- 1) Mapping specifico del BA. Al massimo una
                    --    riga: uq_emittenti_fiscali_ba.
                    (SELECT efba.emittente_soggetto_ruolo_id
                       FROM anagrafiche.emittenti_fiscali_billing_account efba
                      WHERE efba.billing_account_id = p_billing_account_id),
                    -- 2) Fallback: l'emittente di default copre i
                    --    BA non ancora mappati. Al massimo uno:
                    --    uq_emittenti_fiscali_ba_default.
                    --    Il COALESCE fa da solo il «solo se non
                    --    c'e' mapping»: se il ramo 1 ha risposto,
                    --    il ramo 2 non viene nemmeno valutato.
                    (SELECT efba_d.emittente_soggetto_ruolo_id
                       FROM anagrafiche.emittenti_fiscali_billing_account efba_d
                      WHERE efba_d.is_default)
                  )
           END;
$function$

COMMENT ON FUNCTION script.fn_get_ba_emittente_sr_id(p_billing_account_id bigint)
IS 'Risolve «quale emittente fattura questo billing account» e restituisce il soggetto_ruolo_id dell''emittente, oppure NULL se non e'' risolvibile. Regola a due livelli, quella gia'' in vigore: 1) mapping specifico in anagrafiche.emittenti_fiscali_billing_account sul BA (al massimo uno, uq_emittenti_fiscali_ba); 2) se il BA non ha mapping, l''emittente is_default = true (al massimo uno, uq_emittenti_fiscali_ba_default). Sono i due indici univoci a rendere «l''emittente del BA» un singolare. ⭐ Estratta il 2026-08-18 (R-5, brief perimetro-emittente Fase E) perche'' la regola esisteva solo in forma booleana dentro fn_check_ba_visible_for_emittenti: per MOSTRARE il nome dell''emittente nella riga della ricerca universale sarebbe servito riscriverla. Ora il check delega a questa e la definizione e'' una sola. ⚠️ NON risale l''albero dei billing account: un figlio senza mapping NON eredita quello del padre, ricade sul default globale. E'' il comportamento preesistente, spostato e non cambiato; l''omogeneita'' dell''albero e'' presidiata altrove (anagrafiche.fn_guard_albero_ba_emittente, P-1). ⚠️ NON applica lo scope dell''utente: dice chi fattura, non chi puo'' vedere. Il filtro di perimetro e'' del chiamante.';
```

---
{% include-markdown "signature-core.md" %}
