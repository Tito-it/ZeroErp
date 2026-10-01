## 📘 Documentazione Concettuale – View `dbops.vw_stati_check_scrittori`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.stati_check_dichiarazioni](/dbzero/dbops/manual/stati_check_dichiarazioni)
>
Approfondimenti viste:
>
[dbops.vw_stati_check_da_sanare](/dbzero/dbops/manual/vw_stati_check_da_sanare)

---
### 🎯 Scopo Principale
(latest review 21-09-2026)

Risponde a una domanda sola:

> **C'è uno stato che il database ammette e che nessuno scrive mai?**

Ogni riga è un **valore** ammesso da una colonna di stato, con accanto **chi lo
scrive** e **se qualcuno se n'era già accorto**.

---

### ⭐ Perché serviva, e non bastava guardare

Perché il difetto non fa rumore. Un vincolo che ammette `ERRORE` promette che
il sistema sa dire «è andata male». Se nessuno scrive quel valore, il sistema
non dice niente: le corse chiudono «completate» con un documento rifiutato, e
non c'è un errore, una pagina bianca o un test che diventi rosso da solo. È
successo davvero, per mesi, sugli esiti dei lotti di fatturazione — e il valore
era perfino **nominato** nel riepilogo che lo contava.

---

### ⛔ Il perimetro non è un elenco, ed è tutto il punto

La vista non parte da una lista di tabelle: **ricava il perimetro dai vincoli
dichiarati nel database** — ogni colonna il cui nome dice «stato» e che porta
un vincolo di appartenenza a un elenco chiuso. Una tabella nuova con un
vocabolario chiuso compare qui da sola.

⚠️ Il confine fra uno **stato** e una **classificazione** (il tipo di un lotto,
il canale, la natura di un presidio) è il nome della colonna, ed è una scelta
scritta: un valore mai usato in una classificazione è una configurazione non
ancora esercitata, non un fallimento muto.

---

### Chi conta come «scrittore», e chi no

| Scrittore | Come si vede |
| --- | --- |
| il **valore predefinito** della colonna | lo scrive ogni inserimento che non lo nomina — e rende raggiungibile **solo** quel valore, non gli altri |
| una **funzione** che scrive la tabella | il valore compare nel suo corpo |
| una funzione che **chiama** uno scrittore | il valore compare **dentro la chiamata** — è il caso delle funzioni che ricevono lo stato come parametro |

Il resto **non si vede**, ed è dichiarato: un valore che passa per tre funzioni,
un valore **copiato** da un'altra colonna, e soprattutto **il programma**: metà
degli stati li scrive l'applicazione, e per quelli il database può solo leggere
una dichiarazione (colonna `canale` del registro) che il backend verifica dal
suo lato.

⛔ **Le fixture dei test non contano** (rev 2026-09-23, `20260923-51`). Gli helper
che i test pgTAP usano per costruirsi i dati — le funzioni `fn_pgtap_…` negli schemi
`dbops` e `script` — possono scrivere uno stato, ma non sono il sistema che lo
raggiunge: sono chi lo collauda. Se contassero, una fixture che scrive `ERRORE`
farebbe risultare «scritto» proprio lo stato che il sistema non raggiunge mai. Non
contano né quando scrivono né quando chiamano uno scrittore. Il caso è successo: un
helper che scrive `ATTIVA` sulle versioni di listino aveva reso «estinta» una
dichiarazione che diceva il vero.

---

### Le sei risposte, e come si leggono

| `esito` | Che cosa vuol dire | Che cosa fare |
| --- | --- | --- |
| `SCRITTO` | almeno una funzione lo scrive, direttamente o passandolo | niente |
| `SCRITTO_DA_DEFAULT` | è il valore predefinito della colonna | niente — ma gli **altri** valori della stessa colonna vanno guardati |
| `DICHIARATO_APPLICAZIONE` | lo scrive il programma; il test del backend lo verifica | niente, finché quel test è verde |
| `ESENTE` | nessuna funzione lo scrive, e qualcuno ha scritto perché | niente, per ora: è un lavoro con un nome e una data |
| `NON_DICHIARATO` | nessuno lo scrive e nessuno l'ha guardato | **allarme**: o si scrive chi lo scrive, o si dichiara con la ragione |
| `DEBITO_ESTINTO` | il registro lo nomina, ma il valore è scritto (o non esiste più) | togliere la riga dal registro |

> ⛔ **La regola non è «la vista è vuota».** Oggi 114 valori su 114 hanno una
> risposta, e 40 di questi sono dichiarazioni. La regola è: **niente
> `NON_DICHIARATO` e niente `DEBITO_ESTINTO`** — ed è quello che la vista
> gemella `vw_stati_check_da_sanare` proietta.

---

### ⚠️ Che cosa questa vista NON dice

Che il valore venga scritto **nel momento giusto**. Dice che esiste qualcuno che
lo scrive. Che la macchina degli stati sia corretta lo provano i test di
dominio, uno per famiglia.

⚠️ E la misura stessa ha avuto un difetto, ed è scritto apposta: il primo
conteggio trovava 18 colonne, il criterio definitivo ne trova 32. PostgreSQL
stampa lo stesso vincolo in **due modi** (colonna di testo e colonna a lunghezza
variabile), e la prima ricerca ne vedeva uno solo. Il test tiene l'elenco delle
32 colonne come prova che il perimetro non si restringa di nascosto.

---

### Esempio d'uso

Per capire **come** un valore risulta scritto — quale funzione lo porta —
leggere `scrittori_nomi`; per sapere **dove cercare** sul lato del programma,
`scrittori_tabella` elenca le funzioni che scrivono quella tabella.

```sql
SELECT nome_tabella, colonna, valore, esito, scrittori_nomi
  FROM dbops.vw_stati_check_scrittori
 WHERE nome_tabella = 'fatturazione_lotti_esiti'
 ORDER BY valore;
```

Origine: `docs/it/dev/work-done/brief-db-presidio-stati-mai-scritti.md`.

---

{% include-markdown "signature-core.md" %}
