{% include-markdown "it/dbzero/script/manual/fn_get_ba_emittente_sr_id.md" %}
# ⚙️ Funzione `fn_get_ba_emittente_sr_id`

```sql
CREATE FUNCTION fn_get_ba_emittente_sr_id(p_billing_account_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_ba_emittente_sr_id(p_billing_account_id bigint)
 RETURNS bigint
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: «quale emittente fattura questo billing account?» —
    --   il soggetto_ruolo dell'emittente, o NULL se non risolvibile.
    --   Regola a TRE livelli dal 20260913-01 (D13): mapping
    --   specifico; altrimenti, IN SESSIONE, l'emittente di chi
    --   sta agendo; altrimenti il default dell'installazione.
    -- ⚠️ Il CASE esterno non e' ridondante. Senza, un BA NULL
    --   cadrebbe nei rami 2 e 3 e si vedrebbe rispondere un
    --   emittente — cioe' «nessun billing account» verrebbe
    --   letto come «billing account non ancora collegato», che e'
    --   una cosa diversa e apre invece di chiudere.
    SELECT CASE
             WHEN p_billing_account_id IS NULL THEN NULL
             ELSE COALESCE(
                    -- 1) Mapping specifico del BA. Al massimo una
                    --    riga: uq_emittenti_fiscali_ba. Vince sempre:
                    --    il COALESCE non valuta i rami dopo.
                    (SELECT efba.emittente_soggetto_ruolo_id
                       FROM anagrafiche.emittenti_fiscali_billing_account efba
                      WHERE efba.billing_account_id = p_billing_account_id),
                    -- 2) Riserva IN SESSIONE: un BA non ancora
                    --    collegato appartiene a chi lo sta creando.
                    --    E' l'istante fra l'INSERT e il trigger AFTER
                    --    z90_link_ef, cioe' il RETURNING: la riserva
                    --    dice cio' che il trigger sta per scrivere,
                    --    con la STESSA funzione che usa lui.
                    -- ⛔ Il CASE e' il guard: fn_resolve_emittente_for_user
                    --    SOLLEVA (e logga) su NULL o <= 0, e senza
                    --    sessione non va chiamata. Un WHERE sulla
                    --    stessa riga non garantirebbe l'ordine.
                    (SELECT ef.soggetto_ruolo_id
                       FROM anagrafiche.emittenti_fiscali ef
                      WHERE ef.id = (SELECT CASE
                                              WHEN s.auth_user_id > 0
                                              THEN script.fn_resolve_emittente_for_user(s.auth_user_id)
                                            END
                                       FROM (SELECT NULLIF(current_setting('app.current_user_id', true), '')::integer
                                                    AS auth_user_id) s)),
                    -- 3) Riserva SENZA sessione: l'emittente di
                    --    default dell'installazione (batch,
                    --    manutenzione, admin globale senza
                    --    emittente attivo). Al massimo uno:
                    --    uq_emittenti_fiscali_ba_default.
                    (SELECT efba_d.emittente_soggetto_ruolo_id
                       FROM anagrafiche.emittenti_fiscali_billing_account efba_d
                      WHERE efba_d.is_default)
                  )
           END;
$function$

COMMENT ON FUNCTION script.fn_get_ba_emittente_sr_id(p_billing_account_id bigint)
IS '⭐ rev 2026-10-18 (20261018-51, D-3b-2 ondata 2): COST 5000. Legge tabelle ed e'' nominata dalle policy ef_whitelist del billing account (20261018-50). Risolve «quale emittente fattura questo billing account» e restituisce il soggetto_ruolo_id dell''emittente, oppure NULL se non e'' risolvibile. Regola a TRE livelli dal 20260913-01 (D13, decisione di Tid del 2026-09-12): 1) mapping specifico in anagrafiche.emittenti_fiscali_billing_account sul BA (al massimo uno, uq_emittenti_fiscali_ba), che vince sempre; 2) se il BA non ha legame, IN SESSIONE, l''emittente dell''operatore che sta agendo — script.fn_resolve_emittente_for_user(app.current_user_id), la STESSA funzione con cui il trigger z90_link_ef scrive il legame: un BA non ancora collegato appartiene a chi lo sta creando, ed e'' cio'' che rende visibile la riga al RETURNING dell''INSERT, che arriva PRIMA del trigger AFTER; 3) senza sessione (batch, manutenzione, admin globale senza emittente attivo), l''emittente is_default = true (al massimo uno, uq_emittenti_fiscali_ba_default). Fino a quel changeSet il livello 2 non esisteva e un operatore di un emittente non di default non riusciva a creare un cliente: l''INSERT passava, la rilettura negava (42501). ⚠️ Un BA che RESTA senza legame (creato senza sessione) e'', in sessione, di chiunque lo guardi: e'' un dato anomalo che il modello ammette, non un caso d''uso — la forma «emittente come colonna del BA» resta una decisione di modello in coda. ⚠️ NON risale l''albero dei billing account: un figlio senza legame NON eredita quello del padre. L''omogeneita'' dell''albero e'' presidiata altrove (anagrafiche.fn_guard_albero_ba_emittente, P-1). ⚠️ NON applica lo scope dell''utente: dice chi fattura, non chi puo'' vedere. Il filtro di perimetro e'' del chiamante. ⚠️ STABLE e NON PARALLEL SAFE dal 20260913-01: la delegata fn_resolve_emittente_for_user non lo e'' (plpgsql, log via dblink sul ramo d''errore), e la marcatura si dichiara onestamente — come gia'' il 18-08 sulla ricerca universale. Estratta il 2026-08-18 (R-5, brief perimetro-emittente Fase E) perche'' la regola esisteva solo in forma booleana dentro fn_check_ba_visible_for_emittenti, che ora delega a questa: la definizione e'' una sola. Brief: brief-db-ba-riserva-emittente-operatore-d13.';
```

---
{% include-markdown "signature-core.md" %}
