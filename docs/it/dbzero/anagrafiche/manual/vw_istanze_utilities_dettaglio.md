## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_istanze_utilities_dettaglio`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — la tabella di partenza
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il titolare
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp) — il PDP e la sua utility
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — dove stanno davvero le utility dell'istanza
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio) — l'indirizzo normalizzato
> * [script.vw_indirizzo_completo](/dbzero/script/views/vw_indirizzo_completo) — comune, provincia, CAP e strada
> * [anagrafiche.vw_istanze_dati_precontrattuali_dettaglio](/dbzero/anagrafiche/views/vw_istanze_dati_precontrattuali_dettaglio) — chi la compone

---

### 🎯 Scopo Principale

`anagrafiche.vw_istanze_utilities_dettaglio` mostra un'istanza con il suo titolare, il suo PDP con lo stato
tecnico e la utility, e il suo indirizzo con le decodifiche di comune e strada. Una riga per istanza.

---

### Che cosa porta

* **Il titolare**: ragione sociale e identificativo fiscale del soggetto; ogni istanza ha il suo.
* **Il PDP**, quando c'è: codice, stato tecnico, e la utility **del PDP**.
* **L'indirizzo**, quando c'è: i campi normalizzati e le geolocalizzazioni da `vw_indirizzi_dettaglio`;
  comune, provincia, CAP, toponimo e nome della strada da `script.vw_indirizzo_completo`.

Un'istanza senza PDP o senza indirizzo compare lo stesso, con quei campi vuoti.

---

### Chi la vede

La vista non è `security_invoker`, e si legge coi diritti del proprietario. Nessuna delle tabelle che legge
ha la RLS, e oggi la differenza non toglie né aggiunge righe. La compone
`vw_istanze_dati_precontrattuali_dettaglio`.

---

### ⚠️ Che cosa oggi non copre

* **La utility è quella del PDP.** `utility_id`, il codice e la descrizione vengono dal PDP dell'istanza, non
  dai suoi billing account: un'istanza senza PDP non ha utility nella vista, e un'istanza con più utility ne
  mostra una sola, quella del PDP.
* **Se una delle tabelle avesse la RLS**, la vista la scavalcherebbe senza errori.

---

{% include-markdown "signature-core.md" %}
