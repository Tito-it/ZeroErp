## 📘 Documentazione Concettuale – Funzione `dbops.fn_check_funzioni_riferimenti_morti`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.riferimenti_morti_esenzioni](/dbzero/dbops/tabelle/riferimenti_morti_esenzioni) — il registro del debito che si confronta con questa misura
>
> Approfondimento viste:
>
> * [dbops.vw_riferimenti_morti_da_sanare](/dbzero/dbops/views/vw_riferimenti_morti_da_sanare) — i difetti non coperti dal registro
> * [dbops.vw_riferimenti_morti_rientrati](/dbzero/dbops/views/vw_riferimenti_morti_rientrati) — le voci del registro di troppo
>
> Approfondimento funzioni:
>
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio del digest, che la fa girare come proprietario
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — misura e registro

---

### 🎯 Scopo Principale

Compila con `plpgsql_check` ogni funzione PL/pgSQL del database che non appartiene a
un'estensione, e classifica i difetti trovati: è la misura unica dei riferimenti morti, letta dal
guardrail della CI, dal pgTAP, dallo strumento a mano e dalle due viste del presidio.

Il problema è specifico di PL/pgSQL: il corpo di una funzione **non viene validato alla
creazione**. Una funzione che nomina una colonna inesistente si crea senza un fiato, e il difetto
si manifesta solo quando quel ramo viene percorso — spesso il ramo d'errore, cioè proprio quando
servirebbe funzionare.

---

### ⭐ Le trigger function si validano contro ogni tabella su cui sono agganciate

`NEW` e `OLD` non hanno un tipo finché non si sa su quale tabella il trigger è montato: la stessa
trigger function agganciata a due tabelle si controlla due volte, una per tabella. Da qui la classe
`ORFANA`: una trigger function senza trigger non è validabile affatto, ed è già di per sé un
residuo.

---

### Le otto classi

| Classe | Significato | Nella lista di lavoro |
| --- | --- | --- |
| `REALE` | riferimento morto vero, da sanare | sì |
| `ORFANA` | trigger function senza trigger: non validabile | sì |
| `NON_MISURATO` | ⛔ **non si è potuto controllare**: `plpgsql_check` ha sollevato invece di rispondere | sì |
| `FP_RAMO_ALTRA_TABELLA` | l'errore compare solo su alcune delle tabelle del trigger: è il ramo dedicato a un'altra | no |
| `FP_TRANSITION_TABLE` | la relazione mancante è una tabella di transizione del trigger, che esiste solo durante lo scatto | no |
| `FP_SQL_DINAMICO` | errore di sintassi dentro un `EXECUTE`: SQL costruito a runtime, con segnaposto | no |
| `FP_VARIADIC` | funzione non trovata, ma la chiamata è a un `VARIADIC "any"` con soli tipi testuali | no |
| `FP_DEFINER_PRIVILEGIO` | permesso negato dentro una `SECURITY DEFINER` misurata da chi non ne è il proprietario né membro del suo ruolo | no |

⛔ **`NON_MISURATO` non è un difetto e non è un falso positivo: è l'assenza di una misura**, e chi
la consuma la tratta come un rosso. È la differenza fra «non ho trovato difetti» e «non ho potuto
guardare», la più pericolosa che un presidio possa confondere. Per questo la lista di lavoro la
include: filtrarla la farebbe tornare vuota proprio quando nessuno ha guardato.

⭐ **I falsi positivi sono classificati, non nascosti.** Un filtro li farebbe sparire anche quando
smettono di essere falsi; una classe li tiene visibili e dice perché si ignorano. La funzione
restituisce tutto.

⚠️ `FP_VARIADIC` esiste per una sola forma, il `VARIADIC "any"`: è l'unica che ammette zero
argomenti variadici. Fra le funzioni del progetto non ce n'è nessuna, e la classe resta vuota: è il
risultato giusto. Due strette successive l'hanno portata qui perché una regola troppo larga aveva
scusato due argomenti invertiti.

⚠️ `FP_DEFINER_PRIVILEGIO`: il corpo di una `SECURITY DEFINER` gira con i privilegi del
proprietario, quindi «il chiamante può risolvere il riferimento?» è la domanda sbagliata. Quella
giusta la fanno gli altri occhi del presidio (il digest come proprietario, il guardrail della CI da
superuser). Chi è proprietario e prende lo stesso un permesso negato resta `REALE`.

---

### Perimetro

Solo funzioni PL/pgSQL, esclusi `pg_catalog`, `information_schema`, gli schemi `pg_*` e tutto ciò
che appartiene a un'estensione (PostGIS, topology, pgAgent): non è codice mantenuto qui.

