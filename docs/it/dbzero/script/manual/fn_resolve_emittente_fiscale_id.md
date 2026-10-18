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

### I modi

| Modo | La colonna contiene | Come si risolve |
| --- | --- | --- |
| `fiscale` | già `emittente_fiscale_id` | si verifica solo che esista |
| `soggetto_ruolo` | `emittente_soggetto_ruolo_id` | via `anagrafiche.emittenti_fiscali` |
| `fattura` | `fattura_id` | via `vendite.fatture` |
| `listino` | `listino_id` | ⭐ *(dal 2026-09-05)* via `vendite.listini`: il valore è l'id del **listino** (la versione ha il suo modo, `listino_versione`) |
| `ente_incasso` | `ente_incasso_id` | ⭐ via il **conto di incasso** (D5) |
| `contabile` | `contabile_id` | ⭐ la distinta, che **sa di chi è** *(dal 2026-09-15: la colonna `emittente_soggetto_ruolo_id`; prima, il suo canale)* |
| `magazzino` | `magazzino_id` | ⭐ *(dal 2026-09-18, Lotto 2 di magazzino)* via `magazzino.magazzini.emittente_fiscale_id`: un salto solo, come `fattura`. È il modo del guard di scope sul **ledger** (`movimenti`, `movimenti_attesi`, `valore_giacenza`), dove la primitiva `SECURITY DEFINER` scavalca la RLS e il perimetro va rimesso da una sede sola |

⭐ **Rev 2026-10-18 — i documenti di vendita** (`20261018-31`, D-3b-2 giro 1b di
`brief-db-plancache-funzioni-con-query-incorporate`). Diciotto modi, una lettura
per chiave ciascuno (le colonne di collegamento sono tutte `NOT NULL`):

| Modo | Il valore è l'id di | Come si risolve |
| --- | --- | --- |
| `ddt`, `ordine`, `preventivo`, `offerta`, `contratto`, `reso` | il documento | la sua colonna `emittente_fiscale_id` |
| `ddt_riga`, `ordine_riga`, `preventivo_riga`, `offerta_eccezione`, `contratto_riga`, `reso_riga` | la riga | dal documento padre |
| `commessa`, `lotto` | la commessa, il lotto di fatturazione | `emittente_soggetto_ruolo_id` → `anagrafiche.emittenti_fiscali` |
| `commessa_attivita`, `attivita_fatturabile` | l'attività | dalla sua commessa |
| `fattura_sdi` | la pratica SDI | dalla sua fattura |
| `listino_versione` | la versione di listino | dal listino padre |

⭐ **Rev 2026-10-18 bis — magazzino, pratiche, documenti** (`20261018-48`, ondata 2):
`asset`, `documento_generato`, `pratica` (la colonna `emittente_fiscale_id`);
`evento_asset` (dall'asset); `inventario`, `movimento`, `rettifica`, `trasferimento`
(dal magazzino; il trasferimento dal magazzino di **partenza**); `flusso` (dalla
pratica).

Li chiedono, **per riga**, le policy ef_whitelist delle tabelle senza colonna
emittente — col perimetro dell'operatore calcolato una volta per istruzione
(vedi [`fn_scope_ef_perimetro`](fn_scope_ef_perimetro.md)) — e gli adattatori
`fn_scope_ef_whitelist_via_*` di vendite, che da `20261018-32` chiedono qui invece
di leggere il padre: la strada documento → emittente è scritta **una** volta.
⚠️ Il prezzo, deciso da Tid (D-3b-2d): la funzione dice di che emittente è un
documento anche a chi non lo vede — l'id dell'azienda, non il documento. Letta
sotto la RLS del padre, ogni riga rieseguiva la policy del padre.

⭐ `ente_incasso` è **D5** in una riga: quando il denaro arriva in banca non ha
ancora una fattura, e il suo padrone lo dice il **conto** su cui il cliente ha
scelto di pagare. ⚠️ La `JOIN` è **interna apposta**: un canale il cui conto non
è intestato a un emittente risolve a `NULL`, e nessuno inventa un padrone.

⭐ **Rev 2026-09-15 — il modo `contabile` legge la colonna.** Fino a quel giorno
risolveva la distinta *per il suo canale*, con la stessa `JOIN` interna: una
distinta **senza canale** — fondo fattura, sistemazione — rispondeva `NULL`
(«non è il canale di nessuno») e la sua testata era visibile a tutti. Dal brief
[distinta-numerata-sul-registro](/dev/work-done/brief-db-distinta-numerata-sul-registro)
la distinta porta `emittente_soggetto_ruolo_id` (`NOT NULL`, risolto in una sede
sola alla nascita: dato, canale, operatore in sessione, o rifiuto), e questo
modo legge quella colonna: **una lettura invece di tre `JOIN`**, e una distinta
interna risponde il **suo** emittente — come il lotto o l'atto da cui nasce.
Chi ne dipende: `fn_scope_ef_whitelist_via_contabile` (le policy di righe e
manifesto dei lotti) e il guard di scope delle righe in modo `contabile`.

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
* [pagamenti.fn_get_emittente_distinta](/dbzero/pagamenti/funzioni/fn_get_emittente_distinta) — il modo `ente_incasso`
* [fn_scope_ef_whitelist_via_contabile](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_contabile)
* le policy ef_whitelist con adattatore (69, `20261018-33`): l'emittente della riga, per riga
* i 21 adattatori `fn_scope_ef_whitelist_via_*` di vendite (`20261018-32`) e i 10 di magazzino, pratiche e documenti (`20261018-49`)
* le policy dell'ondata 2 (`20261018-50`)

{% include-markdown "signature-core.md" %}
