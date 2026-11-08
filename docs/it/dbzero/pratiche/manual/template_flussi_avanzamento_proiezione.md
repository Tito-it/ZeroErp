## 📘 Documentazione Concettuale – Tabella `pratiche.template_flussi_avanzamento_proiezione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — il milestone che avanza, e il tipo di documento che attende
> * [pratiche.template_flussi_handler_eventi](/dbzero/pratiche/tabelle/template_flussi_handler_eventi) — gli handler su evento, mutuamente esclusivi con questo binding
> * [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche) — il vocabolario dei verdetti
>
> Approfondimento funzioni:
>
> * [pratiche.fn_reconcile_sorgente](/dbzero/pratiche/funzioni/fn_reconcile_sorgente) — il motore che legge questo binding
> * [pratiche.fn_stato_sorgente](/dbzero/pratiche/funzioni/fn_stato_sorgente) — il verdetto proiettato dal documento
> * [pratiche.trgfn_tfap_guard_compatibilita](/dbzero/pratiche/funzioni/trgfn_tfap_guard_compatibilita) — il guard di configurazione
> * [pratiche.fn_copia_definizione](/dbzero/pratiche/funzioni/fn_copia_definizione) — copia il binding con la definizione

---

### 🎯 Scopo Principale

`pratiche.template_flussi_avanzamento_proiezione` dichiara con quale verdetto un milestone avanza da
solo, quando il documento che attende ha proiettato un esito.

`template_flussi.attende_sorgente_tipo_id` dice quale tipo di documento il milestone attende; questa
tabella dice con quale verdetto si completa. Quando il documento proietta l'esito
(`pratiche.fn_stato_sorgente`), `pratiche.fn_reconcile_sorgente` porta il milestone a `COMPLETATO`
con quel verdetto. Senza una riga qui il milestone non avanza da solo.

---

### Il verdetto del documento è l'esito del milestone

* L'esito con cui il milestone si completa è il verdetto proiettato dal documento: i vocabolari
  coincidono, e non c'è nessuna traduzione.
* `esito_richiesto` vuoto vuol dire «qualsiasi verdetto»; valorizzato, è uno dei quattro verdetti
  (`POSITIVO`, `NEGATIVO`, `PARZIALE`, `NON_APPLICABILE`).
* Un binding non si ripete: la coppia (milestone, esito richiesto) è unica, e due righe «qualsiasi
  verdetto» sullo stesso milestone sono un duplicato.
* Contano solo i binding attivi, per il motore e per la mutua esclusione.
* Il binding segue il milestone: cancellato il template di flusso, se ne va anche lui; il milestone deve
  essere attivo.

---

### ⭐ Una tabella sua, non un handler

La semantica «avanza quando il documento proietta» è diversa da «handler lato server su un evento di
flusso», e ha una tabella dedicata invece di allargare il vocabolario degli eventi di
`pratiche.template_flussi_handler_eventi`.

Il guard di configurazione `pratiche.trgfn_tfap_guard_compatibilita` ammette il binding solo su uno
step non di tipo `DOMINIO`, e non lo lascia coesistere con un handler attivo sull'evento `COMPLETATO`
dello stesso step: due meccanismi che completano lo stesso milestone si contraddirebbero.

---

### Configurazione versionata

È configurazione di step versionata: `pratiche.fn_copia_definizione` la copia quando un'edizione della
definizione si deriva per fork o nuova versione.

---

### Note di migrazione

* 2026-07-06 — nasce come secondo tassello dell'avanzamento guidato dall'esito proiettato
  (brief-db-guida-avanza-esito-proiettato).

---

{% include-markdown "signature-core.md" %}
