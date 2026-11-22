## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — i titoli su cui è montata
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_titolo_iva_ambito](/dbzero/anagrafiche/funzioni/fn_check_titolo_iva_ambito) — la regola, che chiama
> * [anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_ambiti_guard) — il gemello sulle righe di ambito

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito` applica le regole dell'ambito quando a cambiare è il titolo e
non le sue righe. Chiama `anagrafiche.fn_check_titolo_iva_ambito`, la stessa del gemello sulle righe, e solleva il
primo motivo.

---

### 🔴 Il lato che si dimentica

Due titoli ristretti diventano un pareggio anche senza che nessuno tocchi le righe di ambito:

* si allarga `valido_al` o si anticipa `valido_dal`;
* si riattiva un titolo spento;
* si cambia il tipo, il titolare o l'emittente;
* si passa un titolo da ristretto a totale con le righe ancora presenti.

In nessuno di questi casi la tabella delle righe viene scritta, e il guard che sta lì non scatta. Le colonne che lo
svegliano sono quelle della chiave del pareggio, più le date e lo stato.

Scatta dopo la modifica, perché la funzione legge il titolo com'è diventato. Alla nascita non serve: un titolo
appena scritto non ha righe di ambito, e la sovrapposizione fra titoli totali la chiude il vincolo di esclusione.

---

### ⚠️ Che cosa oggi non copre

* **Il rifiuto punta sempre su `valido_al`.** Qualunque colonna abbia creato il pareggio (il tipo, l'emittente,
  la riattivazione), il campo indicato a chi scrive è la data di fine.

---

### Codici errore

* `E_TITOLO_IVA_AMBITO_SOVRAPPOSTO` — il titolo cambiato fa pareggio con un altro.
* `E_TITOLO_IVA_AMBITO_NON_AMMESSO` — il titolo diventa totale con righe di ambito. Sul cambio di ambito però parla
  prima `anagrafiche.trgfn_soggetti_titoli_iva_guard_coerenza`, che lo stesso caso lo rifiuta prima della scrittura.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-titoli-iva.sql` — il periodo del padre allargato che fa scattare il guard.

---

{% include-markdown "signature-core.md" %}
