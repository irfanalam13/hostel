"use client";

import React, { useEffect, useState } from "react";
import { Button, EmptyState, Input, Modal, Select, Table, Textarea, useToast, useConfirm } from "@hostel/ui";
import { Plus, RotateCcw, Trash2 } from "lucide-react";
import { Badge, Tabs } from "@/features/platform/components/primitives";
import { securityApi } from "../api/security.api";
import type {
  IPRule,
  KillSwitchTarget,
  SecurityEvent,
  SecuritySetting,
  SecuritySummary,
  TopOffender,
} from "../types/security.types";

const KILL_TARGETS: { target: KillSwitchTarget; label: string; blurb: string }[] = [
  { target: "rate_limiter", label: "Rate limiter", blurb: "Stops throttling every request platform-wide." },
  { target: "auth", label: "Auth guard", blurb: "Disables login-attempt protection platform-wide." },
  { target: "waf", label: "WAF", blurb: "Disables the web-application firewall." },
  { target: "bots", label: "Bot detection", blurb: "Disables automated bot/crawler blocking." },
  { target: "maintenance", label: "Maintenance mode", blurb: "Puts the whole platform into DR maintenance mode." },
  { target: "emergency", label: "Emergency mode", blurb: "Puts the whole platform into DR emergency mode — most severe." },
];

