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

### 🔄 rev 2026-09-24 — un controllo che **passa la parola** a un altro

Certi controlli non scrivono i propri motivi: restituiscono quelli di un altro
controllo, tutti o una parte. «Si può creare una revisione?» chiede a
«i prezzi sono autorizzati?» e ne tiene solo il prezzo **in attesa**. È la
forma giusta — la regola sul prezzo sta in un posto solo — ma questa vista si
fermava al primo controllo, che di motivi suoi non ne ha, e il presidio del
canale campo dava le due revisioni come «senza codice».

Da questo giorno la vista **segue il passaggio**, anche su più livelli:

| Il controllo… | … e la vista |
| --- | --- |
| **accoda** i motivi dell'altro (`v_motivi \|\| …`) o li prende per rilanciarli (`v_m := …`) | eredita tutti i suoi codici |
| li **filtra** (`jsonb_agg` sugli elementi, `WHERE … ->> 'codice' = 'E_…'` o `IN (…)`) | eredita **solo** i codici del filtro |
| li **conta** o ci fa un `IF`, e poi scrive un motivo suo | non eredita niente: il codice è il suo |

⚠️ La terza riga non è un dettaglio: la prima stesura trattava ogni chiamata
come un passaggio di parola, e metteva nel perimetro del rubinetto due punti
del controllo di annullamento del preventivo, che i motivi dell'altro li conta
e basta. Il filtro si legge solo nell'istruzione della chiamata; un filtro per
esclusione (`<>`, `NOT IN`) non è riconosciuto, e allora si eredita tutto — un
collegamento in più, mai uno in meno. Presidio: `test-punti-canale-campo-v1`,
casi 15 e 16.

Origine: `docs/it/dev/work-done/brief-be-presidio-ui-action-e-canale-campi.md`
(§4-bis.2); la revisione: `brief-db-ricerca-full-colonne-da-accendere` §7.

### 🔄 rev 2026-10-10 — legge solo i testi che possono contenere un collegamento

La vista partiva dal testo di **tutte** le funzioni del database, anche se un
collegamento nasce solo dove compare il nome di un controllo (`fn_check_…`).
Il risultato era giusto, ma PostgreSQL, guardando quanto lavoro *sembrava*
esserci, decideva di compilare la query prima di eseguirla: più di un secondo
di preparazione per un decimo di secondo di lavoro, pagato da ogni lettura,
compresi i due controlli che la interrogano.

Da questo giorno la vista legge solo i testi che contengono `fn_check_`. Le
righe sono le stesse — un testo senza quel nome non può collegare niente — e
la lettura torna a costare un decimo di secondo.

⚠️ È una proprietà che **non si vede nei risultati**: chi riscrive la vista
senza quel filtro ottiene le stesse righe, solo dieci volte più lente. Per
questo c'è un controllo apposta, `test-vw-funzioni-check-codici-sotto-jit-v1`,
che guarda la stima del costo e non le righe.

Origine: changeSet `20261010-43`.

---

{% include-markdown "signature-core.md" %}
