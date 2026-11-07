## 📘 Documentazione Concettuale – Funzione `script.fn_resolve_emittente_fiscale_id`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.emittente_modi](/dbzero/dbops/tabelle/emittente_modi) — i modi e le loro strade: da lì si genera il corpo di questa funzione
>
> Approfondimento funzioni:
>
> * [script.fn_resolve_emittente_sr_id](/dbzero/script/funzioni/fn_resolve_emittente_sr_id) — il gemello che risponde col soggetto-ruolo
> * [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope) — il guard di scrittura, che la chiama col modo del suo montaggio
> * [script.fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope) — la domanda di permesso, che qui non si fa
> * [script.fn_scope_ef_perimetro](/dbzero/script/funzioni/fn_scope_ef_perimetro) — il perimetro delle policy, che la chiama per riga
> * [dbops.fn_genera_risolutori_emittente](/dbzero/dbops/funzioni/fn_genera_risolutori_emittente) — chi scrive il corpo

---

### 🎯 Scopo Principale

Risponde a **una** domanda di fatto, *«di chi è questa riga?»*, **fuori dalla row security**: dato
un modo e un valore, restituisce l'id dell'emittente fiscale, oppure `NULL` se il riferimento non
porta a nessun emittente.

È la sola strada da una riga al suo emittente: la usano le policy, gli adattatori di scope, il guard
di scrittura e i verbi. Due copie della stessa strada sono il modo in cui un perimetro comincia a
rispondere in modo diverso a seconda di chi chiede.

---

### I modi stanno nel registro

Che cosa vuol dire ogni modo, da quale tabella parte e quali salti fa fino all'emittente, lo dice
**una** riga di [`dbops.emittente_modi`](/dbzero/dbops/tabelle/emittente_modi). Il corpo di questa
funzione lo genera il migrate da quelle righe, un ramo per modo: ⛔ **non si modifica a mano**, il
migrate successivo lo riporterebbe al registro. Un modo nuovo è una riga del seed.

---

### ⭐ Chi risolve non è chi applica

| Domanda | Chi risponde | Sotto RLS? |
| --- | --- | --- |
| «di chi è questa riga», un **fatto** | questa funzione | **no**, e deve saperlo per intero |
| «posso scriverci», un **permesso** | `script.fn_check_user_emittente_scope` | è lei il perimetro |

Il guard di scrittura gira con i permessi di chi scrive. Se leggesse da sé la testata, per un utente
fuori perimetro la testata non ci sarebbe, l'emittente risulterebbe nullo e il guard lascerebbe
passare: si spegnerebbe esattamente nel caso che esiste per coprire. Per questo la lettura sta qui,
`SECURITY DEFINER`.

⚠️ Il prezzo, deciso da Tid: la funzione dice di che azienda è un documento anche a chi non lo vede.
Dice l'id dell'azienda, non il documento.

---

### Regole principali

* ⛔ **Un modo sconosciuto solleva** `E_PARAMETRO_INVALIDO`, con l'elenco dei modi: `NULL` vorrebbe
  dire «nessun padrone, lascia passare», e un refuso in un montaggio spegnerebbe il guard in silenzio.
* Su un valore nullo risponde `NULL` senza sollevare: la domanda non si pone.
* Le strade che passano da una testata usano collegamenti interni: una testata il cui soggetto non è
  (più) un emittente risponde `NULL`, e nessuno inventa un padrone.
* È `STABLE`: legge e basta.

### ⚠️ `SECURITY DEFINER`: la dipendenza che va detta

`search_path` bloccato su `pg_catalog, pg_temp` e nomi qualificati per intero. Gira come
**proprietario**, e le tabelle hanno la row security **abilitata ma non forzata**: il proprietario la
salta. Il giorno in cui arrivasse un `FORCE ROW LEVEL SECURITY` questa funzione tornerebbe a leggere
filtrata, e andrebbe rivista.

---

### Test

`dbops/test-emittente-modi-registro-v1`: il corpo vivo è quello del registro; salti, radici e modo
sconosciuto su tabelle costruite; ogni modo nominato da guard, funzioni e policy è nel registro.

---

{% include-markdown "signature-core.md" %}
