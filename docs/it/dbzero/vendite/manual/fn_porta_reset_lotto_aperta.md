## 📘 Documentazione Concettuale – Funzione `vendite.fn_porta_reset_lotto_aperta`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella) — la seconda condizione: chi scrive è il proprietario della tabella
> * [vendite.fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids) — l'unica che accende la GUC, e la spegne prima di uscire
> * [vendite.trgfn_attivita_fatturabili_guard_fatturato](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_guard_fatturato) — chiamante: l'attività già in fattura
> * [vendite.trgfn_attivita_fatturabili_guard_quantita_immutabile](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_guard_quantita_immutabile) — chiamante: la quantità dell'attività fatturabile
> * [vendite.trgfn_commesse_attivita_guard_quantita_immutabile](/dbzero/vendite/funzioni/trgfn_commesse_attivita_guard_quantita_immutabile) — chiamante: la quantità della riga di commessa emessa
> * [vendite.trgfn_commesse_guard_chiave_immutabile](/dbzero/vendite/funzioni/trgfn_commesse_guard_chiave_immutabile) — chiamante: le condizioni di pagamento della commessa
> * [vendite.trgfn_fattura_satellite_guard_congelamento](/dbzero/vendite/funzioni/trgfn_fattura_satellite_guard_congelamento) — chiamante: i satelliti della fattura
> * [vendite.trgfn_fatturazione_lotti_guard_stato](/dbzero/vendite/funzioni/trgfn_fatturazione_lotti_guard_stato) — chiamante: lo stato del lotto
> * [vendite.trgfn_logs_guard_delete](/dbzero/vendite/funzioni/trgfn_logs_guard_delete) — chiamante: i log della fattura e del lotto
>
> Guide:
>
> * [Fatturazione](/guide/fatturazione) — il reset del lotto, chi lo può fare e dove si apre la porta
> * [Architettura permessi](/guide/architettura-permessi-e-autorizzazioni) §7.4 — le porte: la GUC e il proprietario

---

### 🎯 Scopo Principale

Risponde a una domanda sola: **la porta del reset del lotto è aperta per chi sta scrivendo su
questa tabella?** La leggono le sette funzioni di trigger che la pulizia di un lotto attraversa.

---

### La regola

La porta è aperta solo se valgono **tutte e due** le condizioni:

* la GUC `zeroerp.maintenance_reset_lotto_draft` è accesa: `on`, `true` o `1`. Assente, vuota o
  con qualunque altro valore, è spenta;
* chi scrive è il **proprietario** della tabella che il trigger giudica
  ([`script.fn_is_proprietario_tabella`](/dbzero/script/funzioni/fn_is_proprietario_tabella)).
  La tabella la passa il trigger.

⭐ **Per l'applicazione la porta è sempre chiusa.** L'app che accende la GUC da sé e scrive diretta
su una delle tabelle del reset viene rifiutata, come se la GUC non ci fosse.

---

### Chi la apre, e per quanto

La GUC la accende una funzione sola,
[`vendite.fn_cleanup_fatture_by_ids`](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids): prima
della pulizia la accende, prima di uscire la spegne. La pulizia è riservata al proprietario (l'app
non la può eseguire), e la chiamano solo i verbi del reset del lotto, che girano come proprietario
e controllano permesso e perimetro all'ingresso.

Così la porta resta aperta **solo mentre la pulizia lavora**. Le scritture che i verbi fanno dopo,
come lo stato del lotto, le giudicano di nuovo i guard.

⚠️ **La GUC è un interruttore, non l'id di una riga.** Le altre porte di verbo portano nella GUC la
chiave della riga che aprono. Questa no, ed è un'eccezione voluta: le sette funzioni stanno su dodici
tabelle, e ognuna dovrebbe risalire dalla sua riga al lotto per una strada diversa. Qui il limite lo
danno il proprietario e la durata: la porta la apre solo il proprietario, dentro una funzione
riservata, e si richiude prima che il verbo vada avanti.

---

### Perché una funzione sola

Prima ognuna delle sette funzioni di trigger leggeva la GUC da sé, e le copie avevano già cominciato
a dire cose diverse (alcune accettavano anche `yes`). Una lettura sola tiene uguali i sette punti, e
il controllo del proprietario si aggiunge in un posto solo.

`SECURITY INVOKER`: deve vedere chi scrive davvero. Una funzione che girasse come proprietario
risponderebbe sempre «è il proprietario».

---

### Test

* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — gira come l'applicazione: la GUC la
  legge solo questa funzione e la accende solo la pulizia; con la GUC accesa dall'app la porta
  risponde no, e una riga viva del log del lotto non si cancella; dopo il verbo la GUC è vuota.

---

### Note di migrazione

* 2026-11-25 — nasce e prende il posto delle sette letture copiate nelle funzioni di trigger. Prima
  bastava la GUC, e la pulizia non la spegneva: restava accesa fino alla fine della transazione
  (brief-db-porte-aperte-dalla-sola-guc, giro 8 + 1-7, D-W a).

---

{% include-markdown "signature-core.md" %}
