## 📘 Documentazione Concettuale – Funzione `dbops.fn_admin_merge_stradario`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.stradario](/dbzero/config/tabelle/stradario) — le due vie che si fondono
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — gli indirizzi che la fusione ripunta
> * [storico.stradario_trasformazioni](/dbzero/storico/tabelle/stradario_trasformazioni) — il registro delle fusioni delle vie
>
> Approfondimento funzioni:
>
> * [dbops.fn_admin_merge_comune](/dbzero/dbops/funzioni/fn_admin_merge_comune) — la gemella, un livello più in alto: fonde due comuni
> * [dbops.fn_fusione_ripunta_figlie](/dbzero/dbops/funzioni/fn_fusione_ripunta_figlie) — il ripuntamento, con il controllo dei doppi
> * [script.fn_get_vie_discendenti](/dbzero/script/funzioni/fn_get_vie_discendenti) — percorre la catena delle trasformazioni
> * [anagrafiche.trgfn_indirizzi_dettaglio_protect_update](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_protect_update) — il trigger che protegge la via di un indirizzo
> * [dbops.fn_audit_log_once](/dbzero/dbops/funzioni/fn_audit_log_once) — la porta da cui si scrive l'audit
>
> Guide:
>
> * [Riclassificazione vie e toponomastica](/guide/riclassificazione-vie) — la policy, e il passo che sposta un indirizzo su un'altra via

---

### 🎯 Scopo Principale

Strumento DBA che **fonde due vie** dello stradario: registra la trasformazione nel registro
delle fusioni e sposta sulla via di destinazione tutto ciò che stava su quella d'origine,
indirizzi compresi.

Le vie cambiano nome, vengono accorpate, cambiano numerazione, e gli indirizzi esistenti devono
restare validi. Nessun chiamante applicativo la usa: si lancia a mano.

---

### Che cosa fa, nell'ordine

1. controlla che origine e destinazione siano indicate, diverse, esistano entrambe in
   `config.stradario` e non siano soppresse;
2. scrive la trasformazione (via d'origine, via nuova, tipo di evento, data, nota) in
   `storico.stradario_trasformazioni`. Il tipo di evento ha come default la fusione, la data quella
   operativa del giorno;
3. apre la porta degli indirizzi (vedi sotto) e ripunta sulla destinazione **ogni tabella che
   riferisce la via d'origine**, letta dal catalogo con `dbops.fn_fusione_ripunta_figlie`. Oggi è
   una sola, `anagrafiche.indirizzi_dettaglio`; una tabella nuova con una chiave esterna verso lo
   stradario entra da sola;
4. richiude la porta;
5. segna la via d'origine come **soppressa** (`obsoleto_dal`, con la data dell'evento e mai oltre
   la data operativa): ora nessuno la riferisce più;
6. scrive l'audit **dalla porta**, una volta, a fine lavoro: esito `OK`, i parametri ricevuti, le
   righe ripuntate per tabella e la durata, nella sua colonna.

---

### ⭐ La porta degli indirizzi si apre solo per il ripuntamento

Il cambio di via di un indirizzo è bloccato da
`anagrafiche.trgfn_indirizzi_dettaglio_protect_update` (`E_COLONNA_NON_MODIFICABILE`), che lo
lascia passare solo con la manutenzione esplicita `zeroerp.maintenance_indirizzi_dettaglio`. La
fusione è il verbo per cui quella porta esiste: la accende solo attorno al ripuntamento, e subito
dopo la riporta al valore che aveva.

⇒ Dopo la fusione, nella stessa transazione, un cambio di via a mano è di nuovo rifiutato. Se il
ripuntamento si ferma, la porta torna chiusa da sola: annullando la transazione, o il savepoint di
chi ha chiamato, PostgreSQL riporta il parametro al valore di prima.

---

### ⭐ Due indirizzi uguali fermano la fusione