---

### ⛔ Il `search_path` è pinnato, e non è una questione di stile

La funzione dichiara `pg_catalog, public, pg_temp`, e la chiamata a `plpgsql_check_function` è
qualificata con `public`. Sono due strati della stessa cosa, e servono entrambi:

| che cosa risolve | che cosa succede senza `public` |
| --- | --- |
| la chiamata a `plpgsql_check_function` (l'estensione sta in `public`) | non si risolve, il gestore d'eccezione lo scrive come misura fallita, e **ogni** funzione esce `NON_MISURATO` |
| i riferimenti dentro le funzioni che si compilano | `unaccent`, `dblink`, il tipo `geometry` sono nominati senza schema, come è normale: funzioni sane escono `REALE` |

`public` non è arbitrario: è nel `search_path` reale dell'applicazione, e una misura di riferimenti
morti è fedele solo se compila nel contesto in cui quelle funzioni girano davvero. Senza il pin la
funzione eredita il path di chi la chiama — e il digest la chiama da una `SECURITY DEFINER` con un
path stretto.

⚠️ Chi rifà questa funzione tenga la clausola `SET`: un `CREATE OR REPLACE` che la perde non
fallisce, riporta il presidio a mentire. È la stessa trappola di `security_invoker` su
`CREATE OR REPLACE VIEW`. La prende solo il test del pgTAP che conta attraverso il digest.

---

### ⚠️ È costosa, e usa una tabella temporanea

Gira `plpgsql_check_function` su ogni funzione, moltiplicata per le tabelle agganciate: va bene in
un guardrail, in un test o nel digest settimanale, mai in un percorso frequente.

Usa una tabella temporanea d'appoggio, creata se manca, svuotata in testa e cancellata al commit.
Due chiamate nella stessa istruzione non si pestano (il risultato si materializza prima di essere
usato), ma il controllo gira due volte. ⚠️ Una chiamata da una `SECURITY DEFINER` e una dal ruolo
corrente nella stessa sessione invece **non convivono**: la tabella appartiene al ruolo che l'ha
creata, e chi chiama per secondo prende un permesso negato. Un test che fa entrambe le letture
cancella la tabella fra le due.

---

### Consumatori

* `scripts/sql/guardrail_riferimenti_morti.sql` — il cancello della CI, dopo il migrate di Django
  (le funzioni devono essere già nel database). Si ferma per primo su `NON_MISURATO`.
* `scripts/sql/check_funzioni_riferimenti_morti.sql` — lo strumento da lanciare a mano.
* le due viste del presidio, e attraverso la lista di lavoro il digest settimanale, che la fa girare
  come proprietario.

⚠️ Il verdetto dipende dal ruolo che misura: lo strumento a mano va lanciato con il ruolo che il
difetto lo subisce, l'applicazione.

---

### Test

* `db/pgtap/dbops/test-riferimenti-morti-v1.sql` — l'estensione c'è e ha potuto controllare ogni
  funzione; nessun difetto fuori dal registro e nessuna voce rientrata; ogni voce ha un motivo;
  nessun riferimento morto nei dati di configurazione; il conteggio del digest concorda con la
  misura diretta; un permesso negato dentro una `SECURITY DEFINER` di un altro proprietario non è
  mai `REALE`; l'esenzione legata a pgAgent c'è solo dove pgAgent manca.

---

### Note di migrazione

* 2026-08-04 — nasce con `brief-db-bonifica-riferimenti-morti` §5: il 2026-03-31 due funzioni morte
  erano state viste e lasciate lì, e cinque mesi dopo una ha fatto fallire un migrate.
* 2026-08-05 — `FP_VARIADIC` ristretto al solo `VARIADIC "any"`, su segnalazione del backend.
* 2026-09-10 — nasce `NON_MISURATO`: prima una misura fallita cadeva nell'ultimo ramo e usciva
  `REALE` (su dbdev 779 righe su 780 funzioni, con due voci nel registro).
* 2026-09-12 — `search_path` pinnato (`brief-db-un-destinatario-per-i-presidi` §13.2): il digest
  riferiva 784 «riferimenti morti» mentre la lettura diretta ne dava zero.
* 2026-09-14 — nasce `FP_DEFINER_PRIVILEGIO`: la stessa funzione usciva `REALE` letta
  dall'applicazione e pulita letta dal proprietario, e una voce del registro risultava insieme
  necessaria e di troppo.

---

{% include-markdown "signature-core.md" %}
