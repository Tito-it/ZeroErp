{% include-markdown "it/dbzero/dbops/manual/vw_lotti_congelati_con_errori_da_guardare.md" %}
# 🔍 View `vw_lotti_congelati_con_errori_da_guardare`

> 📝 **Descrizione**
>
> PRESIDIO: i lotti CONGELATI (stato fiscale non piu' pre-fiscale, o ignoto) che contengono documenti in ERRORE, qualunque sia stato_lotto. DEVE restare VUOTA. ⭐ E' un LETTORE: la contraddizione la definisce vendite.vw_lotti_congelati_con_gruppi_in_errore, qui si aggiunge solo l'emittente, per chi arriva dal digest. ⭐ Si spartisce l'asse fiscale con dbops.vw_lotti_fermi_da_guardare: pre-fiscale -&gt; quel presidio, congelato -&gt; questo, senza buchi ne' doppioni. Un lotto ANNULLATO non compare perche' l'annullo gli chiude gli esiti, non perche' qualcuno lo filtri. ⚠️ In dbops e non in vendite: iscrivere a catalogo una vista di vendite porterebbe l'intero schema nel perimetro di test-catalogo-presidi-v1 (test 2). ⛔ Perimetro DEFINER a catalogo: le tabelle sotto hanno la RLS e le viste sono security_invoker — da una sessione senza GUC risponde zero PER CECITA', il digest conta da proprietario con fn_conta_presidio, una persona legge col proprio perimetro. Fino al 2026-11-07 si chiamava vw_lotti_chiusi_con_errori_da_guardare (brief-db-annullamento-chiude-la-vita §9.6). Brief: brief-db-revisione-dbops, giro 6 (Q14 ⑦).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_lotti_congelati_con_errori_da_guardare
WITH (security_invoker=true) AS
SELECT c.lotto_id,
    c.lotto_codice,
    c.competenza_mese,
    c.stato_lotto,
    c.stato_codice_interno,
    c.emittente_soggetto_ruolo_id,
    ef.codice AS emittente_codice,
    c.gruppi_in_errore,
    c.primo_errore,
    c.ultimo_errore,
    c.codici_errore
   FROM (vendite.vw_lotti_congelati_con_gruppi_in_errore c
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.soggetto_ruolo_id = c.emittente_soggetto_ruolo_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
