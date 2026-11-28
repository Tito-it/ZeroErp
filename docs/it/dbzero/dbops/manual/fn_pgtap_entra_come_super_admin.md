## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_entra_come_super_admin`

> **Ultimo aggiornamento**: 28 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_rimetti_contesto](/dbzero/dbops/funzioni/fn_pgtap_rimetti_contesto) — la gemella che chiude
> * [dbops.fn_pgtap_crea_operatore_umano](/dbzero/dbops/funzioni/fn_pgtap_crea_operatore_umano) — il SUPER_ADMIN di fixture
> * [dbops.fn_pgtap_sposta_scope_operatore](/dbzero/dbops/funzioni/fn_pgtap_sposta_scope_operatore) / [dbops.fn_pgtap_scrivi_profilo_accesso](/dbzero/dbops/funzioni/fn_pgtap_scrivi_profilo_accesso) / [dbops.fn_pgtap_lega_profilo_identita](/dbzero/dbops/funzioni/fn_pgtap_lega_profilo_identita) — i builder che la usano
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — i builder dell'accesso

---

### 🎯 Scopo Principale

In un pgTAP, entra nel contesto di un SUPER_ADMIN di fixture per chiamare un verbo che lo chiede. Il
SUPER_ADMIN lo crea la fixture, con `dbops.fn_pgtap_crea_operatore_umano(<etichetta>, true)`: il test non
dipende da un SUPER_ADMIN già presente sul database, che su un database da zero non c'è.

Scrive `app.current_user_id` e `app.ruolo_applicativo` per la sessione e restituisce il contesto di prima,
`{utente, ruolo}`, da passare a [fn_pgtap_rimetti_contesto](/dbzero/dbops/funzioni/fn_pgtap_rimetti_contesto).
`app.current_emittente_id` non si tocca.

### 🧭 Uso

```sql
v_prima := dbops.fn_pgtap_entra_come_super_admin('mio-test');
BEGIN
    -- il verbo
EXCEPTION WHEN OTHERS THEN
    PERFORM dbops.fn_pgtap_rimetti_contesto(v_prima);
    RAISE;
END;
PERFORM dbops.fn_pgtap_rimetti_contesto(v_prima);
```

Lo stampo è quello della coppia `fn_pgtap_apri_area_per_nascita` / `fn_pgtap_richiudi_area`.

---

### ⭐ Un SUPER_ADMIN per transazione

Il primo ingresso della transazione crea il SUPER_ADMIN; gli ingressi seguenti **lo riusano**. Ci passano
tutti i builder che scrivono le tabelle dell'accesso (`fn_pgtap_concedi_azione`, `fn_pgtap_concedi_livello_area`,
`fn_pgtap_scrivi_override`…) e, attraverso loro, i builder di documenti e di magazzino: con un SUPER_ADMIN a
ogni ingresso, un test che concede dieci permessi fabbricava dieci persone fisiche, ognuna con il suo codice
fiscale di fixture, ed esauriva i codici di [fn_pgtap_cf_libero](/dbzero/dbops/funzioni/fn_pgtap_cf_libero).

L'id sta nella GUC **locale** `dbops.pgtap_super_admin`. PostgreSQL la annulla da sola a fine transazione e a
ogni savepoint annullato, cioè proprio quando si annulla la riga del SUPER_ADMIN che nomina: la GUC non può
nominare un utente che in quella transazione non esiste.

* Prima di riusarlo, la fixture chiede a `script.fn_is_super_admin_account` se lo è ancora: un test che gli
  revoca il profilo, o lo spegne, riceve al giro dopo un SUPER_ADMIN nuovo e non uno falso.
* ⚠️ L'etichetta vale solo per il SUPER_ADMIN che si crea: un ingresso che lo riusa non cambia il cognome di
  quello creato prima.
* ⚠️ Non è una porta. La GUC la legge solo questa fixture, che non è `SECURITY DEFINER`, e l'id letto si
  verifica comunque come SUPER_ADMIN.
