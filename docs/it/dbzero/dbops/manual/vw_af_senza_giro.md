## 📘 Documentazione Concettuale – View `dbops.vw_af_senza_giro`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)
>
[vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)

---
### 🎯 Scopo Principale
(latest review 04-09-2026)

Elenca il lavoro che sta in coda di fatturazione e che **nessun giro
rivendica**: riga libera, non fatturata, senza il marchio di consegna
(`emit_batch_id IS NULL`).

> ⚠️ **Deve restare a zero righe.** Ogni riga qui è una domanda con una
> risposta sola: *quale giro doveva consegnarla, e perché non l'ha fatto?*

---

### La regola che presidia

> **Il perimetro di un giro è ciò che il pull ha consegnato, non «tutto ciò che
> è libero e in competenza».**

Prima del marchio, una riga liberata da un giro disfatto era indistinguibile da
una appena consegnata: la select la raccoglieva per **coordinate**, e la
commessa che il pull aveva *respinto* finiva in fattura lo stesso — senza
nessun errore.

---

### ⭐⭐ Perché questa vista esiste: il rimedio cambia il RUMORE del danno

È la parte che si dimentica, e va detta prima che qualcuno se ne accorga dopo:

| | Che cosa succede |
| --- | --- |
| **Prima** del marchio | una riga di troppo produce una **fattura in più**. Sbagliato, ma **si vede**: c'è un documento che non doveva nascere |
| **Dopo** | una riga che nessun giro ri-marchia **non viene fatturata**. Per sempre, e **senza nessun errore** |

⛔ E «non è successo niente» lo nota solo chi si aspettava qualcosa: è la stessa
forma del «FATTO, 0 elaborate» che nessuno legge. Il fail-closed da solo non è
un presidio, è un silenzio più educato. **Questa vista è ciò che lo rende di
nuovo visibile.**

---

### ⭐ Nasce piena, e si svuota da sé

Al primo giro dopo l'introduzione della colonna nessuna riga porta un marchio:
la vista elenca tutto il lavoro libero. Non è un difetto della vista, è il
**registro del debito** — e cala da solo, perché il pull **ri-adotta** le righe
esistenti e ci scrive sopra il proprio nome, una per una, al primo giro in cui
quella commessa passa.

⭐ Ciò che **resta** dopo qualche giro è la domanda vera: lavoro libero, in
competenza, che nessun giro ha mai rivendicato.

> ⛔ **La scorciatoia da non prendere**: «contiamo solo le righe nate dopo la
> colonna, così parte vuota». Escludere il pregresso è il modo classico di far
> nascere un presidio già verde — e quelle righe **sono** la popolazione del
> difetto.

---

### Esempio d'uso

```sql
-- Che lavoro nessuno sta rivendicando, e da quanto?
SELECT commessa_id, competenza_mese, emittente_soggetto_ruolo_id, data_insert
FROM dbops.vw_af_senza_giro
ORDER BY data_insert;
```

---

### Note operative

* ⚠️ **Non elenca il lavoro che in fatturazione non è mai entrato.** Una
  commessa che nessun giro ha pullato non ha righe in `attivita_fatturabili`,
  quindi non compare qui — e non deve: quella domanda ha già la sua superficie,
  la **lane** (`fn_list_commesse_emittibili` / `fn_list_emittibili_lane`).
  Confonderle renderebbe questa vista un elenco di due cose diverse, e quindi
  di nessuna.
* Il predicato è quello della select di fatturazione **meno le coordinate**:
  `fatturato IS FALSE` e non lucchettata dicono «lavoro che aspetta».
  Competenza, tipo documento ed emittente **non** ci sono di proposito: una
  riga senza giro è un problema qualunque sia il mese in cui cadrebbe.
* `fatturato` è una colonna **generata** (`fattura_riga_id IS NOT NULL`): si
  legge, non si scrive.
* `security_invoker = true`. ⚠️ L'opzione si azzera a ogni `CREATE OR REPLACE
  VIEW` e va ri-specificata nella stessa istruzione.

Origine: `docs/it/dev/work-in-progress/brief-residuo-fatturabili-e-bandiere-esito-parziale.md`, D1+D2.
