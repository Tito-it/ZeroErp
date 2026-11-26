## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_apri_area_per_nascita`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.user_override_aree](/dbzero/config/tabelle/user_override_aree) — l'override d'area che scrive o alza
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_richiudi_area](/dbzero/dbops/funzioni/fn_pgtap_richiudi_area) — la rimette com'era
> * [dbops.fn_pgtap_concedi_azione](/dbzero/dbops/funzioni/fn_pgtap_concedi_azione) — l'altra strada, che apre l'area per sempre
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP: dà all'operatore in sessione il livello «tutto» sull'area di un oggetto **per il tempo di una nascita** fatta da un builder sul verbo. Ritorna il ricordo di ciò che c'era, da passare a `dbops.fn_pgtap_richiudi_area`.

---

### ⭐ Un'apertura che dura una chiamata

L'operatore costruito per i test non ha livelli: è bloccato ovunque. Un builder che passa dal verbo ha bisogno del livello per un istante; poi il test deve ritrovare i permessi come li aveva lasciati, così un rifiuto per livello si prova prima o dopo la fixture senza che la fixture lo veda. Se il livello c'è già, non scrive niente.

---

### ⚠️ Un override sull'oggetto resta sotto il tetto

Se il test ha scritto un override sull'oggetto più basso di «tutto», aprire l'area non basta: la fixture lo dice e si ferma, invece di scavalcare il test.

---

### Test

Non ha un test suo: la usano tutti i builder sui verbi di magazzino.

---

### Note di migrazione

* 2026-11-22 — nasce quando le anagrafiche di magazzino si chiudono all'applicazione e i pgTAP passano dai verbi (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
