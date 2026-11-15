## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_offerte_commerciali_guard_transizione()`

> **Ultimo aggiornamento**: 13 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> * [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte) — il vocabolario, da cui il guard legge il significato degli stati
> * [config.stati_doc_offerte_transizioni](/dbzero/config/tabelle/stati_doc_offerte_transizioni) — la matrice dei passaggi
>
> Approfondimento funzioni:
>
> * [script.fn_available_actions_offerta](/dbzero/script/funzioni/fn_available_actions_offerta) — spegne i pulsanti con gli stessi motivi, nello stesso ordine
> * [script.fn_check_listino_congelabile](/dbzero/script/funzioni/fn_check_listino_congelabile) · [script.fn_check_prezzi_autorizzati](/dbzero/script/funzioni/fn_check_prezzi_autorizzati) · [script.fn_check_indirizzi_documento_cliente](/dbzero/script/funzioni/fn_check_indirizzi_documento_cliente) · [script.fn_check_righe_documento](/dbzero/script/funzioni/fn_check_righe_documento) · [script.fn_check_offerta_annullabile](/dbzero/script/funzioni/fn_check_offerta_annullabile) — i predicati
> * [vendite.fn_cambia_stato_offerta](/dbzero/vendite/funzioni/fn_cambia_stato_offerta) — il verbo del cambio di stato, che passa da qui
>
> Guide:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §4 — il significato di uno stato lo dice il vocabolario

---

### 🎯 Scopo Principale

Il guard del cambio di stato dell'offerta commerciale. Giudica ogni passaggio e scrive la data del
passaggio. ⭐ **Non riconosce mai uno stato dal suo codice**: ogni regola chiede a una colonna del
vocabolario che cosa significa lo stato di partenza o di arrivo (`iniziale`, `emissione`,
`accettazione`, `rifiuto`, `is_abortito`, `is_superato`). I codici servono solo ai messaggi.
Spostata una marca nel vocabolario, il guard la segue.

---

### Aggancio

Trigger `trg_offerte_commerciali_a10_guard_transizione_upd` — fase `_a10_`,
`BEFORE UPDATE OF stato_doc_offerta_id` su `vendite.offerte_commerciali`, `FOR EACH ROW`. Nessun
altro trigger `BEFORE` scrive lo stato, quindi `UPDATE OF` è la forma giusta.

---

### Regole, nell'ordine

Se lo stato non cambia, non fa niente.

1. **Il passaggio è nella matrice.** La coppia di stati deve essere una riga attiva di
   `config.stati_doc_offerte_transizioni`, altrimenti `E_OFFERTA_TRANSIZIONE_NON_AMMESSA`.
2. **Il rientro dal superamento.** Da uno stato `is_superato` si esce solo se non resta una
   revisione figlia viva (`E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA`). Il passaggio di rientro esiste
   per l'automatismo «annullo la revisione, il padre torna vivo», ma un passaggio ammesso vale per
   chiunque scriva: la condizione sta qui.
3. **L'emissione** è il passaggio dallo stato `iniziale` allo stato di `emissione`. Solleva, nell'ordine:
   * il primo motivo di `script.fn_check_listino_congelabile`, poi **congela** la versione di
     listino (`vendite.fn_listino_versione_operativa`: la fissata, altrimenti quella in vigore oggi);
   * il primo motivo di `script.fn_check_indirizzi_documento_cliente`;
   * il primo motivo di `script.fn_check_righe_documento`.

   ⚠️ Anche il rientro dal superamento arriva nello stato di emissione, ma non parte dallo stato
   iniziale: non è un invio al cliente, e queste regole non lo toccano.
4. **I prezzi.** Verso lo stato di `emissione` e verso quello di `accettazione`, fuori dal rientro,
   il primo motivo di `script.fn_check_prezzi_autorizzati` (`E_DOC_PREZZO_PENDENTE`,
   `E_DOC_PREZZO_RIFIUTATO`). Un prezzo rimasto non autorizzato sul padre bloccherebbe
   l'annullamento della revisione, cioè una via d'uscita.
5. **L'annullo.** Verso lo stato `is_abortito`, il primo motivo di
   `script.fn_check_offerta_annullabile` (`E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI`): un contratto o un
   ordine ancora vivo nato dall'offerta si annulla prima.
6. **La data del passaggio**, dalla colonna della destinazione:

   | La destinazione è | Si scrive |
   | --- | --- |
   | `emissione` | `data_emissione`, solo se è ancora vuota |
   | `accettazione` | `data_accettazione` |
   | `rifiuto` | `data_rifiuto` |
   | `is_abortito` | `data_annullamento` |

   ⚠️ `data_emissione` non si riscrive: il rientro dal superamento è un secondo ingresso nello stato
   di emissione, e riscriverla cancellerebbe il giorno in cui l'offerta è stata davvero mandata al
   cliente. Le altre date registrano l'ultimo passaggio.

I predicati delle regole 3-5 sono gli stessi che
[`script.fn_available_actions_offerta`](/dbzero/script/funzioni/fn_available_actions_offerta) legge
per spegnere i pulsanti, nello stesso ordine: pulsante e guard non possono dissentire.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_OFFERTA_TRANSIZIONE_NON_AMMESSA` | il passaggio non è una riga attiva della matrice |
| `E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA` | uscita dal superamento con una revisione figlia viva |
| quelli di `script.fn_check_listino_congelabile` | emissione senza una versione di listino in vigore, o con una fissata non attiva |
| `E_INDIRIZZO_DOC_NON_DEL_CLIENTE` | emissione con un indirizzo che non è del cliente dell'offerta |
| `E_DOC_RIGA_NON_AMMESSA` | emissione con una riga che la regola intera non ammette più |
| `E_DOC_PREZZO_PENDENTE`, `E_DOC_PREZZO_RIFIUTATO` | verso emissione o accettazione con un prezzo non autorizzato |
| `E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI` | annullo con un contratto o un ordine vivo nato dall'offerta |

---

### Test

* `db/pgtap/vendite/test-offerta-guard-dal-vocabolario-v1.sql` — le date dal significato, e la marca
  spostata in transazione: con l'accettazione su `RIFIUTATA`, lo stesso passaggio scrive
  `data_accettazione`; il presidio sulla forma (nessun codice di stato nel corpo).
* `db/pgtap/vendite/offerte_commerciali/test_offerte_commerciali_state_machine.sql` — la matrice.
* `db/pgtap/vendite/offerte_commerciali/test-offerte-rientro-padre-revisione-annullata.sql` — il rientro.

---

{% include-markdown "signature-core.md" %}
