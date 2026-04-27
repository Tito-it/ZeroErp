## 📘 Documentazione Concettuale – Trigger Function `shop.trgfn_ricevute_guard_ba_canale()`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [shop.ricevute](/dbzero/shop/tabelle/ricevute) — tabella guardata
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — BA con colonna `canale_origine` verificata
>
> Approfondimento funzioni:
>
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
> Guide:
>
> [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth) §6.4 — Tracciabilita' canale sui dati transazionali
> [Linee Guida Trigger](/linee-guida-trigger) — convenzioni naming e fasi

La trigger function **`shop.trgfn_ricevute_guard_ba_canale()`** blinda
l'invariante "ricevuta shop → BA di canale SHOP". E' specifica della
tabella `shop.ricevute` (non generica), perche' l'invariante e' un
vincolo di dominio dedicato allo schema shop.

---

### 🎯 Scopo Principale

(latest revision 21-04-2026)

* **Separazione di canale** — decisione di dominio 20-04-2026: lo shop
  B2C e' canale autonomo rispetto al portale B2B. I `billing_account`
  sono discriminati da `canale_origine` (ADMIN / PORTALE / SHOP) e le
  ricevute shop devono vivere **solo** su BA di canale SHOP, non su BA
  portale dello stesso cliente anagrafico.
* **Difesa DB-side** — la verifica era inizialmente solo applicativa
  (service-side). Il trigger la sposta nel DB: qualsiasi writer
  (backend, Liquibase data-fixup, psql manuale) non puo' aggirare
  l'invariante.
* **Coerenza con RLS** — le policy RLS di `shop.ricevute` filtrano per
  ownership tramite `soggetto_ruolo_id` comune all'identita
  `SHOP_CUSTOMER`. Se una ricevuta venisse ancorata a un BA portale,
  l'utente shop continuerebbe a vederla (la RLS non guarda il BA) ma la
  contabilita' sarebbe ambigua tra i due canali. Il trigger impedisce
  questa ambiguita' alla radice.

---

### Logica

1. `SELECT canale_origine INTO v_ba_canale FROM anagrafiche.billing_account
   WHERE id = NEW.billing_account_id`.
2. Se `v_ba_canale IS DISTINCT FROM 'SHOP'` (incluso il caso `NULL`
   per BA inesistente — caso di race estrema, gia' protetto dalla FK):
   chiama `script.fn_log_and_raise_error` con codice
   `E_SHOP_RICEVUTA_BA_CANALE_INVALIDO` (id 386). Il raise interrompe
   la transazione.
3. Se `v_ba_canale = 'SHOP'`: `RETURN NEW`, operazione accettata.

Context di errore riportato nel payload JSONB:

* `op` — operazione (`TG_OP`: `INSERT` o `UPDATE`)
* `ricevuta_id` — `NEW.id` (UUID v7 della ricevuta)
* `billing_account_id` — il FK rifiutato
* `canale_ba` — canale effettivo del BA (o `'NULL'` se non trovato)

Messaggio format: "Ricevuta shop `<id>`: il billing_account collegato
ha canale_origine `<canale>`, atteso SHOP."

---

### Applicazione

Trigger creato dalla migration `20260421-02-02`:

* **`trg_shop_ricevute_a10_guard_ba_canale_ins_upd`** su `shop.ricevute`

Specifiche:

* Timing: **BEFORE INSERT OR UPDATE OF billing_account_id**
* Fase: **_a10_** (guard/block)
* Scope: **FOR EACH ROW**

---

### Codice errore sollevato

**`E_SHOP_RICEVUTA_BA_CANALE_INVALIDO`** (id 386) —
`config.messaggi_errore` CSV. Seminato in PR DB shop B2C (20-04-2026).

Messaggio utente: "Il billing_account referenziato dalla ricevuta shop
non e' un BA di canale SHOP. Le ricevute shop vivono su BA dedicati con
`canale_origine='SHOP'` (separati dai BA portale B2B)."

Soluzione suggerita nel CSV: "Verificare che la ricevuta punti a un
billing_account con `canale_origine='SHOP'`. Se il cliente non ha
ancora un BA shop, crearne uno prima di emettere la ricevuta."

---

### Quando NON scatta

* UPDATE che non tocca `billing_account_id`: la clausola
  `UPDATE OF billing_account_id` evita la valutazione del trigger. Un
  UPDATE su `pagamento_esito`, `meta`, `totale_iva` non rivaluta il
  vincolo (performance, e il BA non puo' cambiare canale per effetto
  del trigger `trg_billing_account_a10_canale_origine_immutable_upd`).
* UPDATE di `billing_account_id` con stesso valore: il trigger scatta,
  ma se l'`OLD` era gia' su BA SHOP anche il `NEW` lo e' → accettato.
* DELETE: il trigger non scatta (scope `INSERT OR UPDATE`).

---

### Note implementative

* `LANGUAGE plpgsql` — necessario per variabile locale e RAISE via
  `fn_log_and_raise_error`.
* **Non generalizzabile** con `trgfn_canale_origine_immutable` perche'
  quella verifica immutabilita' (OLD vs NEW della stessa riga), questa
  verifica un valore su una riga **diversa** (join FK → BA). Sono
  responsabilita' disgiunte.
* La FK `fk_shop_ricevute_billing_account` garantisce l'esistenza del
  BA; il trigger si concentra sul canale. Il fail-closed su
  `v_ba_canale IS NULL` e' difesa addizionale contro race condition
  (DELETE + INSERT nel gap tra FK check e trigger).
