## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_indirizzo_libero_forma()`

> 👀 **Vedi anche**
>
[anagrafiche.trgfn_indirizzi_guard_forma_libera](/dbzero/anagrafiche/manual/trgfn_indirizzi_guard_forma_libera)
>
**Guide:**
>
[Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test)

---
### 🎯 Scopo Principale
(18-10-2026)

**Helper delle fixture pgTAP**: per uno stato, una riga con `comune_id`,
`codice_postale_id`, `locality`, `postal_code` nella forma che il guard dell'indirizzo libero
pretende:

* stato col catalogo completo (l'Italia): il primo comune dello stato che ha un CAP, e quel
  CAP (ordine per id: sempre lo stesso; il catalogo dei comuni c'è anche su un database
  ricostruito da zero);
* altrimenti: `locality = 'Localita pgTAP'`, `postal_code = '00000'`.

Uso tipico in una fixture:

* in un `INSERT … SELECT`: `CROSS JOIN dbops.fn_pgtap_indirizzo_libero_forma(<stato>) f`, poi
  `f.comune_id, f.codice_postale_id, f.locality, f.postal_code`;
* in un payload jsonb: `|| (SELECT jsonb_strip_nulls(to_jsonb(f)) FROM dbops.fn_pgtap_indirizzo_libero_forma(<stato>) f)`.

---

### Perché esiste

Fino al 18-10-2026 le fixture scrivevano indirizzi italiani nella forma estera (Roma,
`00100`, `RM`), che il CHECK di allora ammetteva e il guard di oggi no. Ogni fixture che si
inventa i campi tiene una copia della regola; l'helper la legge dal flag dello stato, come il
guard. Lo usano `dbops.fn_pgtap_crea_soggetto_ruolo`, `dbops.fn_pgtap_crea_soggetto_pg` e le
fixture di una ventina di pgTAP.

---

{% include-markdown "signature-core.md" %}
