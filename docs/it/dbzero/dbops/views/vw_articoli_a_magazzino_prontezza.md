{% include-markdown "it/dbzero/dbops/manual/vw_articoli_a_magazzino_prontezza.md" %}
# 🔍 View `vw_articoli_a_magazzino_prontezza`

> 📝 **Descrizione**
>
> Presidio di PRONTEZZA del magazzino: UNA riga, stato = MARCATI se esiste almeno un articolo attivo con gestito_a_magazzino, altrimenti NESSUNO_MARCATO. Esiste perche' gestito_a_magazzino nasce false (fail-safe): senza una spia, un magazzino senza articoli gestiti resterebbe vuoto senza che nessun rosso lo dica. In dbops.presidi: natura ZERO, colonna_stato = stato, stato_atteso = MARCATI: dbops.fn_conta_presidio conta le righe IS DISTINCT FROM MARCATI, quindi lo zero suona e il pieno tace. catalogo.articoli non ha RLS: perimetro LIBERO. Cadenza SETTIMANALE: una condizione di prontezza, non un incidente.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_articoli_a_magazzino_prontezza AS
SELECT
        CASE
            WHEN (EXISTS ( SELECT 1
               FROM catalogo.articoli a
              WHERE (a.gestito_a_magazzino AND a.attivo))) THEN 'MARCATI'::text
            ELSE 'NESSUNO_MARCATO'::text
        END AS stato,
    ( SELECT count(*) AS count
           FROM catalogo.articoli a
          WHERE (a.gestito_a_magazzino AND a.attivo)) AS n_marcati;
```

</div>


---
{% include-markdown "signature-core.md" %}
