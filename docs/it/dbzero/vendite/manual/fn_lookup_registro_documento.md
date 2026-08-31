## 📘 Documentazione Concettuale – Funzione `vendite.fn_lookup_registro_documento`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[vendite.fn_get_registro_documento](/dbzero/vendite/manual/fn_get_registro_documento)
> • [vendite.fn_lookup_registro_id](/dbzero/vendite/funzioni/fn_lookup_registro_id)
>
Approfondimenti tabelle:
>
[vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
> • [vendite.famiglie_documento](/dbzero/vendite/manual/famiglie_documento)

---
### 🎯 Scopo Principale
(latest review 31-08-2026)

**Cerca** il registro su cui un certo tipo di documento si numera per un certo
emittente, e se non lo trova risponde **una riga vuota**. Non è un errore: è la
risposta.

⭐ Risponde *sempre* una riga, anche quando è tutta vuota, ed è voluto: così chi
la chiama distingue «ho cercato e non c'è» da «non ho cercato».

---

### Il lettore e chi pretende

Questa è la metà che **legge**. Serve a chi ha bisogno di *sapere*: una lista che
mostra la configurazione, un controllo che verifica se un emittente è pronto, una
maschera che anticipa cosa succederà.

Chi invece sta **scrivendo un documento** non usa questa: usa la funzione che
pretende, che di fronte a un registro mancante ferma. La differenza è il motivo
per cui sono due e non una — una funzione sola che ora tace e ora blocca
costringe chi la chiama a ricordarsi ogni volta quale delle due cose farà.

---

### Come sceglie, quando ce n'è più d'uno

Un emittente può avere più registri per lo stesso tipo di documento, tipicamente
perché uno è **specifico di una utility** e l'altro vale per tutto il resto. In
quel caso vince il più **specifico**: se si chiede il registro passando una
utility e ne esiste uno dedicato, si prende quello; altrimenti si ricade su
quello generale.

⛔ **Sull'emittente non c'è nessuna ricaduta**, e questa è la riga che conta. Il
registro «di nessuno» — quello senza emittente — non esiste più dal 30 agosto
2026, e riaprirlo qui rimetterebbe due partite IVA a pescare dalla stessa serie
di numeri: nessuna delle due avrebbe più una propria progressione, e nessun
errore lo direbbe.

⚠️ Solo i registri **attivi** entrano nella scelta: spegnere un registro è il modo
di ritirarlo, e un registro spento non deve tornare a numerare per una ricaduta.

---

### Impatto e Vantaggi

* si può chiedere «questo emittente è configurato per i documenti di trasporto?»
  senza rischiare di far esplodere qualcosa;
* la regola di priorità fra registro di utility e registro generale è **scritta
  una volta sola**, e chi pretende il registro la eredita invece di ricopiarla.
