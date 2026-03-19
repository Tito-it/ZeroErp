## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_emittenti_fiscali_normalize`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
>
**Approfondimento funzioni:**
>
[config.sistema_codici](/dbzero/config/manual/sistema_codici)

---
### 🎯 Scopo Principale
(latest review 12-03-2026)
La trigger function **`anagrafiche.trgfn_emittenti_fiscali_normalize()`** e'
attualmente una **no-op controllata**: non modifica `NEW`, ma mantiene
esplicitato nel flusso trigger che la normalizzazione locale non e' necessaria e
che l'eventuale generazione del `codice` resta demandata al sistema automatico
basato su `config.sistema_codici`.

---

### Contesto di esecuzione

* Trigger **BEFORE INSERT OR UPDATE** su `anagrafiche.emittenti_fiscali`.
* La funzione riceve il record `NEW` e lo restituisce invariato.

---

### Effetto operativo

* Nessun campo viene riscritto.
* Non applica trim, uppercase o derive locali.
* Lascia invariata la responsabilita' della generazione codice al meccanismo
  centralizzato di sistema.

---

### Perche' esiste comunque

Anche se oggi non contiene logica trasformativa, il trigger conserva un punto
di estensione coerente per eventuali regole future sugli emittenti fiscali,
senza spostare responsabilita' applicative fuori dal database.

---

{% include-markdown "signature-core.md" %}
