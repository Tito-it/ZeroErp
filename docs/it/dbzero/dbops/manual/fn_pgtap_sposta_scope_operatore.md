## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_sposta_scope_operatore`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope) — il verbo che chiama
> * [dbops.fn_pgtap_crea_operatore_umano](/dbzero/dbops/funzioni/fn_pgtap_crea_operatore_umano) — il SUPER_ADMIN di fixture
> * [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore) — il contesto dei pgTAP
>
> Guide:
>
> * [pgTAP: come si scrive un test](/guide/pgtap-come-si-scrive-un-test)

---

### 🎯 Scopo Principale

Solo per i pgTAP. Porta un operatore su un'azienda (`p_emittente_fiscale_id`), o toglie l'azienda
(`NULL`) a un SUPER_ADMIN, passando dal verbo
[fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope). Restituisce
il risultato del verbo.

Serve ai test che spostano l'operatore di contesto in mezzo al file, per vedere che cosa cambia nel
suo perimetro. Dalla porta del `DELETE` non si passa a mano: si apre solo dal verbo.

```sql
PERFORM dbops.fn_pgtap_sposta_scope_operatore(
    (SELECT user_id FROM tmp_refs), (SELECT emittente_b FROM tmp_refs));
```

---

### Come lavora

Il verbo chiede il SUPER_ADMIN. Il builder entra nel contesto di un SUPER_ADMIN creato a ogni chiamata
([fn_pgtap_entra_come_super_admin](/dbzero/dbops/funzioni/fn_pgtap_entra_come_super_admin)), chiama il verbo e
rimette il contesto di prima ([fn_pgtap_rimetti_contesto](/dbzero/dbops/funzioni/fn_pgtap_rimetti_contesto):
`app.current_user_id`, `app.ruolo_applicativo`), anche in errore. `app.current_emittente_id` non lo tocca. Le
stesse due fixture le usano i builder del profilo e del legame.

Le regole sono quelle del verbo: l'ultimo SUPER_ADMIN attivo non si sposta, più di un'azienda no, e a un
operatore normale l'azienda non si toglie (`E_OPERATORE_SCOPE_GLOBALE_SOLO_SUPER_ADMIN`). Un rifiuto del verbo
arriva al test com'è.

⛔ **L'operatore senza azienda si costruisce, non si ottiene togliendogliela.** Un test che prova il fail-closed
prende un operatore che nasce senza azienda,
[fn_pgtap_crea_operatore_umano](/dbzero/dbops/funzioni/fn_pgtap_crea_operatore_umano)`(…, false)`: è lo stato di un
operatore appena creato. Il builder non ha una strada che aggiri il verbo.

È `SECURITY INVOKER`, come gli altri builder: gira come app e come owner.
