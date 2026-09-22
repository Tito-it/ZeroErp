## 📘 Documentazione Concettuale – View `dbops.vw_funzioni_check_codici`

> 👀 **Vedi anche**
>
Approfondimenti viste:
>
[dbops.vw_punti_canale_campo](/dbzero/dbops/manual/vw_punti_canale_campo)
>
[dbops.vw_punti_primo_motivo](/dbzero/dbops/views/vw_punti_primo_motivo)

---
### 🎯 Scopo Principale
(latest review 21-09-2026)

Una tabella di **collegamenti**, non un allarme: per ogni funzione del
database che usa una **funzione di controllo** (`fn_check_*`), quale controllo
usa e **quali codici d'errore** quel controllo può produrre — con l'indicazione
se, accanto al codice, il controllo scrive anche **il nome del campo** da
correggere.

---

### ⭐ Perché esiste da sola

Due controlli diversi hanno bisogno della stessa lettura:

* il **rubinetto** (`vw_punti_primo_motivo`), che sorveglia le poche funzioni
  che sollevano il primo motivo «a mano» invece di passare dal meccanismo
  condiviso;
* il controllo sul **canale del campo** (`vw_punti_canale_campo`), che deve
  vedere *tutte* le funzioni che sollevano il codice di un motivo — quelle a
  mano e le venti che passano dal meccanismo.

Se ciascuno si tenesse la propria copia della lettura, il giorno in cui una
delle due cambia le due misure comincerebbero a dire cose diverse sullo stesso
fatto, senza che nessuno se ne accorga. Perciò la lettura sta **qui**, una
volta, e le due viste la interrogano.

---

### Come si legge

| Colonna | Che cosa porta |
| --- | --- |
| `funzione` | chi nomina il controllo |
| `check_funzione` | il controllo nominato (tutti quelli nominati nel testo, non solo quello usato in un ramo: la lettura è volutamente **larga**) |
| `check_emette_valori` | il controllo prepara anche i valori per comporre la frase del messaggio |
| `codice` | un codice che il controllo può produrre — `NULL` se non ne produce nessuno (il collegamento resta visibile) |
| `n_motivi` | quante volte lo produce |
| `motivo_chiave` | `campo` o `parametro` se **ogni** motivo con quel codice porta anche il nome del campo; altrimenti vuoto |

---

### ⚠️ Che cosa NON dice

Legge il **testo** delle funzioni, tolti i commenti: riconosce la forma scritta,
non il significato. Un controllo nominato in due rami di cui uno solo viene
percorso compare comunque — è il verso dell'errore scelto apposta, perché un
collegamento in più costa una riga da guardare, uno in meno costa un caso non
visto.

Origine: `docs/it/dev/work-done/brief-be-presidio-ui-action-e-canale-campi.md`
(§4-bis.2).

---

{% include-markdown "signature-core.md" %}
