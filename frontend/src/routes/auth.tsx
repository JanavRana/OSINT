import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Radar, ShieldCheck, ArrowRight, KeyRound } from "lucide-react";

export const Route = createFileRoute("/auth")({
  head: () => ({ meta: [{ title: "Sign in — AXIOM OSINT" }] }),
  component: Auth,
});

type Mode = "login" | "signup" | "forgot";

function Auth() {
  const nav = useNavigate();
  const [mode, setMode] = useState<Mode>("login");

  return (
    <div className="min-h-screen relative flex items-center justify-center px-4 overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 grid-bg opacity-40" />
      <div className="absolute -top-40 -left-40 h-[520px] w-[520px] rounded-full bg-primary/25 blur-[120px] float" />
      <div className="absolute -bottom-40 -right-40 h-[520px] w-[520px] rounded-full bg-accent/25 blur-[120px] float" />

      <div className="relative grid md:grid-cols-2 gap-8 max-w-5xl w-full">
        {/* Brand pane */}
        <div className="hidden md:flex flex-col justify-between p-8">
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 rounded-xl bg-gradient-to-br from-primary to-accent grid place-items-center shadow-[0_0_30px_-4px_var(--primary)]">
              <Radar className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <div className="font-display font-bold text-xl">AXIOM</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">OSINT Intelligence Aggregator</div>
            </div>
          </div>

          <div className="space-y-4">
            <h1 className="text-4xl font-display font-bold tracking-tight">
              Investigate <span className="gradient-text">at the speed of intent.</span>
            </h1>
            <p className="text-sm text-muted-foreground max-w-md">
              Unify emails, wallets, domains and social identifiers into a single graph.
              Purpose-built for cybercrime investigators and analysts.
            </p>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <ShieldCheck className="h-4 w-4 text-success" /> SOC 2 · TLP compliant · end-to-end encrypted
            </div>
          </div>

          <div className="text-xs text-muted-foreground">© AXIOM Intel · v3.2</div>
        </div>

        {/* Form pane */}
        <Card className="glass border-border/60 p-8 relative">
          <div className="md:hidden flex items-center gap-2 mb-6">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary to-accent grid place-items-center">
              <Radar className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-display font-bold">AXIOM</span>
          </div>

          <h2 className="text-2xl font-display font-semibold">
            {mode === "login" && "Welcome back"}
            {mode === "signup" && "Create your account"}
            {mode === "forgot" && "Reset password"}
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            {mode === "login" && "Sign in to continue your investigations."}
            {mode === "signup" && "Provision an analyst account with SSO or credentials."}
            {mode === "forgot" && "We'll send a secure recovery link to your email."}
          </p>

          <form
            className="mt-6 space-y-4"
            onSubmit={(e) => { e.preventDefault(); nav({ to: "/dashboard" }); }}
          >
            {mode === "signup" && (
              <div>
                <Label>Full name</Label>
                <Input placeholder="Mei Chen" className="mt-1.5 bg-surface/60" />
              </div>
            )}
            <div>
              <Label>Work email</Label>
              <Input type="email" placeholder="you@agency.gov" className="mt-1.5 bg-surface/60" />
            </div>
            {mode !== "forgot" && (
              <div>
                <div className="flex items-center justify-between">
                  <Label>Password</Label>
                  {mode === "login" && (
                    <button type="button" onClick={() => setMode("forgot")} className="text-xs text-primary hover:underline">
                      Forgot?
                    </button>
                  )}
                </div>
                <Input type="password" placeholder="••••••••" className="mt-1.5 bg-surface/60" />
              </div>
            )}

            <Button type="submit" className="w-full bg-gradient-to-r from-primary to-accent text-primary-foreground gap-2">
              {mode === "login" && <>Sign in <ArrowRight className="h-4 w-4" /></>}
              {mode === "signup" && <>Create account <ArrowRight className="h-4 w-4" /></>}
              {mode === "forgot" && <>Send reset link <KeyRound className="h-4 w-4" /></>}
            </Button>

            <div className="relative py-1">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-border/60" /></div>
              <div className="relative flex justify-center"><span className="bg-card px-3 text-[10px] uppercase tracking-widest text-muted-foreground">or</span></div>
            </div>

            <Button variant="secondary" type="button" className="w-full">Continue with SSO</Button>
          </form>

          <div className="mt-5 text-center text-xs text-muted-foreground">
            {mode === "login" && (<>Need an account? <button onClick={() => setMode("signup")} className="text-primary hover:underline">Sign up</button></>)}
            {mode === "signup" && (<>Have an account? <button onClick={() => setMode("login")} className="text-primary hover:underline">Sign in</button></>)}
            {mode === "forgot" && (<><button onClick={() => setMode("login")} className="text-primary hover:underline">Back to sign in</button></>)}
          </div>

          <div className="mt-6 text-center text-[10px] text-muted-foreground">
            By continuing you agree to the <Link to="/" className="underline">Terms</Link> and <Link to="/" className="underline">TLP handling policy</Link>.
          </div>
        </Card>
      </div>
    </div>
  );
}
