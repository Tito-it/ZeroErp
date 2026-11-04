## 📘 Documentazione Concettuale – Vista `dbops.vw_codici_errore_da_dichiarare`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.codici_errore_senza_policy](/dbzero/dbops/tabelle/codici_errore_senza_policy) — il registro del debito, che è un'altra cosa
> * [config.codici_errore](/dbzero/config/tabelle/codici_errore) — il catalogo dei codici
>
> Approfondimento viste:
>
> * [dbops.vw_codici_errore_argomenti_trigger](/dbzero/dbops/views/vw_codici_errore_argomenti_trigger) — i codici che un trigger passa alla sua funzione
> * [dbops.vw_codici_errore_forme_condizione](/dbzero/dbops/views/vw_codici_errore_forme_condizione) — l'altra lente sui codici, per forma della condizione
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la porta da cui passano i codici sollevati
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — la differenza fra misura e registro

---

### 🎯 Scopo Principale

La misura del «terzo lato» del presidio sui codici errore: ogni codice `E_*` che il codice PL/pgSQL
vivo può nominare, con le funzioni che lo nominano e se una di esse sta sul percorso di una
richiesta. È una misura, non il registro del debito.

> ⛔ **Il numero di questa vista non è il debito.** Cresce a ogni codice nuovo e legittimo. Il debito
> sono le voci di [dbops.codici_errore_senza_policy](/dbzero/dbops/tabelle/codici_errore_senza_policy),
> e il catalogo dei presidi classifica questa vista `CANCELLO`, presidiata da un test del backend.
> Contarla come un registro di debito è un errore di lettura.

I primi due lati del presidio sono dichiarativi: il codice è in catalogo, la frase è nel catalogo
dei messaggi. Il terzo guarda **i corpi delle funzioni**, e risponde a «questo codice qualcuno lo può
sollevare davvero?», l'unica domanda che collega il catalogo al codice. Il cancello del backend la
confronta con le proprie regole di risposta: un codice che il database può sollevare e che il
backend non sa come rispondere è il difetto.

---

### Come si legge

* `da_trigger` — almeno una delle funzioni che nominano il codice è agganciata a un trigger, quindi
  il codice sta sul percorso di una richiesta: è il criterio di priorità.
* `n_funzioni`, `funzioni` — dove compare.

---

### ⭐ È volutamente larga: una scelta fra due errori

Raccoglie **ogni letterale** `E_*` in un corpo PL/pgSQL, non solo quelli dentro una chiamata a
`fn_log_and_raise_error`. Restringere sarebbe stato più preciso, e avrebbe perso i codici che
arrivano **da espressione**: per esempio un guard che delega il verdetto a una funzione di
controllo e solleva il codice del primo motivo che questa gli restituisce.

E raccoglie anche **ogni codice che un trigger passa alla sua funzione come argomento**, letto da
[vw_codici_errore_argomenti_trigger](/dbzero/dbops/views/vw_codici_errore_argomenti_trigger): le
funzioni generiche montate su molte tabelle (il lucchetto di colonna, il blocco dei documenti fuori
bozza) ricevono il codice dal trigger e nel loro testo non lo nominano. Questi codici contano sempre
come `da_trigger`.

Fra i due errori possibili si sceglie quello che **si corregge guardando**: un falso positivo si vede
e si scarta, un codice mancante non si vede affatto.

Dal testo si tolgono i commenti di riga (dal `--` a fine riga), così un codice citato in una nota
non conta.

---

### ⚠️ Che cosa non vede

1. **I codici costruiti per concatenazione** o passati in una variabile: non sono letterali.
2. **I `RAISE EXCEPTION` diretti** che non passano dall'helper: non hanno un codice da trovare.
3. **I codici dentro un commento a blocco**: il testo toglie solo i commenti di riga, quindi un
   codice citato in un commento a blocco conta come nominato.
4. Funzioni che non sono PL/pgSQL.

---

### Legge i cataloghi di sistema

La vista è `security_invoker` e legge solo i cataloghi di sistema: il perimetro è quello dei
privilegi PostgreSQL, non della row level security.

---

### Test

* `db/pgtap/dbops/test-punti-canale-campo-v1.sql` — un codice passato da un trigger alla sua
  funzione come argomento compare qui, come `da_trigger` (caso costruito).

Il cancello vero è `backend/apps/core/tests/test_error_codes_db_policy_guardrail.py`: nessun codice
nuovo senza regola di risposta, nessuna voce del registro già risolta o non più nominata, e la misura
non degradata.

---

### Note di migrazione

* 2026-08-05 — nasce con `brief-db-be-terzo-lato-presidio-codici`.
* 2026-11-03 — legge anche i codici negli argomenti dei trigger (D24 di
  `migliorie-generali-da-test-valutazione`): prima trenta codici dei building block trigger erano
  invisibili qui, e un codice nuovo montato così senza la sua regola non avrebbe fatto scattare il
  cancello.

---

{% include-markdown "signature-core.md" %}
