## 📘 Documentazione Concettuale – Tabella `vendite.famiglie_documento`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
> • [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_registro_documento](/dbzero/vendite/manual/fn_get_registro_documento)
> • [anagrafiche.fn_ba_ha_storia_emittente](/dbzero/anagrafiche/manual/fn_ba_ha_storia_emittente)

---
### 🎯 Scopo Principale
(latest review 31-08-2026)

È l'**elenco dei tipi di documento che prendono il numero da un registro**:
fattura, documento di trasporto, ordine, commessa, reso.

Per ognuno dice **dove vive**: in quale tabella stanno i suoi documenti, come si
chiama la colonna che ne porta il numero, e come si chiama quella che porta il
cliente.

---

### Perché non è un semplice elenco di parole

Sarebbe stato più veloce scrivere quei cinque nomi dentro il campo del registro e
finirla lì. Non basta, e la ragione non è «un domani potrebbero servirne altri».

La ragione è che **un'altra regola deve leggerli**. Un cliente non si sposta da un
emittente a un altro quando ha già un documento numerato: quel numero viene dal
registro di quell'emittente e nessuno lo rifà. Per rispondere «questo cliente ha
già dei documenti numerati?» bisogna guardare in cinque tabelle diverse.

Se quell'elenco di cinque tabelle fosse **ricopiato** dentro la regola, il giorno
in cui un sesto documento entrasse nei registri qualcuno dovrebbe ricordarsi di
aggiungerlo. Chi se ne dimentica non rompe niente: la regola continua a
funzionare, semplicemente **smette di guardare** dove dovrebbe. È il difetto
peggiore, perché non si vede.

⭐ Leggendo l'elenco da qui, il sesto documento entra nella regola **il giorno in
cui si registra la sua famiglia**. Non c'è nessuna copia da tenere allineata,
perché non c'è nessuna copia.

---

### ~~Le due colonne~~ **Le tre colonne** che sembrano ripetute e non lo sono

*(la terza è arrivata il 2026-09-01)*

* **la colonna del numero** non si chiama allo stesso modo dappertutto: è
  *numero* per fattura, documento di trasporto, ordine e reso, ma è *codice* per
  la commessa. È esattamente il genere di dettaglio che non si può indovinare;
* **la colonna del cliente** è obbligatoria su fattura e commessa, mentre su
  documento di trasporto, ordine e reso può mancare. Chi legge deve saperlo, e
  non ha modo di dedurlo;
* ⭐ **la colonna della serie** — `colonna_serie` — che su fattura, documento di
  trasporto e ordine si chiama *serie*, e su reso e commessa **non esiste
  affatto**. Il vuoto qui non è un dato mancante: è la dichiarazione che quella
  famiglia **una serie non ce l'ha**.

#### ⛔ Perché la terza è la più importante delle tre

Le prime due servono a *leggere* il documento. La terza serve a **non
rompere il contatore**.

La serie entra nella chiave del contatore, quindi cambiare la serie di un
registro apre un contenitore nuovo che riparte da 1. Su fattura, documento di
trasporto e ordine è innocuo — la serie è scritta sul documento **e** dentro il
suo vincolo di unicità, quindi i numeri restano distinguibili: è il modo
legittimo di aprire una serie nuova. ⛔ Su reso e commessa no: la serie non la
registrano da nessuna parte, quindi il numero 1 va a sbattere contro uno già
emesso e **il documento non si numera più**.

⇒ Da qui la regola generale, scritta per esteso nella
[guida alla numerazione §8-bis](/guide/numerazione-documenti-e-codici):

> **Tutto ciò che discrimina il contatore deve poter discriminare anche il
> documento.**

⭐ **Ed è il NOME e non un sì/no**, per la stessa ragione delle altre due: un
interruttore «gestisce la serie» acceso su una famiglia la cui tabella non ha la
colonna riporterebbe il difetto senza che nessuno se ne accorga. Col nome, il
controllo automatico verifica che la colonna **esista davvero** e che stia nel
vincolo di unicità del numero.

⚠️ **E un registro di una famiglia senza serie non può averne una**: si rifiuta,
non si ignora. Un campo che si può cambiare e non fa niente è il difetto che il
trasloco del prefisso ha appena finito di togliere.

---

### Cosa qui non c'è, ed è una decisione

Non esiste una casella «questa famiglia blocca lo spostamento del cliente, questa
no». La regola è **categorica**: se un tipo di documento prende il numero da un
registro, quel numero appartiene a un emittente, punto. Una casella che nessuno
avrebbe mai messo a «no» sarebbe una promessa che il resto del programma non
mantiene.

---

### Una famiglia ritirata resta scritta

Si può spegnere una famiglia senza cancellarla, ed è il modo giusto di ritirarla:
la riga resta come traccia del fatto che quel documento è esistito. Una famiglia
spenta può anche nominare una tabella che non c'è più — è storia, non
configurazione — mentre una famiglia accesa **deve** nominare cose che esistono
davvero, e c'è un controllo apposta che se ne accerta.

---

### 🔄 rev 2026-08-31 (sera) — qui vive anche la **forma con cui un registro nasce**

Due colonne nuove, `prefisso_default` e `lunghezza_default`, dicono con che
aspetto nasce un registro di questa famiglia:

| famiglia | prefisso | cifre |
| --- | --- | --- |
| DDT | `DDT` | 7 |
| ORDINE | `ORD` | 7 |
| RESO | `RESO` | 7 |
| COMMESSA | `CMM-` | **9** |
| FATTURA | *nessuno* | 7 |

⭐ **Sono DEFAULT, non il valore effettivo.** Quello vive su
`vendite.registri_fatturazione`, e un sezionale può averlo diverso: è a questo che
serve un sezionale. La divisione è netta — **qui il tipo documento, lì il
sezionale**.

#### ⛔ Perché queste colonne esistono, ed è una storia che vale la pena leggere

Il piano prevedeva di togliere da `config.sistema_codici` le quattro righe dei
documenti traslocati. ⚠️ Ma la funzione che crea i registri di un emittente nuovo
derivava **proprio da lì** prefisso e lunghezza.

⇒ Togliendo le righe, ogni emittente **nuovo** sarebbe nato con registri senza
prefisso e con 7 cifre — la commessa quindi sbagliata, in silenzio. E non si
sarebbe visto quel giorno: si sarebbe visto **al primo emittente creato dopo il
rilascio**, cioè quando nessuno guarda.

⭐ La sede giusta c'era già: questo è il catalogo che dice **cos'è** ogni famiglia,
e prefisso e lunghezza sono proprietà del tipo di documento. Non è stata una
colonna aggiunta per far quadrare un passo: è il posto dove quel dato apparteneva.

⚠️ **Nessun `NOT NULL` sul prefisso:** vuoto è legittimo e significa «nessun
prefisso», come sul registro. La lunghezza invece è `NOT NULL` con default 7, così
non c'è mai un valore assente da interpretare — ed è esattamente l'assenza da
interpretare che ha prodotto il difetto corretto dal changeSet `20260831-55`.

---

### Impatto e Vantaggi

* una sola sede dice quali documenti si numerano sui registri, e tutti la
  leggono;
* aggiungere un tipo di documento è **una riga**, non una caccia ai posti da
  aggiornare;
* il messaggio che spiega perché un cliente non si può spostare usa le parole di
  questa tabella, quindi resta corretto da sé;
* i registri di un emittente nuovo nascono con la forma giusta senza che nessuno
  debba ricordarsene, e **il backfill dei registri monchi legge dalla stessa
  fonte** — così nascita e riparazione non possono divergere.
