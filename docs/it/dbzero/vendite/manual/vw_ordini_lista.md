## 📘 Documentazione Concettuale – Vista `vendite.vw_ordini_lista`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ordini](/dbzero/vendite/tabelle/ordini) — la tabella base, con la provenienza in `sorgente_*`
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento d'origine
> * [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini) — lo stato e la modalità PDF
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il cliente e l'agente
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — ragione sociale e identificativo fiscale
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il codice del billing account
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — l'emittente, asse dello scope
> * [config.utilities](/dbzero/config/tabelle/utilities) — la utility
> * [config.modalita_pagamento](/dbzero/config/tabelle/modalita_pagamento) — la modalità di pagamento
> * [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento) — il termine di pagamento
> * [config.valute](/dbzero/config/tabelle/valute) — la valuta
>
> Approfondimento funzioni:
>
> * [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) — le colonne del grafo, chieste dal backend per la sola pagina
>
> Guide:
>
> * [Configurazione, personalizzazione e responsività delle liste](/guide/configurazione-liste) — il sistema delle liste configurabili
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

`vendite.vw_ordini_lista` è la vista canonica che alimenta la lista ordini di vendita configurabile e il dettaglio dell'ordine: la testata con le decodifiche denormalizzate e la provenienza leggibile.

È pura **denormalizzazione**: nessuno scope, filtro o paginazione (restano nel repository
backend che la consuma). È gemella di `vw_contratti_lista`, `vw_preventivi_lista` e
`vw_offerte_commerciali_lista`.

È `security_invoker = on`: la vista gira col contesto del chiamante, così le **policy RLS**
della tabella base `vendite.ordini` (operatore, portale, shop) si applicano attraverso la vista.

---

### Che cosa ha di proprio l'ordine

* **Niente revisioni**: gli ordini non hanno storico di revisioni, quindi nessuna colonna
  `rev`, `is_attiva` o `has_next_revisione`.
* **Niente listino in testata**: l'ordine fissa i prezzi sulle righe alla conferma e non
  eredita una versione di listino.
* **Cliente dal `soggetto_ruolo` diretto**: `soggetto_ruolo_id` è obbligatorio e porta al
  soggetto senza passare dall'istanza utility; il cliente si risolve anche per i **prospect**
  senza billing account (`ba_codice` resta vuoto).
* **Assi propri dell'ordine**: `fatturazione_trigger` (quando scatta il passaggio a commessa)
  e `canale_origine` (ADMIN, PORTALE, SHOP).
* **`numero` sempre valorizzato**: lo genera il trigger di numerazione all'inserimento, anche
  in bozza, quindi è esposto senza fallback.

---

### La provenienza: da `sorgente_*`, in forma leggibile

La provenienza dell'ordine sta nelle colonne del modello (`sorgente_tipo_id`, `sorgente_id`
oppure `sorgente_uid`), che la vista espone in coda così come sono. Accanto, per la lista,
ne dà una forma leggibile **calcolata**:

* **`documento_origine_tipo`** — il codice del tipo di documento in `config.sorgenti`
  (`PREVENTIVO`, `OFFERTA_COMMERCIALE`, …);
* **`documento_origine_id`** — l'id del documento d'origine, anche per preventivo e offerta,
  che nel modello si riconoscono per uid;
* **`documento_origine_codice`** — il suo numero leggibile: il numero del preventivo o il
  codice dell'offerta; vuoto per gli altri tipi.

Il documento si cerca con la regola d'incontro del modello (l'id o l'uid del documento,
secondo la chiave che la provenienza porta), solo nella tabella del tipo dichiarato: al più
un documento risponde. Le tre colonne sono vuote per l'**ordine nato da solo**, cioè non
generato da un documento a monte.

Un preventivo può generare più ordini; un'offerta ne genera al più uno vivo (la regola sta
sulla tabella `vendite.ordini`).

---

### Nomi canonici

Ogni `campo_sorgente` del catalogo della lista combacia con una colonna della vista (lo
valida il trigger anti-refuso del catalogo colonne):

| Significato | Colonna vista |
| --- | --- |
| Ragione sociale del cliente | **`ragione_sociale_completa`** |
| Identificativo fiscale (CF/P.IVA) | **`id_fiscale_univoco_cf_piva`** |
| Codice billing account | **`ba_codice`** |
| Codice interno stato (severità del Tag nel frontend) | **`stato_codice_interno`** |

---

### Colonne calcolate, non salvate

* **`data_consegna_richiesta_cliente_min`** — la prima data di consegna che il cliente ha
  chiesto sulle righe **attive** dell'ordine. La data vive sulla riga (una riga può essere
  pronta e un'altra no) e la testata la espone come minimo delle righe: una colonna in
  `vendite.ordini` sarebbe una seconda verità. Vuota = nessuna riga attiva la dichiara. Il
  suffisso `_cliente` dice di chi è la data: non marcato = nostro, marcato = della controparte.
* **`pratica_id`, `pratica_numero`, `n_pratiche`** — la pratica del documento, filtrabile e
  ordinabile, letta da `pratiche.fn_pratica_del_documento`.
* **`registro_codice`, `registro_descrizione`** — il registro di fatturazione, come nelle
  liste sorelle che hanno un registro.

⛔ **La vista non calcola il grafo.** Le colonne della frontiera e del transito
(`frontiera_*`, `n_discendenti_attivi`, `is_transitato`) le chiede il backend a
`vendite.fn_documento_lineage_sintesi` per i soli documenti della pagina: calcolarle qui
vorrebbe dire leggere la lineage di tutti gli ordini a ogni pagina.

---

### Il catalogo della lista

Le colonne visibili di default nel preset degli ordini sono `numero`, `data`, cliente
(`ragione_sociale_completa`), `ba_codice`, `id_fiscale`, `utility_codice`, `totale_doc`,
`fatturazione_trigger`, `stato`, `azioni`. La colonna tecnica nascosta `stato_codice_interno`
alimenta il Tag di severità. Il resto (descrizione utility, canale d'origine, imponibile e IVA,
pagamento, valuta, emittente, anno, serie, provenienza, agente, data di inserimento, consegna
richiesta) è **extra opt-in** in «Personalizza colonne».

L'attributo **`priorita`** governa il ritiro dinamico responsive: resistono `numero`, cliente,
`stato` e `totale_doc`; si ritirano per primi `ba_codice` e `fatturazione_trigger`; `numero` e
`azioni` non si ritirano mai.

⚠️ Le colonne nuove della vista vanno **in coda**: la vista si ridefinisce solo appendendo.

---

### Note di migrazione

* 2026-06-03 — aggiunte `agente_denominazione` e la provenienza leggibile
  (`documento_origine_tipo`, `documento_origine_codice`).
* 2026-09-13 — aggiunta `data_consegna_richiesta_cliente_min`
  (brief-db-modifiche-certe-ciclo-vendita-e-articolo, §5.2).
* 2026-10-11 — tolte dalla vista le colonne del grafo, passate a
  `vendite.fn_documento_lineage_sintesi` per le sole righe della pagina.
* 2026-11-06 — ritirate da `vendite.ordini` le colonne `documento_origine_tipo` e
  `documento_origine_id` (vocabolario chiuso `PREVENTIVO` / `OFFERTA`): la provenienza
  dell'ordine sta in `sorgente_*`, e la vista ne calcola gli alias `documento_origine_*`,
  col tipo nel codice di `config.sorgenti` (`OFFERTA_COMMERCIALE`, non più `OFFERTA`).
  Le colonne `sorgente_tipo_id`, `sorgente_id`, `sorgente_uid` sono esposte in coda
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
