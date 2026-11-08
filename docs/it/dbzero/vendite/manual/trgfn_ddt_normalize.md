## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_ddt_normalize`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) — la testata che normalizza
> * [vendite.ordini](/dbzero/vendite/tabelle/ordini) — l'ordine da cui eredita
>
> Approfondimento funzioni:
>
> * [script.fn_cliente_dal_billing_account](/dbzero/script/funzioni/fn_cliente_dal_billing_account) — destinatario e utility dal cliente
> * [vendite.trgfn_resi_normalize](/dbzero/vendite/funzioni/trgfn_resi_normalize) — la gemella del reso
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

Normalizza la testata della bolla di vendita, `BEFORE INSERT` e `BEFORE UPDATE` (`trg_ddt_normalize_ins_upd`): completa anno e data, eredita cliente, valuta ed emittente dall'ordine da cui la bolla nasce, e tiene destinatario e utility allineati al cliente.

---

### Le regole, in ordine

1. **Anno e data**: all'inserimento, se il numero c'è e anno o data mancano, prende quelli del
   giorno operativo (`script.fn_data_operativa`).
2. **Eredità dall'ordine**: all'inserimento, se la bolla dichiara come provenienza un
   **ordine di vendita** (tipo `ORDINE_VENDITA`, riconosciuto per `codice_interno`), prende
   dall'ordine i campi che mancano — `billing_account_id`, `valuta_id`, `emittente_fiscale_id` —
   e la utility dal cliente dell'ordine. L'ordine è a chiave `id`: la bolla lo dichiara in
   `sorgente_id`, come la scrive `vendite.fn_genera_ddt_da_ordine`. Le bolle che nascono da altro
   (la bolla di riconsegna, che dichiara il reso) o da niente non ereditano da qui.
3. **Destinatario e utility seguono il cliente**: col cliente (`billing_account_id`) sono **copie**
   di ciò che il cliente dice. Che cosa valgono lo dice
   [`script.fn_cliente_dal_billing_account`](/dbzero/script/funzioni/fn_cliente_dal_billing_account)
   (le scrive se mancano, `E_DOC_CLIENTE_DIVERSO_DA_BA` se dissentono); **quando**, lo dice la bolla:
   all'inserimento, e su una modifica che tocca cliente, destinatario o utility (in bozza: fuori,
   le ferma il lock di testata). Se il cliente cambia, la copia che il chiamante non ha toccato
   segue il cliente nuovo. Un cliente tolto toglie la utility (le due vanno insieme) e lascia il
   destinatario, che senza cliente è libero.
4. **Emittente dal cliente**: all'inserimento, se dopo i passi precedenti l'emittente manca e c'è
   un cliente, lo risolve con `anagrafiche.fn_get_emittente_fiscale_pk`.

Non sovrascrive mai un valore che il chiamante ha scritto, salvo la copia che segue il cliente
nuovo.

---

### ⭐ Il tipo si riconosce per codice, e la bolla dichiara l'ordine

Il tipo si legge per **`codice_interno`** (immutabile), mai per `codice` (modificabile). Ed è la
ragione per cui chi genera la bolla da un ordine deve dichiarare come provenienza l'**ordine**, non
la bolla stessa: con un tipo diverso l'eredità non scatta.

L'`emittente_fiscale_id` ereditato è la chiave del perimetro della bolla: obbligatorio, guard di
scrittura `script.trgfn_guard_emittente_scope`, policy `rls_ddt_ef_whitelist`.

---

### Note di migrazione

* 2026-10-10 — destinatario e utility seguono il cliente col BB condiviso (brief-db-esecutivi-ba-coppia §10.2).
* 2026-11-06 — l'ordine di provenienza si dichiara con la chiave del modello, `sorgente_id`; prima
  la bolla lo dichiarava con il suo uid in `sorgente_uid` (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
