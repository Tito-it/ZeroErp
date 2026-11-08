## 📘 Documentazione Concettuale – Funzione `dbops.fn_dati_di_sviluppo_ammessi_su_valori`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.installazione](/dbzero/dbops/tabelle/installazione) — l'ambiente che i chiamanti passano
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_etichette_di_prova_guard](/dbzero/dbops/funzioni/trgfn_etichette_di_prova_guard) — il guard delle etichette di prova, che la legge
> * [anagrafiche.fn_provisiona_dati_di_sviluppo](/dbzero/anagrafiche/funzioni/fn_provisiona_dati_di_sviluppo) — il verbo dei dati di sviluppo, che la legge
> * [script.fn_ambiente_installazione](/dbzero/script/funzioni/fn_ambiente_installazione) — il lettore dell'ambiente, che dice quando manca

---

### 🎯 Scopo Principale

La regola dei dati di sviluppo, pura sul valore: le etichette di prova e il provisioning dei dati di
sviluppo sono ammessi solo se l'ambiente è `SVILUPPO`. Riceve l'ambiente e risponde sì o no.

---

### ⭐ Una regola sola, sui valori

La regola è scritta una volta e la leggono due chiamanti: il guard delle etichette di prova e il
verbo che crea i dati di sviluppo. Tutti e due passano l'ambiente vero dell'installazione.

È pura sul valore perché l'ambiente di un'installazione non cambia e la CI è sempre `SVILUPPO`: un
test che volesse provare il ramo `PRODUZIONE` leggendo l'ambiente dovrebbe riscrivere
l'installazione. Così basta passare il valore.

⚠️ **Ambiente vuoto, risposta vuota.** Con l'ambiente non dichiarato la funzione non risponde né sì
né no, e non solleva: dirlo tocca al lettore dell'ambiente, che fallisce con `E_CONFIG_MANCANTE`.

---

### Test

* `db/pgtap/dbops/test-etichette-di-prova-v1.sql` — la regola sui tre valori (sviluppo, produzione,
  vuoto), poi il guard e il verbo che la leggono.

---

### Note di migrazione

* 2026-10-18 — nasce con le etichette di prova (`brief-db-processi-accensione-per-ambiente`, R-4).

---

{% include-markdown "signature-core.md" %}
