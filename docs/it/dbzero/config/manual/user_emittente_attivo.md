## 📘 Documentazione Concettuale – Tabella `config.user_emittente_attivo`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> • [storico.user_emittente_attivo](/dbzero/storico/tabelle/user_emittente_attivo)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

L'**emittente fiscale di lavoro** di un utente: quello che l'applicazione gli ripropone al
login.

---

### 🔴 È una PREFERENZA, non un PERMESSO

È la cosa da capire di questa tabella, e il nome non aiuta a capirla.

**Non concede accesso a nulla.** L'autorizzazione a operare su un emittente resta interamente
altrove:

* la whitelist `config.user_emittenti_fiscali`, e
* il profilo `SUPER_ADMIN`.

Scrivere qui un emittente su cui l'utente non è autorizzato **non gli dà alcun accesso**: gli
fa solo riproporre una scelta che le funzioni di scope rifiuteranno.

⚠️ Il corollario vale nel verso opposto ed è quello che conta per chi legge il codice: **non
si controlla il perimetro leggendo questa tabella.** Il perimetro della sessione viaggia sulla
GUC `app.current_emittente_id`, unica fonte letta dalle funzioni di scope.

---

### Storicizzata, e per una ragione

`storicizza = true` di default: `storico.user_emittente_attivo` è il **registro append-only
degli switch di emittente**.

Non è audit generico. Sapere *quando* un utente ha cambiato emittente di lavoro è ciò che
permette, a posteriori, di ricostruire in quale veste ha operato in un dato momento — la
domanda che ci si pone dopo, quando un documento risulta intestato a un emittente inatteso.

---

### ⚠️ L'immutabilità dell'associazione

`config.user_emittenti_fiscali` (la whitelist, non questa tabella) è protetta da un lock di
colonna dal 2026-08-18: l'`UPDATE` che sposterebbe l'associazione su un altro emittente è
vietato, perché otterrebbe lo stesso effetto di un `DELETE` che era già guardato. La porta di
dominio fa `DELETE` + `INSERT`, mai `UPDATE`.

Qui invece l'aggiornamento è l'operazione normale: cambiare emittente di lavoro è ciò per cui
la tabella esiste.

---

### Riferimenti

`brief-db-impersonazione-scope-emittente` §8.8 (2026-08-04).

---

{% include-markdown "signature-core.md" %}
