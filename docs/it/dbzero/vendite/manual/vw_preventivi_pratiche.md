## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi_pratiche`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.preventivi](/dbzero/vendite/tabelle/preventivi) — il preventivo
> * [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti) — il collegamento documento → pratica
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il tipo `PREVENTIVO`
> * [config.stati_pratiche](/dbzero/config/tabelle/stati_pratiche) — lo stato della pratica
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

Le **pratiche collegate a ciascun preventivo di vendita**: una riga per ogni collegamento in `pratiche.pratiche_sorgenti` che dichiara come documento un preventivo, con i dati della pratica, il suo stato e il tipo di prestazione.

---

### Come aggancia il preventivo

Il collegamento dichiara il documento con la provenienza del modello. Il tipo `PREVENTIVO` è a
chiave `uid`: il collegamento porta l'uid del preventivo in `sorgente_uid` (uuid), e la vista lo
confronta con l'uid del preventivo, sul tipo risolto da `config.sorgenti` per `codice_interno`
(attivo). Un collegamento può nominare anche una **riga** del preventivo (`sorgente_riga`).

Stato della pratica e tipo di prestazione sono in `LEFT JOIN`: una pratica senza l'uno o l'altro
compare con le colonne vuote.

---

### Che cosa espone

* **Preventivo**: id, uid, numero.
* **Collegamento**: `pratica_sorgente_id` (l'id della riga di `pratiche_sorgenti`), `ruolo_link`,
  `sorgente_riga`, `sorgente_meta`.
* **Pratica**: id, codice, descrizione, date di apertura e scadenza.
* **Stato**: `stato_codice`, `stato_descrizione`.
* **Tipo di prestazione**: codice e descrizione.

`security_invoker = on`: la vista applica le policy di chi la interroga.

---

### Note di migrazione

* 2026-04-03 — nasce per la sezione pratiche del preventivo.
* 2026-11-08 — il collegamento si legge sulle colonne tipizzate di `pratiche_sorgenti`; l'id della
  riga di collegamento si chiama `pratica_sorgente_id` (era `sorgente_id`, che nel modello è la
  chiave del documento) (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
