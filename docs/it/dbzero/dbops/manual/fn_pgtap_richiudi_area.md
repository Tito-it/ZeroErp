## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_richiudi_area`

> **Ultimo aggiornamento**: 27 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_apri_area_per_nascita](/dbzero/dbops/funzioni/fn_pgtap_apri_area_per_nascita) — che cosa ha aperto
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP: rimette l'override d'area com'era prima di `dbops.fn_pgtap_apri_area_per_nascita` — tolto se l'aveva scritto, coi valori di prima se l'aveva alzato. Un ricordo vuoto non rimette niente.

---

### Test

Non ha un test suo: la usano tutti i builder sui verbi di magazzino.

---

### Note di migrazione

* 2026-11-22 — nasce quando le anagrafiche di magazzino si chiudono all'applicazione e i pgTAP passano dai verbi (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).
* 2026-11-27 — la chiusura passa dal verbo del SUPER_ADMIN ([`dbops.fn_pgtap_scrivi_override`](/dbzero/dbops/funzioni/fn_pgtap_scrivi_override)), e il contesto dell'operatore torna com'era. Il ricordo cambia forma (l'utente, l'area, l'eccezione di prima); i builder lo passano senza aprirlo (brief-db-porte-aperte-dalla-sola-guc, giro 10-quater).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
