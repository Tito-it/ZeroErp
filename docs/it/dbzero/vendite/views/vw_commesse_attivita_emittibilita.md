# 🔍 View `vw_commesse_attivita_emittibilita`

> 📝 **Descrizione**
>
> SEDE UNICA del criterio «questa riga di commessa puo' entrare in un giro di fatturazione, e se no perche'». Una riga per riga di commessa. Consumatori: vendite.fn_list_emittibili_lane (filtra classe = PRONTA), vendite.fn_list_commesse_emittibili (quali commesse visitare), vendite.fn_emit_attivita_fatturabili_da_commessa (quali righe emettere) e vendite.fn_diagnostica_gruppi_fatturabili (conta per classe).
> ⭐ NASCE PERCHE' IL CRITERIO ERA SCRITTO DUE VOLTE: la lane lo FILTRA, la diagnostica lo CONTA, ed e' dichiarata «lo specchio della lane». Il 2026-09-09 lo specchio si e' rotto in silenzio — un criterio aggiunto alla lane e non alla diagnostica, che rispondeva «era pronto» su un documento che la lane non aveva offerto. Ora il criterio non e' scritto in nessuna delle due.
> ⭐ I DUE FATTORI SONO ORTOGONALI: `classe_emittibilita` descrive la RIGA, `commessa_emittibile` la TESTATA, e chi decide dichiara quali dei due usa. ⛔ Fonderli toglierebbe alla diagnostica la sola cosa che sa dire meglio della lane («le righe sarebbero pronte, e' la commessa a essere in BOZZA»).
> ⭐ VOCABOLARIO CHIUSO di sei valori: EMESSA · ANNULLATA · RIFIUTATA · NON_APPROVATA · TRATTENUTA · PRONTA.
> ⛔ NON contiene il PERIMETRO DELLA DOMANDA — tetto di competenza, billing account, utility, emittente, corsia, p_gruppi, e l'auto-esclusione del proprio lotto nel pull: quelli dipendono da chi chiede. E' anche il motivo per cui «fuori competenza» non e' una classe: quella riga e' PRONTA, solo non per quel mese.
> ⭐ MA IL LEGAME DI COMPETENZA DEL TRATTENUTO SI': qui la competenza della riga c'e'. E' `lotto_competenza_mese &gt;= ca.competenza_mese`, perche' la selezione e' CUMULATIVA. ⛔ Non e' un'uguaglianza: il LATERAL dell'esito su vw_dash_competenza_gruppi lega =, e copiarlo darebbe un blocco piu' stretto della regola.
> ⚠️ `tipo_doc_fiscale_id IS NOT NULL` non e' fra i criteri: e' un ramo irraggiungibile da quando chk_commesse_attivita_tipo_doc_emittibile e' VALIDATO, e i presidi sono i test 9 e 10 di test-diagnostica-gruppi-fatturabili-v1.sql.
> ⚠️ `trattenuta_da_lotti` e' NULL quando la riga non e' trattenuta (mai un array vuoto) ed e' ORDINATO per lotto_id: chi ne vuole uno prende il primo e non scommette.
> Brief: brief-db-il-trattenuto-passa-lo-stesso.md (L3).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_commesse_attivita_emittibilita
WITH (security_invoker=on) AS
SELECT ca.id AS commessa_attivita_id,
    co.id AS commessa_id,
    co.codice AS commessa_codice,
    sc.codice_interno AS commessa_stato_codice_interno,
    COALESCE(sc.descrizione, sc.codice) AS commessa_stato_descrizione,
    sc.emittibile AS commessa_emittibile,
    vendite.fn_build_gruppo_fatturabile_key(ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id) AS gruppo_key,
    ca.competenza_mese,
    ca.tipo_doc_fiscale_id,
    co.emittente_soggetto_ruolo_id,
    co.utility_id,
    co.billing_account_id,
    co.fatturazione_immediata,
    ca.stato_emissione,
    ca.stato_approvazione,
    (
        CASE
            WHEN ((ca.stato_emissione)::text = 'EMESSA'::text) THEN 'EMESSA'::text
            WHEN ((ca.stato_emissione)::text = 'ANNULLATA'::text) THEN 'ANNULLATA'::text
            WHEN ((ca.stato_approvazione)::text = 'RIFIUTATA'::text) THEN 'RIFIUTATA'::text
            WHEN ((ca.stato_approvazione)::text <> 'APPROVATA'::text) THEN 'NON_APPROVATA'::text
            WHEN (trat.lotti IS NOT NULL) THEN 'TRATTENUTA'::text
            ELSE 'PRONTA'::text
        END)::character varying AS classe_emittibilita,
    trat.lotti AS trattenuta_da_lotti
   FROM (((vendite.commesse_attivita ca
     JOIN vendite.commesse co ON ((co.id = ca.commessa_id)))
     JOIN vendite.stati_commessa sc ON ((sc.id = co.stato_commessa_id)))
     LEFT JOIN LATERAL ( SELECT array_agg(t.lotto_id ORDER BY t.lotto_id) AS lotti
           FROM vendite.vw_documenti_trattenuti_da_lotto t
          WHERE ((t.gruppo_key = vendite.fn_build_gruppo_fatturabile_key(ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id)) AND (t.lotto_competenza_mese >= ca.competenza_mese))) trat ON (true));
```

</div>


---
{% include-markdown "signature-core.md" %}
