## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_billing_account_guard_normalize`

> 👀 **Vedi anche**
>
Approfondimenti tabelle: 
>
[anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
>
Approfondimenti funzioni:
>
[config.sistema_codici](/dbzero/config/manual/sistema_codici)

---
### 🎯 Scopo Principale
(latest review 28-12-25)
Il trigger `anagrafiche.trgfn_billing_account_guard_normalize` applica le **validazioni di business** e normalizza i campi, mentre la generazione del `codice` e' demandata al sistema automatico basato su `config.sistema_codici`.

---

### Contesto di Esecuzione

* **Tipo**: `BEFORE INSERT OR UPDATE` trigger sulla tabella `anagrafiche.billing_account`
* **Oggetto**: opera sul record `NEW`

---


### Logica Operativa

1. **Genitore diverso da se stesso** — un billing account non puo' essere
   genitore di se stesso.

2. **Data di inizio obbligatoria** — se c'e' un genitore, la validita' deve
   partire da una data.

3. **Coerenza del soggetto fiscale fra genitore e figlio** *(rivisto 18-08-26)*

   E' il controllo che impedisce di appendere un billing account sotto quello di
   **un'altra persona o azienda**. Procede in tre gradini:

   * **il genitore non si raggiunge** → si rifiuta. Puo' voler dire che non
     esiste, oppure che **esiste ma e' fuori dal perimetro di chi sta
     scrivendo**: la lettura passa dalle regole di visibilita' per emittente, e
     il controllo non finge di distinguere due cose che non puo' distinguere.
     ⚠️ Prima di questa revisione il caso cadeva sull'errore *«identificativi
     fiscali diversi»* — su due codici fiscali **identici**. Un messaggio che
     nominava la causa sbagliata;
   * **manca il codice fiscale da una delle due parti** → il confronto fiscale
     non e' utilizzabile come prova, quindi si confronta il **soggetto**, che
     c'e' sempre. Due billing account della **stessa** persona senza codice
     fiscale restano legittimi; due di persone **diverse** vengono rifiutati.
     ⚠️ Prima passavano entrambi: `NULL` confrontato con `NULL` non risulta
     diverso, ed era il classico buco del dato mancante in una chiave;
   * **entrambi i codici fiscali presenti** → si confrontano. Due soggetti
     diversi con lo **stesso** codice fiscale continuano a passare, ed e'
     voluto: quella e' identita' fiscale, che e' cio' che il controllo presidia.

4. **Coerenza delle date di validita'** — la fine non puo' precedere l'inizio.

5. **Distacco dal genitore** — non si puo' togliere il genitore a un billing
   account che ha ancora attivita' da fatturare: spezzerebbe la catena che porta
   al documento.

6. **Restituzione record** — il record viene ritornato al motore, che prosegue
   l'operazione.

> ℹ️ La normalizzazione del `codice` e' rimasta un posto riservato: la
> generazione vera e' demandata al sistema automatico dei codici.

---

### Impatto e Vantaggi

* **Consistenza**: garantisce che nessun record venga creato senza un codice di fatturazione.
* **Automazione**: la generazione del codice e' gestita dal trigger automatico su `config.sistema_codici`.
* **Estendibilita**: la configurazione e' centralizzata in `config.sistema_codici` per tutte le tabelle.
* **Nessun dato mancante che apre una porta** *(18-08-26)*: dove il codice
  fiscale non c'e', il controllo ripiega sul soggetto invece di lasciar passare.
  E dove il genitore non si vede, lo dice — invece di attribuire il rifiuto a
  una causa che non c'entra.

> ℹ️ **Questo controllo non guarda l'emittente.** Che un albero non attraversi
> due emittenti fiscali e' presidiato a parte, da
> [`fn_guard_albero_ba_emittente`](/dbzero/anagrafiche/manual/fn_guard_albero_ba_emittente):
> sono due domande diverse — *«e' la stessa persona?»* e *«e' lo stesso
> emittente?»* — e tenerle separate e' voluto.

---

### ⚠️ Note Operative

* Assicurarsi che in `config.sistema_codici` sia presente la riga per `codice_interno = 'billing_account'` con `usa_sequenza = TRUE`.
* La generazione del codice avviene nel trigger automatico sulla tabella target.

---

{% include-markdown "signature-core.md" %}
