{% include-markdown "it/dbzero/vendite/manual/vw_dash_competenza_attivita.md" %}
# 🔍 View `vw_dash_competenza_attivita`

> 📝 **Descrizione**
>
> Lente 1 Competenza, grana ATTIVITA': una riga per attivita' di commessa con lo stadio del ciclo (DA_APPROVARE / DA_EMETTERE / EMESSA_NON_FATTURATA / FATTURATA), il valore, il collegamento a fattura e lotto e lo stato della commessa. Alimenta il drill-down commesse, che il backend AGGREGA per commessa. SCOPE EMITTENTE via fn_get_emittenti_scope_sr_ids(GUC): fail-closed. security_invoker=on. ⭐ Rev 2026-08-18 (R-4, brief perimetro-emittente Fase E): aggiunta in coda `emittente_ragione_sociale`. Il drill-down puo' metterla nel GROUP BY in sicurezza: l'emittente e' una colonna di vendite.commesse e commessa_id ne e' la chiave primaria, quindi una commessa non puo' avere attivita' di emittenti diversi — l'emittente non sta sull'attivita'. La colonna nel GROUP BY serve comunque: su una colonna di VISTA PostgreSQL non deduce la dipendenza funzionale. ⚠️ Due catene distinte sulle stesse tabelle: sr/s sono il CLIENTE (via billing account), sr_ef/s_ef l'EMITTENTE. Scambiarle non darebbe nessun errore, solo un nome sbagliato a video. ⭐ Rev 2026-08-26 (L4, brief-db-registro-e-data-prevista-in-competenza): quattro colonne nuove in coda — registro_id, registro_codice, politica_data_documento, data_documento_prevista. Rispondono alle due domande che la schermata da cui si fattura non sapeva dire PRIMA di premere: su quale sezionale finira' il documento, e che data portera'. ⭐ Il sezionale si risolve chiamando vendite.fn_resolve_registro_documento, cioe' LA STESSA funzione che usa fn_build_fattura_key quando la fattura nasce davvero: la previsione e' una lettura, non una profezia, e non puo' divergere dal documento perche' non e' una seconda implementazione. ⚠️ Le si passa co.billing_account_id, il BA della RIGA: la funzione risale al padre da se', e passarle il BA di fatturazione darebbe una previsione plausibile e sbagliata proprio sui BA con padre. ⛔ L'aggancio e' CONDIZIONATO — ON (af.fattura_riga_id IS NULL), decisione D-9: dove il documento esiste gia' la previsione non si fa, o la colonna mentirebbe al proprio nome. ⚠️ Il discriminante e' la riga di fattura e non lo stadio: su EMESSA_NON_FATTURATA il documento non c'e' ancora — e li' finiscono le attivita' rimaste orfane di una fattura eliminata, cioe' lavoro da ri-emettere, per cui sapere dove finira' e' proprio l'informazione utile. ⛔ Il CASE sulla data e' obbligatorio e non difensivo: fn_calcola_data_documento SOLLEVA su registro nullo, un CASE cortocircuita e un argomento no — senza, la prima riga con un sezionale non risolvibile farebbe morire l'intera lista. ⚠️ registro_codice viene da registri_fatturazione.codice, colonna MUTABILE: e' display, l'alias e' fedele alla sorgente (linee-guida-sql §6c) e quella tabella non espone codice_interno. Nessuna logica puo' appoggiarcisi — chi filtra lo fa su registro_id. ℹ️ Costo dichiarato: due chiamate di funzione per riga su una vista che ne alimenta altre quattro. Tutta la catena e' STABLE e le tabelle di configurazione lette non hanno RLS.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_competenza_attivita
WITH (security_invoker=on) AS
SELECT ca.competenza_mese,
    co.id AS commessa_id,
    (co.codice)::text AS commessa_codice,
    ca.id AS commessa_attivita_id,
    co.emittente_soggetto_ruolo_id,
    s.ragione_sociale_completa AS cliente_display,
    ca.articolo_id,
    ca.data_attivita,
    ca.quantita,
    ca.stato_approvazione,
    ca.stato_emissione,
    (
        CASE
            WHEN (((ca.stato_emissione)::text <> 'EMESSA'::text) AND ((ca.stato_approvazione)::text <> 'APPROVATA'::text)) THEN 'DA_APPROVARE'::text
            WHEN ((ca.stato_emissione)::text <> 'EMESSA'::text) THEN 'DA_EMETTERE'::text
            WHEN (af.fattura_riga_id IS NULL) THEN 'EMESSA_NON_FATTURATA'::text
            ELSE 'FATTURATA'::text
        END)::character varying AS stadio,
    (COALESCE(ca.prezzo_snapshot, (0)::numeric) * ca.quantita) AS valore,
    af.data_insert AS data_emissione,
        CASE
            WHEN (af.id IS NULL) THEN NULL::boolean
            ELSE ((date_trunc('month'::text, af.data_insert))::date > ca.competenza_mese)
        END AS emessa_in_ritardo,
    af.sospesa,
    af.posticipa_al,
    f.id AS fattura_id,
    af.fattura_riga_id,
    f.anno AS fattura_anno,
    f.serie AS fattura_serie,
    f.numero AS fattura_numero,
    sdf.codice_interno AS stato_fattura_codice_interno,
    sdf.codice AS stato_fattura_codice,
    (
        CASE
            WHEN (fr.id IS NULL) THEN NULL::numeric
            WHEN (COALESCE(fr.qta, (0)::numeric) = (0)::numeric) THEN (0)::numeric
            ELSE ((fr.imponibile_riga * af.quantita) / fr.qta)
        END)::numeric(18,6) AS valore_fatturato,
    COALESCE(f.critical, false) AS fattura_critical,
    lf.lotto_id,
    ca.sorgente_tipo_id,
    ca.sorgente_uid,
    ca.tipo_movimento,
    vendite.fn_build_gruppo_fatturabile_key(ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id) AS gruppo_key,
    sc.emittibile AS commessa_emittibile,
    sc.codice_interno AS commessa_stato_codice_interno,
    COALESCE(sc.descrizione, sc.codice) AS commessa_stato_descrizione,
    co.billing_account_id,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
    reg.registro_id,
    rf.codice AS registro_codice,
    reg.politica_data_documento,
        CASE
            WHEN (reg.registro_id IS NOT NULL) THEN vendite.fn_calcola_data_documento(p_registro_id => reg.registro_id, p_competenza_mese => ca.competenza_mese, p_serie => reg.serie, p_data_dichiarata => NULL::date)
            ELSE NULL::date
        END AS data_documento_prevista
   FROM (((((((((((((((vendite.commesse co
     JOIN vendite.stati_commessa sc ON ((sc.id = co.stato_commessa_id)))
     JOIN vendite.commesse_attivita ca ON ((ca.commessa_id = co.id)))
     LEFT JOIN vendite.attivita_fatturabili af ON ((af.commessa_attivita_id = ca.id)))
     LEFT JOIN vendite.fatture_righe fr ON ((fr.id = af.fattura_riga_id)))
     LEFT JOIN vendite.fatture f ON ((f.id = fr.fattura_id)))
     LEFT JOIN config.stati_doc_fiscale sdf ON ((sdf.id = f.stato_doc_fiscale_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = co.billing_account_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = ba.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = co.emittente_soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)))
     LEFT JOIN LATERAL ( SELECT flf.lotto_id
           FROM vendite.fatturazione_lotti_fatture flf
          WHERE (flf.fattura_id = f.id)
          ORDER BY flf.lotto_id DESC
         LIMIT 1) lf ON (true))
     LEFT JOIN LATERAL vendite.fn_resolve_registro_documento(p_billing_account_id_riga => co.billing_account_id, p_tipo_doc_fiscale_id => ca.tipo_doc_fiscale_id, p_natura_doc_id => ca.natura_doc_id) reg(ba_fatturazione_id, utility_id, emittente_soggetto_ruolo_id, registro_id, serie, politica_data_documento) ON ((af.fattura_riga_id IS NULL)))
     LEFT JOIN vendite.registri_fatturazione rf ON ((rf.id = reg.registro_id)))
     CROSS JOIN LATERAL ( SELECT script.fn_get_emittenti_scope_sr_ids((NULLIF(current_setting('app.current_user_id'::text, true), ''::text))::integer) AS sr_ids) escope)
  WHERE (((escope.sr_ids IS NULL) OR (co.emittente_soggetto_ruolo_id = ANY (escope.sr_ids))) AND ((sc.codice_interno)::text <> 'ANNULLATA'::text) AND ((ca.stato_emissione)::text <> 'ANNULLATA'::text) AND (((ca.stato_approvazione)::text <> 'RIFIUTATA'::text) OR ((ca.stato_emissione)::text = 'EMESSA'::text)));
```


---
{% include-markdown "signature-core.md" %}
