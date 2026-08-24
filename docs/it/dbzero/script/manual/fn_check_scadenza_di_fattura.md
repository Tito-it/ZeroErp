## 📘 Documentazione Concettuale – Funzione `script.fn_check_scadenza_di_fattura`

### 🎯 Scopo Principale

(rev 2026-08-22)

Risponde a **una** domanda di fatto — *«questa rata appartiene a questa
fattura?»* — **fuori dalla row security**.

---

### 🔴 Perché non può farla il guard da solo

`vendite.fatture_scadenze` ha la RLS attiva. Un guard che leggesse le scadenze
sotto RLS **non distinguerebbe due verità opposte**:

| Che cosa è successo davvero | Che cosa vede il guard |
| --- | --- |
| la rata **non appartiene** a quella fattura → è un'incoerenza da rifiutare | `EXISTS` falso |
| la rata **c'è ed è di quella fattura**, ma l'operatore non ha diritto di vederla | `EXISTS` falso |

Rifiutarle con lo stesso messaggio significa **dirne una falsa** in uno dei due
casi. Per questo la domanda di fatto si fa fuori dalla row security.

ℹ️ **Diverso è il caso della chiave esterna**: i controlli di integrità
referenziale PostgreSQL li esegue **già** fuori dalla row security. La FK sa che
la rata **esiste**; questa funzione sa **di chi è**.

### ⚠️ Non allarga nessun perimetro

Risponde un **booleano** su una coppia che il chiamante ha **già nominato**:
nessuna riga esce, nessun elenco si popola, nessun dato della rata viene
raccontato. ⭐ Ed è il motivo per cui il messaggio d'errore del guard porta
l'**id** della rata e non il suo numero e la sua scadenza: raccontarli
disferebbe la ragione per cui la funzione è fatta così.

---

### Regole principali

* `fn_check_*` per convenzione: **verifica e risponde, non solleva**. A decidere
  che farne è il guard che la chiama, che è anche l'unico che sa quale messaggio
  dare all'operatore.
* Su un parametro nullo risponde **NULL**: «la domanda non si pone» non è né
  vero né falso, e chi chiama non la fa mai con un nullo.
* È `STABLE`: legge e basta, e dentro lo stesso statement la risposta non cambia.

### ⚠️ `SECURITY DEFINER`: tre cose da sapere

1. `SET search_path TO 'pg_catalog', 'pg_temp'` è obbligatorio, ed è la forma
   delle altre `SECURITY DEFINER` del progetto (verificato: **zero** senza
   search_path). Da cui gli identificatori qualificati per intero nel corpo;
2. l'**owner** lo riallinea `dbops.fn_sync_functions_owner` in `90_end`
   (`runAlways`): è quello che la rende davvero definer;
3. è l'unica cosa che la distingue da una lettura qualunque — e va tenuta
   piccola apposta: **una domanda, un booleano**.

### Chi la usa

`pagamenti.trgfn_vendite_contabili_righe_guard_rata`, nel ramo della coerenza.

{% include-markdown "signature-core.md" %}
