{% include-markdown "it/dbzero/vendite/manual/vw_lotti_gruppi_serviti.md" %}
# 🔍 View `vw_lotti_gruppi_serviti`

> 📝 **Descrizione**
>
> CONSUNTIVO: quali gruppi fatturabili ciascun lotto ha davvero servito, cioe' per quali gruppi esiste almeno un'attivita' con fattura_riga_id valorizzato su una fattura del lotto. Grana (lotto_id, gruppo_key, commessa_id). Risponde alla richiesta §8.2 di brief-db-emittibilita-visibile-e-sbloccabile: vendite.fn_list_emittibili_lane.gruppi_coperti e' una PREVISIONE fatta alla discovery, e fra quella e l'esecuzione il lavoro puo' sparire (righe prese da un altro giro) senza che nessuno lo dica — la pipeline esce senza errore e senza lotto, e l'esito legge pieno successo. ⚠️ vendite.fatturazione_lotti_gruppi NON risponde a questa domanda: registra il PERMESSO (quali gruppi un lotto puo' lavorare), non il servito. ⚠️ La chiave arriva da vendite.fn_build_gruppo_fatturabile_key calcolata su commesse_attivita, mai sulle colonne gemelle di attivita_fatturabili: e' la stessa fonte della lane e di vw_dash_competenza_gruppi, e senza quella identita' il confronto servito/richiesto non sarebbe un confronto. ⚠️ E' una MISURA VIVA, non un log immutabile: se un lotto torna a DRAFT e le fatture spariscono, il gruppo smette di risultare servito — corretto, ma non e' il registro storico di cosa fece quel giro. Nessun importo per scelta: il valore pro-quota di una riga e' una formula che vive gia' in vw_dash_competenza_attivita.valore_fatturato, e la domanda del §8.2 e' quali gruppi, non per quanto. security_invoker=on: il cancello di scope e' il JOIN su vendite.fatture / fatture_righe / commesse_attivita, che la RLS ce l'hanno.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_lotti_gruppi_serviti
WITH (security_invoker=on) AS
SELECT flf.lotto_id,
    vendite.fn_build_gruppo_fatturabile_key(ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id) AS gruppo_key,
    ca.commessa_id,
    count(DISTINCT ca.id) AS n_attivita_fatturate,
    count(DISTINCT f.id) AS n_fatture
   FROM ((((vendite.fatturazione_lotti_fatture flf
     JOIN vendite.fatture f ON ((f.id = flf.fattura_id)))
     JOIN vendite.fatture_righe fr ON ((fr.fattura_id = f.id)))
     JOIN vendite.attivita_fatturabili af ON ((af.fattura_riga_id = fr.id)))
     JOIN vendite.commesse_attivita ca ON ((ca.id = af.commessa_attivita_id)))
  GROUP BY flf.lotto_id, (vendite.fn_build_gruppo_fatturabile_key(ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id)), ca.commessa_id;
```

</div>


---
{% include-markdown "signature-core.md" %}
