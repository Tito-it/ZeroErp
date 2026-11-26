## 📘 Documentazione Concettuale – Funzione `vendite.fn_elimina_fattura_da_lotto`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) · [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture) — il lotto e il suo legame con la fattura
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) · [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe) — la fattura che si toglie
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — le attività che tornano libere
>
> Approfondimento funzioni:
>
> * [vendite.fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids) — la pulizia, riservata
> * [script.fn_check_fattura_eliminabile_da_lotto](/dbzero/script/funzioni/fn_check_fattura_eliminabile_da_lotto) — i motivi
> * [script.fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione) — il permesso: l'azione `reset_lotto_fattura_draft`
> * [vendite.fn_annulla_lotto_da_draft](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft) · [vendite.fn_riporta_lotto_a_draft](/dbzero/vendite/funzioni/fn_riporta_lotto_a_draft) — le sorelle sul lotto intero
> * [vendite.fn_escludi_documento_da_giro](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro) — chiamante: l'uscita di un documento dal giro
>
> Guide:
>
> * [Fatturazione](/guide/fatturazione) — le vie d'uscita da un lotto, e chi le può prendere

---
### 🎯 Scopo Principale

Toglie **una sola fattura** da un lotto **cancellandola**, senza toccare il lotto né le
altre fatture. È il verbo per il caso in cui un documento è sbagliato e va rifatto,
mentre il resto del giro è sano.

> ⚠️ **Rinominata il 2026-08-04** da `fn_elimina_fattura_da_lotto_draft`. Il «draft» era
> riferito al **lotto**, che non deve più essere in bozza: ora basta che sia
> pre-fiscale. Un nome che non dice più la verità è un bug che aspetta — è la terza
> rinomina della famiglia per questa stessa ragione.

---

### Chi la chiama, con quale permesso e su quale lotto

È il verbo dell'endpoint «togli la fattura dal lotto». Gira come proprietario
(`SECURITY DEFINER`), fuori dalla row security, quindi permesso e perimetro li controlla lei,
all'ingresso:

* **il permesso**, in prima riga: l'azione `reset_lotto_fattura_draft`
  ([`script.fn_guard_azione`](/dbzero/script/funzioni/fn_guard_azione)), la stessa dell'endpoint.
  Chi arriva dall'interfaccia non riceve un rifiuto nuovo. Senza l'azione: `E_PERMESSO_NEGATO`;
* **il perimetro**, sul lotto **e** sulla fattura: tutti e due devono essere di un'azienda di chi
  agisce. Il controllo è doppio perché il modello non lega la fattura all'azienda del lotto. Fuori
  dal perimetro il lotto risponde `E_LOTTO_NON_TROVATO` e la fattura `E_FATTURA_NON_TROVATA`, la
  stessa risposta di un oggetto che non esiste, prima di dire qualunque altra cosa.

**Le porte spente all'ingresso.** Il verbo spegne la GUC del reset del lotto e quella delle righe
contabili. La porta del reset la riapre solo la pulizia, mentre lavora: chiamata da qui gira come
proprietario.

---

### Il perimetro: pre-fiscale, non «bozza»

Sia il **lotto** sia la **fattura** devono essere `DRAFT` o `EMESSA`, cioè non ancora
numerati. È lo stesso confine delle due sorelle che lavorano sul lotto intero.

Fino al 2026-08-04 il lotto doveva essere in `DRAFT`. Era il perimetro sbagliato, e si
vedeva in-app: il drawer proponeva la voce di riga su qualunque lotto con una fattura
pre-fiscale — quindi anche sui lotti `EMESSA` — e lì la chiamata **falliva**. Il caso che
motiva l'azione è proprio quello: la fattura critica rimasta indietro in un lotto emesso.

---

### 🔴 Togliere vuol dire cancellare (RD-7)

