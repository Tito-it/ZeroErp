{% include-markdown "it/dbzero/vendite/manual/fn_resi_riga_accreditato_partita.md" %}
# ⚙️ Funzione `fn_resi_riga_accreditato_partita`

```sql
CREATE FUNCTION fn_resi_riga_accreditato_partita(p_resi_riga_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resi_riga_accreditato_partita(p_resi_riga_id bigint)
 RETURNS numeric
 LANGUAGE sql
 STABLE
AS $function$
-- Scopo: quanti pezzi (in unita' di MERCE, cioe' unita' padre)
--   sono gia' stati accreditati per questa riga di reso.
--   Punto UNICO della formula: la consuma vw_resi_da_accreditare
--   per non ri-offrire una quota gia' accreditata.
-- ⚠️ La somma e' UNA VOLTA PER GRUPPO, non per riga, e i due
--   casi che lo impongono tirano in direzioni opposte:
--     kit          -> N righe con la STESSA quota padre
--                     (sommarle la moltiplicherebbe)
--     consumo LIFO -> N righe con quote padre DIVERSE
--                     (vanno sommate)
--   `gruppo` distingue i due casi: un gruppo = un'unita'
--   fatturante consumata.
-- NB: nessun raise. E' letta da una vista, su insiemi in
--   movimento; una riga cancellata non deve farla fallire.
SELECT COALESCE(sum(g.qta_partita), 0::numeric)
  FROM (SELECT DISTINCT a.gruppo, a.qta_partita
          FROM vendite.resi_righe_accrediti a
         WHERE a.resi_riga_id = p_resi_riga_id) g;
$function$

COMMENT ON FUNCTION vendite.fn_resi_riga_accreditato_partita(p_resi_riga_id bigint)
IS 'Quanti pezzi, in unita'' di MERCE (unita'' padre della partita), sono gia'' stati accreditati per una riga di reso. Punto UNICO della formula, consumato da vendite.vw_resi_da_accreditare per non ri-offrire una quota gia'' accreditata — senza, dopo il primo accredito la coda ridistribuirebbe il residuo della partita sulla PRIMA riga di reso invece che su quelle non ancora accreditate, e la quota di una riga diventerebbe irraggiungibile: la stessa malattia per cui questo cantiere esiste, in forma nuova. ⚠️ La somma e'' una volta per GRUPPO e non per riga: su un kit N righe portano la stessa quota padre (sommarle la moltiplicherebbe), su un consumo LIFO N righe portano quote diverse (vanno sommate). La colonna `gruppo` distingue i due casi. brief-design-note-credito-resi D-NC-10. rev 2026-08-18.';
```

</div>

---
{% include-markdown "signature-core.md" %}
