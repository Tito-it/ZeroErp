{% include-markdown "it/dbzero/script/manual/vw_giornale_entita.md" %}
# 🔍 View `vw_giornale_entita`

> 📝 **Descrizione**
>
> La CUCITURA della diagnostica: «che cosa e' successo a questa entita'», letta dai quattro registri che oggi raccontano un pezzo di storia ciascuno — vendite.event_log, fatturazione_lotti_log, fatturazione_lotti_task_runs, fatture_log. ⭐ Vive in script e NON in vendite di proposito: i registri di eventi del progetto sono sei (ci sono anche pratiche.giornale, documenti.documenti_generati_eventi, magazzino.eventi_assets, vendite.fatture_sdi_eventi) e la domanda «cosa e' successo a questa pratica» arrivera'. Un ramo nuovo entra con un UNION ALL: la forma normalizzata non si rinegozia, e un registro che non sa riempire una colonna lascia NULL. ⭐ security_invoker: ogni ramo si protegge con la policy della propria tabella (event_log sulla colonna di perimetro; gli altri tre via lotto/fattura dal 2026-09-10), e il JOIN sulla testata resta come ancora all'entita' e seconda difesa — fino al 2026-09-19 questa frase diceva che i tre «una policy non ce l'hanno», ed era stantia dal 10-09. ⭐ rev 2026-09-19 (R-6, brief osservabilita P-2): nel ramo TASK_RUN `quando` e' started_at — la riga e' la corsa, e la corsa nasce li'. Prima era COALESCE(ended_at, started_at), e ended_at lo puo' scrivere la corsa SUCCESSIVA (fn_start_lotto_task_run chiude ANNULLATO il tentativo rimasto aperto): un task partito il 21 compariva col 22, e una riga di diario cambiava posto dopo essere nata. ended_at resta in tabella: se servira' al lettore sara' una colonna in piu' (fino_a), non l'orario della riga. ⛔ vendite.attivita_fatturabili_log resta FUORI, e non e' una dimenticanza: ne' lui ne' il suo padre hanno un filtro di perimetro, quindi quel ramo mostrerebbe righe di altri emittenti. Entra quando il padre avra' la sua policy — non prima, e non per simmetria. ⚠️ La vista NON filtra le segnalazioni ritirate — un diario dice cosa e' SUCCESSO, non cosa e' ancora aperto — ma dal 2026-08-24 le ESPONE, sulla colonna `disabilitato`. ⭐ Non filtrare e non dire sono due cose diverse: senza quel campo il consumatore non puo' ne' marcare ne' nascondere cio' che e' stato ritirato. ⛔ A filtrare e' il consumatore, che dira' anche quante righe ha nascosto. ⚠️ La colonna e' NULL su event_log (append-only: non c'e' niente da ritirare) e sui task_runs, dove il ritiro esiste ma su un ALTRO asse (`attivo` spegne il record, non il segnale). ⚠️ gravita e' l'unico posto dove i vocabolari C/W/I e i task_stato si mappano su INFO/WARN/ERROR: se esce NULL, un vincolo si e' allargato e la mappa e' rimasta indietro. Brief: brief-db-event-log-scope-e-riga-parlante.md §3.6; brief-db-osservabilita-lotto-fermo-r6-indici §3.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW script.vw_giornale_entita
WITH (security_invoker=true) AS
SELECT format('EVENT_LOG:%s'::text, e.id) AS riga_key,
    'EVENT_LOG'::text AS registro,
    e.id AS riga_id,
    e.event_time AS quando,
    e.entity_type,
    e.entity_id,
    e.severity AS gravita,
    e.event_code AS cosa,
    e.tx_id,
    e.correlation_id,
    e.auth_user_id,
    e.user_insert,
    NULL::boolean AS disabilitato
   FROM vendite.event_log e
UNION ALL
 SELECT format('LOTTO_LOG:%s'::text, ll.id) AS riga_key,
    'LOTTO_LOG'::text AS registro,
    ll.id AS riga_id,
    ll.data_ora AS quando,
    'LOTTO'::text AS entity_type,
    ll.lotto_id AS entity_id,
        CASE ll.status
            WHEN 'C'::bpchar THEN 'ERROR'::text
            WHEN 'W'::bpchar THEN 'WARN'::text
            WHEN 'I'::bpchar THEN 'INFO'::text
            ELSE NULL::text
        END AS gravita,
    ll.messaggio AS cosa,
    ll.tx_id,
    NULL::uuid AS correlation_id,
    NULL::bigint AS auth_user_id,
    ll.user_insert,
    ll.disabilitato
   FROM (vendite.fatturazione_lotti_log ll
     JOIN vendite.fatturazione_lotti l ON ((l.id = ll.lotto_id)))
UNION ALL
 SELECT format('TASK_RUN:%s'::text, tr.id) AS riga_key,
    'TASK_RUN'::text AS registro,
    tr.id AS riga_id,
    tr.started_at AS quando,
    'LOTTO'::text AS entity_type,
    tr.lotto_id AS entity_id,
        CASE tr.task_stato
            WHEN 'ERRORE'::text THEN 'ERROR'::text
            WHEN 'ANNULLATO'::text THEN 'WARN'::text
            WHEN 'COMPLETATO'::text THEN 'INFO'::text
            WHEN 'IN_ESECUZIONE'::text THEN 'INFO'::text
            ELSE NULL::text
        END AS gravita,
    concat_ws(' · '::text, tr.task_code, tr.task_stato, NULLIF(btrim((tr.error_code)::text), ''::text)) AS cosa,
    tr.tx_id,
    tr.correlation_id,
    NULL::bigint AS auth_user_id,
    tr.user_insert,
    NULL::boolean AS disabilitato
   FROM (vendite.fatturazione_lotti_task_runs tr
     JOIN vendite.fatturazione_lotti l ON ((l.id = tr.lotto_id)))
UNION ALL
 SELECT format('FATTURA_LOG:%s'::text, fl.id) AS riga_key,
    'FATTURA_LOG'::text AS registro,
    fl.id AS riga_id,
    fl.data_ora AS quando,
    'FATTURA'::text AS entity_type,
    fl.fattura_id AS entity_id,
        CASE fl.status
            WHEN 'C'::bpchar THEN 'ERROR'::text
            WHEN 'W'::bpchar THEN 'WARN'::text
            WHEN 'I'::bpchar THEN 'INFO'::text
            ELSE NULL::text
        END AS gravita,
    fl.messaggio AS cosa,
    fl.tx_id,
    NULL::uuid AS correlation_id,
    NULL::bigint AS auth_user_id,
    fl.user_insert,
    fl.disabilitato
   FROM (vendite.fatture_log fl
     JOIN vendite.fatture f ON ((f.id = fl.fattura_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
