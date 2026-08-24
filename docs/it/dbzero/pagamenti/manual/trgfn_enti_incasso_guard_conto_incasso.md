## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_enti_incasso_guard_conto_incasso`

### 🎯 Scopo Principale

(rev 2026-08-22)

Il conto agganciato a un **canale di incasso** deve avere `uso = 'INCASSO'`.

---

### 🔴 Perché non basta la chiave esterna

`fk_enti_incasso_conto_incasso` sa che la riga puntata **esiste**. Non sa che
cosa **è**: `uso` è una colonna della riga puntata, e una chiave esterna non
legge le colonne di ciò che punta.

⚠️ E il buco che si aprirebbe è sul pezzo che regge il perimetro. L'unicità
`ex_src_bancari_conto_incasso_un_solo_soggetto` vive **solo sulle righe con
`uso = 'INCASSO'`**: è lì che il domino *un conto → un solo soggetto → un solo
emittente* si tiene in piedi. Un ente agganciato a una riga `PAGAMENTO` o
`GENERICO` starebbe **fuori da quell'unicità**, e il perimetro tornerebbe a
essere un'assunzione — con l'aggravante che **nessuno se ne accorgerebbe**,
perché la configurazione sarebbe passata senza un errore.

---

### ⭐ Cosa verifica, e cosa non verifica di proposito

✅ `uso = 'INCASSO'`, e basta.

⛔ **Non** guarda `bloccato`, e **non** guarda `valido_al`. Sono due stati che
cambiano nel tempo per ragioni che non c'entrano con questo ente: bloccare un
conto è un gesto legittimo, e un guard che lo impedisse perché «c'è un ente che
lo cita» sposterebbe il rifiuto sul gesto sbagliato. Accorgersi di un canale
appeso a un conto bloccato è un **controllo di esercizio**, non un vincolo di
scrittura.

⚠️ `uso` invece **non è uno stato**: è *cosa quel legame è*. Se cambia, il legame
è un altro legame.

---

### Regole principali

* Su `UPDATE` esce in testa se la colonna **non è cambiata**: altrimenti
  rinominare un canale verrebbe rifiutato per una configurazione decisa mesi
  prima, e l'errore accuserebbe il gesto sbagliato.
* Riga puntata inesistente → **tace**: non è affare suo, la chiave esterna la
  rifiuta da sé e con il suo messaggio.
* Codice: `E_ENTE_INCASSO_CONTO_NON_DI_INCASSO`, classe `DATO_ERRATO` — il rimedio
  è scegliere l'altro conto, e il contesto porta la chiave `campo` perché
  l'interfaccia possa evidenziarlo.

### ⚠️ Legge sotto la row security, e oggi va bene

Un trigger guard è `SECURITY INVOKER`: su una tabella con RLS non
distinguerebbe «non è un conto di incasso» da «non lo vedo», e rifiuterebbe una
cosa vera dicendone una falsa. ✅
[soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari)
ha la row security **spenta** (misurato il 2026-08-22).

⚠️ Il giorno in cui quella tabella entra sotto RLS, questa funzione va portata su
una `SECURITY DEFINER` — come è già stato fatto per le scadenze con
[fn_check_scadenza_di_fattura](/dbzero/script/funzioni/fn_check_scadenza_di_fattura).

### Dove vive

Trigger `trg_enti_incasso_a10_guard_conto_incasso_ins_upd` su
[enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso), `BEFORE INSERT OR UPDATE`.

{% include-markdown "signature-core.md" %}
