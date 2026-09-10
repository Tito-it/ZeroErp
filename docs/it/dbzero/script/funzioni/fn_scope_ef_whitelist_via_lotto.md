# ⚙️ Funzione `fn_scope_ef_whitelist_via_lotto`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_lotto(p_auth_user_id integer, p_lotto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_lotto(p_auth_user_id integer, p_lotto_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dire se l'operatore ha nel proprio perimetro
    --   l'emittente del lotto di fatturazione indicato.
    -- ⚠️ Si passa da `_via_sr` e NON dalla canonica: la testata
    --   porta emittente_soggetto_ruolo_id, non emittente_fiscale_id.
    --   Le due numerazioni sono diverse, quindi confonderle non
    --   da' errore — da' zero righe.
    -- ⚠️ Lotto inesistente -> emittente NULL -> la canonica
    --   risponde false quando la whitelist e' valorizzata:
    --   fail-closed, come per tutte le altre famiglie.
    SELECT script.fn_scope_ef_whitelist_via_sr(
        p_auth_user_id,
        (SELECT l.emittente_soggetto_ruolo_id
           FROM vendite.fatturazione_lotti l
          WHERE l.id = p_lotto_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_lotto(p_auth_user_id integer, p_lotto_id bigint)
IS 'Adattatore di scope per i satelliti di vendite.fatturazione_lotti: risale da lotto_id a `emittente_soggetto_ruolo_id` e delega a script.fn_scope_ef_whitelist_via_sr. ⚠️ Via SR e non la canonica fn_scope_ef_whitelist: la testata dei lotti nomina l''emittente per soggetto-ruolo, come vendite.fatture e a differenza delle sei famiglie di documento — e le due numerazioni non sono confrontabili. STABLE e NON security definer, come gli altri fn_scope_*. Lotto inesistente -> emittente NULL -> false a whitelist valorizzata (fail-closed). Brief: brief-db-perimetro-emittente-righe-documento.md §11.9';
```

---
{% include-markdown "signature-core.md" %}
