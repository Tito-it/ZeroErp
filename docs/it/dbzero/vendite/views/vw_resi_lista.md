{% include-markdown "it/dbzero/vendite/manual/vw_resi_lista.md" %}
# 🔍 View `vw_resi_lista`

> 📝 **Descrizione**
>
> Lista/dettaglio resi vendita (mirror vw_ddt_lista). security_invoker=on + RLS su base; espone emittente_fiscale_id/_codice e emittente_ragione_sociale. ⭐ rev 2026-08-25 — LA SESTA SORELLA: fase + colonne di genealogia da vendite.vw_documento_lineage (pratica, frontiera, discendenti, is_transitato), nella stessa forma delle altre liste documento. `fase` non c'era: la vista aveva lo stato ma non la fase normalizzata, e il seed della colonna omonima la cerca con quel nome esatto — senza, la colonna sarebbe nata vuota e in silenzio. ⭐ SU UN RESO frontiera_codice E' IL NUMERO DELLA NOTA DI CREDITO: con l'arco S (20260825-19) il reso smette di essere una foglia e la sua frontiera diventa la nota che lo accredita. La colonna «Transito» risponde percio' a «questo reso e' gia' stato accreditato, e con quale documento» — che prima era una QUANTITA' (gia_accreditato) in un drawer, non un documento in lista. ⚠️ Il join al lineage e' LEFT come sulle sorelle: un reso senza genealogia compare senza genealogia, non sparisce. Consumo: ui.lista_definizione 'vendite.resi' (id 9) + preset resi_default; il frontend e' gia' &lt;ListaConfigurabile&gt;, quindi le colonne arrivano dal seed.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_resi_lista
WITH (security_invoker=on) AS
SELECT r.id,
    r.uid,
    r.numero,
    r.anno,
    r.data,
    r.stato_doc_reso_id,
    sr.codice_interno AS stato_codice_interno,
    sr.descrizione AS stato_descrizione,
    r.destinatario_soggetto_ruolo_id,
    s_dest.id AS destinatario_soggetto_id,
    s_dest.ragione_sociale_completa AS destinatario_denominazione,
    s_dest.id_fiscale_univoco_cf_piva,
    r.billing_account_id,
    ba.codice AS ba_codice,
    r.emittente_fiscale_id,
    ef.codice AS emittente_fiscale_codice,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
    r.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    r.valuta_id,
    v_val.codice AS valuta_codice,
    r.sorgente_tipo_id,
    src.codice_interno AS sorgente_codice_interno,
    r.sorgente_uid,
    d_src.id AS ddt_origine_id,
    d_src.numero AS ddt_origine_numero,
    r.data_insert,
    r.user_insert,
    r.data_update,
    r.user_update,
    sr.fase,
    lin.pratica_id,
    lin.pratica_numero,
    lin.n_pratiche,
    lin.frontiera_tipo_id,
    lin.frontiera_codice,
    lin.frontiera_stato_codice_interno,
    lin.frontiera_fase,
    lin.n_discendenti_attivi,
    lin.is_transitato
   FROM ((((((((((((vendite.resi r
     JOIN config.stati_doc_reso sr ON ((sr.id = r.stato_doc_reso_id)))
     JOIN anagrafiche.soggetti_ruoli sr_dest ON ((sr_dest.id = r.destinatario_soggetto_ruolo_id)))
     JOIN anagrafiche.soggetti s_dest ON ((s_dest.id = sr_dest.soggetto_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = r.billing_account_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.id = r.emittente_fiscale_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = ef.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)))
     LEFT JOIN config.utilities u ON ((u.id = r.utility_id)))
     LEFT JOIN config.valute v_val ON ((v_val.id = r.valuta_id)))
     LEFT JOIN config.sorgenti src ON ((src.id = r.sorgente_tipo_id)))
     LEFT JOIN vendite.ddt d_src ON ((d_src.uid = r.sorgente_uid)))
     LEFT JOIN vendite.vw_documento_lineage lin ON (((lin.tipo_id = ( SELECT s.id
           FROM config.sorgenti s
          WHERE (((s.codice_interno)::text = 'RESO_VENDITA'::text) AND (s.attivo IS TRUE)))) AND (lin.uid = (r.id)::text))));
```


---
{% include-markdown "signature-core.md" %}
