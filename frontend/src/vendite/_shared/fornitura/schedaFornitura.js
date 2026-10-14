// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LA SCHEDA DI FORNITURA nel form di contratto e offerta: i campi del
//        form, da dove si riempiono (il dettaglio, i form-defaults del cliente)
//        e cosa parte verso il backend.
// Note: regola del 2 (brief-db-indirizzi-documento-seguono-il-cliente, R-FE-3):
//       i due drawer tenevano ciascuno la sua copia della scheda, gia'
//       divergenti — l'offerta mostrava i due parametri, il contratto no, e
//       in modifica il contratto non li spediva affatto.
// ------------------------------------------------------------

// Scopo: i campi della scheda nel form, vuoti. Si spalmano in `defaultForm()`.
export function schedaVuota() {
  return {
    utility_istanza_dati_precontrattuali_id: null,
    utility_tipo_utenza_id: null,
    utility_classe_utenza_id: null,
    utility_param_1_num: null,
    utility_param_2_txt: null,
  }
}

// Scopo: i campi del form da una scheda del backend — quella salvata sul
//        documento (`detail.utility`) o quella che l'anagrafica da' al cliente
//        (`fornitura` dei form-defaults). `null` = scheda vuota.
// ⚠️ `param_1_num` arriva come testo (Decimal del backend): l'InputNumber
//    vuole un numero.
export function schedaDaFornitura(s) {
  if (!s) return schedaVuota()
  return {
    utility_istanza_dati_precontrattuali_id: s.istanza_dati_precontrattuali_id ?? null,
    utility_tipo_utenza_id: s.tipo_utenza_id ?? null,
    utility_classe_utenza_id: s.classe_utenza_id ?? null,
    utility_param_1_num: s.param_1_num != null && s.param_1_num !== '' ? Number(s.param_1_num) : null,
    utility_param_2_txt: s.param_2_txt ?? null,
  }
}

// Scopo: il callback `apply` di `useBaFormDefaults` (solo in CREAZIONE): la
//        scheda segue il cliente scelto. Con D-7 di Tid l'operatore vede i dati
//        dell'anagrafica e li corregge; un cliente senza dati precontrattuali
//        svuota la scheda, perche' quella del cliente di prima non e' sua.
// ⚠️ Un backend che non porta `fornitura` non tocca il form.
export function applicaFornituraDaDefaults(data, f) {
  if (!data || !('fornitura' in data)) return
  Object.assign(f, schedaDaFornitura(data.fornitura))
}

// Scopo: il sotto-oggetto `utility` della richiesta, dai campi del form. Senza
//        la coppia (istanza, utility): e' quella della testata, e in modifica
//        il backend del contratto la rifiuta.
export function schedaDaForm(f) {
  return {
    istanza_dati_precontrattuali_id: f.utility_istanza_dati_precontrattuali_id || null,
    tipo_utenza_id: f.utility_tipo_utenza_id || null,
    classe_utenza_id: f.utility_classe_utenza_id || null,
    param_1_num: f.utility_param_1_num != null && f.utility_param_1_num !== ''
      ? String(f.utility_param_1_num) : null,
    param_2_txt: f.utility_param_2_txt || null,
  }
}
