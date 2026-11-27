## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_entra_come_super_admin`

> **Ultimo aggiornamento**: 26 novembre 2026
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
SUPER_ADMIN si crea a ogni chiamata, con `dbops.fn_pgtap_crea_operatore_umano(<etichetta>, true)`: il test non
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
