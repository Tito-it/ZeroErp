## 📘 Documentazione Concettuale – Tabella `dbops.stati_check_dichiarazioni`

> 👀 **Vedi anche**
>
**Approfondimento viste:**
>
• [dbops.vw_stati_check_scrittori](/dbzero/dbops/manual/vw_stati_check_scrittori)
• [dbops.vw_stati_check_da_sanare](/dbzero/dbops/manual/vw_stati_check_da_sanare)
>

### 🎯 Scopo Principale
(latest review 21-09-2026)

L'elenco dei valori di una colonna di stato che il controllo automatico **non
trova scritti** da nessuna funzione del database, ognuno con scritto accanto
**chi lo scrive davvero** o **perché resta così**.

Non è una lista di eccezioni concesse. Una riga qui dice una di due cose:
*«questo valore lo scrive il programma, non il database — e il programma lo
verifica»*, oppure *«questo valore non lo scrive nessuno, sappiamo perché, e
chi lo farà»*. Non dice mai *«va bene così»*.

---

### ⭐ Perché il registro ha un `canale`

Il database vede solo una parte di chi scrive: il valore predefinito di una
colonna, una funzione che scrive la tabella, una funzione che chiama quella
funzione. **Non vede il programma** — e una buona metà degli stati la scrive
proprio il programma (la coda dei lavori, le chiavi di idempotenza, le bozze
delle email).

Se quei valori finissero qui come «esenti», nessuno potrebbe mai accorgersi del
giorno in cui il programma smette di scriverli. Per questo la riga porta il
**canale**, cioè chi la verifica:

| `canale` | Che cosa dichiara | Chi controlla che sia ancora vero |
| --- | --- | --- |
| `APPLICAZIONE` | il valore lo scrive un modulo del programma (anche passandolo a una funzione del database) | il **test del backend**: il valore deve comparire in un file che scrive quella tabella; se sparisce, il test è rosso |
| `ESENTE` | il criterio non lo vede — è un cantiere aperto, una tabella senza scrittori, o un valore **copiato** da un'altra colonna | il **controllo del database**: se una funzione comincia a scriverlo, la riga non serve più e va tolta |

⚠️ `ESENTE` non vuol dire «non scritto». Il caso che l'ha insegnato: il diario
delle fasi di un lotto riceve lo stato **copiandolo** dal lotto stesso, senza
che il valore compaia mai scritto in una funzione. È scritto migliaia di volte,
e il criterio non lo vede. Stringere il vincolo — la prima idea — avrebbe rotto
il diario.

---

### ⚠️ È un debito, quindi deve calare

Ogni riga `ESENTE` ha una data, e una riga ferma da mesi è un'informazione, non
un dettaglio. E quando un lavoro è finito, **la riga va tolta**: una riga rimasta
dopo la riparazione continuerebbe a far tacere il controllo su quel valore. Il
controllo se ne accorge da solo e lo segnala (`DEBITO_ESTINTO`).

---

### Campi chiave

* `schema_tabella` / `nome_tabella` / `colonna` / `valore`: **il singolo
  valore**, non la colonna. Dichiarare «questa colonna la scrive il programma»
  nasconderebbe esattamente il caso per cui il controllo esiste — un valore
  solo, in una colonna per il resto scritta bene, che nessuno scrive;
* `canale`: chi verifica la riga (sopra);
* `ragione`: per `APPLICAZIONE` quale modulo scrive il valore; per `ESENTE` che
  cosa manca perché venga scritto, o perché il criterio non lo vede, e dove
  vive quel lavoro. ⛔ Non un'etichetta e non un rimando nudo;
* `data_registrazione`: da quando la riga è dichiarata.

---

### Le famiglie di oggi, per capire di che cosa si parla

Le righe `APPLICAZIONE` sono il ciclo di vita delle **code** (lavori, stampe,
esiti dei lotti), delle **bozze email**, delle **versioni di listino** e dei
documenti interni di **magazzino** annullati dall'operatore.

Le righe `ESENTE` sono di quattro specie: tre stati del **documento generato**
che nessun verbo scrive ancora (annullato, archiviato, e l'esito negativo della
generazione — il caso più simile a quello originale); gli stati che il motore
di **magazzino** scriverà quando sarà finito; i quattro stati dei **mandati
SEPA**, una tabella che oggi nessuno scrive; e lo stato del diario di lotto
**copiato** dal padre.

Origine: `docs/it/dev/work-done/brief-db-presidio-stati-mai-scritti.md`.

---

{% include-markdown "signature-core.md" %}
