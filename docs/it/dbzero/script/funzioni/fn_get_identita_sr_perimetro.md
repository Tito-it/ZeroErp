{% include-markdown "it/dbzero/script/manual/fn_get_identita_sr_perimetro.md" %}
# ⚙️ Funzione `fn_get_identita_sr_perimetro`

```sql
CREATE FUNCTION fn_get_identita_sr_perimetro(p_identita_id bigint, p_vesti config.ruolo_applicativo[])
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_identita_sr_perimetro(p_identita_id bigint, p_vesti config.ruolo_applicativo[])
 RETURNS bigint
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: il perimetro di chi guarda da CONTROPARTE: il soggetto_ruolo
    --   dell'identita', se e' in una delle vesti date ed e' utilizzabile
    --   oggi. NULL altrimenti: nessuna riga.
    -- Non dipende dalla riga: la policy lo chiama in UNA sottoquery non
    --   correlata, e PostgreSQL lo valuta una volta per istruzione:
    --     script.fn_scope_sr_perimetro(
    --         (SELECT script.fn_get_identita_sr_perimetro(<identita>, ARRAY['<veste>'])),
    --         <soggetto della riga>)
    -- ⭐ La policy passa la SUA veste: l'identita' deve essere quella della
    --   sessione (il middleware imposta app.ruolo_applicativo dalla stessa
    --   riga di identita_digitali).
    -- «Utilizzabile» lo decide script.fn_veste_utilizzabile, non una copia.
    SELECT idg.soggetto_ruolo_id
      FROM anagrafiche.identita_digitali idg
     WHERE idg.id = p_identita_id
       AND idg.ruolo_applicativo = ANY (p_vesti)
       AND script.fn_veste_utilizzabile(idg.id)
$function$

COMMENT ON FUNCTION script.fn_get_identita_sr_perimetro(p_identita_id bigint, p_vesti config.ruolo_applicativo[])
IS 'Il perimetro di chi guarda da controparte (CLIENTE_PORTALE, SHOP_CUSTOMER, FORNITORE_PORTALE): il soggetto_ruolo dell''identita'', se e'' in una delle vesti date ed e'' utilizzabile oggi (script.fn_veste_utilizzabile); NULL altrimenti, cioe'' nessuna riga. Non dipende dalla riga: la policy lo passa a script.fn_scope_sr_perimetro in UNA sottoquery non correlata, valutata una volta per istruzione (linee-guida-sql §10.3). La policy passa la propria veste. ⚠️ NULL = nessuno, al contrario del perimetro dell''operatore (NULL = tutti). Rev 2026-10-21 (20261021-29, giro 2 di brief-db-perimetro-una-volta-famiglie-residue).';
```

</div>

---
{% include-markdown "signature-core.md" %}
