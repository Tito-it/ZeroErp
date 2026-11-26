## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_rimetti_contesto`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_entra_come_super_admin](/dbzero/dbops/funzioni/fn_pgtap_entra_come_super_admin) — la gemella che apre
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — i builder dell'accesso

---

### 🎯 Scopo Principale

In un pgTAP, rimette il contesto che
[fn_pgtap_entra_come_super_admin](/dbzero/dbops/funzioni/fn_pgtap_entra_come_super_admin) ha restituito:
`app.current_user_id` e `app.ruolo_applicativo` tornano com'erano, anche vuoti. Un argomento `NULL` solleva: il
builder che lo passa ha perso il contesto di prima.
