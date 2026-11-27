# ⚙️ Funzione `fn_filiale_stessi_codici`

```sql
CREATE FUNCTION fn_filiale_stessi_codici(p_escludi_id bigint, p_bank_code text, p_branch_code text, p_stato_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_filiale_stessi_codici(p_escludi_id bigint, p_bank_code text, p_branch_code text, p_stato_id integer)
 RETURNS bigint
 LANGUAGE sql
 STABLE PARALLEL SAFE
BEGIN ATOMIC
 SELECT b.id
    FROM ((anagrafiche.bank_branches b
      JOIN anagrafiche.soggetti_ruoli r ON ((r.id = b.soggetto_ruolo_id)))
      JOIN anagrafiche.soggetti s ON ((s.id = r.soggetto_id)))
   WHERE ((b.bank_code = fn_filiale_stessi_codici.p_bank_code) AND (b.branch_code = fn_filiale_stessi_codici.p_branch_code) AND (s.stato_id = fn_filiale_stessi_codici.p_stato_id) AND (b.id IS DISTINCT FROM fn_filiale_stessi_codici.p_escludi_id))
   ORDER BY b.id
  LIMIT 1;
END

COMMENT ON FUNCTION anagrafiche.fn_filiale_stessi_codici(p_escludi_id bigint, p_bank_code text, p_branch_code text, p_stato_id integer)
IS 'La filiale (anagrafiche.bank_branches.id, la minore) che ha gia'' codice della banca e codice della filiale dati nel paese dato (soggetti.stato_id del soggetto della banca), esclusa quella indicata; NULL se non ce n''e''. Riceve i codici nella forma di confronto (script.fn_normalizza_codice_bancario). La usano i due guard dell''unicita'' per paese, anagrafiche.trgfn_bank_branches_guard_unica_per_paese e anagrafiche.trgfn_soggetti_guard_filiali_unica_per_paese.';
```

</div>

---
{% include-markdown "signature-core.md" %}
