## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_trasferimento`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti) — la riga che la fixture fa nascere
>
> Approfondimento funzioni:
>
> * [magazzino.fn_aggiungi_trasferimento](/dbzero/magazzino/funzioni/fn_aggiungi_trasferimento) — il verbo che scrive la riga
> * [dbops.fn_pgtap_apri_area_per_nascita](/dbzero/dbops/funzioni/fn_pgtap_apri_area_per_nascita) — il livello, per il tempo della chiamata
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP: **un trasferimento in bozza fra i due magazzini dati**, dal verbo dell'operatore.

---

### ⭐ Passa dal verbo, non dalla tabella

La fixture chiama il verbo, cioè la strada dell'applicazione: quando la tabella è chiusa all'applicazione, il test continua a funzionare. L'area la apre per il tempo della chiamata e la rimette com'era.

Partenza e arrivo possono coincidere, per un trasferimento fra ubicazioni.

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
