## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_istanze_dati_precontrattuali_protect_update`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali) — la tabella protetta
> * [vendite.contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities) — il contratto che nomina la riga
> * [vendite.offerte_commerciali_utilities](/dbzero/vendite/tabelle/offerte_commerciali_utilities) — l'offerta che nomina la riga, e che il blocco non guarda

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_istanze_dati_precontrattuali_protect_update` impedisce di modificare o cancellare i dati
precontrattuali di una fornitura quando un contratto utility li ha già letti.

---

### Dopo il contratto il dato è definitivo

Scatta prima di ogni modifica e di ogni cancellazione di una riga. Se una riga di
`vendite.contratti_utilities` nomina la riga, il rifiuto è `E_COLONNA_NON_MODIFICABILE`: il contratto resta
coerente con i dati su cui è nato, e una correzione passa da un contratto nuovo. Se nessun contratto la
nomina, la scrittura passa.

Il blocco viene prima dello storico: una scrittura rifiutata non lascia una versione nello storico.

---

### ⚠️ Che cosa oggi non copre

* **L'offerta non protegge.** Una riga che solo un'offerta commerciale nomina si modifica: la cancellazione
  la ferma la chiave esterna dell'offerta, la modifica no.
* **La cancellazione risponde da colonna.** Il codice è quello di una colonna non modificabile anche per una
  cancellazione, e il contesto non porta il campo da evidenziare nel form: nella frase c'è la parola
  «record».
* **Nessuna porta di manutenzione.** A differenza dei blocchi di colonna, non c'è un modo controllato di
  correggere una riga già letta da un contratto.

---

### Codici errore

* `E_COLONNA_NON_MODIFICABILE` — modifica o cancellazione di una riga che un contratto utility nomina.

---

### Test

* `db/pgtap/vendite/test-contratti-utilities-snapshot.sql` — la modifica della riga rifiutata dopo la
  nascita del contratto.

---

{% include-markdown "signature-core.md" %}
