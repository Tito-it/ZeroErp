# 🔍 View `vw_lotti_congelati_con_gruppi_in_errore`

> 📝 **Descrizione**
>
> PRESIDIO. Elenca una contraddizione: un lotto CONGELATO (lo stato fiscale non e' piu' pre-fiscale: vendite.vw_lotti_fase.pre_fiscale falso, o ignoto) che contiene documenti dichiarati in ERRORE, qualunque sia stato_lotto. Il fiscale e' fermo, i documenti non sono nati: non possono stare insieme. DEVE RESTARE VUOTA. ⭐ L'asse e' lo stato FISCALE, lo stesso di dbops.vw_lotti_fermi_da_guardare: un lotto ancora pre-fiscale con un esito in errore e' un lotto fermo e lo dice quel presidio; uno congelato lo dice questo. Nessun buco (congelato con stato_lotto IN_ESECUZIONE o ERRORE), nessun doppione (COMPLETATO in bozza). ⭐ Le porte: COMPLETATO su un lotto fermo lo rifiuta il database (trg_fatturazione_lotti_a10_guard_completato_upd); un esito scritto ERRORE dopo il congelamento, o un congelamento con esiti in errore, sono cio' che questa vista sorveglia. ⭐ Un lotto annullato non compare perche' l'annullo gli chiude gli esiti (fn_annulla_lotto_da_draft), non per un filtro: la vista non esclude gli annullati, e non deve. Legge vendite.fatturazione_lotti_esiti, quindi vede anche i lotti senza perimetro (i giri di massa). Lettore a catalogo: dbops.vw_lotti_congelati_con_errori_da_guardare. Fino al 2026-11-07 si chiamava vw_lotti_chiusi_con_gruppi_in_errore e guardava stato_lotto = COMPLETATO (storia: brief-db-esito-gruppo-lotto §15, §24, §25; brief-db-annullamento-chiude-la-vita §9). Brief: brief-db-revisione-dbops, giro 6 (Q14 ⑦).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_lotti_congelati_con_gruppi_in_errore
WITH (security_invoker=true) AS
SELECT l.id AS lotto_id,
    l.codice AS lotto_codice,
    l.stato_lotto,
    f.stato_codice_interno,
    l.competenza_mese,
    l.emittente_soggetto_ruolo_id,
    count(*) AS gruppi_in_errore,
    min(e.errore_quando) AS primo_errore,
    max(e.errore_quando) AS ultimo_errore,
    array_agg(DISTINCT e.errore_codice) FILTER (WHERE (e.errore_codice IS NOT NULL)) AS codici_errore
   FROM ((vendite.fatturazione_lotti l
     JOIN vendite.vw_lotti_fase f ON ((f.lotto_id = l.id)))
     JOIN vendite.fatturazione_lotti_esiti e ON ((e.lotto_id = l.id)))
  WHERE ((e.stato_esecuzione = 'ERRORE'::text) AND (NOT f.pre_fiscale))
  GROUP BY l.id, l.codice, l.stato_lotto, f.stato_codice_interno, l.competenza_mese, l.emittente_soggetto_ruolo_id;
```

</div>


---
{% include-markdown "signature-core.md" %}
