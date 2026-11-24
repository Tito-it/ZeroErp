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
             script.fn_utente_di_sessione('anagrafiche.fn_id_fiscale_bloccato')),
           false);
$function$

COMMENT ON FUNCTION anagrafiche.fn_id_fiscale_bloccato(p_valore text)
IS 'Vero se una parte dell''identificativo fiscale del soggetto con questo valore attuale non si puo'' cambiare: il valore e'' scritto e chi agisce non e'' SUPER_ADMIN (script.fn_is_super_admin sull''utente di sessione, script.fn_utente_di_sessione; senza utente vale no). Un valore NULL si puo'' riempire. Le parti sono codice_fiscale, partita_iva e stato_id: insieme fanno la chiave d''unicita'' del soggetto (uq_soggetto_idstato_id_fiscale_univoco), e cambiarle farebbe di un soggetto un altro. Lo stato non e'' mai NULL e arriva come testo: per lui la regola e'' «solo il SUPER_ADMIN». La leggono anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile (con il valore OLD) e anagrafiche.fn_soggetto_id_fiscale_bloccato (sulla riga, per il form).';
```

</div>

---
{% include-markdown "signature-core.md" %}
