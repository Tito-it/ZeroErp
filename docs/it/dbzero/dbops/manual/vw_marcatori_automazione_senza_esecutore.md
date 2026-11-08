## 📘 Documentazione Concettuale – Vista `dbops.vw_marcatori_automazione_senza_esecutore`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.marcatori_automazione_debito](/dbzero/dbops/tabelle/marcatori_automazione_debito) — il registro del debito dichiarato, che decide lo stato di ogni riga
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — l'ambito delle automazioni, da cui la vista ricava chi è servito
> * [dbops.automation_cleanup_exclusions](/dbzero/dbops/tabelle/automation_cleanup_exclusions) — le tabelle escluse dalla pulizia
>
> Approfondimento funzioni:
>
> * [dbops.fn_cleanup_esclusa](/dbzero/dbops/funzioni/fn_cleanup_esclusa) — la tabella è esclusa dalla pulizia? La stessa risposta del runner
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che porta la vista nel digest
>
> Approfondimento viste:
>
> * [dbops.vw_rls_perimetro_scoperto](/dbzero/dbops/views/vw_rls_perimetro_scoperto) — lo stesso disegno, per le tabelle che dovrebbero filtrare per azienda
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — la forma comune di misura e registro
> * [Automazione DB](/guide/automazione-db) — i runner che eseguono le promesse

---

### 🎯 Scopo Principale

Le tabelle che hanno una colonna che **promette un'automazione** che nessuno esegue. Ogni riga è
una tabella e un marcatore, con accanto che cosa manca e se qualcuno se n'era già accorto.

Il difetto non fa rumore. Una colonna `storicizza` a vero senza lo storico non dà errori: la storia
semplicemente non c'è, e chi la cerca il giorno che serve trova il vuoto. Un `tx_id` che nessuno
scrive resta vuoto su ogni riga; un `cleanup_at` che nessuno legge lascia le righe per sempre.

---

### I tre marcatori, e chi li esegue

| `marcatore` | La colonna | Chi la esegue |
| --- | --- | --- |
| `TX_ID` | `tx_id` | il trigger di `dbops.trgfn_tx_id_managed`, che il runner dei transaction id monta sulle tabelle dell'ambito |
| `STORICIZZA` | `storicizza`, o quella indicata dall'override `STORICIZZA_COL` | il trigger di `script.trgfn_storico_generic`, che i runner dello storico montano dopo aver creato la shadow |
| `CLEANUP_AT` | `cleanup_at` | il purge del runner della pulizia, che scade e cancella le righe |

Una tabella è **servita dai runner** se è una tabella ordinaria (le partizioni comprese: i runner le
scorrono una a una), il suo schema è fra quelli dell'ambito e il filtro per tabella la ammette. È lo
stesso filtro che usano i runner. Per `cleanup_at` la tabella deve anche non essere esclusa dalla
pulizia, e l'esclusione si legge con [dbops.fn_cleanup_esclusa](/dbzero/dbops/funzioni/fn_cleanup_esclusa),
la stessa domanda che fa il runner.

La colonna si cerca come la cercano i runner: `tx_id` e `cleanup_at` col loro nome; quella di
storicizzazione con `dbops.fn_get_override_col` (ruolo `STORICIZZA_COL`, default `storicizza`), la
stessa chiamata della provision dello storico. Una colonna rinominata con l'override è il marcatore;
una colonna `storicizza` su una tabella che ha l'override verso un'altra colonna non lo è.

Per `tx_id` e `storicizza` basta anche il trigger **montato a mano**, se è abilitato: è così che
`dbops` copre i suoi registri fuori dall'ambito. Per `cleanup_at` no: il purge lo fa solo il runner, e
una tabella esclusa dalla pulizia resta scoperta anche se è nell'ambito.

⚠️ La vista guarda l'**ambito**, non il trigger già montato dai runner. Una tabella appena entrata
nell'ambito non ha ancora i trigger finché la convergenza non gira, ma la sua promessa ha un
esecutore che sta arrivando: segnalarla sarebbe un falso allarme su un caso che il modello prevede.

