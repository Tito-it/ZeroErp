## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_guard_soggetto_contatti`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la tabella su cui è montata
> * [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti) — i contatti che conta
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_soggetto_pf](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pf) — la nascita di una persona fisica, col suo primo contatto
> * [anagrafiche.fn_crea_soggetto_pg](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pg) — la nascita di una società o di un ente, col suo primo contatto
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — il blocco che i contatti mettono alla disattivazione del soggetto
>
> Guide:
>
> * [Gestione dei Contatti](/guide/gestione-dei-contatti) — il contatto obbligatorio nel modello dei contatti

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_guard_soggetto_contatti` pretende che un soggetto abbia almeno un contatto: al COMMIT
di ogni nascita e di ogni modifica del soggetto cerca un suo contatto che sia predefinito o che abbia un recapito
(email, telefono, cellulare o PEC), e se non ne trova rifiuta.

---

### Al COMMIT, perché il contatto arriva dopo

È montata su `anagrafiche.soggetti` come constraint trigger differito, dopo la nascita e dopo ogni modifica, su
qualunque colonna. Il soggetto si scrive per primo, perché il contatto lo riferisce; il contatto arriva dopo,
nella stessa transazione, e il controllo aspetta la fine. I verbi di nascita del soggetto creano il suo primo
contatto nella stessa chiamata, e il controllo li trova sempre in regola.

---

### Che cosa conta

Contano i contatti del soggetto **di ogni contesto**: del soggetto, di un ruolo o di un'istanza. Il primo
contatto di ogni contesto nasce predefinito, quindi in pratica la domanda è «il soggetto ha almeno un contatto».
Resta escluso solo un soggetto i cui contatti hanno tutti perso il segno e non hanno recapiti.

---

### ⚠️ Che cosa oggi non copre

* **L'ultimo contatto cancellato.** Il controllo scatta sulle scritture del soggetto, non su quelle dei contatti:
  cancellare l'ultimo contatto passa, e il soggetto resta senza fino alla sua prossima modifica, che allora è
  rifiutata qualunque cosa cambi.
* **Il soggetto che si spegne.** La disattivazione è una modifica del soggetto, e la controlla anche questo
  trigger. I contatti, che non hanno un loro `attivo`, bloccano la disattivazione finché esistono; tolti tutti,
  la disattivazione non passa questo controllo. Un soggetto con contatti oggi non si disattiva.

---

### Codici errore

* `E_SOGGETTO_NO_CONTATTI` — al COMMIT, il soggetto scritto non ha un contatto predefinito né un contatto con un
  recapito.

---

### Test

Nessun test proprio. `db/pgtap/anagrafiche/soggetti-con-contatti.sql` prova che un soggetto costruito ha un
contatto con un recapito; `db/pgtap/anagrafiche/test-identita-tecnica.sql` e
`db/pgtap/script/test-fn-crea-utente-tecnico.sql` dichiarano differiti i vincoli, perché con i vincoli immediati
il soggetto che costruiscono è rifiutato prima che il suo contatto sia scritto.

---

{% include-markdown "signature-core.md" %}
