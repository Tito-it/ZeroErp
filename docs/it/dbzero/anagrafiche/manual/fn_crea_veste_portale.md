## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_veste_portale()`

> 👀 **Vedi anche**
>
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/manual/identita_digitali)

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1 lotto 6)

**Dare a una credenziale una veste esterna** su un ruolo: l'accesso al
portale clienti, al portale fornitori o allo shop. La veste può nascere
**spenta** (l'invito al portale: la accende chi accetta l'invito) o
**accesa** (lo shop, per chi è già entrato nel portale).

È la sede unica della creazione: la usano il backend (invito al portale,
attivazione dello shop), i test e il provisioning dei dati di sviluppo.

### Regole

* **Solo le tre vesti esterne.** La veste di un operatore nasce dalla
  creazione dell'operatore, che porta anche il perimetro e la risorsa umana.
  Un'altra veste è rifiutata (`E_SCRIPT_CHIAMATA_NON_VALIDA`).
* **Accesa o spenta si dice sempre**: non c'è un default, perché quello della
  tabella (accesa) sarebbe sbagliato per un invito.
* Che la veste sia coerente col ruolo (il portale clienti su un cliente),
  che sia unica e che la credenziale sia di una persona lo dicono i controlli
  della tabella.

### Che cosa non controlla

Il permesso e il flusso dell'invito (il messaggio, il token, il reinvio):
li gestisce il backend.

### Test

`db/pgtap/anagrafiche/test-fn-crea-veste-portale-v1.sql`.

---

{% include-markdown "signature-core.md" %}