⛔ `data_update` e `user_update` non sono nel criterio, per decisione: restano fuori anche quando
nessuno li riscrive.

---

### Le tre risposte

| `stato` | Che cosa vuol dire | Che cosa fare |
| --- | --- | --- |
| `DEBITO_DICHIARATO` | la tabella è nel registro per quel marcatore, con la ragione | niente, per ora: è un lavoro con un nome |
| `NON_DICHIARATO` | nessuno l'ha guardata | **allarme**: una colonna è nata promettendo qualcosa che nessuno fa |
| `DEBITO_ESTINTO` | il registro nomina una tabella che per quel marcatore ha ormai un esecutore, o non ha più la colonna, o non esiste | togliere la riga dal registro |

⛔ **La regola non è «la vista è vuota»**: è «niente fuori da `DEBITO_DICHIARATO`». Il catalogo dei
presidi la porta nel digest settimanale con natura `ZERO` e stato atteso `DEBITO_DICHIARATO`.

Le correzioni possibili per una riga sono tre, e la scelta è per tabella: la tabella entra
nell'ambito, il trigger si monta a mano, o la colonna si toglie.

---

### ⚠️ Che cosa la vista non dice

* Che l'esecutore **funzioni**: dice che c'è. Che il transaction id si scriva, che la shadow si
  armi, che le righe scadano lo provano i pgTAP di ciascun runner.
* Lo schema `storico` è fuori: le shadow ricopiano le colonne della madre, e i loro marcatori sono
  una copia, non una promessa. Fuori anche gli schemi di sistema.
* `cleanup_at` si riconosce per **nome**: è il nome fisso della scadenza nel framework, e nessun
  parametro né override lo cambia.

La vista è `security_invoker`: legge il catalogo di PostgreSQL e tabelle di `dbops` senza row level
security, e la risposta non dipende da chi interroga.

---

### Test

* `db/pgtap/dbops/test-marcatori-automazione-senza-esecutore-v1.sql` — sul database nessuna riga
  fuori da `DEBITO_DICHIARATO`; su casi costruiti in uno schema di prova: i tre marcatori fuori
  ambito escono, il trigger a mano basta per `tx_id` e un trigger disabilitato no, una tabella che
  entra nell'ambito esce dal presidio, l'esclusione dalla pulizia lascia scoperto `cleanup_at`, il
  registro rende una riga dichiarata o estinta e rifiuta una ragione corta o un marcatore fuori
  vocabolario; il vocabolario del vincolo del registro è quello che la vista riconosce; lo schema
  `storico` è fuori; i cataloghi di `dbops` scritti dal solo seed non hanno più i marcatori; la
  colonna rinominata con l'override `STORICIZZA_COL` è il marcatore, e la colonna `storicizza` con
  l'override verso un'altra no.

---

### Note di migrazione

* 2026-11-07 — nasce. Lo stesso giorno `shop.ricevute` e `dbops.ai_query_log` entrano nell'ambito e
  `dbops.audit_sources` perde le colonne che nessuno eseguiva; il debito dichiarato sono i cataloghi
  di `dbops` con `tx_id` e senza trigger.
* 2026-11-08 — la colonna di storicizzazione si legge con l'override, come la provision. Lo stesso
  giorno i cataloghi di `dbops` scritti solo dalla migrazione perdono `tx_id`, `data_update` e
  `user_update` (regola in `automazione-db.md` §1.1): il debito dichiarato si estingue e il registro
  resta vuoto.
* 2026-11-08 — l'esclusione dalla pulizia si legge da `dbops.fn_cleanup_esclusa`, la stessa
  funzione del runner, invece che da una copia della sua domanda (`20261109-90`,
  brief-db-revisione-dbops, giro 10b).

---

{% include-markdown "signature-core.md" %}
