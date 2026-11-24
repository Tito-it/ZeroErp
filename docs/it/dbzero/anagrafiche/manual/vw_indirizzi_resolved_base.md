## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_indirizzi_resolved_base`

> **Ultimo aggiornamento**: 24 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — gli indirizzi dei ruoli, lo strato `RUOLO`
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — gli indirizzi dei soggetti, lo strato `SOGGETTO`
> * [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi) — il tipo, col codice da mostrare e quello interno
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio) — il civico risolto, per gli indirizzi col dettaglio
> * [anagrafiche.vw_indirizzi_resolved_ruolo](/dbzero/anagrafiche/views/vw_indirizzi_resolved_ruolo) — la proiezione del solo strato `RUOLO`
> * [anagrafiche.vw_indirizzi_resolved_soggetto](/dbzero/anagrafiche/views/vw_indirizzi_resolved_soggetto) — la proiezione del solo strato `SOGGETTO`
> * [anagrafiche.vw_indirizzi_resolved_all](/dbzero/anagrafiche/views/vw_indirizzi_resolved_all) — la proiezione dei due strati insieme
>
> Approfondimento funzioni:
>
> * [script.fn_get_indirizzi_by_ruolo](/dbzero/script/funzioni/fn_get_indirizzi_by_ruolo) — gli indirizzi di un ruolo, letti da qui
> * [script.fn_get_indirizzo](/dbzero/script/funzioni/fn_get_indirizzo) — il risolutore che sceglie l'indirizzo da usare
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — il quadro degli indirizzi, dei tipi e dei ripieghi

---

### 🎯 Scopo Principale

`anagrafiche.vw_indirizzi_resolved_base` è la lettura unica degli indirizzi scritti: una riga, e una sola, per
ogni indirizzo di un ruolo o di un soggetto, nelle due forme, con il testo da mostrare, il luogo risolto (comune,
provincia, regione, stato, CAP), il tipo e la posizione. Le tre viste `vw_indirizzi_resolved_*` ne sono
proiezioni.

---

### Due strati, distinti da `scope`

| `scope` | Da dove | Che cosa |
| --- | --- | --- |
| `RUOLO` | `anagrafiche.indirizzi` | l'indirizzo di un ruolo, generico o di un'istanza (`istanza_utility_id`) |
| `SOGGETTO` | `anagrafiche.indirizzi_soggetti` | l'indirizzo del soggetto; ruolo e istanza sono vuoti |

`indirizzo_id` è l'id nella tabella d'origine: lo stesso numero può comparire nei due strati, e una riga si
riconosce da `scope` più `indirizzo_id`. `source` ripete `scope`, per i lettori che la chiamano così.

⭐ La vista mostra ciò che è scritto, non sceglie: non applica la discesa istanza → ruolo → soggetto né i tipi di
ripiego. Quella è di `script.fn_get_indirizzo`, che legge da qui attraverso le funzioni di lista.

---

### Come risolve una riga

* **Col dettaglio**: testo, via, civico e dettaglio vengono dal civico (`anagrafiche.vw_indirizzi_dettaglio`),
  comune, provincia e regione dalla sua via, lo stato dalla regione.
* **Libera**: il testo è `indirizzo_libero`; comune e CAP sono quelli scritti sulla riga nella forma del
  catalogo, provincia e regione vengono dal comune; lo stato è quello della riga. La colonna `cap` è il CAP
  scelto nella riga, e la provincia quella del comune, letti dalle tabelle del catalogo: le vie del comune non
  entrano nella lettura di un indirizzo libero. Località, area
  amministrativa, frazione e codice postale escono come sono, per la forma estera.
* **Il testo da mostrare** (`indirizzo_display`) è l'indirizzo normalizzato del civico, oppure il testo libero:
  via e numero, non il luogo, che sta nelle sue colonne. Il terzo ripiego, che compone località e codice postale,
  non si raggiunge, perché un indirizzo libero ha sempre il testo.
* **La posizione** è il punto del civico, poi quello della via, poi quello scritto sulla riga: per un indirizzo
  col dettaglio la vista legge il civico di oggi, e la riga non ne tiene una sua; quella scritta sulla riga è la
  posizione di un indirizzo libero.
* **Il tipo** esce col codice da mostrare (`tipo_indirizzo_codice`, che l'utente può rinominare), la descrizione
  e il codice interno (`tipo_indirizzo_codice_interno`), che è la chiave da usare nei confronti e nella logica.

---

### ⛔ Le proiezioni hanno le stesse colonne

`vw_indirizzi_resolved_ruolo`, `vw_indirizzi_resolved_soggetto` e `vw_indirizzi_resolved_all` espongono le
colonne della base, con gli stessi nomi, nello stesso ordine e con gli stessi tipi: una colonna nuova qui si
aggiunge anche a loro, altrimenti chi passa da una vista all'altra trova un contratto diverso.

---

### Un civico e la sua via

Un civico la cui via non si risolvesse uscirebbe senza testo, comune e CAP, perché la vista del civico lo perde. Il
modello non lo produce: un civico non nasce su una via che non si risolve, e una via usata non perde la provincia
(vedi [vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio)).

---

### Test

* `db/pgtap/anagrafiche/test-vw-indirizzi-resolved-derivate-codice-interno-v1.sql` — le tre proiezioni con le
  colonne della base, il codice interno distinto da quello da mostrare, il codice da mostrare non troncato.
* `db/pgtap/anagrafiche/test-indirizzi-fallback.sql` — le funzioni di lista allineate alla base, i due strati
  che insieme fanno la vista di tutti.
* `db/pgtap/anagrafiche/test-indirizzi-istanza-cascata.sql` — l'istanza esposta sullo strato del ruolo.
* `db/pgtap/anagrafiche/test-indirizzi-viste-forma-e-vincoli-v1.sql` (7, 8, 16) — l'indirizzo libero della forma del
  catalogo esce una volta sola, col CAP scelto; la posizione del civico letta anche dopo che cambia.

---

### Note di migrazione

* 2026-10-18 — `postal_box` diventa `postal_code`.
* 2026-11-01 — il codice del tipo esce intero (prima era troncato a 10 caratteri), e si aggiunge il codice
  interno, in fondo, nella base e nelle tre proiezioni.
* 2026-11-24 — un indirizzo libero esce una volta sola, col CAP scelto: prima la vista univa le vie del suo comune,
  e l'indirizzo usciva una volta per via, col CAP di ciascuna.

---

{% include-markdown "signature-core.md" %}
