## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_pdp`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp) — la tabella di partenza
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — letta senza esporne niente
> * [config.utilities](/dbzero/config/tabelle/utilities) — la utility del punto
> * [config.stati_pdp](/dbzero/config/tabelle/stati_pdp) — lo stato tecnico
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio) — l'indirizzo già normalizzato

---

### 🎯 Scopo Principale

`anagrafiche.vw_pdp` mostra un punto di prelievo con la sua utility, il suo stato tecnico e il suo indirizzo
già normalizzato, senza ricomporre la catena dall'indirizzo al comune.

---

### L'indirizzo arriva intero da un posto solo

L'indirizzo non si ricostruisce qui: viene da `anagrafiche.vw_indirizzi_dettaglio`, compresi l'indirizzo
normalizzato, la via normalizzata e le due geolocalizzazioni, del civico e della via. I campi tecnici
dell'indirizzo hanno il prefisso `indirizzo_` (`indirizzo_attivo`, `indirizzo_tx_id`, …) perché non si
confondano con quelli del PDP.

Indirizzo, utility e stato sono legami obbligatori: un PDP senza uno dei tre non compare. In particolare un
PDP il cui indirizzo non si risolve nella vista degli indirizzi sparisce, in silenzio.

---

### Chi la vede

La vista è `security_invoker`: si legge con i diritti di chi interroga. `pdp` non ha la RLS; `clienti` sì, ma
il legame con i clienti è esterno e non porta nessuna colonna, e la RLS dei clienti non toglie righe alla
vista.

---

### ⚠️ Che cosa oggi non copre

* **Il «cliente corrente» non lo è.** La vista espone `cliente_id` dalla riga del PDP, una colonna che nessun
  oggetto del database scrive. Chi occupa il PDP in una data lo dicono i periodi dei clienti.
* **Il legame con i clienti non serve.** È esterno e non porta colonne: non toglie e non aggiunge niente.
* **Lo stato attivo del PDP non c'è.** La vista non espone `attivo`, né `meta`, né i campi tecnici del PDP: un
  PDP disattivato non si distingue da uno attivo.

---

{% include-markdown "signature-core.md" %}
