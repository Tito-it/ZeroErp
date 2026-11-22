## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_guard_regime_pa`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — i due flag, `cliente_pa` e `split_payment`
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — la natura, che li ammette
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_regime_pa_campo_non_ammesso](/dbzero/anagrafiche/funzioni/fn_regime_pa_campo_non_ammesso) — la regola, a cui il guard chiede
> * [anagrafiche.fn_check_cambio_natura_soggetto](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto) — il cambio di natura, che legge la stessa regola

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_guard_regime_pa` rifiuta un soggetto con `cliente_pa` o `split_payment` a `S` quando
la sua natura non li ammette, o quando il soggetto non ha natura.

---

### Il valore lo dice un vincolo, il «per chi» la natura

Che i flag valgano `S` o `N` lo dicono i vincoli `chk_soggetti_cliente_pa` e `chk_soggetti_split_payment`. Chi
può averli a `S` sta in un'altra tabella, che un vincolo di riga non può leggere: lo dicono
`cliente_pa_ammesso` e `split_payment_ammesso` della natura. La regola la scrive
`anagrafiche.fn_regime_pa_campo_non_ammesso`, e la leggono questo guard e il controllo del cambio di natura.

Due flag a `N` non hanno niente da chiedere: il guard passa senza guardare la natura. La natura è una condizione
necessaria, non sufficiente: il flag lo accende l'operatore, e il database non lo spegne da sé.

---

### ⭐ Senza natura rifiuta

A differenza dei guard del sesso e della presenza di CF e P.IVA, che senza natura tacciono, questo rifiuta un
flag a `S` su un soggetto senza natura. `split_payment` cambia l'esigibilità della fattura: non si accende su un
soggetto di cui non si sa che cosa sia.

---

### Anche il cambio di natura

Il guard scatta alla nascita e quando cambiano i due flag o la natura. Chi cambia natura verso una che non ammette
un flag acceso lo riporta a `N` nella stessa scrittura. Sul cambio di natura parla per primo il suo guard, che ha
la stessa regola fra i suoi motivi: questo resta la rete per le altre strade.

---

### Codici errore

* `E_CLIENTE_PA_NON_AMMESSO` — `cliente_pa` a `S` e la natura non lo ammette. Il campo dell'errore è
  `cliente_pa`.
* `E_SPLIT_PAYMENT_NON_AMMESSO` — `split_payment` a `S` e la natura non lo ammette. Il campo dell'errore è
  `split_payment`.
* `E_DATO_FISCALE_SENZA_TIPO_SOGGETTO` — un flag a `S` su un soggetto senza natura. Il campo dell'errore è
  `tipo_soggetto_dettaglio_id`.

Con tutti e due i flag fuori regola il rifiuto nomina `cliente_pa`.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-regime-pa-v1.sql` — le nature che ammettono i flag e il vincolo che li
  vieta alle persone fisiche; la società in scissione che passa e quella PA rifiutata, col campo; l'ente con i
  due flag; l'ente PA che cambia natura, rifiutato, e che passa col flag riportato a `N`; il privato PA e la
  ditta in scissione rifiutati; il flag a `S` senza natura rifiutato, i flag a `N` senza natura che passano.

---

### Note di migrazione

* 2026-10-10 — nasce, con i due campi della natura che ammettono i flag.
* 2026-11-14 — la regola passa a `anagrafiche.fn_regime_pa_campo_non_ammesso`, condivisa col cambio di natura;
  il comportamento non cambia.

---

{% include-markdown "signature-core.md" %}
