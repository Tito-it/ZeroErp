## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_attivita_fatturabili_guard_ba_coerenza`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
>
**Approfondimento funzioni:**
>
• [vendite.trgfn_attivita_fatturabili_normalize](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_normalize)  
> • [vendite.trgfn_attivita_fatturabili_guard_commessa](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_guard_commessa)  
>
### 🎯 Scopo Principale
(latest review 10-09-2026)

Controlla che un'attività da fatturare e il suo **billing account** parlino dello
stesso **punto di fornitura**: l'istanza di utility scritta sulla riga deve
essere quella del billing account a cui la riga è intestata.

È una guardia: se le due non coincidono, la scrittura non passa.

---

### 🔴 Fino al 10-09-2026 questo controllo non veniva mai fatto

E vale la pena saperlo, perché è il tipo di difetto che non si vede.

La funzione cominciava saltando il controllo per le righe che nascono da una
**commessa** — con questa motivazione, scritta al suo interno: *«per quelle
righe la coerenza è già garantita da chi le crea»*.

Il problema è che **tutte** le righe nascono da una commessa: la colonna che le
collega è obbligatoria. Quindi il salto valeva sempre, e la guardia usciva senza
controllare niente. Una difesa che esisteva, era montata, non dava mai errore —
e non stava difendendo nulla.

⭐ Dal changeSet `20260910-26` il salto non c'è più: **il controllo si applica a
ogni riga**.

> ⚠️ E la ragione per cui è stato tolto non è che «oggi le righe da commessa
> potrebbero essere incoerenti». È che *«qualcun altro se ne occupa»* è una
> convenzione, non una garanzia. Una guardia esiste per il giorno in cui la
> scrittura arriva da un'altra strada — ed è esattamente ciò a cui deve
> sopravvivere.

---

### Che cosa verifica, in pratica

* il billing account indicato **esiste**;
* il **punto di fornitura** della riga è quello di quel billing account.

Se una delle due non è vera, l'operazione viene bloccata con un messaggio che
dice quale valore ci si aspettava.

---

### Quando entra in gioco

Prima di ogni inserimento e di ogni modifica di una riga da fatturare. Non
produce nessun risultato quando va tutto bene: si fa sentire solo per fermare.

---

### ⭐ Una cosa che da oggi non serve più controllare

Il billing account **non può più mancare**: dal 10-09-2026 è obbligatorio sulle
attività da fatturare (changeSet `20260910-25`). Il motivo sta nel dominio — se
un'attività è *fatturabile*, qualcuno la deve pagare, e il billing account esiste
proprio per rappresentare quel qualcuno anche prima che esista un cliente
anagrafico (l'utility del gas che fattura un allaccio).

Origine: `docs/it/dev/work-done/brief-db-perimetro-emittente-righe-documento.md` §11.13.

---

{% include-markdown "signature-core.md" %}
