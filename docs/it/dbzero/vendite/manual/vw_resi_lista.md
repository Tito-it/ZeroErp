## 📘 Documentazione Concettuale – Vista `vendite.vw_resi_lista`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.resi](/dbzero/vendite/tabelle/resi) — la tabella base
>
> Approfondimento viste:
>
> * [vendite.vw_ddt_lista](/dbzero/vendite/views/vw_ddt_lista) — la gemella delle bolle
>
> Approfondimento funzioni:
>
> * [script.fn_available_actions_reso](/dbzero/script/funzioni/fn_available_actions_reso) — le azioni della riga
> * [pratiche.fn_pratica_del_documento](/dbzero/pratiche/funzioni/fn_pratica_del_documento) — la pratica del reso
> * [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) — frontiera e transito, per le righe della pagina
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

La vista **lista e dettaglio** dei resi per backend e frontend, gemella di `vw_ddt_lista`: la testata del reso con i join di display — stato (`stato_codice_interno`, `stato_descrizione`) e `fase`, destinatario, cliente, emittente, utility, valuta, registro — la **bolla d'origine** (`ddt_origine_*`) e la **pratica**.

---

### Regole

* **`security_invoker = on`** — la RLS del chiamante (`rls_resi_ef_whitelist`) filtra sulla base. La
  reloption va **ri-specificata** in ogni `CREATE OR REPLACE VIEW` (PostgreSQL la azzera).
* Espone `emittente_fiscale_id` (con il codice) per il **filtro applicativo** del backend, e
  `emittente_ragione_sociale`, la ragione sociale del soggetto emittente.
* **Alias fedeli** alla sorgente: `codice_interno AS stato_codice_interno` (logica),
  `descrizione AS stato_descrizione` (display).
* `fase` viene da `config.stati_doc_reso`: la colonna della lista la cerca con quel nome esatto, e
  senza la vista la lascerebbe vuota in silenzio.
* Niente colonne di trasporto, logistica o importi: è un'asimmetria voluta rispetto alla bolla.

---

### La bolla d'origine

Il reso nasce sempre da una bolla, e la dichiara con la provenienza del modello: la vista espone
`sorgente_tipo_id`, `sorgente_codice_interno`, `sorgente_id` e `sorgente_uid` così come stanno sulla
testata. La bolla, tipo `DDT_VENDITA` a chiave `id`, sta in `sorgente_id`, e `sorgente_uid` resta
vuota; la vista ne espone `ddt_origine_id` e `ddt_origine_numero` con un join **qualificato sul
tipo** e per `sorgente_id`. Un reso con un altro tipo non si scrive (lo rifiuta
[vendite.trgfn_resi_guard_cliente_ddt](/dbzero/vendite/funzioni/trgfn_resi_guard_cliente_ddt)); il
join qualificato fa sì che `ddt_origine_*` nomini solo una bolla.

Il reso aggancia la **bolla**, non l'ordine: l'ordine si raggiunge dalla bolla.

---

### La pratica, e il grafo che non sta qui

`pratica_id`, `pratica_numero` e `n_pratiche` arrivano da
[`pratiche.fn_pratica_del_documento`](/dbzero/pratiche/funzioni/fn_pratica_del_documento), con il
tipo `RESO_VENDITA` e le due chiavi del reso: restano filtrabili e ordinabili, e un reso senza
pratica compare con le colonne vuote.

Le colonne del grafo (frontiera, discendenti, transito) le chiede il backend a
[`fn_documento_lineage_sintesi`](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) per i soli
resi della pagina. ⭐ Su un reso la **frontiera** è la nota di credito che lo accredita: la colonna
«Transito» risponde a *«questo reso è già stato accreditato, e con quale documento»*. La natura della
frontiera serve sempre, perché fattura e nota di credito stanno nella stessa tabella e si
distinguono solo per la natura.

---

### Consumo

`ui.lista_definizione 'vendite.resi'` con il preset `resi_default`; il frontend è
`<ListaConfigurabile>`, quindi le colonne arrivano dal seed. Gli slot della pratica, della fase e del
transito vanno scritti nel componente, come sulle liste gemelle: senza, il building block rende il
valore grezzo.

---

### Note di migrazione

* 2026-07-13 — nasce col reso di vendita (brief-db-resi-vendita).
* 2026-08-03 — l'etichetta dell'emittente si chiama `emittente_ragione_sociale` (era
  `emittente_fiscale_descrizione`), in pari su viste, seed delle liste, backend e frontend.
* 2026-08-25 — arrivano le colonne della genealogia e la `fase`.
* 2026-10-11 — la vista non calcola più il grafo: frontiera e transito passano a
  `fn_documento_lineage_sintesi` (brief-db-lineage-seminata-per-chiave).
* 2026-11-06 — `sorgente_id` in coda, e la bolla d'origine con la regola d'incontro sul tipo
  `DDT_VENDITA` (brief-db-sorgente-documento-e-riga).
* 2026-11-08 — la pratica si legge con le due chiavi del reso, sulle colonne tipizzate di
  `pratiche_sorgenti`.
* 2026-11-08 — la bolla d'origine si cerca per `sorgente_id` soltanto: la provenienza del reso è
  solo la bolla (brief-db-sorgente-documento-e-riga, G-3).

---

{% include-markdown "signature-core.md" %}
