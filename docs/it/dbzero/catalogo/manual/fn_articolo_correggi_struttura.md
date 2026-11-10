## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_correggi_struttura`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la regola «un articolo usato non cambia la sua struttura»
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/funzioni/trgfn_articoli_guard_struttura_se_usato) — la regola di cui questo verbo è la porta
> * [catalogo.fn_articolo_colonne_struttura](/dbzero/catalogo/funzioni/fn_articolo_colonne_struttura) — le colonne che si possono correggere
> * [catalogo.fn_articolo_righe_vive_non_ammesse](/dbzero/catalogo/funzioni/fn_articolo_righe_vive_non_ammesse) — le righe vive che la correzione rigiudica
> * [script.fn_guard_super_admin](/dbzero/script/funzioni/fn_guard_super_admin) — il permesso, la stessa regola del backend
> * [script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella) — la seconda chiave della porta

---

### 🎯 Scopo Principale

Il SUPER_ADMIN corregge le colonne strutturali di un articolo anche se l'articolo è usato. Serve
per un errore di caricamento; per vendere o gestire un articolo in modo diverso, la via normale
resta un articolo nuovo.

Il backend lo chiama dal salvataggio dell'articolo, nella stessa transazione della modifica.

---

### Come si chiama

Il verbo riceve l'articolo e un oggetto JSON con le **sole** colonne da cambiare. Le colonne
ammesse sono quelle di `catalogo.fn_articolo_colonne_struttura`; le colonne assenti restano come
sono. Ogni valore è convertito col tipo della sua colonna.

I controlli, nell'ordine:

1. **Il permesso.** Chi chiama dev'essere SUPER_ADMIN (`script.fn_guard_super_admin`), altrimenti
   `E_PERMESSO_NEGATO`.
2. **I parametri.** Un oggetto vuoto, un valore che non è un oggetto o una colonna fuori
   dall'elenco danno `E_PARAMETRO_INVALIDO`, col nome delle colonne non ammesse.
3. **L'articolo.** Un id vuoto o un articolo inesistente danno `E_ARTICOLO_NOT_FOUND`. L'articolo
   si blocca in scrittura per tutta la correzione.
4. **Le righe vive, prima e dopo** (sezione sotto).

---

### La porta si apre solo per questo verbo

Il verbo accende per la sola transazione la GUC `zeroerp.articolo_correggi_struttura` con l'id
dell'articolo, scrive e la spegne. Il guard «usato» la onora solo se chi scrive è anche il
proprietario della tabella: il verbo è SECURITY DEFINER, e una sessione applicativa che accende
la GUC a mano non apre niente.

* La porta apre solo il guard «usato». I guard della distinta, dell'onere e del listino del
  composito parlano lo stesso.
* Il verbo non tocca le righe già scritte: la natura è copiata sulla riga, e un documento chiuso
  resta la fotografia di quando è nato.

---

### ⭐ La correzione non rende non valide le righe dei documenti aperti

Il verbo legge le righe **vive** dell'articolo non ammesse
(`catalogo.fn_articolo_righe_vive_non_ammesse`) prima e dopo la scrittura. Se la correzione rende
non ammessa anche una sola riga che prima lo era, rifiuta tutta la correzione
(`E_ARTICOLO_STRUTTURA_RIGHE_APERTE`). Una riga già non ammessa prima non blocca: non è la
correzione ad averla resa tale.

Una riga è viva se è attiva e il suo documento non è chiuso. La giudica la stessa check dei
guard di riga, sulla riga intera: su offerta e contratto anche l'erogazione e la fonte della
quantità.

* Le righe si contano in tutte le aziende, perché il verbo è SECURITY DEFINER. Il messaggio dà
  solo il codice dell'articolo, il numero di righe e il numero di documenti; le prime cinquanta
  righe, col codice del motivo, stanno nel dettaglio dell'errore.
* Una correzione che non tocca i motivi passa anche con righe vive. La natura, per esempio, è
  copiata sulla riga.

Il controllo sta qui perché la porta è l'unica strada da cui un articolo usato cambia
struttura. Senza, un ordine confermato con un articolo diventato «solo componente» resterebbe
com'è, e la generazione della bolla fallirebbe a metà.

Restano fuori:

* la distinta: un legame non si spegne se le righe dei documenti hanno i suoi componenti, e il
  componente che diventa composito lo ferma
  `catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva`;
* magazzino, lotto e matricola, che li giudica l'emissione della bolla.

---

### ⚠️ Che cosa oggi non copre

* Nessun difetto noto. Prima di scrivere, ogni valore si valida: un valore vuoto su una colonna
  obbligatoria, o di un tipo che la colonna non accetta, è `E_PARAMETRO_INVALIDO` col nome
  leggibile della colonna (`catalogo.fn_articolo_flag_etichetta`), non un errore di PostgreSQL.

---

### Codici errore

* `E_PERMESSO_NEGATO` — chi chiama non è SUPER_ADMIN.
* `E_PARAMETRO_INVALIDO` — l'oggetto delle colonne è vuoto, non è un oggetto o nomina una
  colonna non correggibile.
* `E_ARTICOLO_NOT_FOUND` — l'id è vuoto, o l'articolo non esiste.
* `E_ARTICOLO_STRUTTURA_RIGHE_APERTE` — la correzione rende non ammesse righe vive che prima lo
  erano; la correzione si annulla.

---

### Test

* `db/pgtap/catalogo/test-articolo-usato-struttura-v1.sql` — chi non è SUPER_ADMIN è respinto;
  una colonna non correggibile è respinta; il SUPER_ADMIN corregge la natura di un articolo
  usato.
* `db/pgtap/catalogo/test-articolo-colonne-struttura-v1.sql` — il verbo corregge colonne di tipo
  diverso, lascia le altre come sono, rifiuta un valore del tipo sbagliato con `22P02` e segue
  l'elenco delle colonne quando cambia.
* `db/pgtap/catalogo/test-articolo-correzione-righe-aperte-v1.sql` — una riga viva resa non
  ammessa annulla la correzione; un documento annullato, una riga spenta o una riga già non
  ammessa prima non bloccano; l'elenco delle righe vive legge tutte le tabelle del guard di riga.

---

### Note di migrazione

* 2026-10-13 — nasce, come porta del guard «usato» (brief-db-articoli-ammessi-per-documento).
* 2026-10-18 — le colonne ammesse si leggono da `catalogo.fn_articolo_colonne_struttura`, e la
  correzione rigiudica le righe vive prima e dopo.
* 2026-10-21 — le righe vive si giudicano sulla riga intera, con l'erogazione su offerta e
  contratto (brief-db-offerta-emissione-ed-erogazione).
* 2026-11-09 — i valori si validano prima di scrivere; le colonne vengono dalla dichiarazione, non
  più dalle regole del form; il guard del listino del composito è ritirato, e passa la regola delle
  righe vive (brief-db-revisione-catalogo, giro 3).

---

{% include-markdown "signature-core.md" %}
