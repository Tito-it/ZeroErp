## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_istanze_dati_precontrattuali_dettaglio`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali) — la tabella di partenza, con la sua RLS
> * [config.classi_utenze](/dbzero/config/tabelle/classi_utenze) — la classe d'utenza
> * [config.tipi_utenze](/dbzero/config/tabelle/tipi_utenze) — il tipo d'utenza, letto dalla classe
>
> Approfondimento viste:
>
> * [anagrafiche.vw_istanze_utilities_dettaglio](/dbzero/anagrafiche/views/vw_istanze_utilities_dettaglio) — l'istanza, il titolare, il PDP e l'indirizzo

---

### 🎯 Scopo Principale

`anagrafiche.vw_istanze_dati_precontrattuali_dettaglio` mostra i dati precontrattuali di una coppia
(istanza, utility) con la decodifica della classe e del tipo d'utenza e con il dettaglio dell'istanza.

---

### Che cosa porta

* **I dati della riga**: la classe d'utenza con codice e descrizione, i due parametri, `meta`, e la utility
  della riga in `istanza_dati_utility_id`.
* **Il tipo d'utenza**, che non sta sulla riga: si legge dalla classe.
* **L'istanza**, per intero da `vw_istanze_utilities_dettaglio`: titolare, PDP, indirizzo. I campi tecnici
  dell'istanza hanno il prefisso `istanza_` (`istanza_tx_id`, `istanza_data_insert`, …).

---

### Chi la vede

La vista è `security_invoker`: la RLS dei dati precontrattuali vale anche qui, e un operatore vede solo le
righe delle coppie il cui billing account è di un'azienda del suo perimetro.

---

### ⚠️ Che cosa oggi non copre

* **Due utility con nomi che ingannano.** La utility della riga è `istanza_dati_utility_id`; `utility_id`,
  `utility_codice` e `utility_descrizione` sono quelle del PDP dell'istanza. Su un'istanza con più utility
  tutte le righe mostrano la stessa utility, quella del PDP; su un'istanza senza PDP non ne mostrano
  nessuna.

---

### Test

* `db/pgtap/rls/test-rls-istanze-dati-precontrattuali-v1.sql` — la vista è `security_invoker` e non scavalca
  la regola della tabella.

---

{% include-markdown "signature-core.md" %}
