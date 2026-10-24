## 📘 Documentazione Concettuale – Funzione `magazzino.fn_crea_magazzino()`

> 👀 **Vedi anche**
>
> [magazzino.magazzini](/dbzero/magazzino/manual/magazzini)

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1 lotto 7)

**Aprire un magazzino** di un'azienda: codice, descrizione, indirizzo e, se
servono, l'uso delle ubicazioni e il «predefinito».

È la sede unica della creazione: la usano il backend (l'anagrafica dei
magazzini), le fixture dei test e il provisioning dei dati di sviluppo.

### Regole

* Codice, descrizione e indirizzo sono obbligatori.
* Facoltativi: l'uso delle ubicazioni, il magazzino predefinito, le note
  strutturate (`meta`). Un campo diverso è rifiutato col suo nome
  (`E_CAMPO_NON_AMMESSO`).
* Un magazzino **nasce attivo**: non si sceglie alla nascita.
* **L'azienda**: se non la si indica, è quella su cui lavora l'operatore
  collegato. Se la si indica, deve essere una delle sue.

### Che cosa non controlla

Il permesso e il perimetro dell'operatore: li dicono il backend e il
controllo di perimetro della tabella. ⚠️ Senza un operatore collegato quel
controllo ferma la scrittura: chi crea magazzini senza un operatore (il
provisioning dei dati di sviluppo) deve agire per conto di un operatore
dell'azienda.

### Test

`db/pgtap/magazzino/test-fn-crea-magazzino-v1.sql`.

---

{% include-markdown "signature-core.md" %}
