{% include-markdown "it/dbzero/dbops/manual/vw_lotti_fermi_da_guardare.md" %}
# 🔍 View `vw_lotti_fermi_da_guardare`

> 📝 **Descrizione**
>
> PRESIDIO: i giri di fatturazione PRE-FISCALI che la sede unica (vendite.vw_lotti_segnalazioni_summary) dichiara `fermo` — critiche vive, riga di ponte in ERRORE o esito ERRORE — da OLTRE UN'ORA, e che nessuno ha rilanciato ne' sciolto, qualunque sia stato_lotto (un COMPLETATO in bozza con un esito in errore e' qui). DEVE restare VUOTA. Il banner lo dice a chi apre il lotto; questa riga lo dice a chi non lo apre. ⭐ E' un LETTORE: nessun addendo e' ricalcolato qui — `motivo` e `fermo_da` sono le colonne della sede, e un addendo nuovo del verdetto lo vedono insieme il banner, il digest e il pallino (D-1 di Tid, 18-09: una sede a DB, il backend trasporta). ⭐ SOLO PRE-FISCALI (vw_lotti_fase.pre_fiscale): un lotto congelato con un esito ERRORE, o con lo stato fiscale ignoto, e' la contraddizione di vendite.vw_lotti_congelati_con_gruppi_in_errore — i due presidi si spartiscono lo stesso asse, quello fiscale, senza buchi ne' doppioni (rev 2026-11-07, brief-db-revisione-dbops giro 6: prima l'altro guardava stato_lotto). ⚠️ Un'ora non e' una misura: il rilancio e' il gesto di una persona, e le tre viste delle code usano la stessa soglia per la stessa ragione. L'orologio e' `fermo_da`, il fatto PIU' RECENTE che ferma il lotto: un rilancio che fallisce di nuovo lo riparte, e la domanda resta «da quanto nessuno ci mette le mani». La soglia sta qui, non nel catalogo. ⛔ Perimetro DEFINER a catalogo: le tabelle sotto hanno la RLS e la vista e' security_invoker — da una sessione senza GUC risponde zero PER CECITA', il digest conta da proprietario con fn_conta_presidio, una persona legge col proprio perimetro. Brief: brief-db-osservabilita-lotto-fermo-r6-indici §2; analisi-osservabilita-log §4 Passo C.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_lotti_fermi_da_guardare
WITH (security_invoker=true) AS
SELECT s.lotto_id,
    f.lotto_codice,
    f.lotto_competenza_mese,
    f.stato_codice_interno,
    l.emittente_soggetto_ruolo_id,
    ef.codice AS emittente_codice,
    s.fermo_motivo AS motivo,
    s.fermo_da,
    (now() - s.fermo_da) AS da_quanto,
    (s.fatture_critical_count + s.lotto_critical_count) AS critiche_vive,
    s.fatture_stato_esecuzione_errore_count,
    s.esiti_stato_esecuzione_errore_count,
    s.documenti_bloccanti_count,
    s.documenti_presi_in_carico_count
   FROM (((vendite.vw_lotti_segnalazioni_summary s
     JOIN vendite.vw_lotti_fase f ON ((f.lotto_id = s.lotto_id)))
     JOIN vendite.fatturazione_lotti l ON ((l.id = s.lotto_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.soggetto_ruolo_id = l.emittente_soggetto_ruolo_id)))
  WHERE (s.fermo AND f.pre_fiscale AND (s.fermo_da < (now() - '01:00:00'::interval)));
```

</div>


---
{% include-markdown "signature-core.md" %}
