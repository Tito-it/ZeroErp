> **Ultimo aggiornamento**: 23 novembre 2026

### 🚪 I verbi di scrittura di magazzino — il modello comune

Un **verbo** è la funzione del database che fa un gesto dell'operatore: nuovo magazzino,
modifica di un'ubicazione, conferma di un inventario. È la sola strada con cui l'applicazione
scrive le anagrafiche e i documenti interni di magazzino, e ogni verbo fa gli stessi passi,
nello stesso ordine:

1. **il permesso**: la prima cosa è il livello dell'operatore sull'oggetto, che deve essere
   «tutto». Sotto quel livello, o senza un operatore collegato, il verbo rifiuta con
   `E_PERMESSO_NEGATO`;
2. **il perimetro**: la riga su cui si lavora (o il magazzino in cui qualcosa nasce) deve
   essere dell'azienda dell'operatore. Fuori perimetro e inesistente rispondono con lo stesso
   codice «non trovato», senza dire quale dei due: chi chiede non scopre che cosa esiste in
   un'altra azienda;
3. **i campi**: il verbo accetta solo le colonne della sua lista, letta da una funzione che è
   la sede unica della lista, la stessa che legge il backend per disegnare il form. Un campo
   fuori lista è rifiutato col suo nome (`E_CAMPO_NON_AMMESSO`), così il backend accende
   proprio quel campo;
4. **la scrittura**, con i controlli della tabella: vincoli, perimetro in scrittura, padri
   attivi, stati. Quello che la tabella sa dire non lo ripete il verbo.

### ⭐ Chi controlla che cosa

* Il **verbo** controlla il permesso e il perimetro di lettura, e sceglie i campi.
* Il **building block di nascita** (`fn_crea_*`), dove c'è, scrive la riga: lo usano anche il
  provisioning e le fixture dei test, che non hanno un operatore con un livello. Non controlla
  il permesso.
* La **tabella** fa rispettare tutto il resto, per chiunque scriva.

### Modificare è mandare un delta

I verbi di modifica ricevono solo le colonne che cambiano: una colonna assente resta com'è,
una colonna mandata vuota si svuota, un delta vuoto non scrive niente. Ritornano la riga con
le colonne modificabili, per ridisegnare il form.

### ⛔ Che cosa non fanno

* **Non eliminano** le anagrafiche: un magazzino, un'ubicazione, un lotto si disattivano con
  la modifica. Si elimina solo un documento interno in bozza.
* **Non girano come l'operatore**: girano come il proprietario delle tabelle, con un percorso
  di ricerca bloccato. Per questo il perimetro lo controllano loro, con lo stesso predicato
  della policy: dentro un verbo la sicurezza per riga non filtra.
