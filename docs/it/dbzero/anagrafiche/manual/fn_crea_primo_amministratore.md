## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_primo_amministratore`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings) — i legami ai profili: la condizione che apre il verbo li legge
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — la veste OPERATORE, che qui nasce accesa
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_operatore](/dbzero/anagrafiche/funzioni/fn_crea_operatore) — credenziale, persona, rapporto, veste e legame SUPER_ADMIN
> * [anagrafiche.fn_crea_indirizzi_operatore](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_operatore) — residenza e domicilio fiscale
> * [anagrafiche.fn_accendi_veste](/dbzero/anagrafiche/funzioni/fn_accendi_veste) — accende la veste senza invito
> * [script.fn_check_almeno_un_super_admin_attivo](/dbzero/script/funzioni/fn_check_almeno_un_super_admin_attivo) — la garanzia dell'ultimo SUPER_ADMIN, che il verbo non sostituisce
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — il primo amministratore di un'installazione nuova
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — il verbo senza guard di permesso
> * [Resta sempre almeno un SUPER_ADMIN che non scade](/dbzero/anagrafiche/_ultimo-super-admin) — come si esce da un sistema scoperto

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_primo_amministratore` crea il primo SUPER_ADMIN di un'installazione nuova, e lo fa entrare
subito: una persona privata nuova, il suo rapporto con la qualifica AMMINISTRATORE, la credenziale, la veste
OPERATORE **accesa** e il legame al profilo SUPER_ADMIN. Restituisce la credenziale, il suo username effettivo e se è
stata riusata.

Gli altri amministratori li crea un SUPER_ADMIN, con l'invito. Il primo no, perché non c'è ancora nessuno: questa
funzione è la sua strada. La chiama il comando del backend che si lancia una volta, dopo l'installazione.

---

### ⛔ Si apre solo su un'installazione nuova

La funzione parte solo se **nessuna veste ha un legame verso un profilo SUPER_ADMIN, acceso o spento**. Altrimenti si
ferma con `E_PRIMO_AMMINISTRATORE_GIA_PRESENTE`, e non scrive niente.

La condizione guarda se un amministratore **c'è mai stato**, non se oggi ce n'è uno che entra. Un sistema che ha
avuto un amministratore e lo ha perso (spento, scaduto, con la credenziale bloccata) non si riapre da qui: il
recupero lo fa chi gestisce il database, con le scritture che migliorano la garanzia dell'ultimo SUPER_ADMIN, che
passano sempre. Così la funzione non diventa una porta che si riapre proprio quando la garanzia si è rotta.

Prima di leggere la condizione la funzione blocca la tabella dei legami: due chiamate contemporanee si mettono in
fila, e la seconda vede il legame della prima. Lo stesso blocco ferma, per quell'attimo, la nascita di un legame da
qualunque altra strada.

---

### ⭐ Senza guard di permesso, ed è voluto

La funzione gira come proprietario del database e la può chiamare l'applicazione, ma non chiede nessun permesso:
nessuna persona è ancora autenticata, e non c'è nessuno che possa averne uno. Al posto del guard c'è la condizione:
è l'unica cosa che la chiude.

Per lo stesso motivo le colonne d'audit delle righe che nascono portano il proprietario del database, non una persona.

---

### Che cosa compone

* `anagrafiche.fn_crea_operatore`, col soggetto nuovo (flusso A) e il SUPER_ADMIN: la credenziale, la persona
  privata, il rapporto, la veste spenta e il legame. Valgono tutti i suoi rifiuti; in particolare una credenziale che
  ha già quell'email si riusa solo col consenso (`p_riusa_auth_user_id` dev'essere la credenziale trovata), e la
  password passata allora è ignorata.
* `anagrafiche.fn_crea_indirizzi_operatore`, con la residenza e, se c'è, il domicilio fiscale: ognuno un oggetto nella
  forma di `anagrafiche.fn_crea_indirizzo_soggetto` (indirizzo libero, dettaglio già risolto o via da risolvere),
  **senza** il tipo. Il domicilio fiscale che manca è la residenza.
* `anagrafiche.fn_accendi_veste`: la veste si accende subito, perché non c'è nessuno che possa invitare il primo.

La qualifica si cerca per `codice_interno` AMMINISTRATORE, non per id. Il primo amministratore non ha bisogno di
nessuna azienda: un SUPER_ADMIN vede tutti gli emittenti, e su un'installazione nuova non ce n'è ancora nessuno.

Quali indirizzi siano obbligatori lo dice la configurazione dei tipi d'indirizzo, coi guard del soggetto che
scattano alla chiusura della transazione: la funzione non lo ricopia. Riceve l'hash della password calcolato da
Django: il database non lo calcola.

---

### Tutto o niente

La funzione è una sola istruzione: se un passo fallisce, compreso un guard che scatta alla chiusura della
transazione, non nasce niente.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_PRIMO_AMMINISTRATORE_GIA_PRESENTE` | una veste ha già un legame verso un profilo SUPER_ADMIN, acceso o spento |
| `E_CODICE` | la qualifica AMMINISTRATORE manca o è spenta |

Più quelli di `fn_crea_operatore` (fra gli altri `E_CREDENZIALE_DA_CONFERMARE`, `E_ADMIN_CF_DUPLICATO`,
`E_SESSO_OBBLIGATORIO`), di `fn_crea_indirizzi_operatore` e `fn_crea_indirizzo_soggetto`, e dei guard del soggetto
sugli indirizzi obbligatori.

---

### Test

* `db/pgtap/anagrafiche/test-crea-primo-amministratore-v1.sql` — la postura (proprietario, eseguibile dall'app); sul
  vuoto, costruito spegnendo i guard dell'ultimo SUPER_ADMIN nella transazione, nasce un amministratore che entra
  (veste accesa, SUPER_ADMIN senza scadenza, tutti gli emittenti, privato con la qualifica AMMINISTRATORE, i due
  indirizzi); il rifiuto alla seconda chiamata e con soli legami spenti, senza che nasca niente; il riuso di una
  credenziale, senza e col consenso.
* Non provata, perché in una sessione sola non si può: la concorrenza di due chiamate. La presidia il blocco sulla
  tabella dei legami.

---

### Note di migrazione

* 2026-11-25 — nasce: il primo SUPER_ADMIN di un'installazione nuova.

---

{% include-markdown "signature-core.md" %}
