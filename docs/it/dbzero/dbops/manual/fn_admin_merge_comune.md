## 📘 Documentazione Concettuale – Funzione `dbops.fn_admin_merge_comune`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.comuni](/dbzero/config/tabelle/comuni) — i due comuni che si fondono
> * [config.stradario](/dbzero/config/tabelle/stradario) — l'unica tabella che la fusione ripunta
> * [storico.comune_trasformazioni](/dbzero/storico/tabelle/comune_trasformazioni) — il registro delle fusioni dei comuni
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove resta la traccia della fusione
>
> Approfondimento funzioni:
>
> * [dbops.fn_admin_merge_stradario](/dbzero/dbops/funzioni/fn_admin_merge_stradario) — la gemella, un livello più in basso: fonde due vie
> * [dbops.fn_audit_log_once](/dbzero/dbops/funzioni/fn_audit_log_once) — la porta da cui si scrive l'audit

---

### 🎯 Scopo Principale

Strumento DBA che **fonde due comuni**: registra la trasformazione nel registro delle fusioni
e ripunta sul comune di destinazione le vie dello stradario che stavano sul comune d'origine.

Serve a un fatto del mondo reale: i comuni si fondono, cambiano nome, vengono soppressi. Gli
indirizzi già registrati devono restare validi, e chi cerca sul comune nuovo deve trovare anche
ciò che era stato inserito col vecchio.

⚠️ È un'operazione **amministrativa e non reversibile** dall'applicazione: il prefisso
`fn_admin_` lo dichiara. Nessun chiamante applicativo la usa: si lancia a mano, sapendo che cosa
tocca.

---

### Che cosa fa, nell'ordine

1. controlla che origine e destinazione siano diverse e che esistano entrambe in `config.comuni`;
2. scrive la trasformazione (comune d'origine, comune nuovo, tipo di evento, data, nota) in
   `storico.comune_trasformazioni`. Il tipo di evento ha come default la fusione, la data quella
   operativa del giorno;
3. ripunta sulla destinazione le righe di `config.stradario` del comune d'origine;
4. scrive l'audit **dalla porta**, una volta, a fine lavoro: esito `OK`, i parametri ricevuti,
   quante vie ha ripuntato e la durata.

⛔ Il comune d'origine **non** si cancella e non si spegne: resta, e la sua storia la racconta
il registro delle fusioni.

---

### ⚠️ Ripunta solo lo stradario, non tutto ciò che nomina il comune

Il comune è nominato da più tabelle dello stradario stesso: oltre alle vie, i codici postali,
gli indirizzi, i soggetti, gli indirizzi dei soggetti, le aree geografiche di fatturazione. La
funzione ripunta **solo** `config.stradario`: tutte le altre righe restano sul comune d'origine.

⚠️ E le vie si ripuntano senza guardare se la destinazione ha già la stessa via con lo stesso
CAP: la chiave unica dello stradario (comune, via generale, codice postale) può respingere il
ripuntamento, e allora la fusione intera si annulla.

---

### ⭐ Il registro delle fusioni non è una tabella di storico

`storico.comune_trasformazioni` sta nello schema `storico`, ma non è la copia delle versioni di
una riga: è il **registro delle fusioni**, scritto solo da qui. Non ha una madre, non ha il
trigger di storicizzazione, non entra nella mappa dello scope dello storico.

⚠️ A differenza della gemella delle vie, oggi nessuno lo legge: la risalita delle trasformazioni
(`script.fn_get_vie_discendenti`) percorre solo il registro delle vie.

---

### L'audit: una riga, a fine lavoro

L'audit si scrive con `dbops.fn_audit_log_once`, la stessa porta di tutte le funzioni di `dbops`.
Il ramo d'errore scrive una riga `ERROR` con il messaggio e lo SQLSTATE, poi rilancia l'errore.

⚠️ In una transazione normale quella riga si annulla insieme al resto: sopravvive solo quando il
canale di log fuori transazione (dblink) è acceso, che è l'unico caso in cui serve.

---

### Codici errore

Nessun codice registrato. Le tre validazioni (origine uguale a destinazione, comune d'origine
inesistente, comune di destinazione inesistente) sollevano un errore con un messaggio in chiaro,
senza codice: è un debito dichiarato, da saldare quando la funzione avrà un chiamante applicativo.

---

### Test

Nessun pgTAP prova la fusione. `db/pgtap/dbops/test-character-n-v1.sql` controlla solo la forma
del parametro del tipo di evento.

---

### Note di migrazione

* 2026-09-12 — l'audit passa dalla porta `fn_audit_log_once` (`brief-db-rls-storico-scope-congelato`
  §4d). Prima la funzione apriva una riga con stato `STARTED`, che il CHECK del registro non
  ammette, e quindi falliva alla prima riga: non ha mai fuso niente. Chiudeva poi con un UPDATE
  del registro, che dal 2026-09-11 l'applicazione non può più fare.

---

{% include-markdown "signature-core.md" %}
