## 📘 Documentazione Concettuale – Funzione `dbops.fn_admin_merge_comune`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.comuni](/dbzero/config/tabelle/comuni) — i due comuni che si fondono
> * [config.stradario](/dbzero/config/tabelle/stradario) — le vie, la figlia in cui i doppi sono più probabili
> * [storico.comune_trasformazioni](/dbzero/storico/tabelle/comune_trasformazioni) — il registro delle fusioni dei comuni
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove resta la traccia della fusione
>
> Approfondimento funzioni:
>
> * [dbops.fn_admin_merge_stradario](/dbzero/dbops/funzioni/fn_admin_merge_stradario) — la gemella, un livello più in basso: fonde due vie
> * [dbops.fn_fusione_ripunta_figlie](/dbzero/dbops/funzioni/fn_fusione_ripunta_figlie) — il ripuntamento, con il controllo dei doppi
> * [dbops.fn_fusione_figlie](/dbzero/dbops/funzioni/fn_fusione_figlie) — quali tabelle riferiscono il comune
> * [dbops.fn_audit_log_once](/dbzero/dbops/funzioni/fn_audit_log_once) — la porta da cui si scrive l'audit

---

### 🎯 Scopo Principale

Strumento DBA che **fonde due comuni**: registra la trasformazione nel registro delle fusioni
e sposta sul comune di destinazione tutto ciò che nominava il comune d'origine.

Serve a un fatto del mondo reale: i comuni si fondono, cambiano nome, vengono soppressi. Gli
indirizzi già registrati devono restare validi, e chi cerca sul comune nuovo deve trovare anche
ciò che era stato inserito col vecchio.

⚠️ È un'operazione **amministrativa e non reversibile** dall'applicazione: il prefisso
`fn_admin_` lo dichiara. Nessun chiamante applicativo la usa: si lancia a mano, sapendo che cosa
tocca.

---

### Che cosa fa, nell'ordine

1. controlla che origine e destinazione siano indicate, diverse, ed esistano entrambe in
   `config.comuni`;
2. scrive la trasformazione (comune d'origine, comune nuovo, tipo di evento, data, nota) in
   `storico.comune_trasformazioni`. Il tipo di evento ha come default la fusione, la data quella
   operativa del giorno;
3. ripunta sulla destinazione **ogni tabella che riferisce il comune d'origine**, letta dal
   catalogo con `dbops.fn_fusione_ripunta_figlie`: le vie dello stradario, i codici postali, gli
   indirizzi, i soggetti, gli indirizzi dei soggetti, le aree geografiche di fatturazione, e ogni
   tabella che avrà una chiave esterna verso i comuni;
4. scrive l'audit **dalla porta**, una volta, a fine lavoro: esito `OK`, i parametri ricevuti, le
   righe ripuntate per tabella e la durata, nella sua colonna.

⛔ Il comune d'origine **non** si cancella e non si spegne: resta, e la sua storia la racconta
il registro delle fusioni.

---

### ⭐ Un doppio ferma la fusione

Se una riga del comune d'origine, spostata, diventerebbe uguale a una che il comune di
destinazione ha già, la funzione **si ferma prima di scrivere**, con `E_MERGE_RIGHE_DOPPIE` e
l'elenco delle coppie nel dettaglio dell'errore. Non unisce niente da sola.

Il caso più probabile è lo stradario: la stessa via **viva** (stessa via generale, stesso codice
postale) presente nei due comuni. Si fondono prima le due vie (`dbops.fn_admin_merge_stradario`),
poi i comuni: la via d'origine resta, ma soppressa, e una via soppressa è fuori dalla chiave unica
dello stradario. Nella fusione dei comuni si sposta con le altre senza collidere.

---

### ⭐ Il registro delle fusioni non è una tabella di storico

`storico.comune_trasformazioni` sta nello schema `storico`, ma non è la copia delle versioni di
una riga: è il **registro delle fusioni**, scritto solo da qui. Non ha una madre, non ha il
trigger di storicizzazione, non entra nella mappa dello scope dello storico.

⚠️ A differenza della gemella delle vie, oggi nessuno lo legge: la risalita delle trasformazioni
(`script.fn_get_vie_discendenti`) percorre solo il registro delle vie.

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
| `E_MERGE_ORIGINE_UGUALE_DESTINAZIONE` | origine e destinazione sono lo stesso comune |
| `E_COMUNE_NON_TROVATO` | il comune d'origine o quello di destinazione non esiste |
| `E_MERGE_RIGHE_DOPPIE` | due righe diventerebbero uguali; l'elenco è nel dettaglio |
| `E_MERGE_FIGLIA_SOTTO_RLS` | chi lancia vede solo una parte di una tabella da ripuntare |

Ogni altro rifiuto di una tabella ripuntata arriva col codice del suo guard.

---

### Test

`db/pgtap/dbops/test-fusioni-comune-stradario-v1.sql`, test 15-19: la stessa via nei due comuni
che ferma la fusione, la fusione riuscita con nessuna tabella (letta dal catalogo) che nomini più
il comune soppresso, vie e codici postali sul comune nuovo, il comune inesistente. Il test 15
prova anche che una via soppressa, con la stessa terna di una via viva della destinazione, non è
un doppio.
`db/pgtap/dbops/test-character-n-v1.sql` controlla la forma del parametro del tipo di evento.

---

### Note di migrazione

* 2026-09-12 — l'audit passa dalla porta `fn_audit_log_once`; prima la funzione falliva alla
  prima riga d'audit e non ha mai fuso niente.
* 2026-11-07 — `brief-db-revisione-dbops` (giro 2): ripunta tutte le tabelle che riferiscono il
  comune, lette dal catalogo (prima solo lo stradario); un doppio ferma la fusione con l'elenco
  invece del 23505; le validazioni hanno un codice; la durata va nella sua colonna; esce la riga
  d'audit `ERROR`, che senza il canale dblink si annullava sempre.

---

{% include-markdown "signature-core.md" %}