export function SecurityConsole() {
  const toast = useToast();
  const confirm = useConfirm();
  const [tab, setTab] = useState("overview");
  const [summary, setSummary] = useState<SecuritySummary | null>(null);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [offenders, setOffenders] = useState<TopOffender[]>([]);
  const [ipRules, setIpRules] = useState<IPRule[]>([]);
  const [settings, setSettings] = useState<SecuritySetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const [ruleModal, setRuleModal] = useState(false);
  const [ruleDraft, setRuleDraft] = useState<Partial<IPRule>>({ action: "deny", active: true });

  const [settingModal, setSettingModal] = useState(false);
  const [settingDraft, setSettingDraft] = useState<{ key: string; value: string; note: string }>({
    key: "",
    value: "",
    note: "",
  });

  const loadAll = async () => {
    setLoading(true);
    try {
      const [s, e, o, rules, cfg] = await Promise.all([
        securityApi.summary(),
        securityApi.events({ limit: 50 }),
        securityApi.offenders(),
        securityApi.ipRules.list(),
        securityApi.settings.list(),
      ]);
      setSummary(s);
      setEvents(e.results);
      setOffenders(o.offenders);
      setIpRules(rules);
      setSettings(cfg);
    } catch (e) {
      toast.error((e as Error).message, "Failed to load security console");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const createRule = async () => {
    if (!ruleDraft.cidr) return;
    setBusy(true);
    try {
      await securityApi.ipRules.create(ruleDraft);
      toast.success("IP rule created.");
      setRuleModal(false);
      setRuleDraft({ action: "deny", active: true });
      setIpRules(await securityApi.ipRules.list());
    } catch (e) {
      toast.error((e as Error).message, "Create failed");
    } finally {
      setBusy(false);
    }
  };

  const removeRule = async (rule: IPRule) => {
    const yes = await confirm({ message: `Remove IP rule ${rule.cidr}?`, danger: true, confirmText: "Remove" });
    if (!yes) return;
    try {
      await securityApi.ipRules.remove(rule.id);
      setIpRules(await securityApi.ipRules.list());
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const createSetting = async () => {
    if (!settingDraft.key) return;
    setBusy(true);
    try {
      let value: unknown = settingDraft.value;
      try {
        value = JSON.parse(settingDraft.value);
      } catch {
        // plain string value is fine
      }
      await securityApi.settings.create({ key: settingDraft.key, value, note: settingDraft.note, active: true });
      toast.success("Setting saved.");
      setSettingModal(false);
      setSettingDraft({ key: "", value: "", note: "" });
      setSettings(await securityApi.settings.list());
    } catch (e) {
      toast.error((e as Error).message, "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const removeSetting = async (setting: SecuritySetting) => {
    const yes = await confirm({ message: `Remove setting "${setting.key}"?`, danger: true, confirmText: "Remove" });
    if (!yes) return;
    try {
      await securityApi.settings.remove(setting.id);
      setSettings(await securityApi.settings.list());
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const fireKillSwitch = async (target: KillSwitchTarget, label: string, blurb: string, engage: boolean) => {
    const yes = await confirm({
      title: engage ? `Engage: ${label}` : `Restore: ${label}`,
      message: engage
        ? `${blurb} This takes effect immediately platform-wide, for every tenant. Are you sure?`
        : `Restore ${label} to its normal, protected state?`,
      danger: engage,
      confirmText: engage ? "Engage kill switch" : "Restore",
    });
    if (!yes) return;
    setBusy(true);
    try {
      const reason = window.prompt("Reason for this change (recorded in the audit log):") || "";
      const r = await securityApi.killSwitch(target, engage, reason);
      toast.success(r.detail);
      await loadAll();
    } catch (e) {
      toast.error((e as Error).message, "Kill switch action failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <Tabs
        tabs={[
          { id: "overview", label: "Overview" },
          { id: "events", label: "Events", count: events.length },
          { id: "ip-rules", label: "IP Rules", count: ipRules.length },
          { id: "settings", label: "Settings", count: settings.length },
          { id: "kill-switch", label: "Kill Switch" },
        ]}
        active={tab}
        onChange={setTab}
      />

      {loading ? <div className="text-sm text-[var(--muted)]">Loading…</div> : null}

      {!loading && tab === "overview" && summary ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Threat level" value={summary.threat_level} />
            <StatCard label="Total events (24h)" value={String(summary.total_events)} />
            <StatCard label="Blocked" value={String(summary.blocked_events)} />
            <StatCard label="Threat events" value={String(summary.threat_events)} />
          </div>
          <div className="rounded-xl border border-[var(--border)] p-4">
            <div className="mb-2 text-sm font-medium text-[var(--foreground)]">Posture</div>
            <div className="flex flex-wrap gap-2">
              <Badge tone={summary.posture.enabled ? "success" : "neutral"} color={summary.posture.enabled ? "var(--success)" : undefined}>
                {summary.posture.enabled ? "Protection enabled" : "Protection disabled"}
              </Badge>
              <Badge>{summary.posture.mode || "mode unknown"}</Badge>
              <Badge>WAF: {summary.posture.waf_mode || "—"}</Badge>
              <Badge>Bots: {summary.posture.bots_mode || "—"}</Badge>
              {summary.posture.kill.rate_limiter ? <Badge color="var(--error)">Rate limiter killed</Badge> : null}
              {summary.posture.kill.auth ? <Badge color="var(--error)">Auth guard killed</Badge> : null}
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-[var(--border)] p-4">
              <div className="mb-2 text-sm font-medium text-[var(--foreground)]">Top offending IPs</div>
              {offenders.length === 0 ? (
                <div className="text-xs text-[var(--muted)]">No blocked events in this window.</div>
              ) : (
                <ul className="space-y-1 text-sm">
                  {offenders.map((o) => (
                    <li key={o.ip} className="flex justify-between">
                      <span className="text-[var(--foreground-secondary)]">{o.ip}</span>
                      <span className="text-[var(--muted)]">{o.blocked} blocked</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="rounded-xl border border-[var(--border)] p-4">
              <div className="mb-2 text-sm font-medium text-[var(--foreground)]">Top paths</div>
              <ul className="space-y-1 text-sm">
                {summary.top_paths.map((p) => (
                  <li key={p.path} className="flex justify-between">
                    <span className="truncate text-[var(--foreground-secondary)]">{p.path}</span>
                    <span className="text-[var(--muted)]">{p.count}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      ) : null}

      {!loading && tab === "events" ? (
        events.length === 0 ? (
          <EmptyState title="No security events" description="Nothing recorded in the current window." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                <th className="px-4 py-3 font-medium">Time</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Action</th>
                <th className="px-4 py-3 font-medium">IP</th>
                <th className="px-4 py-3 font-medium">Path</th>
                <th className="px-4 py-3 font-medium">Score</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-4 py-2.5 text-[var(--muted)]">{new Date(e.created_at).toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-[var(--foreground)]">{e.event_type}</td>
                  <td className="px-4 py-2.5">
                    <Badge color={e.action === "blocked" ? "var(--error)" : undefined}>{e.action}</Badge>
                  </td>
                  <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{e.ip}</td>
                  <td className="px-4 py-2.5 text-[var(--foreground-secondary)] truncate max-w-xs">{e.path}</td>
                  <td className="px-4 py-2.5 text-[var(--muted)]">{e.threat_score}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        )
      ) : null}

      {!loading && tab === "ip-rules" ? (
        <div className="space-y-3">
          <div className="flex justify-end">
            <Button size="sm" onClick={() => setRuleModal(true)}>
              <Plus className="h-4 w-4" /> New rule
            </Button>
          </div>
          {ipRules.length === 0 ? (
            <EmptyState title="No IP rules" description="Add an allow, deny or trust rule." />
          ) : (
            <Table>
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                  <th className="px-4 py-3 font-medium">CIDR</th>
                  <th className="px-4 py-3 font-medium">Action</th>
                  <th className="px-4 py-3 font-medium">Active</th>
                  <th className="px-4 py-3 font-medium">Expires</th>
                  <th className="px-4 py-3 font-medium">Note</th>
                  <th className="px-4 py-3 font-medium text-right"></th>
                </tr>
              </thead>
              <tbody>
                {ipRules.map((r) => (
                  <tr key={r.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-4 py-2.5 font-mono text-xs text-[var(--foreground)]">{r.cidr}</td>
                    <td className="px-4 py-2.5">
                      <Badge color={r.action === "deny" ? "var(--error)" : r.action === "trust" ? "var(--success)" : undefined}>
                        {r.action}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5">{r.active ? "Yes" : "No"}</td>
                    <td className="px-4 py-2.5 text-[var(--muted)]">
                      {r.expires_at ? new Date(r.expires_at).toLocaleDateString() : "Never"}
                    </td>
                    <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{r.note}</td>
                    <td className="px-4 py-2.5 text-right">
                      <Button variant="ghost" size="sm" onClick={() => removeRule(r)}>
                        <Trash2 className="h-4 w-4 text-[var(--error)]" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </div>
      ) : null}

      {!loading && tab === "settings" ? (
        <div className="space-y-3">
          <div className="flex justify-end">
            <Button size="sm" onClick={() => setSettingModal(true)}>
              <Plus className="h-4 w-4" /> New setting
            </Button>
          </div>
          {settings.length === 0 ? (
            <EmptyState title="No config overrides" description="Every value falls back to its default." />
          ) : (
            <Table>
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                  <th className="px-4 py-3 font-medium">Key</th>
                  <th className="px-4 py-3 font-medium">Value</th>
                  <th className="px-4 py-3 font-medium">Active</th>
                  <th className="px-4 py-3 font-medium">Note</th>
                  <th className="px-4 py-3 font-medium text-right"></th>
                </tr>
              </thead>
              <tbody>
                {settings.map((s) => (
                  <tr key={s.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-4 py-2.5 font-mono text-xs text-[var(--foreground)]">{s.key}</td>
                    <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{JSON.stringify(s.value)}</td>
                    <td className="px-4 py-2.5">{s.active ? "Yes" : "No"}</td>
                    <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{s.note}</td>
                    <td className="px-4 py-2.5 text-right">
                      <Button variant="ghost" size="sm" onClick={() => removeSetting(s)}>
                        <Trash2 className="h-4 w-4 text-[var(--error)]" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </div>
      ) : null}

      {tab === "kill-switch" ? (
        <div className="space-y-3">
          <div className="rounded-lg border border-[var(--warning)] bg-[color-mix(in_srgb,var(--warning)_10%,transparent)] p-3 text-sm text-[var(--foreground)]">
            These controls act immediately, platform-wide, for every tenant. Every action is recorded in the audit log.
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {KILL_TARGETS.map((k) => {
              const engaged =
                k.target === "rate_limiter"
                  ? summary?.posture.kill.rate_limiter
                  : k.target === "auth"
                    ? summary?.posture.kill.auth
                    : undefined;
              return (
                <div key={k.target} className="rounded-xl border border-[var(--border)] p-4">
                  <div className="flex items-center justify-between">
                    <div className="font-medium text-[var(--foreground)]">{k.label}</div>
                    {engaged ? <Badge color="var(--error)">Engaged</Badge> : null}
                  </div>
                  <p className="mt-1 text-xs text-[var(--muted)]">{k.blurb}</p>
                  <div className="mt-3 flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={busy}
                      onClick={() => fireKillSwitch(k.target, k.label, k.blurb, true)}
                    >
                      Engage
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={busy}
                      onClick={() => fireKillSwitch(k.target, k.label, k.blurb, false)}
                    >
                      <RotateCcw className="h-4 w-4" /> Restore
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      <Modal open={ruleModal} title="New IP rule" onClose={() => setRuleModal(false)}>
        <div className="space-y-3">
          <Input
            label="CIDR"
            placeholder="e.g. 203.0.113.4/32"
            value={ruleDraft.cidr || ""}
            onChange={(e) => setRuleDraft((d) => ({ ...d, cidr: e.target.value }))}
          />
          <Select
            label="Action"
            value={ruleDraft.action || "deny"}
            onChange={(e) => setRuleDraft((d) => ({ ...d, action: e.target.value as IPRule["action"] }))}
            options={[
              { value: "deny", label: "Deny" },
              { value: "allow", label: "Allow" },
              { value: "trust", label: "Trust" },
            ]}
          />
          <Input
            label="Expires at (optional)"
            type="date"
            value={ruleDraft.expires_at || ""}
            onChange={(e) => setRuleDraft((d) => ({ ...d, expires_at: e.target.value }))}
          />
          <Textarea
            placeholder="Note (optional)"
            value={ruleDraft.note || ""}
            onChange={(e) => setRuleDraft((d) => ({ ...d, note: e.target.value }))}
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setRuleModal(false)}>Cancel</Button>
            <Button loading={busy} onClick={createRule} disabled={!ruleDraft.cidr}>Create rule</Button>
          </div>
        </div>
      </Modal>

      <Modal open={settingModal} title="New security setting" onClose={() => setSettingModal(false)}>
        <div className="space-y-3">
          <Input
            label="Key"
            placeholder="e.g. waf.mode"
            value={settingDraft.key}
            onChange={(e) => setSettingDraft((d) => ({ ...d, key: e.target.value }))}
          />
          <Input
            label="Value (JSON or plain text)"
            placeholder='e.g. true, 42, "block"'
            value={settingDraft.value}
            onChange={(e) => setSettingDraft((d) => ({ ...d, value: e.target.value }))}
          />
          <Textarea
            placeholder="Note (optional)"
            value={settingDraft.note}
            onChange={(e) => setSettingDraft((d) => ({ ...d, note: e.target.value }))}
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setSettingModal(false)}>Cancel</Button>
            <Button loading={busy} onClick={createSetting} disabled={!settingDraft.key}>Save setting</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--border)] p-4">
      <div className="text-xs text-[var(--muted)]">{label}</div>
      <div className="mt-1 text-lg font-semibold text-[var(--foreground)]">{value}</div>
    </div>
  );
}
