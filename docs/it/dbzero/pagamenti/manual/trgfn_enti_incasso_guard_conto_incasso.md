## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_enti_incasso_guard_conto_incasso`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso) — la tabella su cui il guard è montato
> * [anagrafiche.soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari) — il conto puntato, di cui legge `uso`
>
> Approfondimento funzioni:
>
> * [script.fn_check_scadenza_di_fattura](/dbzero/script/funzioni/fn_check_scadenza_di_fattura) — il modello da seguire se il conto entra sotto row security

---

### 🎯 Scopo Principale

Garantisce che il conto agganciato a un **canale di incasso** abbia `uso = 'INCASSO'`: la chiave
esterna dice che il conto esiste, questo guard dice che è il conto giusto.

---

### 🔴 Perché non basta la chiave esterna

`fk_enti_incasso_conto_incasso` sa che la riga puntata **esiste**. Non sa che cosa **è**: `uso`
è una colonna della riga puntata, e una chiave esterna non legge le colonne di ciò che punta.

⚠️ E il buco che si aprirebbe è sul pezzo che regge il perimetro. L'unicità
`ex_src_bancari_conto_incasso_un_solo_soggetto` vive **solo sulle righe con `uso = 'INCASSO'`**:
è lì che la catena *un conto → un solo soggetto → un solo emittente* si tiene in piedi. Un ente
agganciato a una riga `PAGAMENTO` o `GENERICO` starebbe **fuori da quell'unicità**, e il
perimetro tornerebbe a essere un'assunzione, con l'aggravante che **nessuno se ne accorgerebbe**,
perché la configurazione sarebbe passata senza un errore.

---

### ⭐ Guarda l'uso, e di proposito non guarda il blocco né la validità

✅ `uso = 'INCASSO'`, e basta.

⛔ **Non** guarda `bloccato`, e **non** guarda `valido_al`. Sono due stati che cambiano nel tempo
per ragioni che non c'entrano con questo ente: bloccare un conto è un gesto legittimo, e un guard
che lo impedisse perché «c'è un ente che lo cita» sposterebbe il rifiuto sul gesto sbagliato.
Accorgersi di un canale appeso a un conto bloccato è un **controllo di esercizio**, non un vincolo
di scrittura.

⚠️ `uso` invece **non è uno stato**: è *che cosa quel legame è*. Se cambia, il legame è un altro
legame.

---

### Parla solo quando il conto cambia, e solo se il conto esiste

* Su `UPDATE` esce subito se il conto **non è cambiato**: altrimenti rinominare un canale
  verrebbe rifiutato per una configurazione decisa mesi prima, e l'errore accuserebbe il gesto
  sbagliato.
* Se il conto puntato non esiste **tace**: non è affare suo, la chiave esterna lo rifiuta da sé
  e con il suo messaggio.

---

### ⚠️ Legge sotto la row security, e oggi va bene

Il guard gira con i privilegi di chi scrive: su una tabella con row security non distinguerebbe
«non è un conto di incasso» da «non lo vedo», e rifiuterebbe una cosa vera dicendone una falsa.
✅ [soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari) ha
la row security **spenta**.

⚠️ Il giorno in cui quella tabella entra sotto row security, questa funzione va portata su una
`SECURITY DEFINER`, come è già stato fatto per le scadenze con
[fn_check_scadenza_di_fattura](/dbzero/script/funzioni/fn_check_scadenza_di_fattura).

---

### Codici errore

* `E_ENTE_INCASSO_CONTO_NON_DI_INCASSO` (`DATO_ERRATO`) — il conto agganciato ha un `uso`
  diverso da `INCASSO`. Il rimedio è scegliere un altro conto; il contesto porta la chiave
  `campo`, perché l'interfaccia possa evidenziarlo, e la frase dice quale uso ha trovato.

---

### Test

* `db/pgtap/pagamenti/test-enti-incasso-conto-incasso.sql` — un conto di incasso passa, un conto
  di pagamento è rifiutato e la frase nomina l'uso trovato, un `UPDATE` che non tocca il conto
  non viene rifiutato.

---

### Note di migrazione

* 2026-08-22 — nasce insieme alla colonna `soggetto_ruolo_conto_bancario_id` di
  `enti_incasso`. In quella data la tabella dei
  conti risultava senza row security.

---

{% include-markdown "signature-core.md" %}
