## 📘 Documentazione Concettuale – Vista `dbops.vw_af_senza_giro`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — la coda di fatturazione che la vista legge
> * [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) — i giri che marchiano le righe
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive
>
> Approfondimento funzioni:
>
> * [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa) — il pull, che scrive il marchio del giro
> * [vendite.fn_select_attivita_fatturabili](/dbzero/vendite/funzioni/fn_select_attivita_fatturabili) — la selezione del giro, che legge il marchio
> * [vendite.fn_list_commesse_emittibili](/dbzero/vendite/funzioni/fn_list_commesse_emittibili) — la lane: il lavoro mai entrato in fatturazione
> * [anagrafiche.fn_get_emittente_fiscale_id](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_id) — l'emittente della riga, dal billing account
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio del digest
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che cala
> * [Fatturazione](/guide/fatturazione) — il giro, il pull e la coda

---

### 🎯 Scopo Principale

Il lavoro in coda di fatturazione che **nessun giro rivendica**: righe libere, non fatturate,
senza il marchio del giro che le ha consegnate. Il traguardo è zero righe: ognuna è una domanda
con una risposta sola, *quale giro doveva consegnarla, e perché non l'ha fatto?*

---

### La regola che presidia

> **Il perimetro di un giro è ciò che il pull ha consegnato, non «tutto ciò che è libero e in
> competenza».**

Il pull scrive su ogni riga che consegna l'identità del giro che l'ha chiesta (`emit_batch_id`),
e la selezione del giro prende solo le righe col proprio marchio. Senza il marchio, una riga
liberata da un giro disfatto era indistinguibile da una appena consegnata: la selezione la
raccoglieva per **coordinate**, e una commessa che il pull aveva *respinto* finiva in fattura lo
stesso, senza nessun errore.

---

### ⭐⭐ Perché questa vista esiste: il rimedio cambia il rumore del danno

| | Che cosa succede |
| --- | --- |
| **senza** il marchio | una riga di troppo produce una **fattura in più**. Sbagliato, ma **si vede**: c'è un documento che non doveva nascere |
| **con** il marchio | una riga che nessun giro marchia **non viene fatturata**. Per sempre, e **senza nessun errore** |

⛔ «Non è successo niente» lo nota solo chi si aspettava qualcosa: è la stessa forma del «FATTO,
0 elaborate» che nessuno legge. Il fail-closed da solo non è un presidio, è un silenzio più
educato. **Questa vista lo rende di nuovo visibile.**

---

### ⭐ È nata piena, e si svuota da sé

Il giorno in cui è nato il marchio nessuna riga lo portava: la vista elencava tutto il lavoro
libero. Non è un difetto della vista, è il **registro del debito**, e cala da solo, perché il
pull **ri-adotta** le righe esistenti e ci scrive sopra il proprio giro, al primo giro in cui
quella commessa passa.

⭐ Ciò che **resta** dopo qualche giro è la domanda vera: lavoro libero che nessun giro ha mai
rivendicato.

⛔ **La scorciatoia da non prendere**: «contiamo solo le righe nate dopo il marchio, così parte
vuota». Escludere il pregresso è il modo classico di far nascere un presidio già verde, e quelle
righe **sono** la popolazione del difetto.

⇒ Per questo nel catalogo dei presidi ha natura `LAVORAZIONE` e non `ZERO`: si guarda la
tendenza, non il numero, ogni settimana. A discesa finita diventa un presidio a zero.

---

### Il predicato: il lavoro che aspetta, meno le coordinate

Una riga entra se non porta il marchio, non è fatturata e non è chiusa nel lucchetto di un giro
in corso. È il predicato della selezione di fatturazione **senza le coordinate**: competenza, tipo
documento ed emittente non ci sono di proposito, perché una riga senza giro è un problema
qualunque sia il mese in cui cadrebbe.

`fatturato` è una colonna generata (vera quando la riga è legata a una riga di fattura): si
legge, non si scrive. L'emittente della riga si ricava dal billing account, per chi deve capire
a quale azienda appartiene.

---

### ⚠️ Che cosa non elenca

Il lavoro che in fatturazione non è mai entrato. Una commessa che nessun giro ha pullato non ha
righe nella coda, quindi qui non compare, e non deve: quella domanda ha già la sua superficie, la
lane (`vendite.fn_list_commesse_emittibili`, `vendite.fn_list_emittibili_lane`). Confonderle
renderebbe questa vista un elenco di due cose diverse, e quindi di nessuna.

---

### Chi la può vedere

La vista è `security_invoker`, e la coda di fatturazione ha la row level security: una persona
la legge col proprio perimetro. Il digest la conta da proprietario con `dbops.fn_conta_presidio`
(perimetro `DEFINER` a catalogo) e riporta il numero, perché da un percorso senza identità
risponderebbe zero per cecità.

---

### Test

* `db/pgtap/vendite/test-af-emit-batch-marchio-v1.sql` — il marchio scritto dal pull, anche sopra
  una riga liberata da un giro disfatto, e le righe marchiate che dalla vista escono.
* `db/pgtap/dbops/test-catalogo-presidi-v1.sql` — la riga a catalogo combacia con la vista.

---

### Note di migrazione

* 2026-09-04 — nasce insieme al marchio `emit_batch_id`
  (`brief-residuo-fatturabili-e-bandiere-esito-parziale`, D1 e D2).
* 2026-09-10 — la coda di fatturazione entra in row level security: il perimetro `DEFINER`
  scelto in anticipo a catalogo diventa necessario.

---

{% include-markdown "signature-core.md" %}
