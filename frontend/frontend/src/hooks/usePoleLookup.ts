import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Pole } from "../types";

export interface PoleLookup {
  [poleId: string]: Pole;
}

/**
 * IMPORTANT: the current backend's IncidentResponse schema (see
 * app/schemas/incident_schema.py) does not include latitude/longitude/
 * pincode, even though the Incident DB model has those columns and
 * the localization service computes them. This is a known gap --
 * flagged in DECISIONS.md as something to fix by adding those three
 * fields to IncidentResponse.
 *
 * Until that's fixed, the console works around it here: it fetches
 * the pole registry once and resolves each incident's `end_pole` to
 * a lat/lon/pincode via this lookup. If the backend is later updated
 * to include coordinates directly on the incident, IncidentDetail and
 * MapView prefer those fields when present (see their `?? lookup[...]`
 * fallbacks) so this keeps working either way.
 */
export function usePoleLookup(): { lookup: PoleLookup; loading: boolean } {
  const [lookup, setLookup] = useState<PoleLookup>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        // 5000 comfortably covers the "a few thousand poles" scale
        // the assignment asks the simulator to generate.
        const poles = await api.getPoles({ limit: 5000 });
        if (cancelled) return;
        const map: PoleLookup = {};
        for (const pole of poles) map[pole.pole_id] = pole;
        setLookup(map);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    // Poles rarely move; refresh occasionally in case new poles are
    // seeded, but there's no need to do this on every 5s tick.
    const interval = window.setInterval(load, 60_000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  return { lookup, loading };
}
