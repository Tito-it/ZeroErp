## 📘 Documentazione Concettuale – Funzione `vendite.fn_commessa_viva_di_sorgente`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti) — i link documento → commessa
>
> Approfondimento funzioni:
>
> * [vendite.fn_link_commessa_sorgente](/dbzero/vendite/funzioni/fn_link_commessa_sorgente) — la porta che scrive il link e rifiuta la seconda commessa aperta
> * [vendite.trgfn_guard_fatturazione_immediata_immutabile](/dbzero/vendite/funzioni/trgfn_guard_fatturazione_immediata_immutabile) — il flag di corsia, bloccato solo con una commessa aperta
> * [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa) — lo stesso predicato decide se una commessa si riusa
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

Risponde a una domanda sola: **in quale commessa aperta sta questo documento?**
Restituisce l'id della commessa, o `NULL`.

**Aperta** vuol dire che lo stato della commessa non la chiude
(`vendite.stati_commessa.chiude_commessa = false`): è lo stesso predicato con cui
l'invio decide se riusare una commessa. Una commessa che l'invio non riusa non
trattiene il documento.

---

### Perché esiste

Il link verso una commessa chiusa o annullata **resta come storia**, e un documento può
averne più d'uno: annullata la commessa, il documento torna «da mandare» e il secondo invio
crea un link nuovo. Questa funzione dice **quale conta**.

| Chi la legge | Per decidere |
| --- | --- |
| `vendite.fn_link_commessa_sorgente` | se un nuovo invio va rifiutato: solo se il documento sta in un'**altra** commessa aperta |
| `vendite.trgfn_guard_fatturazione_immediata_immutabile` | se il flag di corsia è ancora modificabile: no, finché c'è una commessa aperta |
| il backend | quale commessa agganciare alla pratica dopo l'invio |

---

### Note operative

* **Il documento si passa con le colonne del modello**: il tipo, `sorgente_id` e
  `sorgente_uid`. La ricerca segue la regola d'incontro: il link si trova se combacia una
  delle due chiavi. Chi ha il documento passa il suo id **e** il suo uid, senza leggere il
  `key_selector` (nel link la colonna che il tipo non usa è vuota); chi ha la chiave del
  modello passa quella e lascia vuota l'altra.
* **Sotto RLS non perde niente.** Le policy di `commesse` e `commesse_sorgenti`
  filtrano per emittente, e una commessa ha sempre l'emittente del documento
  (`vendite.trgfn_commesse_sorgenti_guard_emittente`): chi vede il documento vede
  tutte le sue commesse.
* **Al più una.** La porta garantisce una sola commessa aperta per documento;
  l'ordinamento rende comunque la risposta deterministica.
* ⚠️ **CHIUSA e ANNULLATA sono terminali** nella matrice degli stati: una commessa
  chiusa non torna aperta, quindi un link di storia non diventa mai un secondo
  link aperto. Se un giorno la matrice ammettesse di uscire da uno stato che
  chiude, la riapertura andrebbe controllata.

---

### Note di migrazione

* 2026-10-12 — nasce la funzione: fino ad allora un documento stava in una commessa per sempre,
  e dopo l'annullo della commessa il secondo invio veniva rifiutato
  (brief-db-annullo-a-valle-riapre-a-monte, D-12 e D-14).
* 2026-11-07 — il documento si passa con le colonne tipizzate del modello (tipo, `sorgente_id`,
  `sorgente_uid` uuid) al posto della chiave testuale canonica (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