Se un indirizzo della via d'origine è identico a uno che la destinazione ha già (stesso civico,
estensione, palazzina, scala, piano, interno), dopo la fusione i due sarebbero lo stesso
indirizzo. La funzione **non li unisce**: si ferma prima di scrivere, con
`E_MERGE_RIGHE_DOPPIE`, e mette nel dettaglio dell'errore l'elenco delle coppie (l'indirizzo
dell'origine e quello della destinazione). Chi fonde decide che cosa farne, poi rilancia.

Il controllo vale per ogni indice unico di ogni tabella ripuntata, non solo per gli indirizzi: lo
descrive `dbops.fn_fusione_righe_doppie`.

---

### ⭐ Il registro delle fusioni non è una tabella di storico

`storico.stradario_trasformazioni` sta nello schema `storico`, ma è il **registro delle
fusioni**, scritto solo da qui: nessuna madre, nessun trigger di storicizzazione, nessuna riga
nella mappa dello scope dello storico.

⭐ Il registro si legge con `script.fn_get_vie_discendenti`, che risale da una via a tutte
quelle che ne sono derivate: chi cerca la via nuova trova anche ciò che stava sulle vecchie.

⭐ La via d'origine **resta** in `config.stradario`, soppressa: è la radice della catena, e lo
storico degli indirizzi la nomina ancora. Non si sceglie più per il nuovo, non riceve indirizzi,
non si fonde più, ed è fuori dalla chiave unica delle vie: per questo, se poi si fondono i due
comuni, non collide con la via viva che ne ha preso il posto. La regola completa è nella pagina di
`config.stradario`.

---

### L'audit: una riga, a fine lavoro

L'audit si scrive con `dbops.fn_audit_log_once`, la stessa porta di tutte le funzioni di `dbops`,
solo a fusione riuscita. Una fusione che si ferma non lascia una riga d'audit: si annullerebbe con
il resto. Il rifiuto lo registra `dbops.error_log`, con il suo codice.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_DBOPS_CHIAMATA_NON_VALIDA` | manca l'origine o la destinazione |
| `E_MERGE_ORIGINE_UGUALE_DESTINAZIONE` | origine e destinazione sono la stessa via |
| `E_STRADARIO_NON_TROVATO` | la via d'origine o quella di destinazione non esiste |
| `E_STRADARIO_SOPPRESSO` | la via d'origine o quella di destinazione è già stata fusa in un'altra |
| `E_MERGE_RIGHE_DOPPIE` | due righe diventerebbero uguali; l'elenco è nel dettaglio |
| `E_MERGE_FIGLIA_SOTTO_RLS` | chi lancia vede solo una parte di una tabella da ripuntare |

Ogni altro rifiuto di una tabella ripuntata (per esempio un indirizzo che il suo guard giudica
non valido) arriva col codice di quel guard.

---

### Test

`db/pgtap/dbops/test-fusioni-comune-stradario-v1.sql`, test 3-14: il doppio che ferma la
fusione senza spostare niente, la porta chiusa dopo il rifiuto e dopo la fusione, gli indirizzi
sulla destinazione, la riga d'audit con la durata, il registro, i tre rifiuti di parametro;
test 29, 34 e 35: la via d'origine soppressa alla data operativa, e una via soppressa che non si
fonde né come origine né come destinazione.
`db/pgtap/dbops/test-character-n-v1.sql` controlla la forma del parametro del tipo di evento.

---

### Note di migrazione

* 2026-08-04 — corretti i nomi delle colonne e i valori scritti nel registro delle fusioni.
* 2026-09-12 — l'audit passa dalla porta `fn_audit_log_once`; prima la funzione falliva alla
  prima riga d'audit.
* 2026-11-07 — `brief-db-revisione-dbops` (giro 2): la porta degli indirizzi si apre attorno al
  ripuntamento (prima la fusione si annullava appena la via aveva un indirizzo); le tabelle da
  ripuntare si leggono dal catalogo; un doppio ferma la fusione con l'elenco invece del 23505; le
  validazioni hanno un codice; la durata va nella sua colonna; esce la riga d'audit `ERROR`, che
  senza il canale dblink si annullava sempre. La via d'origine resta, segnata come soppressa, e una
  via soppressa non si fonde più.

---

{% include-markdown "signature-core.md" %}
