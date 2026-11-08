## 📘 Documentazione Concettuale – Funzione `vendite.fn_log_pipeline_fase`

> **Ultimo aggiornamento**: 8 novembre 2026

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_log_lotto_esito_fatture](/dbzero/vendite/funzioni/fn_log_lotto_esito_fatture)  
> • [vendite.fn_get_lotto_segnalazioni_summary](/dbzero/vendite/funzioni/fn_get_lotto_segnalazioni_summary)  
> • [script.fn_gruppi_di_commessa_nel_lotto](/dbzero/script/funzioni/fn_gruppi_di_commessa_nel_lotto)  
>
### 🎯 Scopo Principale
(latest review 2026-09-08)  
La funzione **`vendite.fn_log_pipeline_fase()`** inserisce un record nel log
del lotto per registrare l’avanzamento (fase) della pipeline.

⭐ È **l'unico canale** con cui il backend scrive su
`vendite.fatturazione_lotti_log`: tutto ciò che quel registro deve poter
contenere passa da qui, o non ci arriva.

---

### Regole principali

* `lotto_id` obbligatorio.
* `status` ammessi: `I` (info), `W` (warning), `C` (critical).
* `fase` e` testo descrittivo utilizzato dalla dashboard.
* Il log cattura `tipo_lotto` e `stato_operativo` dal lotto al momento dell’inserimento.
* L'orario della riga è `clock_timestamp()` — **l'istante della scrittura**, non
  quello della transazione: la storia di un lotto unisce tre registri i cui
  contatori di riga non sono confrontabili fra loro, e senza orari distinti non
  sarebbe ordinabile.

---

### Di chi è la segnalazione — `p_gruppo_key`

Una segnalazione che riguarda **un documento** lo dichiara, e la dichiarazione
finisce nella **colonna** `gruppo_key`.

| Valore | Significato | Conseguenza |
| --- | --- | --- |
| una chiave di gruppo | la segnalazione è **di quel documento** | smette di bloccare il giro quando quel documento ne esce |
| `NULL` | la segnalazione è **del giro** (emittente non risolto, configurazione mancante) | **blocca**, e non c'è nessun documento da togliere |

⚠️ `NULL` è un valore **dichiarato**, non un'assenza di informazione: una
segnalazione del giro *deve* fermare il giro.

⭐ **Chi non ha il documento ma ha la commessa** — è il caso tipico del pull —
la converte con
[`script.fn_gruppi_di_commessa_nel_lotto`](/dbzero/script/funzioni/fn_gruppi_di_commessa_nel_lotto)
e scrive **una riga per documento**. Se quella risponde `[]`, si scrive **una**
riga con `gruppo_key` a `NULL`: il fallimento c'è stato, e va registrato.

⛔ **Il database non deriva il proprietario da sé.** Lo si potrebbe ricavare da
`meta.context.commessa_id` risalendo alla sorgente ROOT della commessa — cioè
proprio il dato che manca nel fallimento più tipico. Una derivazione che smette
di funzionare esattamente nel caso per cui serve non è una derivazione: è una
trappola. **Lo dichiara chi scrive.**

### La commessa della segnalazione — `p_commessa_id` (2026-11-08)

Il nono parametro, in coda, finisce nella colonna `commessa_id`: **di quale
commessa** parla la segnalazione, accanto a **di quale documento**
(`gruppo_key`). Lo dichiara chi scrive, con lo stesso principio: il pull per
commessa ha la commessa in mano, perché è da lì che ricava i documenti. Serve al
riferimento della scheda Critiche: un documento senza numero (un consumo) si
nomina col codice della commessa **di quel lotto**, anche quando quella
commessa è poi chiusa. Un id assente o `<= 0` diventa `NULL`, senza sollevare.

#### Una stringa vuota è assenza, ma qui costa

`''` o soli spazi vengono normalizzati a `NULL`, e il caso viene **dichiarato**
con un `WARNING`. La colonna ha due stati soli: un terzo passerebbe per «nomina
un documento» — e quella riga bloccherebbe il lotto per sempre, senza che
nessuno possa toglierla perché non c'è nessun documento da togliere.

---

### Il codice errore — `p_error_code`

Finisce invece in `meta->>'error_code'`, e la differenza non è un dettaglio:

| | Dove sta | Perché |
| --- | --- | --- |
| `gruppo_key` | una **colonna** | è un **asse di join**: la leggono il conteggio di `fn_get_lotto_segnalazioni_summary` e il presidio `vw_segnalazioni_con_documento_ignoto`. Un dato su cui si fa `EXISTS` non vive in un jsonb |
| `error_code` | dentro `meta` | è un dato **locale alla riga**, non un asse di ricerca, e le righe già scritte non l'avranno mai — non è ricostruibile dal testo del messaggio |

---

### ⛔ Un log non fallisce, e questo governa due assenze

Non c'è **nessuna** verifica che il codice errore sia a catalogo, né che il
documento dichiarato esista davvero. È deliberato: questa funzione viene
chiamata dentro il ramo `EXCEPTION` di qualcun altro, e fallire lì
sostituirebbe il guasto vero con il proprio.

I due presidi stanno altrove, e guardano senza bloccare:

* `dbops.vw_codici_errore_da_dichiarare` — i codici non registrati;
* [`vendite.vw_segnalazioni_con_documento_ignoto`](/dbzero/vendite/views/vw_segnalazioni_con_documento_ignoto)
  — le segnalazioni vive che nominano un documento che il loro lotto non ha.
  **Invariante: deve restare vuota.**

---

### Output

Nessun output (RETURN void).

---

### Esempio

```sql
-- Una fase del giro
SELECT vendite.fn_log_pipeline_fase(
  p_lotto_id => 123,
  p_stato_doc_fiscale_id => 1,
  p_fase => 'Caricamento lista attivita',
  p_status => 'I'
);

-- Una critica che riguarda UN documento: la si dichiara
SELECT vendite.fn_log_pipeline_fase(
  p_lotto_id   => 123,
  p_stato_doc_fiscale_id => NULL,
  p_fase       => 'Pull commesse',
  p_status     => 'C',
  p_messaggio  => 'Errore emissione commessa 34137',
  p_meta       => '{}'::jsonb,
  p_error_code => 'E_PULL_COMMESSA',
  p_gruppo_key => 'ORDINE_VENDITA:01a06ce4-35a6-721a-9cd8-9da48bf77626',
  p_commessa_id => 34137
);
```

> Piano e decisioni: `docs/it/dev/work-done/brief-db-uscita-documento-dal-giro.md` §6.1.

---

{% include-markdown "signature-core.md" %}
