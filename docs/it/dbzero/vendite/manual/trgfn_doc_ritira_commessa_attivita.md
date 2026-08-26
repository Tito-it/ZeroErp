## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_doc_ritira_commessa_attivita`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
> • [vendite.commesse_attivita_log](/dbzero/vendite/tabelle/commesse_attivita_log)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_ritira_commessa_attivita_da_sorgente](/dbzero/vendite/funzioni/fn_ritira_commessa_attivita_da_sorgente)  
> • [vendite.trgfn_doc_guard_chiusura_sorgente](/dbzero/vendite/funzioni/trgfn_doc_guard_chiusura_sorgente) — il freno  

---

### 🎯 Scopo Principale
(latest review 26-08-2026)

**Il motore: la porta che si chiude da sola.** Quando un documento entra in uno
stato **abortito**, riprende le righe di commessa che aveva spinto e che nessuno
ha ancora emesso. Trigger **generico**, fase `_z90_`, `AFTER UPDATE OF` sulla
colonna di stato della testata.

---

### ⭐ Perché un trigger e non una chiamata nei servizi

Lo stato di una testata si cambia da **molti** posti — funzioni DB e `UPDATE`
diretti dal backend — e sono destinati a crescere. Con la chiamata esplicita
basta **uno** distratto e il buco torna, silenzioso identico a quello da cui
nasce il cantiere.

⭐ **E l'argomento è nel cantiere stesso.** Il difetto di partenza era nato
esattamente così: la regola *«prima riallinea, poi cancella»* viveva come
**ordine dei passi dentro una funzione**, cioè come **disciplina**. È bastata una
chiave esterna nuova e la disciplina è saltata **senza un errore**, per quattro
settimane. La lezione — *il muro va nella **struttura**, non nel commento* — è la
stessa applicata portando la FK a `NO ACTION`, e vale identica qui.

⭐ **Secondo argomento, sul modello.** La transizione di stato è già
**data-driven** (`config.transizioni_stati_*`): il progetto ha già deciso che
*«cosa può diventare cosa»* è una proprietà del **dato**, non del chiamante. Il
ritiro è la **conseguenza** di quella transizione — metterlo nel chiamante lo
separerebbe dalla cosa che lo causa.

| | chiamata nei servizi | **trigger** |
| --- | --- | --- |
| l'analogia | un promemoria sul foglio delle istruzioni | **la porta che si chiude da sola** |
| ✅ | si vede leggendo il codice | **non si può dimenticare** |
| ⛔ | i punti sono molti e cresceranno | è **azione a distanza** |

---

### ⚠️ E il prezzo si paga col registro

Un trigger che annulla lavoro è **azione a distanza**: chi chiude l'ordine non
vede che sta annullando anche righe di commessa.

Si paga con il **log riga per riga**, che
[`fn_ritira_commessa_attivita_da_sorgente`](/dbzero/vendite/funzioni/fn_ritira_commessa_attivita_da_sorgente)
scrive sempre — altrimenti «il lavoro è sparito» diventa indistinguibile da un
difetto, che è precisamente il male da cui nasce il cantiere.

Il motivo registrato nomina **il documento**, perché è la cosa che chi indaga
cercherà:

```text
Ritiro automatico alla chiusura del documento di origine (ORDINE_VENDITA 2026/41)
```

---

### ⭐ Si aggancia al DATO: `is_abortito`, non `'ANNULLATO'`

Come il freno. Legge il flag dal vocabolario degli stati del documento, quindi un
**secondo stato abortito** sarà coperto da solo.

ℹ️ Interessa **solo l'ingresso** in uno stato abortito: uscirne o restarci non è
una chiusura. ⚠️ Riscrivere lo **stesso** stato non ritira di nuovo — non ci
sono doppioni nel registro, e c'è un test che lo verifica.

---

### ⚠️ Fase `_z90_` e `AFTER`, e non è un dettaglio

* **`_z90_`**: il freno (`_a10_`) e il motore restano **due oggetti diversi**;
* **`AFTER`**: il ritiro deve avvenire **solo se la transizione è passata**. In
  `BEFORE` girerebbe anche quando un guard successivo la rifiuta.

⚠️ I `BEFORE ROW` scattano in ordine **alfabetico**: il nome del trigger è stato
scelto sapendolo, e la fase `_z90_` lo tiene comunque in coda.

---

### Una funzione sola, parametrizzata

| Argomento | Cosa |
| --- | --- |
| `TG_ARGV[0]` | `codice_interno` della sorgente in `config.sorgenti` |
| `TG_ARGV[1]` | nome della colonna di stato sulla testata |
| `TG_ARGV[2]` | tabella del vocabolario degli stati (`schema.tabella`) |

⛔ **Fail-closed** su un trigger montato con un codice sorgente inesistente: deve
**gridare**, non restare inerte. Un ritiro che non ritira è la forma di difetto
che il cantiere chiude.

**Montato su**: `preventivi`, `ordini`, `ddt`, `contratti` — le quattro sorgenti
che spingono davvero, cioè quelle con una `fn_list_*_da_pushare`.
⚠️ `attivita_consumi` **no**: non ha una colonna di stato con vocabolario, ed è
un flusso non ancora acceso. Offerte e resi non spingono.

---

### ⛔ Cosa non raggiunge, ed è giusto

* le righe **`EMESSA`** non arrivano qui: le ferma il **freno**, impedendo la
  chiusura (e la primitiva comunque non le toccherebbe);
* le righe **sourceless** — `ONERE` e `RETTIFICA` — non hanno sorgente. La loro
  via è `fn_annulla_commessa_attivita` e `fn_annulla_accredito_riga_reso`.

ℹ️ **Zero righe ritirate non è un errore**: un documento può non aver mai spinto
niente.

---

### ⚠️ Un effetto che l'operatore deve sapere prima

Chiudere un documento **smette di essere un'operazione locale**: annulla anche
righe di commessa. È un comportamento che va nella guida operativa, non lasciato
scoprire.

⚠️ E `ANNULLATA` è **irreversibile**: riaprire un documento chiuso **non**
riporta indietro le righe. Le rifà il push, e solo se il documento è tornato
spingibile.

---

### Note operative

* La **chiave** passata alla primitiva è `NEW.uid::text` — quella di
  `commesse_attivita`, non quella di `commesse_sorgenti` che varia per sorgente.
* Test: `db/pgtap/vendite/test-ritiro-alla-chiusura-documento-v1.sql` (4..7).
  ⭐ Il **4** fa un `UPDATE` **nudo** sulla testata, senza passare da nessuna
  funzione di dominio: è precisamente il percorso che una chiamata esplicita nei
  servizi non coprirebbe, ed è l'argomento di questa pagina messo alla prova
  invece che dichiarato. Il **6** verifica che le righe di **altri** documenti,
  nella stessa commessa, non siano toccate.
* Cantiere: `brief-db-lavoro-che-non-torna-indietro.md`, lotto L7b / Q-10.

---

{% include-markdown "signature-core.md" %}
