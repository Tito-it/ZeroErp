## 📘 Documentazione Concettuale – Funzione `script.fn_scrivi_riga_da_jsonb()`

> 👀 **Vedi anche**
>
> [script.fn_prima_chiave_estranea](/dbzero/script/manual/fn_prima_chiave_estranea) ·
> [anagrafiche.fn_crea_emittente_fiscale](/dbzero/anagrafiche/manual/fn_crea_emittente_fiscale)

### 🎯 Scopo
(17-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1)

**Scrivere una riga con le sole colonne del payload.** I verbi che ricevono i
campi come oggetto JSON (la creazione di un emittente, il pannello di
configurazione, la creazione di un contratto) scrivono solo le chiavi
presenti: le altre restano al loro default, o com'erano.

| `p_dove` | Effetto |
| --- | --- |
| `NULL` | **INSERT**: le colonne assenti prendono il DEFAULT (payload vuoto: `DEFAULT VALUES`) |
| `{colonna: valore, ...}` | **UPDATE** delle righe con quei valori: le colonne assenti restano com'erano (payload vuoto: nessuna scrittura) |

I valori li converte PostgreSQL sul tipo della colonna. Restituisce la riga
scritta, o `NULL` se l'UPDATE non trova righe. I trigger della tabella
scattano come sempre.

### Regole

* **Le chiavi le sceglie chi chiama.** Il pannello rifiuta una chiave
  estranea, la creazione del contratto la scarta: sono regole diverse, e
  restano a ciascun verbo. Per rifiutare c'è
  [fn_prima_chiave_estranea](/dbzero/script/manual/fn_prima_chiave_estranea).
* `SECURITY INVOKER`: scrive coi privilegi di chi chiama.
* Chiamata malformata (tabella mancante, dati che non sono un oggetto, chiave
  di riga vuota): `E_SCRIPT_CHIAMATA_NON_VALIDA`.

### Chi la usa

`config.fn_pannello_scrivi`, `vendite.fn_create_contratto`,
`anagrafiche.fn_crea_emittente_fiscale`. Prima ciascuno componeva la stessa
scrittura a mano.

### Test

`db/pgtap/script/test-fn-scrivi-riga-da-jsonb-v1.sql`.

---

{% include-markdown "signature-core.md" %}
