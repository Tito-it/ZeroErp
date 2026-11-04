## 📘 Documentazione Concettuale – Funzione `dbops.fn_admin_merge_stradario`

> **Ultimo aggiornamento**: 4 novembre 2026
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
> * [script.fn_get_vie_discendenti](/dbzero/script/funzioni/fn_get_vie_discendenti) — percorre la catena delle trasformazioni
> * [anagrafiche.trgfn_indirizzi_dettaglio_protect_update](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_protect_update) — il trigger che oggi respinge il ripuntamento
> * [dbops.fn_audit_log_once](/dbzero/dbops/funzioni/fn_audit_log_once) — la porta da cui si scrive l'audit
>
> Guide:
>
> * [Riclassificazione vie e toponomastica](/guide/riclassificazione-vie) — la policy, e il passo che sposta un indirizzo su un'altra via

---

### 🎯 Scopo Principale

Strumento DBA che **fonde due vie** dello stradario: registra la trasformazione nel registro
delle fusioni e ripunta sulla via di destinazione gli indirizzi che stavano su quella d'origine.

Stesso fatto del mondo reale della gemella dei comuni: le vie cambiano nome, vengono accorpate,
cambiano numerazione, e gli indirizzi esistenti devono restare validi. Nessun chiamante
applicativo la usa: si lancia a mano.

---

### Che cosa fa, nell'ordine

1. controlla che origine e destinazione siano diverse e che esistano entrambe in `config.stradario`;
2. scrive la trasformazione (via d'origine, via nuova, tipo di evento, data, nota) in
   `storico.stradario_trasformazioni`. Il tipo di evento ha come default la fusione, la data quella
   operativa del giorno;
3. ripunta sulla destinazione le righe di `anagrafiche.indirizzi_dettaglio` della via d'origine;
4. scrive l'audit **dalla porta**, una volta, a fine lavoro: esito `OK`, i parametri ricevuti,
   quanti indirizzi ha ripuntato e la durata.

---

### ⛔ Oggi la fusione si ferma al primo indirizzo

Il cambio di via di un indirizzo dettaglio è bloccato da
`anagrafiche.trgfn_indirizzi_dettaglio_protect_update` (`E_COLONNA_NON_MODIFICABILE`), che lo
lascia passare solo in manutenzione esplicita. Questa funzione non apre quella manutenzione:
⇒ appena la via d'origine ha almeno un indirizzo, il ripuntamento è respinto e la fusione intera
si annulla. Passa soltanto la fusione di una via senza indirizzi.

La porta di manutenzione del trigger resta proprio per un verbo che sposti gli indirizzi su
un'altra via: questa funzione è il candidato naturale, ma oggi non la usa.

⚠️ Anche aperta la porta, due indirizzi identici (stesso civico, palazzina, scala, piano,
interno) sulle due vie si scontrerebbero sulla chiave dell'indirizzo, e la fusione si
annullerebbe: la funzione non li unisce.

---

### ⭐ Il registro delle fusioni non è una tabella di storico

`storico.stradario_trasformazioni` sta nello schema `storico`, ma è il **registro delle
fusioni**, scritto solo da qui: nessuna madre, nessun trigger di storicizzazione, nessuna riga
nella mappa dello scope dello storico.

⭐ Il registro si legge con `script.fn_get_vie_discendenti`, che risale da una via a tutte
quelle che ne sono derivate: chi cerca la via nuova trova anche ciò che stava sulle vecchie.

---

### L'audit: una riga, a fine lavoro

L'audit si scrive con `dbops.fn_audit_log_once`, la stessa porta di tutte le funzioni di `dbops`.
Il ramo d'errore scrive una riga `ERROR` con il messaggio e lo SQLSTATE, poi rilancia l'errore.

⚠️ In una transazione normale quella riga si annulla insieme al resto: sopravvive solo quando il
canale di log fuori transazione (dblink) è acceso.

---

### Codici errore

Nessun codice registrato sollevato da qui. Le tre validazioni (origine uguale a destinazione,
via d'origine inesistente, via di destinazione inesistente) sollevano un errore con un messaggio
in chiaro, senza codice: è un debito dichiarato, da saldare quando la funzione avrà un chiamante
applicativo. Il rifiuto del ripuntamento arriva dal trigger degli indirizzi, col suo codice
`E_COLONNA_NON_MODIFICABILE`.

---

### Test

Nessun pgTAP prova la fusione. `db/pgtap/dbops/test-character-n-v1.sql` controlla solo la forma
del parametro del tipo di evento.

---

### Note di migrazione

* 2026-08-04 — corretti i nomi delle colonne e i valori scritti nel registro delle fusioni.
* 2026-09-12 — l'audit passa dalla porta `fn_audit_log_once` (`brief-db-rls-storico-scope-congelato`
  §4d). Prima la funzione apriva una riga con stato `STARTED`, che il CHECK del registro non
  ammette, e quindi falliva alla prima riga; chiudeva poi con un UPDATE del registro, che dal
  2026-09-11 l'applicazione non può più fare.

---

{% include-markdown "signature-core.md" %}
