{% include-markdown "it/dbzero/anagrafiche/manual/fn_id_fiscale_bloccato.md" %}
# ⚙️ Funzione `fn_id_fiscale_bloccato`

```sql
CREATE FUNCTION fn_id_fiscale_bloccato(p_valore text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_id_fiscale_bloccato(p_valore text)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
  SELECT p_valore IS NOT NULL
     AND NOT COALESCE(
           script.fn_is_super_admin(
             NULLIF(current_setting('app.current_user_id', true), '')::integer),
           false);
$function$

COMMENT ON FUNCTION anagrafiche.fn_id_fiscale_bloccato(p_valore text)
IS 'Vero se un codice fiscale o una partita IVA con questo valore attuale non si possono cambiare: il valore e'' scritto e chi agisce non e'' SUPER_ADMIN (script.fn_is_super_admin sull''utente della richiesta, app.current_user_id; senza utente vale no). Un valore NULL si puo'' riempire. CF e P.IVA sono la chiave d''unicita'' del soggetto (uq_soggetto_idstato_id_fiscale_univoco): cambiarli farebbe di un soggetto un altro. La leggono anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile (con il valore OLD) e anagrafiche.fn_soggetto_id_fiscale_bloccato (sulla riga, per il form).';
```

</div>

---
{% include-markdown "signature-core.md" %}
