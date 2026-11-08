## 📘 Documentazione Concettuale – Funzione `maintenance.fn_sveglia_accesa`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il catalogo: canale, default di accensione per ambiente, spegnibile, accendibile in produzione
> * [dbops.processi_accensione](/dbzero/dbops/tabelle/processi_accensione) — la scelta a mano
> * [dbops.installazione](/dbzero/dbops/tabelle/installazione) — l'ambiente dichiarato dell'installazione
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il panorama, che dice `SPENTO` dal catalogo
>
> Approfondimento funzioni:
>
> * [dbops.fn_processo_acceso_su_valori](/dbzero/dbops/funzioni/fn_processo_acceso_su_valori) — la regola dell'accensione
> * [dbops.fn_processo_acceso_dichiarato](/dbzero/dbops/funzioni/fn_processo_acceso_dichiarato) — la lettura per chi descrive, che non solleva
> * [dbops.fn_accensione_a_mano_ammessa_su_valori](/dbzero/dbops/funzioni/fn_accensione_a_mano_ammessa_su_valori) — il divieto di accensione in produzione
> * [script.fn_ambiente_installazione](/dbzero/script/funzioni/fn_ambiente_installazione) — il lettore dell'ambiente che solleva
>
> Guide:
>
> * [Processi pgAgent funzionali](/guide/processi-pgagent-funzionali) — i lavori a orario e la loro sveglia

---

### 🎯 Scopo Principale

Risponde a una domanda sola: la sveglia di questo processo deve far partire il lavoro?
`true` o `false`, mai `NULL`: ciò che non si sa decidere è un errore.

È la lettura per **chi decide**. Chi descrive — il panorama dei processi — usa
`dbops.fn_processo_acceso_dichiarato`, che non solleva e risponde `NULL` dove non si sa.

---

### Chi la chiede

* **Il passo di ogni job pgAgent** di un processo con sveglia. Il passo chiede alla sveglia
  col proprio codice di processo e, solo se la risposta è `true`, chiama la procedura del job.
  Da spento il lavoro non parte e il giornale non scrive niente: il panorama dice `SPENTO`
  dal catalogo, non da una corsa. I passi, già avvolti, si leggono in
  [Job pgAgent](/dbzero/maintenance/job_pgagent).
* **Le sveglie systemd dei comandi del backend**, e «Esegui ora», che su un processo spento
  non parte.

⛔ **Non la chiede la convergenza del rilascio**: quella chiama le procedure strutturali
sempre. Spegnere ferma la sveglia notturna, non l'aggiornamento: un rilascio lascia il
database completo.

---

### La regola sta altrove: qui i `NULL` diventano errori

La regola dell'accensione ha **una** sede, `dbops.fn_processo_acceso_su_valori`, e si legge
in quest'ordine:

1. un processo senza sveglia (canale `CODA`, o ritiro raggiunto secondo `script.fn_e_obsoleto`)
   non ha risposta; un ritiro programmato risponde fino al suo giorno;
2. un processo **non spegnibile** è acceso sempre, senza leggere né la scelta a mano né
   l'ambiente: un'installazione non ancora dichiarata non ferma i processi che non devono
   fermarsi mai;
3. una **scelta a mano** decide, se il divieto di accensione in produzione la ammette
   (`dbops.fn_accensione_a_mano_ammessa_su_valori`); una scelta non ammessa si ignora;
4. altrimenti vale il **default del catalogo** per l'ambiente dichiarato, sviluppo o
   produzione;
5. con l'ambiente non dichiarato la risposta non si sa decidere.

Questa funzione legge il processo, rifiuta i casi senza sveglia, chiede la risposta a
`dbops.fn_processo_acceso_dichiarato` e, se è `NULL`, la trasforma nell'errore giusto: prima
chiede l'ambiente a `script.fn_ambiente_installazione`, che solleva se non è dichiarato; se
l'ambiente c'è, il buco è nel catalogo.

⚠️ Una scelta a mano non decide sempre senza ambiente. Spegnere, o accendere un processo
accendibile in produzione, si decide anche senza sapere dove si è. Accendere a mano un processo
**non accendibile in produzione** no: il divieto non sa dire se vale, la scelta non conta, e
senza ambiente la sveglia risponde `E_CONFIG_MANCANTE`. In produzione, la stessa scelta si
ignora e vale il default di produzione.

---

### ⭐ Una porta stretta, `SECURITY DEFINER`

pgAgent si collega come `zeroerp_job`, che chiama solo le procedure dei job e non legge
`dbops`. La funzione gira coi privilegi del proprietario, e la porta è stretta: un codice in,
un booleano fuori.

---

### Codici errore

| Caso | Codice |
| --- | --- |
| codice di processo inesistente | `E_PROCESSO_NON_TROVATO` |
| processo senza sveglia (`CODA`, o ritiro raggiunto) | `E_PROCESSO_SENZA_SVEGLIA` |
| ambiente non dichiarato, senza una scelta a mano che decida da sola | `E_CONFIG_MANCANTE` (da `script.fn_ambiente_installazione`) |
| scelta a mano di accensione non ammessa dal divieto, con l'ambiente non dichiarato | `E_CONFIG_MANCANTE` |
| ambiente dichiarato, ma il catalogo non ha il default di accensione | `E_CONFIG_MANCANTE` |

L'ultimo caso è una difesa: il CHECK `chk_processi_accensione` del catalogo pretende i default
su ogni processo con sveglia.

---

### Test

* `db/pgtap/dbops/test-processi-accensione-v1.sql` — la forma (`SECURITY DEFINER` con
  `search_path` fissato, eseguibile da `zeroerp_job`), la regola sui valori ramo per ramo
  (compresa la scelta non ammessa con l'ambiente non dichiarato, test 41), la sveglia di un
  non spegnibile, i due rifiuti, e la sveglia che segue lo spegnimento a mano.
* `db/pgtap/dbops/test-installazione-ambiente-v1.sql` — con l'ambiente non dichiarato
  costruito: lo spegnibile senza scelta solleva `E_CONFIG_MANCANTE`, il non spegnibile risponde
  `true`, la scelta a mano decide; e il cancello dei passi pgAgent (ogni passo chiede alla
  sveglia col proprio codice, nessun passo avvolto due volte, un processo spento non scrive nel
  giornale).
* `db/pgtap/dbops/test-processi-accensione-produzione-v1.sql` — in produzione costruita, una
  riga accesa a mano di un processo non accendibile non accende: la sveglia dice `false`.
* `db/pgtap/dbops/test-processo-vivo-v1.sql` — un ritiro programmato risponde, un ritiro
  raggiunto oggi dà `E_PROCESSO_SENZA_SVEGLIA`, anche con `attivo` falso conta solo la data.

---

### Note di migrazione

* 2026-10-16 — nasce con l'accensione dei processi per ambiente, insieme al cancello che
  avvolge i passi pgAgent (`brief-db-processi-accensione-per-ambiente`).
* 2026-10-18 — la regola ignora la scelta a mano che il divieto di accensione in produzione
  non ammette.

---

{% include-markdown "signature-core.md" %}
