## Documentazione – `vendite.trgfn_guard_fatturazione_immediata_immutabile()` (presidio corsia di fatturazione)

> **Versione**: 2026-07-27 (brief-db-emissione-fattura-per-documento-sorgente
> PARTE B / decisione D-7, migration `20260727-08`)
> **Stato**: **attiva** su `vendite.preventivi`, `vendite.ordini`,
> `vendite.contratti`, `vendite.ddt` (armata da `20260727-09`)

---

### 👀 Vedi anche
>
**Approfondimento tabelle:**
>
[vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
>
**Approfondimento funzioni**:
>
[vendite.fn_link_commessa_sorgente](/dbzero/vendite/funzioni/fn_link_commessa_sorgente) — normalizza la chiave che questo guard va a cercare
> [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa) — il flag è parte della sua chiave di dedup
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
**Guide**: [sorgente polimorfa](/guide/sorgente-polimorfa) · [fatturazione](/guide/fatturazione)

---

### 🎯 Scopo Principale

Impedire la modifica di `fatturazione_immediata` su un documento che sta in una
commessa **aperta**.

> ⭐ **Dal 2026-10-12** (brief-db-annullo-a-valle-riapre-a-monte, D-14) conta solo
> la commessa **aperta**, chiesta a
> [vendite.fn_commessa_viva_di_sorgente](/dbzero/vendite/funzioni/fn_commessa_viva_di_sorgente).
> Il link verso una commessa chiusa o annullata resta come storia, e il documento
> torna da mandare: il suo flag torna una scelta da fare.

Il flag decide su quale **corsia** finisce il lavoro:

| Valore | Corsia | `tipo_lotto` | Arriva a |
|---|---|---|---|
| `true` | immediata | `GIORNALIERO` | `DEFINITIVA` (numera da sola) |
| `false` | differita | `MASSIVO` | `EMESSA` (la numerazione è un atto separato) |

Viene letto **una sola volta**, dal push verso la commessa. Da quel momento in
poi è **inerte**.

---

### Perché serve un guard su un valore già inerte

Non è pignoleria formale: senza il guard il campo resterebbe **editabile a
video senza produrre alcun effetto**, che è il peggiore dei casi — *sembra*
funzionare. Tre ragioni concorrenti rendono il flag inerte dopo il push:

1. **È nella chiave di dedup della commessa.**
   `fn_get_or_create_commessa` identifica la commessa per
   `(BA, utility, tipo_commessa, policy_fatturazione, fatturazione_immediata,
   emittente, competenza_dal/al)`. Cambiarlo sul documento **non sposta** le
   righe già pushate: quelle stanno in una commessa che è nata con il vecchio
   valore.
2. **Un documento sta in una sola commessa aperta.** Finché la sua commessa è
   aperta, ri-pusharlo verso una commessa di corsia diversa darebbe
   `E_COMMESSA_SORGENTE_ALTRA_COMMESSA` (la porta,
   `vendite.fn_link_commessa_sorgente`). Fino al 2026-10-12 il legame era «per
   sempre» (`UNIQUE` globale); ora vale finché la commessa non si chiude o non
   si annulla.
3. **Anche potendo, si sposterebbe l'intera commessa**, che è multi-sorgente
   (`ROOT` + N `COLLEGATO`): trascinerebbe con sé documenti che nessuno ha
   chiesto di spostare.

> **Il caso «cambio idea dopo» non è scoperto**: è gestito dall'**emissione
> mirata per gruppo fatturabile**, che fattura esattamente le righe di quel
> documento senza toccare il resto della commessa. Sono due strumenti distinti:
> il flag è *instradamento automatico* deciso a monte, l'emissione mirata è un
> *atto puntuale dell'operatore*.

---

### Regole principali

* **Solo cambi reali.** Il trigger è armato con
  `WHEN (NEW.fatturazione_immediata IS DISTINCT FROM OLD.fatturazione_immediata)`.
  Riscrivere lo **stesso** valore passa senza errore: serve al percorso
  legittimo di ri-accettazione di un preventivo, che riscrive il flag
  invariato. `IS DISTINCT FROM` e non `<>` perché su `vendite.preventivi` la
  colonna è nullable.
* **Chirurgico sulla colonna.** `BEFORE UPDATE OF fatturazione_immediata`: non
  interferisce con le altre modifiche del documento.
* **Generico per sorgente.** Il tipo arriva da `TG_ARGV[0]` come
  **`codice_interno`** (immutabile, linee-guida-sql §6b), mai come id.
* **Fail-loud sulla configurazione.** Argomento mancante, sorgente non trovata
  o `key_selector` fuori dominio → errore. Un guard che non risolve la chiave è
  un guard che non protegge, e non deve poter passare inosservato.
* **Nessun filtro su `attivo`** nella lookup della sorgente: il legame
  documento→commessa esiste anche se la sorgente venisse disattivata, e va
  protetto lo stesso.

---

### ⚠️ La chiave di ricerca: si segue `key_selector`, non il push

Il guard cerca il documento in `commesse_sorgenti`, che contiene la chiave
**canonica** definita da `config.sorgenti.key_selector`:

* `key_selector = 'uid'` → `NEW.uid::text` (preventivi, offerte);
* `key_selector = 'id'` → `NEW.id::text` (ordini, contratti, DDT).

La forma canonica è garantita **in scrittura** da `fn_link_commessa_sorgente`,
che **normalizza**: i chiamanti storici passano l'uid del documento anche per i
tipi a chiave `id` (tutte le `fn_list_*_da_pushare` proiettano
`<tabella>.uid::text`), e la funzione traduce prima dell'idempotenza e
dell'insert.

> ⚠️ **Trappola**: non dedurre la chiave da ciò che il **chiamante** passa. La
> normalizzazione avviene un livello più sotto, dentro la funzione di scrittura.
> Guardare solo il push porta a concludere «è sempre l'uid» e a scrivere un
> `WHERE` che non trova mai il link → **guard no-op silenzioso**.
> Vedi [guida sorgente polimorfa §4a](/guide/sorgente-polimorfa).

---

### 📦 Errori sollevati

| Codice | Quando |
|---|---|
| `E_FATT_IMMEDIATA_NON_MODIFICABILE` (561) | il documento sta in una commessa aperta (dal 2026-10-12; prima: qualunque riga in `commesse_sorgenti`) |
| `E_PARAMETRO_INVALIDO` | `TG_ARGV[0]` mancante o vuoto (trigger mal configurato) |
| `E_CODICE` | `codice_interno` non presente in `config.sorgenti` |
| `E_SORG_CONF` | `key_selector` fuori dominio (`id`/`uid`) |

Il contesto dell'errore include tabella, `documento_id`, `documento_uid`,
`chiave_canonica`, `commessa_id`, valore attuale e valore richiesto: serve a
capire *dove* è finito il documento senza doverlo cercare a mano.

---

### Esempio d'uso (armamento)

```sql
CREATE TRIGGER trg_ordini_a10_guard_fatt_immediata_upd
    BEFORE UPDATE OF fatturazione_immediata ON vendite.ordini
    FOR EACH ROW
    WHEN (NEW.fatturazione_immediata IS DISTINCT FROM OLD.fatturazione_immediata)
    EXECUTE FUNCTION vendite.trgfn_guard_fatturazione_immediata_immutabile('ORDINE_VENDITA');
```

---

### Perimetro: perché non sui consumi

`vendite.attivita_consumi` **non ha il flag** e quindi non ha il guard
(decisione D-6, 2026-07-27). Un consumo è una **misura**, non un accordo
commerciale: la corsia la decide il **contratto** che lo governa. Un flag sulla
singola lettura creerebbe lo stesso interruttore in due posti, con la
possibilità che dicano cose opposte e nessuna regola su chi vince.

---

{% include-markdown "signature-core.md" %}
