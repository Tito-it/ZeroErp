## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_prezzo_listino_v2_esito`

> 👀 **Vedi anche**
>
**Il guscio che la solleva:**
>
• [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2)
>
**Consumatori diretti (vogliono l'esito, non l'eccezione):**
>
• [vendite.fn_ddt_riga_componenti_init](/dbzero/vendite/funzioni/fn_ddt_riga_componenti_init)
> • [vendite.fn_ddt_riga_componenti_preview](/dbzero/vendite/funzioni/fn_ddt_riga_componenti_preview)

### 🎯 Scopo Principale

(creata 2026-08-19 — brief-ddt-righe-senza-prezzo §9 slice A)

**È il NUCLEO del calcolo prezzi.** Fa esattamente ciò che fa
`fn_resolve_prezzo_listino_v2` — stessi tre stadi, stesso corpo — con una
differenza sola: quando il prezzo **non si trova**, non solleva un'eccezione.
Lo **dice**, e restituisce comunque una riga.

Serve a chi può convivere con un prezzo assente. Oggi è il DDT: la merce si
muove anche quando non si vende — conto visione, campionatura, riparazione,
trasferimento — e su quei documenti un prezzo di listino è un dato che non ha
significato.

### Le tre colonne dell'esito

Alle 14 colonne del resolver se ne aggiungono tre. **Se `esito_codice` è `NULL`,
il prezzo c'è**: le altre colonne valgono come sempre.

| colonna | quando ha risolto | quando non ha risolto |
|---|---|---|
| `esito_codice` | `NULL` | il codice del motivo (es. `E_CATEGORIA_LISTINO_NON_MAPPATA`) |
| `esito_context` | `NULL` | il contesto: **tutti i nove parametri della chiamata** più i dati dello stadio che ha fallito |
| `esito_valori` | `NULL` | i valori che riempiono i segnaposto del messaggio, nell'ordine |

> ⚠️ **Una riga esce sempre.** Chi la legge con `SELECT … INTO` deve comunque
> controllare `FOUND`: `SELECT INTO` senza righe non solleva, azzera le
> variabili — e un prezzo `NULL` verrebbe scambiato per un prezzo risolto.

### La regola: che cosa è un errore e che cosa è un esito

**Un parametro sbagliato è un errore; un prezzo che non c'è è un esito.**

Restano errori — e vengono sollevati anche da questa funzione — i due
`E_PARAMETRO_INVALIDO`: argomenti fuori dominio, e billing account inesistente.
Lì ha sbagliato chi chiama, o si sta parlando di qualcosa che non esiste.

Diventano esito tutti e nove i casi in cui il prezzo semplicemente non si trova,
compreso **l'articolo escluso da contratto**. L'esclusione dice che quell'articolo
non si *fattura* a quel cliente, non che non possa *viaggiare*: serve appunto a
mandarlo in riparazione o a riprenderselo indietro. Il divieto non si allenta —
se la causale del DDT è di vendita, la riga resta senza prezzo e il documento
non si emette.

### ⛔ Perché esiste, invece di catturare l'eccezione

È la domanda che si fanno tutti guardando questa coppia di funzioni, e la
risposta non è di gusto.

`script.fn_log_error_only` scrive su `dbops.error_log` attraverso una
**connessione separata, fuori dalla transazione**: la riga di log resta anche se
tutto il resto viene annullato. Un `BEGIN … EXCEPTION` attorno alla chiamata —
in SQL o in Python — nasconderebbe l'errore a chi chiama, ma il log lo avrebbe
già scritto il database un istante prima di sollevare: **una riga per ogni
tentativo**, moltiplicata per le righe del documento.

Il log lo scrive il database, quindi solo il database può smettere di scriverlo.
Da qui un nucleo che non solleva affatto, invece di un guscio che ingoia.

### Regole

- **Non logga e non solleva** sugli otto esiti. Presidiato da pgTAP: venti
  risoluzioni fallite devono lasciare `dbops.error_log` intatto.
- `STABLE`. Nessuna scrittura.
- **La logica di risoluzione vive solo qui.** Il guscio delega e basta: chi deve
  modificare il calcolo dei prezzi lavora su questa funzione, altrimenti le due
  smettono di essere lo stesso corpo — che è l'unica cosa che rende la coppia
  sicura.
- Firma identica al guscio (9 parametri, stessi nomi e default): passare
  dall'uno all'altro è cambiare un nome di funzione.

### Note

> ⚠️ **Un ramo è stato tolto il 2026-08-19**, non aggiunto. Il caso «billing
> account senza categoria» non può più verificarsi da quando quella colonna è
> diventata obbligatoria (2026-04-14), e il codice che sollevava è andato in
> pensione. Con la categoria a `NULL` la ricerca sulla matrice non trova righe e
> si esce con l'esito `E_CATEGORIA_LISTINO_NON_MAPPATA`: un codice vivo, il cui
> messaggio nomina la tabella giusta.

---

<!-- rev-2026-09-28-liste-righe -->
### 🔄 rev 2026-09-28 — brief-db-liste-righe-documento

La versione del listino in vigore alla data di riferimento (contratto senza versione fissata, listino della categoria) non è più scelta qui: la dice [vendite.fn_listino_versione_in_vigore](/dbzero/vendite/funzioni/fn_listino_versione_in_vigore) (`20260928-41`). Per ogni data la versione in vigore è **al più una**, per costruzione (nessuna sovrapposizione fra versioni ATTIVE e CHIUSE, date di una CHIUSA bloccate), quindi «la prima» e «tutte le valide» sono la stessa cosa. Stesso esito, provato sui dati di dev. La firma è di nuovo ancorata (`%TYPE`, da `20260819-07`: l'ultimo YAML l'aveva sciolta) e `SECURITY INVOKER` è esplicito.

<!-- rev-2026-10-16-versione-bozza -->
### 🔄 rev 2026-10-16 — mai un prezzo da una versione in bozza

Il **percorso rapido** (`p_listino_versione_id_preferito`: la versione la sceglie chi chiama)
leggeva la versione senza guardarne lo stato, mentre gli altri rami escludevano già la
`BOZZA` (`fn_listino_versione_in_vigore`). Una bozza si modifica ancora, quindi il prezzo
preso da lì non sarebbe riproducibile. Ora la versione in `BOZZA` dà l'esito
**`E_PREZZO_LISTINO_VERSIONE_BOZZA`** (valori: codice della versione, codice del listino),
non un ripiego al passo successivo, che nasconderebbe il chiamante sbagliato.

Un'opzione «anche bozza» **non c'è**: i chiamanti di oggi (contratti e offerte, dal
backend) passano la versione di `vendite.fn_documento_listino_operativo`, che esclude già
la bozza. Nasce col primo chiamante che la chiede davvero, con il suo caso d'uso.
Decisione di Tid; brief `brief-db-coerenza-listino-della-riga-di-commessa` §6 D-4
(`20261016-04`).

