## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_indirizzi_operatore`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_soggetto) — scrive ogni indirizzo e ne giudica la forma
> * [anagrafiche.fn_crea_operatore_v2](/dbzero/anagrafiche/funzioni/fn_crea_operatore_v2) — la chiama coi dettagli già risolti
> * [anagrafiche.fn_crea_primo_amministratore](/dbzero/anagrafiche/funzioni/fn_crea_primo_amministratore) — la chiama con gli indirizzi scritti dal comando
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — le forme di un indirizzo e i tipi obbligatori
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — l'operatore e i suoi indirizzi

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_indirizzi_operatore` scrive i due indirizzi di un operatore: la **residenza** e il **domicilio
fiscale**, che se non è dato è la residenza. È il posto unico di questa regola: la usano la creazione di un operatore
e quella del primo amministratore.

---

### Come si passano gli indirizzi

Ogni indirizzo è un oggetto nella forma di `anagrafiche.fn_crea_indirizzo_soggetto`: un indirizzo libero, un
dettaglio già risolto o una via da risolvere. **Senza il tipo**: il tipo lo dice il parametro (residenza o domicilio
fiscale). Un oggetto che porta già un tipo, o che non è un oggetto, è una chiamata non valida
(`E_SCRIPT_CHIAMATA_NON_VALIDA`): un tipo scritto due volte, in due modi, non si sceglie.

Senza residenza la funzione non scrive niente, anche se il domicilio fiscale c'è. Se gli indirizzi sono
obbligatori per quel soggetto lo dicono i guard del soggetto alla chiusura della transazione.

La forma di ogni indirizzo, e se il tipo è ammesso per quel soggetto, li giudica `fn_crea_indirizzo_soggetto`. La
funzione gira coi privilegi di chi la chiama.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_SCRIPT_CHIAMATA_NON_VALIDA` | un indirizzo porta il tipo, o non è un oggetto |

Più quelli di `fn_crea_indirizzo_soggetto`.

---

### Test

* `db/pgtap/anagrafiche/test-crea-primo-amministratore-v1.sql` — il domicilio fiscale che manca è la residenza; un
  indirizzo che porta il tipo si rifiuta.
* Coi dettagli già risolti la provano i pgTAP di `fn_crea_operatore_v2` che passano gli indirizzi.

---

### Note di migrazione

* 2026-11-25 — nasce, estratta da `fn_crea_operatore_v2` quando la stessa regola è servita al primo amministratore.

---

{% include-markdown "signature-core.md" %}
