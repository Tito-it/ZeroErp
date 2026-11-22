## 📘 Documentazione Concettuale – Funzione `ui.fn_check_forma_configurazione`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — la configurazione di una preferenza di lista
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — la configurazione di una preferenza di dashboard
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — i codici che una voce di colonna può citare
> * [ui.dashboard_widget](/dbzero/ui/tabelle/dashboard_widget) — il pool da cui una voce di widget prende il codice
>
> Approfondimento funzioni:
>
> * [ui.trgfn_preferenza_guard_forma](/dbzero/ui/funzioni/trgfn_preferenza_guard_forma) — il guard che la chiama e solleva il codice
> * [ui.fn_intero_da_jsonb](/dbzero/ui/funzioni/fn_intero_da_jsonb) — ordine e larghezza sono interi?
> * [ui.fn_dimensione_max_ammessa](/dbzero/ui/funzioni/fn_dimensione_max_ammessa) — il tetto delle card della home
> * [ui.fn_guard_misura_pagina](/dbzero/ui/funzioni/fn_guard_misura_pagina) — la misura di pagina, che questa funzione non giudica
>
> Guide:
>
> * [Configurazione liste](/guide/configurazione-liste) — che cosa si salva nella preferenza

---

### 🎯 Scopo Principale

`ui.fn_check_forma_configurazione` dice se la configurazione di una preferenza, di una lista o di una
dashboard, ha la forma ammessa. Risponde il **primo motivo** per cui non ce l'ha, come la chiave
toccata e una frase, oppure niente se la forma è buona.

---

### Una regola per le due famiglie

Le preferenze delle liste e quelle delle dashboard hanno la stessa struttura: un oggetto con poche
chiavi, una delle quali è un elenco di voci citate per codice. La regola di forma è una sola, e la
famiglia sceglie le chiavi:

| Famiglia | Chiavi della radice | Chiavi di una voce |
| --- | --- | --- |
| lista | `colonne`, `pagina_dimensione` | `codice`, `ordine`, `larghezza`, `visibile`, `fissata` |
| dashboard | `widget`, `dimensione_max` | `codice`, `ordine`, `visibile` |

Chi chiama passa anche la lista o la dashboard della preferenza: serve a dire se un codice è del
contenitore.

---

### Che cosa si rifiuta

* **La radice** che non è un oggetto, una chiave che non è della famiglia, una chiave a null. Una
  preferenza di lista non porta più `ordinamento` né `filtri`: l'ordinamento di partenza è del preset,
  i filtri di partenza sono dell'interfaccia, e le due chiavi si rifiutano come ogni altra chiave
  estranea.
* **L'elenco** (`colonne` o `widget`) che non è un elenco, o una voce che non è un oggetto.
* **La voce** senza codice (o con un codice vuoto), con una chiave che non è della famiglia, con un
  campo a null, con un codice già usato da un'altra voce dello stesso elenco, con un codice che non è
  una colonna della lista o una card del pool della dashboard.
* **I campi della voce** di tipo sbagliato: `ordine` e `larghezza` devono essere interi positivi (la
  domanda la fa [fn_intero_da_jsonb](/dbzero/ui/funzioni/fn_intero_da_jsonb): un numero scritto come
  testo non vale), `visibile` e `fissata` vero o falso.
* **`dimensione_max`** fuori dal tetto da 1 a 100
  ([fn_dimensione_max_ammessa](/dbzero/ui/funzioni/fn_dimensione_max_ammessa)).

Il controllo si ferma al primo motivo: le chiavi della radice si guardano in ordine alfabetico, le voci
nell'ordine dell'elenco.

---

### Che cosa passa

* La configurazione vuota: la preferenza segue il preset in tutto. «Almeno una chiave» è una regola
  dell'interfaccia di salvataggio, non della forma del dato, e resta del backend.
* Una voce con il solo codice: ogni altro campo può mancare, e chi legge gli dà il default della
  colonna o del widget. Un campo può mancare, ma non essere null.
* Il codice di una colonna spenta o di una card del pool spenta: una colonna si sospende e torna, e la
  scelta dell'utente non va persa nel frattempo. La lettura, finché resta spenta, la salta.
* `pagina_dimensione`: qui non si giudica. La misura la giudica
  [fn_guard_misura_pagina](/dbzero/ui/funzioni/fn_guard_misura_pagina), col suo codice, subito dopo.

---

### ⭐ Risponde un motivo, non solleva

Non solleva sul dato: restituisce il motivo, e sceglie chi chiama che cosa farne. Il guard delle
preferenze lo trasforma nel rifiuto `E_UI_CONFIGURAZIONE_FORMA`; chi porta in forma le righe esistenti
la usa per verificare di non lasciarne nessuna che il guard rifiuterebbe al salvataggio successivo.

⚠️ È più stretta del vecchio controllo del backend su due punti: il codice deve essere della lista o
del pool, e due voci di colonna non possono avere lo stesso codice. Il salvataggio dell'interfaccia
manda le colonne che la lista ha risolto, una voce per codice, e non ne è toccato.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — una famiglia diversa da lista e dashboard, o un contenitore vuoto o non
  positivo. Sul dato la funzione non solleva.

---

### Test

* `db/pgtap/ui/test-ui-forma-configurazione-v1.sql` — attraverso il guard: le chiavi `filtri` e
  `ordinamento` rifiutate, un campo della voce a null, il codice di un'altra lista, un codice ripetuto,
  un ordine scritto come stringa, un `visibile` non booleano, una radice che non è un oggetto, la
  configurazione vuota che passa, la voce di una colonna spenta che passa; per le dashboard un codice
  fuori dal pool, 101 card, una voce con una chiave in più.

---

### Note di migrazione

* 2026-11-21 — nasce: della configurazione il database verificava solo la misura di pagina delle liste,
  e il resto stava solo nel backend. Le regole della voce (un campo può mancare, mai null) vengono da
  ciò che il backend accettava.

---

{% include-markdown "signature-core.md" %}
