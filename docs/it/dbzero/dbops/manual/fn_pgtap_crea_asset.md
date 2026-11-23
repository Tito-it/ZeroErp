## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_asset`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.assets](/dbzero/magazzino/tabelle/assets) — la riga che la fixture fa nascere
>
> Approfondimento funzioni:
>
> * [magazzino.fn_aggiungi_asset](/dbzero/magazzino/funzioni/fn_aggiungi_asset) — il verbo che scrive la riga
> * [dbops.fn_pgtap_apri_area_per_nascita](/dbzero/dbops/funzioni/fn_pgtap_apri_area_per_nascita) — il livello, per il tempo della chiamata
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP: **un seriale dell'articolo dato, dell'azienda dell'operatore**, dal verbo dell'operatore.

---

### ⭐ Passa dal verbo, non dalla tabella

La fixture chiama il verbo, cioè la strada dell'applicazione: quando la tabella è chiusa all'applicazione, il test continua a funzionare. L'area la apre per il tempo della chiamata e la rimette com'era.

Senza stato e proprietà, prende il primo attivo dei due cataloghi.

---

### Test

Non ha un test suo: la presidiano i file che la usano.

---

### Note di migrazione

* 2026-11-22 — nasce quando le anagrafiche di magazzino si chiudono all'applicazione e i pgTAP passano dai verbi (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
