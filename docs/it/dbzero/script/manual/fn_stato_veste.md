## 📘 Documentazione Concettuale – Funzione `script.fn_stato_veste()`

> 👀 **Vedi anche**
>
> [anagrafiche.vw_accessi_altri](/dbzero/anagrafiche/views/vw_accessi_altri) ·
> [config.token_monouso](/dbzero/config/tabelle/token_monouso)

### 🎯 Scopo

(02-10-2026 — brief `brief-db-be-fe-area-accessi`, A-7)

**Lo stato di una veste, calcolato solo a DB.** Lo leggono la vista degli «Altri accessi» e
lo stato accessi della scheda di cliente e fornitore, che fino a quel giorno lo calcolava
il backend. La regola è quella del backend, portata com'era:

| Stato | Quando |
| --- | --- |
| `ATTIVO` | la veste è accesa |
| `PENDING` | spenta, con un invito pendente, e l'email di **quel** token è partita (`invito_inviato_at >=` emissione: le due cose possono stare nello stesso `now()`) |
| `NON_SPEDITO` | spenta, con un invito pendente, ma l'email di quel token non è partita |
| `DISATTIVO` | spenta, nessun invito pendente |

Restituisce anche `token_scade_at`, la scadenza del token pendente più lontano (`NULL` se
non ce n'è): la scheda la usa per «scade tra N ore».

* **Invito pendente** = un token di `config.token_monouso` non usato e non scaduto che porta
  nel meta l'`identita_id` della veste. Il token della **veste**, non della credenziale:
  cliente e fornitore portale della stessa persona condividono i tipi di token.
* ⚠️ Il backend filtrava anche il **tipo** del token; qui no, perché l'`identita_id` nel
  meta lo scrive solo l'emissione di un invito. È il punto da guardare se un giorno un token
  che non è un invito lo porterà.
* `NESSUNO` (nessuna veste) non è uno stato di una veste: resta a chi cerca la veste.
* Zero righe per un id assente: è la chiave di un `JOIN LATERAL`.

### Test

`db/pgtap/anagrafiche/test-area-accessi-v1.sql` (casi 8-10).
