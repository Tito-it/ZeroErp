## 📘 Documentazione Concettuale – Funzione `config.trgfn_sorgenti_normalize()`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [config.sorgenti](/dbzero/config/tabelle/sorgenti)    
>
### 🎯 Scopo Principale
(latest review 29-03-2026)
La trigger function `config.trgfn_sorgenti_normalize()` normalizza il campo
`codice_interno` delle sorgenti applicative, portandolo in formato uniforme
prima del salvataggio.

---

### Quando si attiva

* trigger `BEFORE INSERT OR UPDATE` su `config.sorgenti`;
* opera sulla riga `NEW` prima della persistenza.

---

### Regole operative

* se `NEW.codice_interno` e` valorizzato, applica `btrim(...)` per rimuovere spazi esterni;
* converte il valore in **uppercase** con `upper(...)`;
* se il campo e` `NULL`, non forza alcun valore e lascia invariato il comportamento della tabella.

---

### Effetto pratico

* evita varianti come `ddt_vendita`, ` DDT_vendita ` o `ddt_vendita `;
* rende stabile il confronto dei codici interni in configurazioni, trigger e query;
* riduce errori dovuti a casing o spazi accidentali nei dati di setup.

---

{% include-markdown "signature-core.md" %}
