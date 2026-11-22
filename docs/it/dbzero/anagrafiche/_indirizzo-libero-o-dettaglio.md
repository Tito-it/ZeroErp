### 🏠 Le due forme di un indirizzo

> **Ultimo aggiornamento**: 22 novembre 2026

Un indirizzo di un ruolo (`anagrafiche.indirizzi`) o di un soggetto (`anagrafiche.indirizzi_soggetti`) ha una
di due forme, mai tutte e due insieme (`chk_indirizzi_xor_norm_libero`, `chk_indirizzi_soggetti_xor_norm_libero`):

* **col dettaglio**: la riga punta a un civico di `anagrafiche.indirizzi_dettaglio`, cioè a una via dello
  stradario con numero, estensione, palazzina, scala, piano e interno. Comune, CAP, provincia e posizione li
  dice la via. È la forma da preferire: il civico è una riga sola per ogni indirizzo fisico, e una correzione
  del civico vale per tutti quelli che lo usano;
* **libera**: la via e il numero sono un testo (`indirizzo_libero`), accompagnato dallo stato e dai dati del
  luogo. Serve per gli indirizzi esteri e per quelli che lo stradario non conosce.

#### L'indirizzo libero: la forma la decide lo stato

Il testo e lo stato ci sono sempre. Se chi scrive non dice lo stato, il database scrive lo **stato proposto**
(`script.fn_stato_proposto_id`, dal parametro `STATO_PROPOSTO_ISO2`), e si ferma se il parametro manca o non
indica uno stato solo: non ripiega su un valore scritto nel codice. Poi conta lo stato, con la sua proprietà
`config.stati.catalogo_comuni_completo`:

| Forma | Quando | Che cosa serve | Che cosa resta vuoto |
| --- | --- | --- | --- |
| **del catalogo** | lo stato ha il catalogo dei comuni completo (l'Italia) | `comune_id` e `codice_postale_id`, il comune dello stato e il CAP del comune | `locality`, `postal_code`, `administrative_area`: li dice già il catalogo. La frazione (`sublocality`) è ammessa |
| **estera** | lo stato non ha il catalogo completo | `locality` | `comune_id` e `codice_postale_id`. Facoltativi `postal_code` (ci sono paesi senza codice postale), `administrative_area`, `sublocality` |

Uno stato col catalogo non ancora completo accetta anche la forma del catalogo, quando chi scrive sceglie un
comune o un CAP: allora vale tutta, coerenza compresa.

#### Che cosa fa il database alla riga, prima di salvarla

I trigger della riga girano nell'ordine del loro nome, e quello del giudizio è in fascia `z10` apposta, per
vedere i valori come si salveranno:

1. `anagrafiche.trgfn_indirizzi_base_normalize` mette in ordine la riga: con il dettaglio svuota tutti i campi
   della forma libera e la posizione; nella forma libera porta a `NULL` i testi vuoti e scrive lo stato
   proposto se manca;
2. `anagrafiche.trgfn_indirizzi_sync_geoloc` copia nella riga la posizione del civico, se c'è il dettaglio;
3. `anagrafiche.trgfn_indirizzi_guard_forma_libera` giudica la forma libera e, se qualcosa manca o non torna,
   rifiuta col codice e col nome del campo.

I `CHECK` `chk_indirizzi_free_requirements` e `chk_indirizzi_soggetti_free_requirements` restano come rete,
con la forma minima comune alle due varianti. Le due tabelle hanno le stesse colonne e montano le stesse tre
funzioni.

Il civico ha una sua normalizzazione (maiuscolo, vuoto uguale a nessun valore, estensione col `/`, `SNC` per il
civico senza numero), che vive in `anagrafiche.fn_build_indirizzo_normalizzato`; chi deve collegare un
civico lo ottiene da `anagrafiche.fn_get_or_create_indirizzo_dettaglio`, che lo trova o lo crea.
