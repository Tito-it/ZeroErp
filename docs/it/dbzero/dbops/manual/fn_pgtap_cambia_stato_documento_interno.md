## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_cambia_stato_documento_interno`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [magazzino.fn_cambia_stato_documento_interno](/dbzero/magazzino/funzioni/fn_cambia_stato_documento_interno) — il verbo che scrive lo stato
> * [dbops.fn_pgtap_apri_area_per_nascita](/dbzero/dbops/funzioni/fn_pgtap_apri_area_per_nascita) — il livello, per il tempo della chiamata
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP: porta un documento interno (inventario, rettifica, trasferimento) allo stato chiesto, dal verbo dello stato. Ritorna lo stato scritto.

---

### Un builder per le tre famiglie

Come il verbo, riceve la famiglia come primo argomento. La matrice la fanno rispettare i controlli della tabella: un passaggio non ammesso arriva al test col suo codice, e «registrato» non si chiede qui, lo scrive la registrazione.

---

### Test

Non ha un test suo: la presidiano i file che la usano.

---

### Note di migrazione

* 2026-11-23 — nasce quando i pgTAP dei documenti interni smettono di scrivere le tabelle a mano, in vista della chiusura delle tabelle all'applicazione (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
