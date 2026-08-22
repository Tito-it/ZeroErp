## 📘 Documentazione Concettuale – Funzione `script.fn_resolve_emittente_fiscale_id`

### 🎯 Scopo Principale

(rev 2026-08-22)

Risponde a **una** domanda di fatto — *«di chi è questa riga?»* — **fuori dalla
row security**, e risponde con un id di emittente fiscale. Nient'altro.

⭐ È la **sede unica** della catena che porta da un riferimento al suo emittente.
Prima quella catena era scritta dentro il guard di scrittura; oggi la usano sia
il guard sia gli adapter di lettura, e questo è il punto: **due copie della
stessa catena sono il modo in cui un perimetro comincia a rispondere in modo
diverso a seconda di chi chiede.**

---

### 🔴 Il difetto che chiude, e perché era il peggiore possibile

`script.trgfn_guard_emittente_scope` presidia la scrittura di **dodici** tabelle.
Risolveva l'emittente da sé e, se non ci riusciva, **lasciava passare**:

```sql
IF v_emittente_fiscale_id IS NULL THEN
    RETURN NEW;   -- «emittente non risolvibile»
END IF;
```

Quel ramo era pensato per i **dati non ancora collegati**. Ma il guard è
`SECURITY INVOKER`, e nel modo `fattura` leggeva `vendite.fatture` — che **ha la
row security accesa**. Per un utente fuori perimetro quella lettura restituisce
**zero righe**, l'emittente resta `NULL`, e il guard **lascia passare**.

> 🔴 Il guard che deve impedire di scrivere sui documenti di un altro emittente
> **si spegneva esattamente quando il documento era di un altro emittente**. Non
> un buco residuo: un buco che si apre **solo nel caso che il guard esiste per
> coprire**.

⚠️ E la chiave esterna non si opponeva: i controlli di integrità referenziale
PostgreSQL li esegue **già** fuori dalla row security, quindi la riga entrava. La
vedeva poi il proprietario del documento, come sua.

---

### ⭐ La distinzione portante: chi RISOLVE non è chi APPLICA

| Domanda | Chi risponde | Sotto RLS? |
| --- | --- | --- |
| «di chi è questa riga» — un **fatto** | questa funzione | **no**, e deve saperlo per intero |
| «posso scriverci» — un **permesso** | `fn_check_user_emittente_scope` | è lei il perimetro |

Chiedere entrambe allo stesso lettore fa dare la risposta sbagliata alla prima.
⭐ È la stessa mossa già fatta per le rate con
[fn_check_scadenza_di_fattura](/dbzero/script/funzioni/fn_check_scadenza_di_fattura).

---

### I cinque modi

| Modo | La colonna contiene | Come si risolve |
| --- | --- | --- |
| `fiscale` | già `emittente_fiscale_id` | si verifica solo che esista |
| `soggetto_ruolo` | `emittente_soggetto_ruolo_id` | via `anagrafiche.emittenti_fiscali` |
| `fattura` | `fattura_id` | via `vendite.fatture` |
| `ente_incasso` | `ente_incasso_id` | ⭐ via il **conto di incasso** (D5) |
| `contabile` | `contabile_id` | ⭐ la distinta, poi il suo canale |

⭐ Gli ultimi due sono **D5** in una riga: quando il denaro arriva in banca non ha
ancora una fattura, e il suo padrone lo dice il **conto** su cui il cliente ha
scelto di pagare. Sono due e non uno perché i due presidi partono da due colonne
diverse: la **testata** conosce il proprio canale, la **riga** conosce solo la
testata.

⚠️ Le `JOIN` di quei due modi sono **interne apposta**: una distinta **senza
canale** — fondo fattura, compensazione, che nascono così per disegno — risolve a
`NULL`, e il guard la lascia stare. È giusto: una distinta interna non è il
canale di nessuno, e pretendere un perimetro da lì rifiuterebbe **la prima riga
scritta dalla pipeline dei fondi**.

---

### Regole principali

* ⛔ **Un modo sconosciuto solleva**, non restituisce `NULL`: `NULL` significa
  «lascia passare», e un errore di battitura in un `CREATE TRIGGER` spegnerebbe
  il guard **in silenzio**. Codice `E_PARAMETRO_INVALIDO`.
* Su un valore nullo risponde `NULL` senza sollevare: la domanda non si pone, e i
  chiamanti escono prima.
* È `STABLE`: legge e basta.

### ⚠️ `SECURITY DEFINER`: la dipendenza che va detta

`SET search_path TO 'pg_catalog', 'pg_temp'` obbligatorio, identificatori
qualificati per intero. Ma soprattutto:

> ⚠️ Gira come **proprietario**, e le tabelle di questo database hanno la RLS
> **abilitata ma non forzata**: il proprietario la salta. Il giorno in cui arriva
> un `FORCE ROW LEVEL SECURITY` — l'ondata coordinata di cui parlano i changeSet
> della RLS — questa funzione **va rivista**, perché tornerebbe a leggere
> filtrata. Vale identico per `fn_check_scadenza_di_fattura`.

⭐ È anche la ragione per cui il pgTAP del perimetro incassi **non usa il
`FORCE`** locale alla transazione e gira invece come utente applicativo: con il
`FORCE`, questa funzione rientrerebbe sotto la policy della tabella che sta
leggendo e nascerebbe una **ricorsione**.

### Chi la usa

* [trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope) — tutti e cinque i modi
* [fn_scope_ef_whitelist_via_ente_incasso](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_ente_incasso)
* [fn_scope_ef_whitelist_via_contabile](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_contabile)

{% include-markdown "signature-core.md" %}