Non esiste un modello «reperto»: la fattura non viene staccata e conservata, viene
**eliminata** insieme a righe, riepiloghi, note, log e collegamento al lotto. Le sue
attività tornano libere e rientreranno nel giro successivo.

La ragione è la coerenza: riportare in bozza un lotto **intero** cancella già le sue
fatture emesse. Sarebbe strano che la stessa operazione, fatta su **una** riga, lasciasse
in archivio un documento vuoto.

> ⚠️ **La cancellazione non lascia traccia del contenuto.** `vendite.fatture` non è
> storicizzata (il flag è spento di default e nessuno lo accende): dopo l'operazione non
> è più possibile sapere cosa diceva quel documento. Resta la riga del **ponte**, quella
> sì storicizzata, che registra «la fattura X era in questo lotto ed è uscita».

---

### Regole principali

* `p_lotto_id` e `p_fattura_id` obbligatori e `> 0`.
* Le precondizioni **non sono scritte qui**: arrivano da
  `script.fn_check_fattura_eliminabile_da_lotto`, che è anche la sorgente dei messaggi.
  Si solleva il codice del **primo** motivo, con l'elenco completo nel contesto.
* La pulizia è **tutta** di `vendite.fn_cleanup_fatture_by_ids`: questa funzione decide
  *cosa* si toglie, non *come* si ripulisce.
* ⚠️ Alla primitiva si passa **`NULL`** come `lock_batch_id` (C-22): passando quello del
  lotto si libererebbero anche le attività delle **altre** fatture, che invece restano
  dove sono.
* **Non** modifica lo stato del lotto.

---

### Errori

| Codice | Quando |
| --- | --- |
| `E_LOTTO_NON_PRE_FISCALE` (831) | il lotto è oltre il pre-fiscale |
| `E_FATTURA_NON_COLLEGATA_AL_LOTTO` (832) | la fattura non appartiene a quel lotto |
| `E_FATTURA_GIA_FISCALE` (833) | la fattura è oltre il pre-fiscale |
| `E_FATTURA_GIA_NUMERATA` (834) | la fattura ha già un numero |
| `E_PERMESSO_NEGATO` | manca l'azione `reset_lotto_fattura_draft` |
| `E_LOTTO_NON_TROVATO` / `E_FATTURA_NON_TROVATA` | lotto o fattura inesistenti, oppure fuori dal perimetro di chi agisce |
| `E_PARAMETRO_INVALIDO` | parametri assenti o `<= 0` |

---

### Output

Ritorna una riga con quattro contatori:

* `updated_attivita` — attività sbloccate
* `deleted_fatture`
* `deleted_righe`
* `riemesse_attivita` — attività di commessa tornate `NON_EMESSA`

Il quarto è separato dal primo di proposito: un numero unico direbbe «dieci cose fatte»
senza distinguere le attività sbloccate da quelle rimesse in coda, che per il cockpit
sono fatti diversi.

---

### Test

* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — gira come l'applicazione: il verbo è
  `SECURITY DEFINER`; senza `reset_lotto_fattura_draft` risponde `E_PERMESSO_NEGATO`; sul lotto di
  un'altra azienda risponde `E_LOTTO_NON_TROVATO`.
* `db/pgtap/vendite/test-elimina-fattura-da-lotto-v1.sql`,
  `db/pgtap/vendite/test-elimina-fattura-da-lotto-effetti-v1.sql` — che cosa toglie e che cosa
  ripristina.

---

### Note di migrazione

* 2026-08-04 — rinominata da `fn_elimina_fattura_da_lotto_draft`; il lotto basta che sia
  pre-fiscale.
* 2026-11-25 — `SECURITY DEFINER`: il permesso dell'endpoint in prima riga, il perimetro su lotto e
  fattura all'ingresso (prima lo dava la row security), le porte spente all'ingresso
  (brief-db-porte-aperte-dalla-sola-guc, giro 1-7, D-Y a).

---

{% include-markdown "signature-core.md" %}
