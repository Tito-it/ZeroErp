## 📘 Documentazione Concettuale – Tabella `ui.lista_colonna_permesso`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — la colonna a cui il permesso si applica
> * [config.profili_accesso](/dbzero/config/tabelle/profili_accesso) — il profilo che riceve il permesso
>
> Approfondimento funzioni:
>
> * [ui.fn_lista_colonne_livello](/dbzero/ui/funzioni/fn_lista_colonne_livello) — la regola che legge questi permessi, sede unica
> * [script.fn_get_profili_accesso_applicabili](/dbzero/script/funzioni/fn_get_profili_accesso_applicabili) — i profili di un utente, con la loro priorità
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — i permessi di colonna raccontati a chi li imposta
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — i profili d'accesso

---

### 🎯 Scopo Principale

`ui.lista_colonna_permesso` dice, per una colonna di una lista e un profilo d'accesso, con quale
livello chi ha quel profilo vede la colonna: tutta, solo a video, o per niente. Serve a tenere
lontani da certi profili dati personali, margini, condizioni commerciali.

Non ha un sistema di profili suo: usa `config.profili_accesso`, gli stessi degli altri permessi.

---

### Tre livelli

* `TUTTO` — la colonna si vede e si esporta.
* `LETTURA` — la colonna si vede ma non si esporta: la configurazione della schermata le spegne
  l'export.
* `BLOCCATO` — la colonna non c'è: esce dalla configurazione della schermata e dalla ricerca libera.

---

### ⭐ Il verso lo decide la colonna

Una riga di permesso vale per la sua coppia colonna-profilo, e al più una per coppia
(`uq_ui_lista_colonna_permesso_col_profilo`). Che cosa succede senza riga lo dice `sensibile` della
colonna:

* colonna non sensibile: senza riga si vede tutto, e le righe scrivono le **restrizioni**;
* colonna sensibile: senza riga è bloccata, e le righe scrivono le **concessioni**.

---

### Con più profili vince il più specifico

Un utente può avere più profili che danno un permesso sulla stessa colonna. Vince il profilo più
specifico (AD_HOC sull'identità, poi REPARTO sull'unità organizzativa, poi PORTALE sulla veste), e a
parità il livello più restrittivo. La regola ha una sede sola,
[fn_lista_colonne_livello](/dbzero/ui/funzioni/fn_lista_colonne_livello), che la legge per la
configurazione della schermata e per la ricerca libera: le due risposte coincidono per costruzione.

L'azienda non entra: i permessi di colonna sono per profilo, non per emittente fiscale.

---

### Una riga di composizione, senza `attivo`

Il permesso è una parte della colonna, non un'entità col suo ciclo di vita: non ha `attivo`, si
toglie cancellando la riga, e se ne va con la colonna (FK con cascata). Non blocca lo spegnimento
della colonna né quello del profilo: spegnere un profilo è un gesto del suo dominio, e il permesso
di un profilo spento semplicemente non si applica, perché il risolutore dei profili non lo
restituisce.

---

### ⚠️ Che cosa oggi non copre

* **Nulla impedisce righe che non dicono niente**: `TUTTO` su una colonna non sensibile, o un
  permesso su un'azione.
* **Il `BLOCCATO` nasconde la colonna, non il dato.** La vista della lista porta il valore comunque:
  che il backend non lo esponga per altre strade (filtri, ordinamenti, export) è affar suo.

---

### Codici errore

Nessun trigger proprio. L'unicità della coppia e le due FK arrivano come violazione di vincolo, e il
backend le traduce per nome.

---

### Test

* `db/pgtap/ui/test-fn-lista-colonne-ricerca-full-v1.sql` — colonna sensibile con e senza permesso,
  `BLOCCATO`, `LETTURA`, il profilo più specifico che batte il più restrittivo, la veste letta dalla
  sessione.
* `db/pgtap/ui/test-fn-resolve-lista-config.sql` — i permessi nella configurazione della schermata.

---

### Note di migrazione

* 2026-05-06 — nasce la tabella.
* 2026-09-23 — la regola del livello passa dal risolutore della configurazione a
  `fn_lista_colonne_livello`, condivisa con la ricerca libera.
* 2026-11-08 — il permesso diventa una riga di composizione per la regola ATTIVO: non blocca più lo
  spegnimento della colonna né del profilo.

---

{% include-markdown "signature-core.md" %}
