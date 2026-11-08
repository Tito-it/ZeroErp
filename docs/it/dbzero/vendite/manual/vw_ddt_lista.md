## 📘 Documentazione Concettuale – Vista `vendite.vw_ddt_lista`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) — la tabella base
> * [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt) — stato e fase
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — destinatario, mittente, vettore
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — l'emittente
> * [config.causali_trasporto](/dbzero/config/tabelle/causali_trasporto) · [config.aspetti_beni](/dbzero/config/tabelle/aspetti_beni) · [config.modalita_addebito_trasporto](/dbzero/config/tabelle/modalita_addebito_trasporto) — il trasporto
>
> Approfondimento viste:
>
> * [vendite.vw_ordini_lista](/dbzero/vendite/views/vw_ordini_lista) — la gemella degli ordini
>
> Approfondimento funzioni:
>
> * [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt) — le azioni della riga
> * [script.fn_sorgente_documento](/dbzero/script/funzioni/fn_sorgente_documento) — il BB che risolve un documento d'origine qualunque
> * [pratiche.fn_pratica_del_documento](/dbzero/pratiche/funzioni/fn_pratica_del_documento) — la pratica della bolla
> * [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) — frontiera e transito, per le righe della pagina
>
> Guide:
>
> * [Configurazione, personalizzazione e responsività delle liste](/guide/configurazione-liste)
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

La vista sorgente della lista configurabile delle bolle di vendita (`<ListaConfigurabile>`): pura **denormalizzazione** (join e campi di display), **nessun** filtro, scope o paginazione, che restano nel repository del backend.

---

### Che cosa espone

* identificazione (numero, anno, serie, data, registro), stato (`stato_codice_interno`,
  `stato_descrizione`) e la `fase`;
* **destinatario** (obbligatorio), **mittente** e **vettore** (facoltativi), cliente, utility,
  valuta;
* **`emittente_fiscale_id`** con codice e ragione sociale, per il perimetro;
* i campi del **trasporto** (causale, aspetto, modalità di addebito, colli, pesi, volume, targa,
  autista, date, tracciamento) per il PDF;
* la **provenienza** e la **pratica** (sotto).

`security_invoker = on`: la vista gira col contesto del chiamante, e le policy RLS di `vendite.ddt`
si applicano. Nomi canonici: `ragione_sociale_completa`, `id_fiscale_univoco_cf_piva`, `ba_codice`,
`stato_codice_interno`. `numero` è vuoto in bozza, valorizzato all'emissione.

---

### La provenienza: due popolazioni

Una bolla dichiara il documento da cui nasce con la provenienza del modello: la vista espone
`sorgente_tipo_id`, `sorgente_codice_interno`, `sorgente_id` e `sorgente_uid` così come stanno sulla
testata. Due popolazioni:

* la bolla **da ordine** dichiara `ORDINE_VENDITA`, a chiave `id`: l'id dell'ordine sta in
  `sorgente_id`, e la vista ne espone anche `ordine_origine_id` e `ordine_origine_numero`;
* la bolla **di riconsegna** dichiara `RESO_VENDITA`, il reso da cui nasce
  ([`fn_genera_ddt_riconsegna`](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna)), anche lui a
  chiave `id`. Lì la lista dice **da dove viene il documento** e lascia vuoto `ordine_origine_*`,
  perché un ordine non c'è.

⭐ **Il join all'ordine è qualificato sul tipo**: trova l'ordine solo se la bolla dichiara
`ORDINE_VENDITA`, con la regola d'incontro (id o uid). Senza la condizione sul tipo, l'id di un reso
potrebbe coincidere con l'id di un ordine qualsiasi e la lista nominerebbe un ordine che non c'entra.

⚠️ Per **risolvere** una provenienza qualunque in «id, uid e numero del documento» c'è il BB che
risolve, [`script.fn_sorgente_documento`](/dbzero/script/funzioni/fn_sorgente_documento), che sa
quale chiave usa il tipo e dove sta il numero. Questa vista **non** lo chiama — è una lista, e una
funzione per riga sarebbe N chiamate — ma chi avesse bisogno del numero di un documento d'origine
generico usi quello, non un secondo join scritto a mano.

---

### La pratica, e il grafo che non sta qui

`pratica_id`, `pratica_numero` e `n_pratiche` arrivano da
[`pratiche.fn_pratica_del_documento`](/dbzero/pratiche/funzioni/fn_pratica_del_documento), con il
tipo `DDT_VENDITA` e le due chiavi della bolla: restano filtrabili e ordinabili. Le colonne della
frontiera e del transito le chiede il backend a
[`fn_documento_lineage_sintesi`](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) per le sole
bolle della pagina.

---

### Il perimetro dell'emittente

`emittente_fiscale_id` alimenta il **filtro applicativo** del repository
(`script.fn_get_emittenti_scope_pk_ids`, difesa in profondità) e la policy RLS
`rls_ddt_ef_whitelist` su `vendite.ddt`.

La definizione della lista e le sue colonne sono in `ui.lista_definizione` / `ui.lista_colonna`
(`codice = vendite.ddt`).

---

### Note di migrazione

* 2026-08-28 — arriva la bolla di riconsegna, e il join all'ordine si qualifica sul tipo.
* 2026-10-11 — la vista non calcola più il grafo: frontiera e transito passano a
  `fn_documento_lineage_sintesi` (brief-db-lineage-seminata-per-chiave).
* 2026-11-06 — `sorgente_id` in coda, e l'ordine d'origine con la regola d'incontro: la provenienza
  delle bolle passa alla chiave del modello, e la riconsegna dichiara il reso in `sorgente_id`
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
