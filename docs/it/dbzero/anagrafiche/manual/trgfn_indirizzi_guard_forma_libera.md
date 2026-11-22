## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_indirizzi_guard_forma_libera`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — gli indirizzi dei ruoli, su cui è montata
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — gli indirizzi dei soggetti, su cui è montata
> * [config.stati](/dbzero/config/tabelle/stati) — il flag `catalogo_comuni_completo`, che decide la forma
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_indirizzi_base_normalize](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_base_normalize) — gira prima, e mette in ordine la riga
> * [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_soggetto) — il verbo del soggetto, che passa i campi senza giudicarli
> * [anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_ruolo) — il verbo del ruolo, che fa lo stesso
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — il quadro degli indirizzi e delle due forme

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_indirizzi_guard_forma_libera` dice che cosa manca, o che cosa non torna, in un indirizzo
scritto a mano, con un codice e il nome del campo da correggere, invece dell'errore tecnico del `CHECK`. Un corpo
solo per gli indirizzi dei ruoli e dei soggetti, che hanno le stesse colonne.

---

### I rifiuti, nell'ordine

Il guard prende il primo problema che trova, nell'ordine della tabella. Il nome della colonna viaggia nel
contesto `campo`, così l'applicazione accende quel campo; la frase lo dice come lo legge una persona.

| Codice | Quando |
| --- | --- |
| `E_INDIRIZZO_LIBERO_INCOMPLETO` | manca un campo: prima la via, poi lo stato, poi quelli della forma (comune e CAP nella forma del catalogo, la località in quella estera) |
| `E_INDIRIZZO_CAMPO_ALTRA_FORMA` | nella forma del catalogo è compilato un campo della forma estera (località, codice postale, area amministrativa) |
| `E_INDIRIZZO_COMUNE_ALTRO_STATO` | il comune non è dello stato. Anche quando il catalogo non sa dirlo (un comune senza provincia, una provincia senza regione): non si può affermare che lo sia |
| `E_INDIRIZZO_CAP_ALTRO_COMUNE` | il CAP non è del comune |

---

### Quando giudica, e quando no

* In fascia `z10`, dopo la messa in ordine della riga, che porta a nessun valore i testi vuoti e scrive lo stato
  proposto: un guard prima di lei vedrebbe la riga com'era, e rifiuterebbe ciò che il `CHECK` accetta.
* Un indirizzo col dettaglio non si giudica qui.
* Una modifica che non tocca nessun campo dell'indirizzo non si giudica. ⭐ Per questo le righe scritte prima della
  regola, o prima che il flag di uno stato si accenda, restano valide finché nessuno tocca il loro indirizzo;
  quando lo si tocca, vale la forma di oggi.

---

### La regola sta in un posto solo

I verbi che creano gli indirizzi non ripetono la completezza: passano i campi, e il giudizio è qui. Il form
legge lo stesso flag dello stato per scegliere quale forma mostrare. I `CHECK` `chk_indirizzi_free_requirements`
e `chk_indirizzi_soggetti_free_requirements` restano come rete per le scritture che non passano dai trigger.

---

### Codici errore

* `E_INDIRIZZO_LIBERO_INCOMPLETO`, `E_INDIRIZZO_CAMPO_ALTRA_FORMA`, `E_INDIRIZZO_COMUNE_ALTRO_STATO`,
  `E_INDIRIZZO_CAP_ALTRO_COMUNE`: quando, nella tabella dei rifiuti.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzo-libero-due-forme-v1.sql` — l'ordine dei trigger, le due forme, i quattro
  rifiuti, il campo nel contesto, le righe di prima che restano valide finché non si toccano.

---

### Note di migrazione

* 2026-10-18 — nasce su richiesta dell'applicazione: prima l'indirizzo incompleto arrivava come errore tecnico
  del `CHECK`, senza dire il campo. Con lui nascono le due forme decise dallo stato.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzo-libero-o-dettaglio.md" %}

---

{% include-markdown "signature-core.md" %}
