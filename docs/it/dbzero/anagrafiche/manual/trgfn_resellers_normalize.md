## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_resellers_normalize`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.resellers](/dbzero/anagrafiche/tabelle/resellers)
> [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)

---

### 🎯 Scopo Principale

(latest review 10-03-2026)
La trigger function **`anagrafiche.trgfn_resellers_normalize()`** e' oggi una
**no-op**: non modifica il record `NEW` e ritorna semplicemente il contenuto
ricevuto dal trigger.

La presenza del trigger mantiene esplicito il punto di estensione per eventuali
normalizzazioni future, mentre la generazione del codice reseller resta
demandata al sistema di codifica configurabile (`config.sistema_codici`).

---

### Regola applicata

* Trigger **BEFORE INSERT OR UPDATE** su `anagrafiche.resellers`.
* Nessuna trasformazione sui campi.
* `RETURN NEW` immediato.

---

### Ruolo nel processo

La funzione conserva un hook architetturale dedicato ai reseller senza
duplicare logica gia' gestita altrove. In particolare, non genera il campo
`codice`: questa responsabilita' resta nel framework generale di
`sistema_codici`.

---

{% include-markdown "signature-core.md" %}
