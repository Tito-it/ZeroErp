{% include-markdown "it/dbzero/dbops/manual/vw_stati_check_da_sanare.md" %}
# 🔍 View `vw_stati_check_da_sanare`

> 📝 **Descrizione**
>
> La lista di lavoro del presidio degli stati mai scritti: i valori di una colonna di stato che nessuno scrive e nessuno ha dichiarato (NON_DICHIARATO), e le righe del registro dbops.stati_check_dichiarazioni che non servono piu' (DEBITO_ESTINTO), dalla misura dbops.vw_stati_check_scrittori. DEVE restare vuota, ed e' un CANCELLO: la fa rossa in CI db/pgtap/dbops/test-stati-check-scrittori-v1.sql, e sul lato Python il test del backend test_stati_check_scrittori_python verifica le righe DICHIARATO_APPLICAZIONE della misura. Non e' un filtro da allargare per farla tacere: si allarga il registro, con la ragione.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_stati_check_da_sanare AS
SELECT schema_tabella,
    nome_tabella,
    colonna,
    valore,
    esito,
    canale,
    ragione,
    data_registrazione,
    scrittori_tabella,
        CASE esito
            WHEN 'NON_DICHIARATO'::text THEN 'nessuna funzione, nessun default e nessuna dichiarazione: o si scrive lo scrittore, o la riga entra in dbops.stati_check_dichiarazioni con il canale e la ragione'::text
            ELSE 'la riga di registro non serve piu'': il valore ha trovato uno scrittore a DB, o e'' uscito dal CHECK. Va tolta dal CSV e cancellata con un DELETE forward-only'::text
        END AS da_fare
   FROM dbops.vw_stati_check_scrittori s
  WHERE (esito = ANY (ARRAY['NON_DICHIARATO'::text, 'DEBITO_ESTINTO'::text]));
```

</div>


---
{% include-markdown "signature-core.md" %}
