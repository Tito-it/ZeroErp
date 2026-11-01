## 📘 Documentazione Concettuale – Funzione `magazzino.fn_crea_magazzino`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — la tabella in cui scrive la riga

---

### 🎯 Scopo Principale

**Aprire un magazzino** di un'azienda: codice, descrizione, indirizzo e, se
servono, l'uso delle ubicazioni e il «predefinito».

È la sede unica della creazione: la usano il backend (l'anagrafica dei
magazzini), le fixture dei test e il provisioning dei dati di sviluppo.

---

### Regole

* Codice, descrizione e indirizzo sono obbligatori.
* Facoltativi: l'uso delle ubicazioni, il magazzino predefinito, le note
  strutturate (`meta`). Un campo diverso è rifiutato col suo nome
  (`E_CAMPO_NON_AMMESSO`).
* Un magazzino **nasce attivo**: non si sceglie alla nascita.
* **L'azienda**: se non la si indica, è quella su cui lavora l'operatore
  collegato. Se la si indica, deve essere una delle sue.

---

### Che cosa non controlla

Il permesso e il perimetro dell'operatore: li dicono il backend e il
controllo di perimetro della tabella. Anche l'unicità del codice e l'indirizzo
attivo li fanno rispettare i vincoli e i controlli della tabella.

⚠️ Senza un operatore collegato quel controllo ferma la scrittura: chi crea
magazzini senza un operatore (il provisioning dei dati di sviluppo) deve agire
per conto di un operatore dell'azienda.

---

### Codici errore

* `E_CAMPO_NON_AMMESSO` — fra i campi facoltativi ce n'è uno che la funzione
  non conosce; il codice nomina quel campo.
* `E_SCRIPT_CHIAMATA_NON_VALIDA` — i campi facoltativi non sono un oggetto:
  chi chiama è rotto.

---

### Test

`db/pgtap/magazzino/test-fn-crea-magazzino-v1.sql`.

---

### Note di migrazione

* 2026-10-18 — nasce con `brief-db-processi-accensione-per-ambiente` (2b-1,
  lotto 7). Prende il posto della creazione scritta nel repository del backend
  (`AnagraficheMagazzinoRepository.create_magazzino`), dell'inserimento fatto a
  mano in `dbops.fn_pgtap_crea_magazzino` e delle fixture dei pgTAP del
  magazzino.

---

{% include-markdown "signature-core.md" %}
