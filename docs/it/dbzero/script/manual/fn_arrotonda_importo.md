## ⚙️ Documentazione Concettuale – Funzione `script.fn_arrotonda_importo`

> **Versione**: 2026-07-28 (brief-fix-importi-riga-fattura-zero §4.1 ·
> migration `20260728-08`, vocabolario unificato dal `20260728-07`)

> **Vedi anche**
>
[vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe) — l'importo di riga
> [vendite.articolo_regole_fatturazione](/dbzero/vendite/tabelle/articolo_regole_fatturazione) — decimali e metodo per articolo
> [anagrafiche.emittenti_fiscali_utilities](/dbzero/anagrafiche/tabelle/emittenti_fiscali_utilities) — decimali e metodo del totale a pagare

---

### 🎯 Scopo Principale

Arrotondare un importo secondo i **decimali** e il **metodo** configurati, in
**un punto solo** per tutto il database.

Nasce quando il secondo consumatore si affaccia: il `CASE` con i metodi viveva
inline dentro `vendite.fn_ricalcola_totali_fattura`, e il trigger sull'importo di
riga avrebbe dovuto o richiamarlo o riscriverlo — e riscriverlo significa due
copie della stessa regola fiscale destinate a divergere.

---

### Il vocabolario, che prima era tre

Estraendo la funzione è emerso che il metodo di arrotondamento era configurabile
in **quattro punti** del modello, e ogni punto ammetteva un insieme **diverso** di
valori. In comune ce n'era **uno solo** (`HALF_UP`).

Il `20260728-07` ha unificato tutto sul vocabolario di
`emittenti_fiscali_utilities`, che è quello che questa funzione implementa:

| Metodo | Comportamento | Esempio a 2 decimali |
|---|---|---|
| `UP` | allontana da zero | `2.001 → 2.01` · `-2.001 → -2.01` |
| `DOWN` | avvicina a zero | `2.009 → 2.00` · `-2.009 → -2.00` |
| `HALF_UP` | sul mezzo allontana da zero | `2.005 → 2.01` · `-2.005 → -2.01` |
| `HALF_DOWN` | sul mezzo avvicina a zero | `2.005 → 2.00` · `-2.005 → -2.00` |

Sono spariti `CEIL`/`FLOOR` — sui valori non negativi, cioè la totalità dei casi
di fatturazione, coincidono con `UP`/`DOWN` — e `HALF_EVEN`, che era **ammesso in
due tabelle ma non implementato da alcuna funzione**: una promessa scritta nel
CHECK e mai mantenuta.

Il comportamento sui **negativi** è quello del `CASE` inline che la funzione
sostituisce (`ceil`/`floor` sull'assoluto col segno riapplicato): nessun risultato
preesistente è cambiato.

---

### ⚠️ Nessun default silenzioso

Un metodo non riconosciuto **solleva** `E_PARAMETRO_INVALIDO`.

Il `CASE` inline aveva invece un `ELSE` che assorbiva qualunque valore ignoto in
`HALF_UP`: con un refuso in configurazione l'importo sarebbe risultato comunque
«giusto», e nessuno se ne sarebbe accorto. Un helper fiscale non deve indovinare.

---

### Contratto

* **`STRICT`**: `NULL` in ingresso → `NULL` in uscita. Guardare i parametri spetta
  ai chiamanti, che già lo fanno — `fn_ricalcola_totali_fattura` solleva
  `E_CONFIG_MANCANTE` se mancano i decimali dell'emittente, il trigger di riga
  applica i default `2 / HALF_UP` delle regole articolo.
* **`VOLATILE`** (non `IMMUTABLE`): l'errore passa dal canale di log. Non serve
  immutabile — il consumatore è un trigger, non un indice né una colonna generata.
* `p_decimali` negativo → solleva.

---

### ⚠️ Due arrotondamenti diversi, da non confondere

Questa funzione è il **meccanismo**; la **politica** è di chi la chiama, e sono
due politiche distinte:

| Cosa si arrotonda | Configurazione | Chi decide |
|---|---|---|
| Importo di **riga** | `vendite.articolo_regole_fatturazione` (per **articolo**) | trigger sulla riga di fattura |
| **Totale a pagare** | `anagrafiche.emittenti_fiscali_utilities` (per **emittente-utility**) | `fn_ricalcola_totali_fattura`, con saldo riportato fra documenti |

Unificarle sarebbe un errore: la prima riguarda quanto vale una riga, la seconda
quanto il cliente deve pagare.

---

### Nota di adozione

`vendite.fn_ricalcola_totali_fattura` **non è ancora stata allineata** a questa
funzione: continua a usare il proprio `CASE` inline. È una scelta — sostituire un
blocco funzionante dentro una funzione fiscale già testata sarebbe rischio senza
guadagno. L'allineamento va fatto quando quella funzione verrà toccata per motivi
suoi.
