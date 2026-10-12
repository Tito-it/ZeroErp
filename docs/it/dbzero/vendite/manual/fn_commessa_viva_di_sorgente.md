## 📘 Documentazione Concettuale – Funzione `vendite.fn_commessa_viva_di_sorgente`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [vendite.fn_link_commessa_sorgente](/dbzero/vendite/funzioni/fn_link_commessa_sorgente) — la porta che scrive il link e rifiuta la seconda commessa aperta  
> • [vendite.trgfn_guard_fatturazione_immediata_immutabile](/dbzero/vendite/funzioni/trgfn_guard_fatturazione_immediata_immutabile) — il flag di corsia, bloccato solo con una commessa aperta  
> • [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa) — lo stesso predicato decide se una commessa si riusa  
>
**Approfondimento tabelle:**
>
• [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)  

---

### 🎯 Scopo Principale
(2026-10-12, brief-db-annullo-a-valle-riapre-a-monte, D-12 e D-14)

Risponde a una domanda sola: **in quale commessa aperta sta questo documento?**
Restituisce l'id della commessa, o `NULL`.

**Aperta** vuol dire che lo stato della commessa non la chiude
(`vendite.stati_commessa.chiude_commessa = false`): è lo stesso predicato con cui
l'invio decide se riusare una commessa. Una commessa che l'invio non riusa non
trattiene il documento.

---

### Perché esiste

Fino al 2026-10-12 un documento stava in una commessa **per sempre**: un solo link,
qualunque fosse lo stato della commessa. Annullata la commessa, il documento
tornava «da mandare», ma il secondo invio veniva rifiutato.

Da quel giorno il link verso una commessa chiusa o annullata **resta come storia**,
e un documento può averne più d'uno. Questa funzione dice **quale conta**.

| Chi la legge | Per decidere |
| --- | --- |
| `vendite.fn_link_commessa_sorgente` | se un nuovo invio va rifiutato: solo se il documento sta in un'**altra** commessa aperta |
| `vendite.trgfn_guard_fatturazione_immediata_immutabile` | se il flag di corsia è ancora modificabile: no, finché c'è una commessa aperta |
| il backend | quale commessa agganciare alla pratica dopo l'invio (richiesta nel brief) |

---

### Note operative

* **La chiave è quella canonica** di `commesse_sorgenti`, secondo
  `config.sorgenti.key_selector`: `id::text` per ordini, contratti, bolle e
  consumi; l'uuid per preventivi e offerte. Chi ha l'uid di un documento a chiave
  `id` lo traduce prima, come fanno la porta e il guard.
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

{% include-markdown "signature-core.md" %}
