## 📘 Documentazione Concettuale – Funzione `dbops.fn_grant_storico_shadows`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove finiscono il riepilogo e i grant senza effetto
>
> Approfondimento funzioni:
>
> * [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic) — il marcatore delle madri, e chi scrive nella shadow coi privilegi di chi scrive la madre
> * [dbops.fn_storico_arma_scope](/dbzero/dbops/funzioni/fn_storico_arma_scope) — la stessa forma di convergenza, per colonne e policy; e chi toglie il `DELETE`
> * [dbops.fn_ensure_storico_table](/dbzero/dbops/funzioni/fn_ensure_storico_table) — chi crea le shadow e le cede al proprietario della madre
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — le shadow e chi le possiede

---

### 🎯 Scopo Principale

Allinea i privilegi delle shadow `storico.*` a quelli della loro madre: a ogni ruolo che sulla
madre può inserire o aggiornare concede lettura, inserimento e aggiornamento sulla shadow. I
privilegi si **derivano** dalla madre, non si elencano.

Serve perché il trigger di storico è `SECURITY INVOKER`: scrive nella shadow come il ruolo che sta
aggiornando la madre. Senza questi privilegi non si perde solo lo storico, fallisce l'aggiornamento
della madre.

---

### ⭐ Nessun nome scritto da nessuna parte

Le coppie madre e shadow si trovano dal catalogo: una tabella di `storico` con lo stesso nome di
una tabella che porta il trigger su `script.trgfn_storico_generic`. Il marcatore è il trigger:
una tabella che esce dalla storicizzazione esce da qui da sola, una shadow nuova è coperta senza
che nessuno se ne ricordi. I privilegi della madre si leggono dalle sue ACL, quindi valgono per
qualunque ruolo, non solo per quello connesso.

Non si concede niente al proprietario della shadow, che ha già tutto, né ai superuser.

---

### ⛔ Mai il `DELETE`

La regola non è «copia i privilegi della madre»: sulla madre un ruolo può avere anche il `DELETE`,
sulla shadow mai. Uno snapshot non si cancella: è una regola di dominio, e la stessa che
`fn_storico_arma_scope` applica togliendo il `DELETE` all'applicazione.

---

### ⚠️ Si verifica l'esito di ogni grant

Un grant lo dà il proprietario. Quando chi concede non è proprietario della shadow, PostgreSQL non
solleva un errore: emette un avviso e prosegue senza concedere niente. Per questo la funzione,
dopo ogni grant, **rilegge** i privilegi del ruolo sulla shadow:

* se ci sono, il grant conta come fatto;
* se non ci sono, scrive un `WARN` nell'audit con shadow e ruolo e prosegue: non ferma il migrate.
  A concedere sarà il provisioning, che gira da superuser.

---

### Idempotente e forward-only

Non revoca mai niente, e sulle coppie in cui il ruolo ha già i tre privilegi non scrive e non
registra niente: la passata normale è muta. Se ha concesso o saltato qualcosa scrive un riepilogo
nell'audit con i due conteggi. In simulazione non concede niente e conta i grant che farebbe.

La chiama un changeSet di `90_end` a ogni migrate.

---

### Test

Nessun pgTAP la chiama né verifica che i ruoli che scrivono una madre possano scrivere la sua
shadow. Il divieto del `DELETE` lo presidia, per l'applicazione, il test 22 di
`db/pgtap/storico/test-storico-scope-congelato-v1.sql`.

---

### Note di migrazione

* 2026-09-02 — nasce per dare alle shadow i privilegi dei ruoli che scrivono la madre, derivandoli
  invece di elencarli. Allora le shadow appartenevano a chi aveva eseguito l'automazione, e i grant
  su quelle di un altro proprietario restavano senza effetto.
* 2026-09-11 — il generatore cede ogni shadow nuova al proprietario della madre: i grant senza
  effetto restano per le shadow create da un altro ruolo prima di allora.
* 2026-10-15 — si ritira il ruolo batch di fatturazione, e con lui il pgTAP della sua postura, che
  verificava anche il divieto del `DELETE` sulle shadow.

---

{% include-markdown "signature-core.md" %}
