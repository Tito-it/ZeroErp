{% include-markdown "it/dbzero/dbops/manual/vw_radici_di_prova_in_produzione.md" %}
# 🔍 View `vw_radici_di_prova_in_produzione`

> 📝 **Descrizione**
>
> PRESIDIO: le radici di prova (le righe di dbops.credenziali_di_prova e dbops.soggetti_di_prova) in un database dichiarato PRODUZIONE. DEVE restare vuota: il guard dbops.trgfn_etichette_di_prova_guard impedisce che un'etichetta nasca in PRODUZIONE e l'ambiente non cambia; questa e' l'ultima rete per cio' che i guard non vedono (un dump di sviluppo ripristinato su un server di produzione con l'ambiente riscritto a mano, un trigger disattivato). Legge script.fn_ambiente_dichiarato(), che non solleva: su un'installazione non dichiarata e' vuota. Legge solo dbops: in CI non e' rotta. Brief: brief-db-processi-accensione-per-ambiente (R-4).

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_radici_di_prova_in_produzione AS
SELECT 'CREDENZIALE'::text AS tipo,
    c.chiave,
    (c.auth_user_id)::text AS radice_id,
    c.data_insert
   FROM dbops.credenziali_di_prova c
  WHERE (script.fn_ambiente_dichiarato() = 'PRODUZIONE'::text)
UNION ALL
 SELECT 'SOGGETTO'::text AS tipo,
    s.chiave,
    (s.soggetto_id)::text AS radice_id,
    s.data_insert
   FROM dbops.soggetti_di_prova s
  WHERE (script.fn_ambiente_dichiarato() = 'PRODUZIONE'::text);
```

</div>


---
{% include-markdown "signature-core.md" %}
