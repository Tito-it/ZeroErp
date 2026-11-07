{% include-markdown "it/dbzero/vendite/manual/vw_lotti_segnalazioni_summary.md" %}
# 🔍 View `vw_lotti_segnalazioni_summary`

> 📝 **Descrizione**
>
> SEDE UNICA del riepilogo segnalazioni di un lotto e del verdetto «fermo» (D-1 di Tid, 2026-09-18: «la regola va a DB»). Una riga per lotto con i DIECI conteggi che fn_get_lotto_segnalazioni_summary restituiva dalle proprie CTE — sei storici (segnalazioni C/W/I per canale fattura e lotto, righe di ponte in ERRORE), tre del banner (documenti bloccanti, presi in carico, critiche del giro), il decimo (esiti ERRORE) — piu' TRE colonne nuove. ⭐ fermo = (fatture_critical + lotto_critical) &gt; 0 OR fatture_stato_esecuzione_errore &gt; 0 OR esiti_stato_esecuzione_errore &gt; 0: era LottoSegnalazioniService.evaluate_lotto_status, ricopiato qui UNA volta per non doverlo ricopiare mai piu' — il backend lo LEGGE (undicesima colonna della funzione). ⚠️ E' il verdetto su OGNI lotto, qualunque sia lo stato fiscale: la spartizione sull'asse fiscale la fanno i due presidi (dbops.vw_lotti_fermi_da_guardare per i pre-fiscali, vendite.vw_lotti_congelati_con_gruppi_in_errore per i congelati), non questa vista. ⭐ fermo_motivo: vocabolario chiuso CRITICHE | FATTURE_IN_ERRORE | ESITI_IN_ERRORE, con la precedenza del banner; NULL se non fermo. ⭐ fermo_da: il PIU' RECENTE dei fatti che lo fermano (data_ora della critica viva, data_update della riga di ponte in ERRORE, errore_quando dell'esito con data_update a ripiego) — il presidio chiede «da quanto nessuno lo rilancia ne' lo scioglie», e un rilancio fallito di nuovo riparte l'orologio; NOT NULL ogni volta che fermo e' vero. ⛔ Gli aggregati vivono SOLO qui: la funzione e il presidio sono due lettori, e un addendo nuovo si aggiunge in un posto solo. Gli stessi filtri della funzione: disabilitato IS FALSE, il NOT EXISTS su ESCLUSO nel canale lotto (con gruppo_key NULL la riga CONTA: la critica del giro ferma il giro), il denominatore sugli ESITI e non sul perimetro. security_invoker: una persona legge i propri lotti; un lotto fuori perimetro NON e' nella vista. Brief: brief-db-osservabilita-lotto-fermo-r6-indici §2; rev 2026-11-07 brief-db-revisione-dbops giro 6.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_lotti_segnalazioni_summary
WITH (security_invoker=true) AS
SELECT l.id AS lotto_id,
    COALESCE(fa.fc, (0)::bigint) AS fatture_critical_count,
    COALESCE(fa.fw, (0)::bigint) AS fatture_warning_count,
    COALESCE(la.lc, (0)::bigint) AS lotto_critical_count,
    COALESCE(la.lw, (0)::bigint) AS lotto_warning_count,
    COALESCE(la.li, (0)::bigint) AS lotto_info_count,
    COALESCE(pa.pe, (0)::bigint) AS fatture_stato_esecuzione_errore_count,
    COALESCE(la.docs_bloccanti, (0)::bigint) AS documenti_bloccanti_count,
    COALESCE(ea.dt, (0)::bigint) AS documenti_presi_in_carico_count,
    COALESCE(la.critiche_giro, (0)::bigint) AS critiche_giro_count,
    COALESCE(ea.de, (0)::bigint) AS esiti_stato_esecuzione_errore_count,
    (((COALESCE(fa.fc, (0)::bigint) + COALESCE(la.lc, (0)::bigint)) > 0) OR (COALESCE(pa.pe, (0)::bigint) > 0) OR (COALESCE(ea.de, (0)::bigint) > 0)) AS fermo,
        CASE
            WHEN ((COALESCE(fa.fc, (0)::bigint) + COALESCE(la.lc, (0)::bigint)) > 0) THEN 'CRITICHE'::text
            WHEN (COALESCE(pa.pe, (0)::bigint) > 0) THEN 'FATTURE_IN_ERRORE'::text
            WHEN (COALESCE(ea.de, (0)::bigint) > 0) THEN 'ESITI_IN_ERRORE'::text
            ELSE NULL::text
        END AS fermo_motivo,
    GREATEST(fa.ultima_critica, la.ultima_critica, pa.ultimo_errore, ea.ultimo_errore) AS fermo_da
   FROM ((((vendite.fatturazione_lotti l
     LEFT JOIN ( SELECT lf.lotto_id,
            count(*) FILTER (WHERE (fl.status = 'C'::bpchar)) AS fc,
            count(*) FILTER (WHERE (fl.status = 'W'::bpchar)) AS fw,
            max(fl.data_ora) FILTER (WHERE (fl.status = 'C'::bpchar)) AS ultima_critica
           FROM (vendite.fatturazione_lotti_fatture lf
             JOIN vendite.fatture_log fl ON ((fl.fattura_id = lf.fattura_id)))
          WHERE (fl.disabilitato IS FALSE)
          GROUP BY lf.lotto_id) fa ON ((fa.lotto_id = l.id)))
     LEFT JOIN ( SELECT ll.lotto_id,
            count(*) FILTER (WHERE (ll.status = 'C'::bpchar)) AS lc,
            count(*) FILTER (WHERE (ll.status = 'W'::bpchar)) AS lw,
            count(*) FILTER (WHERE (ll.status = 'I'::bpchar)) AS li,
            count(DISTINCT ll.gruppo_key) FILTER (WHERE ((ll.status = 'C'::bpchar) AND (ll.gruppo_key IS NOT NULL))) AS docs_bloccanti,
            count(*) FILTER (WHERE ((ll.status = 'C'::bpchar) AND (ll.gruppo_key IS NULL))) AS critiche_giro,
            max(ll.data_ora) FILTER (WHERE (ll.status = 'C'::bpchar)) AS ultima_critica
           FROM vendite.fatturazione_lotti_log ll
          WHERE ((ll.disabilitato IS FALSE) AND (NOT (EXISTS ( SELECT 1
                   FROM vendite.fatturazione_lotti_esiti e
                  WHERE ((e.lotto_id = ll.lotto_id) AND (e.gruppo_key = ll.gruppo_key) AND (e.stato_esecuzione = 'ESCLUSO'::text))))))
          GROUP BY ll.lotto_id) la ON ((la.lotto_id = l.id)))
     LEFT JOIN ( SELECT e.lotto_id,
            count(*) AS dt,
            count(*) FILTER (WHERE (e.stato_esecuzione = 'ERRORE'::text)) AS de,
            max(COALESCE(e.errore_quando, e.data_update)) FILTER (WHERE (e.stato_esecuzione = 'ERRORE'::text)) AS ultimo_errore
           FROM vendite.fatturazione_lotti_esiti e
          GROUP BY e.lotto_id) ea ON ((ea.lotto_id = l.id)))
     LEFT JOIN ( SELECT lf.lotto_id,
            count(*) FILTER (WHERE ((lf.stato_esecuzione)::text = 'ERRORE'::text)) AS pe,
            max(lf.data_update) FILTER (WHERE ((lf.stato_esecuzione)::text = 'ERRORE'::text)) AS ultimo_errore
           FROM vendite.fatturazione_lotti_fatture lf
          GROUP BY lf.lotto_id) pa ON ((pa.lotto_id = l.id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
